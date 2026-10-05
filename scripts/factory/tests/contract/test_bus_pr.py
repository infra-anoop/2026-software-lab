"""T030 — `bus pr` refuses changes outside the bus decision/correction/post-mortem trees."""

from __future__ import annotations

import pytest

from factory.cli import exit_codes
from tests.fixtures.cli_runner import FactoryCli
from tests.fixtures.repo_builder import RepoBuilder, message

pytestmark = pytest.mark.contract


def test_bus_pr_refuses_non_bus_paths(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    written = repo.write_message(message("decision_request", decision_id="web-view"))
    repo.write("apps/demo/app/calc.py", "X = 1\n")
    result = factory_cli(
        "bus",
        "pr",
        "--message",
        written,
        "--message",
        "apps/demo/app/calc.py",
        repo=repo.path,
    )
    assert result.exit_code == exit_codes.REFUSED, (
        f"expected exit 2, got {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )
    combined = result.stdout + result.stderr
    assert "apps/demo/app/calc.py" in combined or "bus/" in combined


def test_bus_pr_allows_decision_correction_postmortem_only(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    decision = repo.write_message(message("decision_request", decision_id="web-view"))
    result = factory_cli("bus", "pr", "--message", decision, repo=repo.path)
    assert result.exit_code == exit_codes.OK, (
        f"expected exit 0, got {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )
    prs = [pr for pr in repo.github.prs.values() if pr.head_ref.startswith("bus/")]
    assert prs, "bus pr must open a bus/<date>-<slug> PR"
    assert "bus/decisions/" in decision
