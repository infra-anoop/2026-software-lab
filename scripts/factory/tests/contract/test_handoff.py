"""T028 — `factory handoff` requires green gates, deviations, and a run-complete event.

Catalog: `handoff.done_requires_green`.
"""

from __future__ import annotations

import json

import pytest

from factory.cli import exit_codes
from tests.fixtures.cli_runner import FactoryCli
from tests.fixtures.repo_builder import RepoBuilder, message, order

pytestmark = pytest.mark.contract

DAY = "20261007"


def oid(slug: str) -> str:
    return f"wo-{DAY}-{slug}"


def _claimed(repo: RepoBuilder, slug: str, extra_files: dict[str, str] | None = None) -> str:
    order_id = oid(slug)
    repo.add_demo_feature()
    repo.issue_order(
        order(order_id, owned_paths=["apps/demo/app/calc.py"], checks=["diff-within-owned-paths"])
    )
    repo.add_event(order_id, message("claim", order_id=order_id))
    files = {"apps/demo/app/calc.py": "def add(a, b):\n    return a + b\n"}
    if extra_files:
        files.update(extra_files)
    start = repo.current_branch()
    repo.checkout(f"wo/{order_id}")
    for relative, text in files.items():
        repo.write(relative, text)
    repo.commit("work")
    repo.push()
    repo.checkout(start)
    return order_id


def test_handoff_refuses_while_a_registered_gate_fails(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    order_id = _claimed(
        repo,
        "outside",
        extra_files={"deploy/railway/demo.toml": "[deploy]\n"},
    )
    repo.checkout(f"wo/{order_id}")
    result = factory_cli("handoff", order_id, repo=repo.path)
    assert result.exit_code == exit_codes.REFUSED, (
        f"expected exit 2, got {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )


def test_handoff_requires_deviations_key(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    order_id = _claimed(repo, "nodev")
    repo.checkout(f"wo/{order_id}")
    repo.write(
        f"bus/orders/{order_id}/handoff.yaml",
        "schema_version: 1\nkind: handoff\n"
        f"id: {order_id}.handoff\ncreated: 2026-10-07T16:00:00Z\n"
        "actor: worker\nactor_model: claude-opus-5.5\n"
        "summary: Work landed.\nchecks_run: []\n"
        "open_questions: []\nauthor_model: claude-opus-5.5\n"
        f"refs: [{order_id}]\n",
    )
    repo.commit("handoff without deviations", allow_empty=True)
    result = factory_cli("handoff", order_id, repo=repo.path)
    assert result.exit_code == exit_codes.REFUSED
    assert "deviations" in result.stdout + result.stderr


def test_handoff_blocker_governor_exits_2_and_waits_on_board(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    order_id = _claimed(repo, "blocker-q")
    repo.checkout(f"wo/{order_id}")
    repo.write_message(
        message(
            "handoff",
            order_id=order_id,
            open_questions=[
                {
                    "question": "Should the demo keep the locked host?",
                    "class": "blocker_governor",
                }
            ],
        )
    )
    repo.commit("handoff with blocker question")
    result = factory_cli("handoff", order_id, repo=repo.path)
    assert result.exit_code == exit_codes.REFUSED, (
        f"expected exit 2, got {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )
    assert "Should the demo keep the locked host?" in result.stdout
    assert "T028" not in result.stdout and "FR-010" not in result.stdout

    board = factory_cli("status", "--json", repo=repo.path)
    assert board.exit_code == exit_codes.OK, board.stderr
    data = json.loads(board.stdout)["data"]
    waiting = json.dumps(data["waiting_on_governor"])
    assert order_id in waiting
    assert "Should the demo keep the locked host?" in waiting


def test_handoff_writes_run_complete_event(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    order_id = _claimed(repo, "complete")
    repo.checkout(f"wo/{order_id}")
    repo.write_message(message("handoff", order_id=order_id))
    repo.commit("handoff")
    result = factory_cli("handoff", order_id, repo=repo.path)
    assert result.exit_code == exit_codes.OK, (
        f"expected exit 0, got {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )
    relative = f"bus/orders/{order_id}/run-complete.yaml"
    assert (repo.path / relative).is_file() or relative in repo.git(
        "ls-tree", "-r", "--name-only", f"wo/{order_id}"
    )
    text = (
        repo.git("show", f"HEAD:{relative}")
        if (repo.path / relative).is_file()
        else repo.git("show", f"wo/{order_id}:{relative}")
    )
    for key in ("wall_minutes", "governor_interrupts", "deviations_count"):
        assert key in text
    assert "cost_usd" in text
