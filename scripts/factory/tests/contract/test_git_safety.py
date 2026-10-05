"""PR-A2 — order commands are ref-only: the caller's checkout is never touched.

Event commits go to origin through plumbing. The caller's HEAD, index, worktree and a
checked-out order branch stay exactly as they were, and a rejected push changes no
local ref. Behaviour recorded in `bus/orders/wo-20261004-factory-slice-a/amendment-04.yaml`.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import NamedTuple

import pytest

from factory.cli import exit_codes
from tests.contract.push_barrier import WAIT_SECONDS, PushBarrier, origin_sha
from tests.fixtures.cli_runner import CliResult, FactoryCli
from tests.fixtures.repo_builder import RepoBuilder, message, order, yaml_text

pytestmark = pytest.mark.contract

DAY = "20261007"
MODEL = "claude-opus-5.5"
COMMAND_TIMEOUT = 2 * WAIT_SECONDS


def oid(slug: str) -> str:
    return f"wo-{DAY}-{slug}"


class CallerState(NamedTuple):
    head: str
    local_refs: str
    index: str
    worktree: dict[str, bytes]
    status: str


def _worktree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


def _caller_state(repo: RepoBuilder, work: Path | None = None) -> CallerState:
    """HEAD, index, files and status of `work` (default: the caller's checkout)."""
    work = work or repo.path

    def git(*args: str) -> str:
        return repo.git("-C", str(work), *args)

    return CallerState(
        head=git("rev-parse", "HEAD"),
        local_refs=git("for-each-ref", "--format=%(refname) %(objectname)", "refs/heads"),
        index=git("ls-files", "--stage"),
        worktree=_worktree(work),
        status=git("status", "--porcelain=v1", "--untracked-files=all"),
    )


def _issue(repo: RepoBuilder, slug: str) -> str:
    order_id = oid(slug)
    repo.issue_order(order(order_id, owned_paths=[f"apps/demo/{order_id}/**"]))
    return order_id


def _on_origin(repo: RepoBuilder, order_id: str) -> list[str]:
    return _origin_git(repo, "ls-tree", "-r", "--name-only", f"refs/heads/wo/{order_id}").split()


def _origin_git(repo: RepoBuilder, *args: str) -> str:
    """Run git in the bare origin directly (authoritative, independent of the caller's fetches)."""
    identity = ["-c", "user.name=Elsewhere", "-c", "user.email=elsewhere@example.test"]
    return subprocess.run(
        ["git", *identity, "--git-dir", str(repo.origin), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _handoff_ready(repo: RepoBuilder, slug: str) -> str:
    """Claimed order with a committed, pushed handoff; `wo/<id>` is checked out."""
    order_id = _issue(repo, slug)
    repo.add_event(order_id, message("claim", order_id=order_id))
    repo.checkout(f"wo/{order_id}")
    repo.write_message(message("handoff", order_id=order_id))
    repo.commit("handoff")
    repo.push()
    return order_id


def _verdict_ready(repo: RepoBuilder, slug: str) -> tuple[str, Path]:
    """Handed-off order and a valid different-family verdict file; `wo/<id>` is checked out."""
    order_id = _issue(repo, slug)
    for kind in ("claim", "handoff", "run_complete"):
        repo.add_event(order_id, message(kind, order_id=order_id))
    head = repo.head_sha(f"wo/{order_id}")
    verdict = message(
        "verdict",
        order_id=order_id,
        actor_model="gpt-5.6-sol",
        reviewer_model="gpt-5.6-sol",
        reviewer_family="openai",
        inputs=[{"path": f"bus/orders/{order_id}/order.yaml", "sha": head}],
    )
    path = repo.root / "verdict.yaml"
    path.write_text(yaml_text(verdict), encoding="utf-8")
    repo.checkout(f"wo/{order_id}")
    return order_id, path


def _assert_told_to_pull(result: CliResult) -> None:
    assert "git pull --ff-only" in result.stdout + result.stderr, (
        "the caller is told origin is ahead and how to pick the event up:\n"
        f"{result.stdout}\n{result.stderr}"
    )


def test_claim_leaves_a_dirty_index_and_worktree_untouched(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    order_id = _issue(repo, "dirty-checkout")
    repo.checkout(f"wo/{order_id}")
    repo.write("README.md", "# fixture repo\nunstaged edit\n")
    repo.write("scratch/staged.txt", "staged, not committed\n")
    repo.git("add", "scratch/staged.txt")
    before = _caller_state(repo)

    result = factory_cli("claim", order_id, "--actor-model", MODEL, repo=repo.path)

    assert result.exit_code == exit_codes.OK, (
        f"expected exit 0, got {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )
    assert f"bus/orders/{order_id}/claim.yaml" in _on_origin(repo, order_id)
    after = _caller_state(repo)
    assert after.index == before.index, "claim must not touch the caller's index"
    assert after.worktree == before.worktree, "claim must not touch the caller's worktree"
    assert after.status == before.status
    assert after.head == before.head


EVENT_ARGS = {
    "claim": ["--actor-model", MODEL],
    "release": ["--reason", "abandoned"],
}


@pytest.mark.parametrize("command", list(EVENT_ARGS))
def test_event_commands_leave_a_checked_out_order_branch_where_it_was(
    repo: RepoBuilder, factory_cli: FactoryCli, command: str
) -> None:
    order_id = _issue(repo, f"checked-out-{command}")
    if command == "release":
        repo.add_event(order_id, message("claim", order_id=order_id))
    repo.checkout(f"wo/{order_id}")
    before = _caller_state(repo)

    result = factory_cli(command, order_id, *EVENT_ARGS[command], repo=repo.path)

    assert result.exit_code == exit_codes.OK, (
        f"expected exit 0, got {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )
    assert f"bus/orders/{order_id}/{command}.yaml" in _on_origin(repo, order_id)
    after = _caller_state(repo)
    assert after.local_refs == before.local_refs, (
        f"wo/{order_id} is checked out, so {command} must leave it where it was"
    )
    assert after.head == before.head
    assert after.index == before.index
    assert after.worktree == before.worktree
    assert "git pull --ff-only" in result.stdout + result.stderr, (
        "the caller is told origin is ahead and how to pick the event up:\n"
        f"{result.stdout}\n{result.stderr}"
    )


@pytest.mark.parametrize("command", ["handoff", "verdict"])
def test_handoff_and_verdict_leave_a_checked_out_order_branch_where_it_was(
    repo: RepoBuilder, factory_cli: FactoryCli, command: str
) -> None:
    if command == "handoff":
        order_id = _handoff_ready(repo, "checked-out-handoff")
        args: list[str] = []
        event = "run-complete.yaml"
    else:
        order_id, path = _verdict_ready(repo, "checked-out-verdict")
        args = ["--file", str(path)]
        event = "verdict-01.yaml"
    before = _caller_state(repo)

    result = factory_cli(command, order_id, *args, repo=repo.path)

    assert result.exit_code == exit_codes.OK, (
        f"expected exit 0, got {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )
    assert f"bus/orders/{order_id}/{event}" in _on_origin(repo, order_id)
    after = _caller_state(repo)
    assert after.local_refs == before.local_refs, (
        f"wo/{order_id} is checked out, so {command} must leave it where it was"
    )
    assert after.head == before.head
    assert after.index == before.index
    assert after.worktree == before.worktree
    assert after.status == before.status
    _assert_told_to_pull(result)


def test_claim_leaves_an_order_branch_checked_out_in_another_worktree_alone(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    order_id = _issue(repo, "linked-worktree")
    linked = repo.root / "linked"
    repo.git("worktree", "add", "-q", str(linked), f"wo/{order_id}")
    caller_before = _caller_state(repo)
    linked_before = _caller_state(repo, linked)

    result = factory_cli("claim", order_id, "--actor-model", MODEL, repo=repo.path)

    assert result.exit_code == exit_codes.OK, (
        f"expected exit 0, got {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )
    assert f"bus/orders/{order_id}/claim.yaml" in _on_origin(repo, order_id)
    linked_after = _caller_state(repo, linked)
    assert linked_after.local_refs == linked_before.local_refs, (
        f"wo/{order_id} is checked out in a linked worktree, so it must not move"
    )
    assert linked_after.head == linked_before.head
    assert linked_after.index == linked_before.index
    assert linked_after.worktree == linked_before.worktree
    assert linked_after.status == linked_before.status
    assert _caller_state(repo) == caller_before
    _assert_told_to_pull(result)


def test_claim_fast_forwards_an_order_branch_that_is_not_checked_out(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    order_id = _issue(repo, "not-checked-out")
    branch = f"wo/{order_id}"
    old = repo.head_sha(f"refs/heads/{branch}")
    before = _caller_state(repo)

    result = factory_cli("claim", order_id, "--actor-model", MODEL, repo=repo.path)

    assert result.exit_code == exit_codes.OK, (
        f"expected exit 0, got {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )
    pushed = origin_sha(repo.origin, branch)
    assert _origin_git(repo, "rev-parse", f"{pushed}^") == old, "the claim is one commit on wo/<id>"
    assert repo.head_sha(f"refs/heads/{branch}") == pushed, (
        f"{branch} is not checked out anywhere, so it is fast-forwarded to the pushed claim"
    )
    after = _caller_state(repo)
    assert after.head == before.head
    assert after.index == before.index
    assert after.worktree == before.worktree
    assert after.status == before.status


def _claim_while_held(
    repo: RepoBuilder, factory_cli: FactoryCli, order_id: str, hook: Callable[[], None]
) -> CliResult:
    """Run `claim`; `hook()` runs once the claim is built and its push is held at origin."""
    barrier = PushBarrier(repo.root / "push-barrier")
    barrier.install(repo.path, 1)
    with ThreadPoolExecutor(max_workers=1) as pool, barrier:
        pending = pool.submit(
            factory_cli, "claim", order_id, "--actor-model", MODEL, repo=repo.path
        )
        barrier.wait_arrived(1, commands=[pending])
        hook()
        barrier.release(1)
        return pending.result(timeout=COMMAND_TIMEOUT)


@pytest.mark.parametrize("when", ["before-command", "during-push"])
def test_claim_leaves_a_diverged_local_order_branch_alone(
    repo: RepoBuilder, factory_cli: FactoryCli, when: str
) -> None:
    """A local `wo/<id>` that is not an ancestor of the pushed claim is never moved.

    `during-push` makes the local branch diverge after the claim is built, while its push
    is held at origin, so an advance that does not compare-and-swap would overwrite it.
    """
    order_id = _issue(repo, f"diverged-{when}")
    branch = f"wo/{order_id}"
    base = repo.head_sha(f"refs/heads/{branch}")
    local_only = repo.git("commit-tree", f"{base}^{{tree}}", "-p", base, "-m", "unpushed work")

    def diverge() -> None:
        repo.git("update-ref", f"refs/heads/{branch}", local_only, base)

    if when == "before-command":
        diverge()
        result = factory_cli("claim", order_id, "--actor-model", MODEL, repo=repo.path)
    else:
        result = _claim_while_held(repo, factory_cli, order_id, diverge)

    assert result.exit_code == exit_codes.OK, (
        f"expected exit 0 (origin took the claim), got {result.exit_code}\n"
        f"{result.stdout}\n{result.stderr}"
    )
    pushed = origin_sha(repo.origin, branch)
    assert _origin_git(repo, "rev-parse", f"{pushed}^") == base, "the claim builds on origin"
    assert repo.head_sha(f"refs/heads/{branch}") == local_only, (
        f"local {branch} diverged from origin, so it is left where it was"
    )
    _assert_told_to_pull(result)


def test_handoff_push_rejection_leaves_local_refs_and_worktree_unchanged(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    """Origin moves after handoff has built run-complete and while its push is held at origin.

    An initial fetch sees origin unchanged, so only the push itself can be rejected. The
    moved commit exists only on origin, so git rejects the push client-side (fetch first).
    """
    order_id = _handoff_ready(repo, "rejected-push")
    branch = f"wo/{order_id}"
    barrier = PushBarrier(repo.root / "push-barrier")
    barrier.install(repo.path, 1)
    before = _caller_state(repo)
    moved: list[str] = []

    def move_origin() -> None:
        tip = origin_sha(repo.origin, branch)
        elsewhere = _origin_git(repo, "commit-tree", f"{tip}^{{tree}}", "-p", tip, "-m", "moved")
        _origin_git(repo, "update-ref", f"refs/heads/{branch}", elsewhere, tip)
        moved.append(elsewhere)

    with ThreadPoolExecutor(max_workers=1) as pool, barrier:
        pending = pool.submit(factory_cli, "handoff", order_id, repo=repo.path)
        barrier.wait_arrived(1, commands=[pending])
        move_origin()
        barrier.release(1)
        result = pending.result(timeout=COMMAND_TIMEOUT)

    assert barrier.advertised(1).get(f"refs/heads/{branch}") == moved[0], (
        "the push met the moved origin"
    )
    assert origin_sha(repo.origin, branch) == moved[0], "the rejected event did not land"
    after = _caller_state(repo)
    assert after.local_refs == before.local_refs, (
        "a rejected push must leave every local branch where it was"
    )
    assert after.head == before.head
    assert after.index == before.index
    assert after.worktree == before.worktree
    assert not (repo.path / f"bus/orders/{order_id}/run-complete.yaml").exists()
    assert result.exit_code == exit_codes.REFUSED, (
        f"expected exit 2 (origin moved), got {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )
