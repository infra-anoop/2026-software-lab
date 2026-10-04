"""T007 — bus loader + layout resolver (read-only)."""

from __future__ import annotations

from pathlib import PurePosixPath

import pytest

from factory.bus.models import parse_message
from factory.bus.store import BusError, expected_path, load_all, load_files
from tests.fixtures.repo_builder import SAMPLE_FILES, RepoBuilder, load_sample, message, order

ORDER_ID = "wo-20261006-store-test"

EXPECTED_LAYOUT = {
    "order": "bus/orders/wo-20261005-red-first-gate/order.yaml",
    "amendment": "bus/orders/wo-20261005-red-first-gate/amendment-01.yaml",
    "claim": "bus/orders/wo-20261005-red-first-gate/claim.yaml",
    "release": "bus/orders/wo-20261005-red-first-gate/release.yaml",
    "run_complete": "bus/orders/wo-20261005-red-first-gate/run-complete.yaml",
    "handoff": "bus/orders/wo-20261005-red-first-gate/handoff.yaml",
    "verdict": "bus/orders/wo-20261005-red-first-gate/verdict-01.yaml",
    "override": "bus/orders/wo-20261005-red-first-gate/override-01.yaml",
    "decision_request": "bus/decisions/board-web-view/request.yaml",
    "decision_lock": "bus/decisions/board-web-view/lock.yaml",
    "correction": "bus/corrections/corr-20261005-thin-substitute.yaml",
}


@pytest.mark.parametrize("kind", sorted(SAMPLE_FILES))
def test_expected_path_per_layout(kind: str) -> None:
    assert expected_path(parse_message(load_sample(kind))) == PurePosixPath(EXPECTED_LAYOUT[kind])


def test_load_all_at_ref_reads_the_order_branch(repo: RepoBuilder) -> None:
    branch = repo.issue_order(order(ORDER_ID))
    repo.add_event(ORDER_ID, message("claim", order_id=ORDER_ID))
    messages = load_all(repo.path, f"origin/{branch}")
    assert sorted(m.kind for m in messages) == ["claim", "order"]
    assert load_all(repo.path, "origin/main") == []


def test_load_all_working_tree(repo: RepoBuilder) -> None:
    repo.write_message(message("decision_request"))
    assert [m.kind for m in load_all(repo.path)] == ["decision_request"]


def test_misplaced_file_is_an_error(repo: RepoBuilder) -> None:
    written = repo.path / repo.write_message(order(ORDER_ID))
    misplaced = repo.path / "bus/orders/wo-20261006-other/order.yaml"
    misplaced.parent.mkdir(parents=True)
    written.rename(misplaced)
    with pytest.raises(BusError, match="belongs at"):
        load_files(repo.path)


def test_invalid_file_error_names_the_path(repo: RepoBuilder) -> None:
    repo.write_message(order(ORDER_ID, status="claimed"), validate=False)
    with pytest.raises(BusError) as excinfo:
        load_all(repo.path)
    assert excinfo.value.path == f"bus/orders/{ORDER_ID}/order.yaml"
    assert "status" in excinfo.value.problem


def test_postmortems_are_skipped(repo: RepoBuilder) -> None:
    repo.write("bus/postmortems/2026-10-sprint-02.yaml", "sprint: 2026-10-sprint-02\n")
    assert load_all(repo.path) == []


def test_loader_never_writes(repo: RepoBuilder) -> None:
    repo.issue_order(order(ORDER_ID))
    before = repo.git("status", "--porcelain")
    load_all(repo.path, f"origin/wo/{ORDER_ID}")
    load_all(repo.path)
    assert repo.git("status", "--porcelain") == before
