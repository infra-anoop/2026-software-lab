"""T026 — `order new` / `order issue` refusals and issuance shape.

Catalogs: `seed.substitution_undeclared`, `handoff.open_od_refused`.
"""

from __future__ import annotations

import json

import pytest
import yaml

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
    payload = order(order_id, owned_paths=[f"apps/demo/{order_id}/**"])
    order_path = repo.write_message(payload)
    main_before = repo.head_sha("main")
    result = factory_cli("order", "issue", order_id, repo=repo.path)
    assert result.exit_code == exit_codes.OK, (
        f"expected exit 0, got {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )
    assert repo.head_sha("origin/main") == main_before, "order issue must never push main"
    branch = f"wo/{order_id}"
    branch_only = repo.git("rev-list", "--reverse", f"origin/main..origin/{branch}").splitlines()
    assert branch_only, f"origin/{branch} has no commit beyond origin/main"
    first = branch_only[0]
    parents = repo.git("rev-list", "--parents", "-n", "1", first).split()[1:]
    assert parents == [main_before], f"first order commit must branch from main: {parents}"
    changes = repo.git("diff-tree", "--no-commit-id", "--name-status", "-r", first).splitlines()
    assert changes == [f"A\t{order_path}"], changes
    assert yaml.safe_load(repo.git("show", f"{first}:{order_path}")) == payload


def test_order_issue_refuses_empty_checks(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    """FR-011: an order with no checks could never earn acceptance, so it is not issued."""
    order_id = oid("no-checks")
    repo.write_message(order(order_id, owned_paths=[f"apps/demo/{order_id}/**"], checks=[]))
    main_before = repo.head_sha("origin/main")
    result = factory_cli("order", "issue", order_id, "--json", repo=repo.path)
    assert result.exit_code == exit_codes.REFUSED, (
        f"expected exit 2, got {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )
    envelope = json.loads(result.stdout)
    assert envelope["ok"] is False
    assert envelope["error"]["code"] == exit_codes.REFUSED
    assert "checks" in envelope["error"]["message"], envelope["error"]
    assert "T026" not in result.stdout and "FR-011" not in result.stdout
    branches = repo.git("ls-remote", "--heads", "origin", f"wo/{order_id}")
    assert branches == "", "a refused order must not be issued"
    assert repo.head_sha("origin/main") == main_before


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
