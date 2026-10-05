"""T027 — claim is an atomic fast-forward under cap 3.

Catalog: `handoff.concurrency_cap` (claim half).
"""

from __future__ import annotations

import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import NamedTuple

import pytest

from factory.cli import exit_codes
from factory.cli.app import run
from factory.cli.common import DEPS
from tests.contract.push_barrier import WAIT_SECONDS, PushBarrier, has_object, origin_sha
from tests.fixtures.cli_runner import FactoryCli
from tests.fixtures.repo_builder import RepoBuilder, message, order

pytestmark = pytest.mark.contract

DAY = "20261007"
OPEN_DECISION = "pick-host"
RACE_TIMEOUT = 2 * WAIT_SECONDS


def oid(slug: str) -> str:
    return f"wo-{DAY}-{slug}"


def _issue(repo: RepoBuilder, slug: str, **fields: object) -> str:
    order_id = oid(slug)
    fields.setdefault("owned_paths", [f"apps/demo/{order_id}/**"])
    repo.issue_order(order(order_id, **fields))
    return order_id


def test_claim_fast_forward_exactly_one_of_two_concurrent_wins(repo: RepoBuilder) -> None:
    order_id = _issue(repo, "race")
    second = repo.root / "work-b"
    shutil.copytree(repo.path, second, symlinks=True)
    # Second clone must share origin so both FF-push the same ref.
    subprocess.run(
        ["git", "-C", str(second), "remote", "set-url", "origin", str(repo.origin)],
        check=True,
        capture_output=True,
    )

    def claim(work: Path) -> int:
        return run(
            [
                "claim",
                order_id,
                "--actor-model",
                "claude-opus-5.5",
                "--repo",
                str(work),
            ]
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(claim, repo.path)
        other = pool.submit(claim, second)
        codes = [first.result(), other.result()]
    assert codes.count(exit_codes.OK) == 1, codes
    assert codes.count(exit_codes.REFUSED) == 1, f"a lost claim race is a refusal (2): {codes}"
    claim_files = repo.git("ls-tree", "-r", "--name-only", f"origin/wo/{order_id}")
    assert f"bus/orders/{order_id}/claim.yaml" in claim_files


def test_claim_refuses_at_active_cap_of_three(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    for n in range(3):
        active = _issue(repo, f"active-{n}")
        repo.add_event(active, message("claim", order_id=active))
    fourth = _issue(repo, "fourth")
    result = factory_cli("claim", fourth, "--actor-model", "claude-opus-5.5", repo=repo.path)
    assert result.exit_code == exit_codes.REFUSED, (
        f"expected exit 2, got {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )
    assert "3" in result.stdout or "3" in result.stderr


def test_stale_claim_still_counts_toward_cap(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    for n in range(2):
        fresh = _issue(repo, f"fresh-{n}")
        repo.add_event(fresh, message("claim", order_id=fresh))
    claimed_at = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    stale = oid("stale")
    repo.issue_order(
        order(stale, owned_paths=[f"apps/demo/{stale}/**"], size_minutes=10),
        when=claimed_at - timedelta(minutes=5),
    )
    repo.add_event(
        stale,
        message("claim", order_id=stale, claimed_at=claimed_at.isoformat().replace("+00:00", "Z")),
        when=claimed_at,
    )
    fourth = _issue(repo, "fourth-after-stale")
    before = repo.head_sha(f"origin/wo/{fourth}")
    result = factory_cli("claim", fourth, "--actor-model", "claude-opus-5.5", repo=repo.path)
    assert result.exit_code == exit_codes.REFUSED, (
        f"a stale claim must still hold a slot: exit {result.exit_code}\n"
        f"{result.stdout}\n{result.stderr}"
    )
    assert "3" in result.stdout or "3" in result.stderr
    assert repo.head_sha(f"origin/wo/{fourth}") == before, "refused claim must push nothing"


def test_release_frees_capacity(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    held: list[str] = []
    for n in range(3):
        active = _issue(repo, f"held-{n}")
        repo.add_event(active, message("claim", order_id=active))
        held.append(active)
    factory_cli("release", held[0], "--reason", "abandoned", repo=repo.path)
    waiting = _issue(repo, "after-release")
    result = factory_cli("claim", waiting, "--actor-model", "claude-opus-5.5", repo=repo.path)
    assert result.exit_code == exit_codes.OK, (
        f"expected exit 0 after release, got {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )


def test_claim_refuses_owned_path_overlap(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    holder = _issue(repo, "holder", owned_paths=["apps/demo/**"])
    repo.add_event(holder, message("claim", order_id=holder))
    overlap = _issue(repo, "overlap", owned_paths=["apps/demo/app/calc.py"])
    result = factory_cli("claim", overlap, "--actor-model", "claude-opus-5.5", repo=repo.path)
    assert result.exit_code == exit_codes.REFUSED


def test_claim_refuses_blocked_on_governor(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    repo.checkout("main")
    repo.write_message(message("decision_request", decision_id=OPEN_DECISION, blocking=True))
    repo.commit("decision")
    repo.push("main")
    waiting = _issue(repo, "waiting", depends_on_decisions=[OPEN_DECISION])
    result = factory_cli("claim", waiting, "--actor-model", "claude-opus-5.5", repo=repo.path)
    assert result.exit_code == exit_codes.REFUSED


def test_claim_refuses_already_claimed(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    taken = _issue(repo, "taken")
    repo.add_event(taken, message("claim", order_id=taken))
    result = factory_cli("claim", taken, "--actor-model", "claude-opus-5.5", repo=repo.path)
    assert result.exit_code == exit_codes.REFUSED


def _hold_three(repo: RepoBuilder, prefix: str) -> list[str]:
    held: list[str] = []
    for n in range(3):
        active = _issue(repo, f"{prefix}-{n}")
        repo.add_event(active, message("claim", order_id=active))
        held.append(active)
    return held


def test_closed_unmerged_pr_frees_capacity(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    held = _hold_three(repo, "pr-held")
    abandoned = repo.make_pr(f"wo/{held[0]}")
    repo.github.close_pr(abandoned.number)
    waiting = _issue(repo, "after-closed-pr")
    result = factory_cli("claim", waiting, "--actor-model", "claude-opus-5.5", repo=repo.path)
    assert result.exit_code == exit_codes.OK, (
        "a PR closed without merging releases its order (data-model § Lifecycle), so its"
        f" slot is free: exit {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )
    claim_files = repo.git("ls-tree", "-r", "--name-only", f"origin/wo/{waiting}")
    assert f"bus/orders/{waiting}/claim.yaml" in claim_files


def test_open_pr_still_holds_a_slot(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    held = _hold_three(repo, "pr-open")
    repo.make_pr(f"wo/{held[0]}")
    waiting = _issue(repo, "behind-open-pr")
    before = repo.head_sha(f"origin/wo/{waiting}")
    result = factory_cli("claim", waiting, "--actor-model", "claude-opus-5.5", repo=repo.path)
    assert result.exit_code == exit_codes.REFUSED, (
        f"an order in review is active: exit {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )
    assert repo.head_sha(f"origin/wo/{waiting}") == before, "refused claim must push nothing"


class HeldRace(NamedTuple):
    codes: list[int]
    base: str
    winner: str
    loser_had_winner: bool
    advertised_to_loser: str | None


def _held_race(repo: RepoBuilder, order_id: str, models: tuple[str, str]) -> HeldRace:
    """Two claims of `order_id`; both pushes are held at origin until both claimers arrive.

    Claimer 1 (`repo.path`) is released first and must exit before claimer 2 (a copy of the
    clone) is released. `loser_had_winner` is read between the two releases, while claimer 2
    is still blocked in its push and cannot have fetched.
    """
    branch = f"wo/{order_id}"
    second = repo.root / "work-b"
    shutil.copytree(repo.path, second, symlinks=True)
    subprocess.run(
        ["git", "-C", str(second), "remote", "set-url", "origin", str(repo.origin)],
        check=True,
        capture_output=True,
    )
    barrier = PushBarrier(repo.root / "push-barrier")
    barrier.install(repo.path, 1)
    barrier.install(second, 2)
    base = origin_sha(repo.origin, branch)

    def claim(work: Path, model: str) -> int:
        return run(["claim", order_id, "--actor-model", model, "--repo", str(work)])

    with ThreadPoolExecutor(max_workers=2) as pool, barrier:
        first = pool.submit(claim, repo.path, models[0])
        other = pool.submit(claim, second, models[1])
        barrier.wait_arrived(1, 2, commands=[first, other])
        barrier.release(1)
        first_code = first.result(timeout=RACE_TIMEOUT)
        winner = origin_sha(repo.origin, branch)
        loser_had_winner = has_object(second, winner)
        barrier.release(2)
        other_code = other.result(timeout=RACE_TIMEOUT)
    return HeldRace(
        codes=[first_code, other_code],
        base=base,
        winner=winner,
        loser_had_winner=loser_had_winner,
        advertised_to_loser=barrier.advertised(2).get(f"refs/heads/{branch}"),
    )


def test_lost_claim_race_at_the_push_is_refused(repo: RepoBuilder) -> None:
    """PR-A7: a claim that loses the race at its own push exits 2, not 4.

    `_held_race` holds both pushes at origin until both claimers have fetched (no claim yet)
    and built their claim, then releases claimer 1, then claimer 2. The claimers use different
    models, so their commits differ and claimer 2 has never seen claimer 1's. Receive-pack
    advertises claimer 1's commit to claimer 2, which git cannot verify as a fast-forward and
    rejects client-side (`[rejected] (fetch first)`, reported on `--porcelain` stdout).
    """
    order_id = _issue(repo, "push-race")
    race = _held_race(repo, order_id, ("claude-opus-5.5", "gpt-5.6-sol"))
    assert race.winner != race.base, f"claimer 1's push did not land: {race.codes}"
    assert race.advertised_to_loser == race.winner, "claimer 2 is shown claimer 1's claim"
    assert not race.loser_had_winner, (
        "claimer 2 must not hold claimer 1's commit, so git rejects its push (fetch first)"
    )
    assert race.codes == [exit_codes.OK, exit_codes.REFUSED], (
        f"claimer 1 wins (0); claimer 2 lost the race at the push and is refused (2): {race.codes}"
    )
    repo.git("fetch", "-q", "origin")
    claim_text = repo.git("show", f"origin/wo/{order_id}:bus/orders/{order_id}/claim.yaml")
    assert "actor_model: claude-opus-5.5" in claim_text, claim_text


def test_identical_same_second_claims_have_one_winner(
    repo: RepoBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PR-A8: a push that finds origin already at our commit lost the race (exit 2, not 0).

    Clock, git commit dates and actor are pinned, so both claimers build byte-identical claim
    commits on the same tip. `_held_race` holds both pushes at origin until both are built,
    then lets claimer 1's land before claimer 2's receive-pack starts. Receive-pack advertises
    claimer 1's commit, which is claimer 2's own commit, so claimer 2's push reports
    `=` / `[up to date]`.
    """
    order_id = _issue(repo, "same-second")
    pinned = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(DEPS, "clock", lambda: pinned)
    for name in ("GIT_AUTHOR_DATE", "GIT_COMMITTER_DATE"):
        monkeypatch.setenv(name, "2026-10-07T12:00:00+0000")

    race = _held_race(repo, order_id, ("claude-opus-5.5", "claude-opus-5.5"))
    assert race.winner != race.base, f"claimer 1's push did not land: {race.codes}"
    assert race.loser_had_winner, "claimer 2 built the very commit claimer 1 pushed"
    assert race.advertised_to_loser == race.winner, (
        "claimer 2 is shown its own commit, so its push is `[up to date]`"
    )
    assert race.codes == [exit_codes.OK, exit_codes.REFUSED], (
        f"identical claims: claimer 1 wins (0) and claimer 2 is refused (2): {race.codes}"
    )
    repo.git("fetch", "-q", "origin")
    claims = repo.git(
        "log", "--format=%H", f"origin/wo/{order_id}", "--", f"bus/orders/{order_id}/claim.yaml"
    ).splitlines()
    assert len(claims) == 1, f"only one claim lands on origin/wo/{order_id}: {claims}"
