"""T026 — `order new` / `order issue` refusals and issuance shape.

Catalogs: `seed.substitution_undeclared`, `handoff.open_od_refused`.
"""

from __future__ import annotations

import json

import pytest

from factory.cli import exit_codes
from tests.fixtures.cli_runner import FactoryCli
from tests.fixtures.repo_builder import RepoBuilder, message, order

pytestmark = pytest.mark.contract

DAY = "20261007"
OPEN_DECISION = "pick-host"


def oid(slug: str) -> str:
    return f"wo-{DAY}-{slug}"


def test_order_new_refuses_size_over_horizon(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    repo.add_demo_feature()
    result = factory_cli(
        "order",
        "new",
        "--feature",
        "demo-feature",
        "--from-task",
        "T001",
        "--size-minutes",
        "90",
        repo=repo.path,
    )
    assert result.exit_code == exit_codes.REFUSED, (
        f"expected exit 2, got {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )
    assert "60" in result.stdout or "60" in result.stderr


def test_order_new_refuses_touched_named_lock_without_fidelity(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    """Seed `undeclared_substitution`: T002 touches locked D1 (Railway) with no --lock."""
    repo.add_demo_feature()
    result = factory_cli(
        "order",
        "new",
        "--feature",
        "demo-feature",
        "--from-task",
        "T002",
        "--size-minutes",
        "45",
        repo=repo.path,
    )
    assert result.exit_code == exit_codes.REFUSED, (
        f"expected exit 2, got {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )
    combined = result.stdout + result.stderr
    assert "D1" in combined or "Railway" in combined or "fidelity" in combined.lower()


def test_order_issue_first_commit_is_only_the_order_file(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    order_id = oid("issue-shape")
    repo.write_message(order(order_id, owned_paths=[f"apps/demo/{order_id}/**"]))
    main_before = repo.head_sha("main")
    result = factory_cli("order", "issue", order_id, repo=repo.path)
    assert result.exit_code == exit_codes.OK, (
        f"expected exit 0, got {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )
    branch = f"wo/{order_id}"
    first = repo.git("rev-list", "--max-parents=0", f"origin/{branch}")
    if not first:
        first = repo.git("rev-list", "--reverse", f"origin/main..origin/{branch}").splitlines()[0]
    names = repo.git("diff-tree", "--no-commit-id", "--name-only", "-r", first).splitlines()
    assert names == [f"bus/orders/{order_id}/order.yaml"], names
    assert repo.head_sha("origin/main") == main_before, "order issue must never push main"


def test_order_issue_refuses_open_human_decision_in_plain_language(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    repo.checkout("main")
    repo.write_message(
        message(
            "decision_request",
            decision_id=OPEN_DECISION,
            blocking=True,
            prompt="Which host should the demo deploy to?",
        )
    )
    repo.commit("decision request")
    repo.push("main")
    order_id = oid("blocked-issue")
    repo.write_message(
        order(
            order_id,
            owned_paths=[f"apps/demo/{order_id}/**"],
            depends_on_decisions=[OPEN_DECISION],
        )
    )
    result = factory_cli("order", "issue", order_id, "--json", repo=repo.path)
    assert result.exit_code == exit_codes.REFUSED, (
        f"expected exit 2, got {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )
    combined = result.stdout + result.stderr
    assert "Which host should the demo deploy to?" in combined
    assert "T026" not in combined and "FR-007" not in combined
    envelope = json.loads(result.stdout)
    assert envelope["ok"] is False
    assert envelope["error"]["code"] == exit_codes.REFUSED
