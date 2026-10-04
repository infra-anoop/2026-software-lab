"""T027 — claim is an atomic fast-forward under cap 3.

Catalog: `handoff.concurrency_cap` (claim half).
"""

from __future__ import annotations

import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from factory.cli import exit_codes
from factory.cli.app import run
from tests.fixtures.cli_runner import FactoryCli
from tests.fixtures.repo_builder import RepoBuilder, message, order

pytestmark = pytest.mark.contract

DAY = "20261007"
OPEN_DECISION = "pick-host"


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
    assert codes.count(exit_codes.REFUSED) + codes.count(exit_codes.EXTERNAL) == 1, codes
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
