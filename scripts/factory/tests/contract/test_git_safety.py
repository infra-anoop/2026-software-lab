"""PR-A2 — order commands are ref-only: the caller's checkout is never touched.

Event commits go to origin through plumbing. The caller's HEAD, index, worktree and a
checked-out order branch stay exactly as they were, and a rejected push changes no
local ref. Behaviour recorded in `bus/orders/wo-20261004-factory-slice-a/amendment-04.yaml`.
"""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import pytest

from factory.cli import exit_codes
from tests.fixtures.cli_runner import FactoryCli
from tests.fixtures.repo_builder import RepoBuilder, message, order

pytestmark = pytest.mark.contract

DAY = "20261007"
MODEL = "claude-opus-5.5"


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


def _caller_state(repo: RepoBuilder) -> CallerState:
    return CallerState(
        head=repo.head_sha(),
        local_refs=repo.git("for-each-ref", "--format=%(refname) %(objectname)", "refs/heads"),
        index=repo.git("ls-files", "--stage"),
        worktree=_worktree(repo.path),
        status=repo.git("status", "--porcelain=v1", "--untracked-files=all"),
    )


def _issue(repo: RepoBuilder, slug: str) -> str:
    order_id = oid(slug)
    repo.issue_order(order(order_id, owned_paths=[f"apps/demo/{order_id}/**"]))
    return order_id


def _on_origin(repo: RepoBuilder, order_id: str) -> list[str]:
    return repo.git("ls-tree", "-r", "--name-only", f"origin/wo/{order_id}").splitlines()


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


def test_handoff_push_rejection_leaves_local_refs_and_worktree_unchanged(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    order_id = _issue(repo, "rejected-push")
    repo.add_event(order_id, message("claim", order_id=order_id))
    repo.checkout(f"wo/{order_id}")
    repo.write_message(message("handoff", order_id=order_id))
    repo.commit("handoff")
    repo.push()
    tip = repo.head_sha()
    elsewhere = repo.git(
        "commit-tree", repo.git("rev-parse", f"{tip}^{{tree}}"), "-p", tip, "-m", "elsewhere"
    )
    repo.git("push", "-q", "origin", f"{elsewhere}:refs/heads/wo/{order_id}")
    before = _caller_state(repo)

    result = factory_cli("handoff", order_id, repo=repo.path)

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
