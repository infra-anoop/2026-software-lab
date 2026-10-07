"""T052 — bus gates: `bus.schema`, `bus.immutable`, `bus.no-handwritten-status`.

contracts/messages.md § Invariants: every bus file validates; no existing bus file is
modified or deleted in a PR (append-only); no message carries `status`, `state`,
`done`, or `progress` at any depth. Renames count as delete + add (`--no-renames`).
"""

from __future__ import annotations

import pytest

from factory.cli import exit_codes
from tests.fixtures.cli_runner import FactoryCli
from tests.fixtures.repo_builder import RepoBuilder, message, yaml_text
from tests.unit.gates.pr.helpers import (
    ORDER_DIR,
    ORDER_ID,
    assert_blocks,
    assert_passes,
    oid,
    order_for,
    raw_context,
)

OTHER = oid("already-merged")
OTHER_ORDER = f"bus/orders/{OTHER}/order.yaml"
OTHER_CLAIM = f"bus/orders/{OTHER}/claim.yaml"
POSTMORTEM = "bus/postmortems/2026-10-sprint-01.yaml"


def merged_bus() -> dict[str, str]:
    return {
        OTHER_ORDER: yaml_text(order_for(OTHER)),
        OTHER_CLAIM: yaml_text(message("claim", order_id=OTHER)),
        POSTMORTEM: "sprint: 2026-10-sprint-01\ncorrections: []\n",
    }


# --- bus.schema (repo scope) ---------------------------------------------------------------


def test_bus_schema_passes_on_valid_bus(repo: RepoBuilder) -> None:
    pair = repo.base_head_pair(
        merged_bus(), {f"{ORDER_DIR}/order.yaml": yaml_text(order_for(ORDER_ID))}
    )
    assert_passes("bus.schema", raw_context(repo, pair))


def test_bus_schema_blocks_invalid_message_at_head(repo: RepoBuilder) -> None:
    bad = order_for(ORDER_ID, size_minutes=90)
    pair = repo.base_head_pair({}, {f"{ORDER_DIR}/order.yaml": yaml_text(bad)})
    assert_blocks("bus.schema", raw_context(repo, pair), f"{ORDER_DIR}/order.yaml")


def test_bus_schema_blocks_misplaced_message(repo: RepoBuilder) -> None:
    misplaced = f"bus/orders/{oid('elsewhere')}/order.yaml"
    pair = repo.base_head_pair({}, {misplaced: yaml_text(order_for(ORDER_ID))})
    assert_blocks("bus.schema", raw_context(repo, pair), misplaced)


def test_bus_schema_reads_head_not_working_tree(repo: RepoBuilder) -> None:
    """The gate judges the head commit; an invalid uncommitted file is not its input."""
    pair = repo.base_head_pair({}, {f"{ORDER_DIR}/order.yaml": yaml_text(order_for(ORDER_ID))})
    repo.write(f"bus/orders/{oid('scratch')}/order.yaml", "kind: order\nprogress: 50%\n")
    assert_passes("bus.schema", raw_context(repo, pair))


# --- bus.immutable (changed scope) ---------------------------------------------------------


def test_bus_immutable_passes_on_added_bus_files(repo: RepoBuilder) -> None:
    pair = repo.base_head_pair(
        merged_bus(),
        {
            f"{ORDER_DIR}/order.yaml": yaml_text(order_for(ORDER_ID)),
            "bus/postmortems/2026-10-sprint-02.yaml": "sprint: 2026-10-sprint-02\n",
        },
    )
    assert_passes("bus.immutable", raw_context(repo, pair))


def test_bus_immutable_passes_on_non_bus_changes(repo: RepoBuilder) -> None:
    pair = repo.base_head_pair(merged_bus(), {"README.md": "# fixture repo, edited\n"})
    assert_passes("bus.immutable", raw_context(repo, pair))


def test_bus_immutable_blocks_modified_message(repo: RepoBuilder) -> None:
    edited = order_for(OTHER, goal="Rewrite history after the fact.")
    pair = repo.base_head_pair(merged_bus(), {OTHER_ORDER: yaml_text(edited)})
    assert_blocks("bus.immutable", raw_context(repo, pair), OTHER_ORDER)


def test_bus_immutable_blocks_deleted_message(repo: RepoBuilder) -> None:
    pair = repo.base_head_pair(merged_bus(), {OTHER_CLAIM: None})
    assert_blocks("bus.immutable", raw_context(repo, pair), OTHER_CLAIM)


def test_bus_immutable_blocks_moved_message(repo: RepoBuilder) -> None:
    """A rename is a delete of the old path (renames off)."""
    text = merged_bus()[OTHER_CLAIM]
    moved = f"bus/orders/{OTHER}/claim-old.yaml"
    pair = repo.base_head_pair(merged_bus(), {OTHER_CLAIM: None, moved: text})
    assert_blocks("bus.immutable", raw_context(repo, pair), OTHER_CLAIM)


def test_bus_immutable_blocks_modified_postmortem(repo: RepoBuilder) -> None:
    """Append-only covers every bus file, including kinds the loader skips."""
    pair = repo.base_head_pair(merged_bus(), {POSTMORTEM: "sprint: 2026-10-sprint-01\nedited: 1\n"})
    assert_blocks("bus.immutable", raw_context(repo, pair), POSTMORTEM)


def test_check_immutability_cli_fails_on_modification(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    edited = order_for(OTHER, goal="Rewrite history after the fact.")
    pair = repo.base_head_pair(merged_bus(), {OTHER_ORDER: yaml_text(edited)})
    result = factory_cli(
        "check", "immutability", "--base", pair.base_sha, "--head", pair.head_sha, repo=repo.path
    )
    assert result.exit_code == exit_codes.GATE_FAILURE, result
    assert OTHER_ORDER in result.stdout + result.stderr


# --- bus.no-handwritten-status (changed scope) ---------------------------------------------


def test_no_status_passes_on_clean_message(repo: RepoBuilder) -> None:
    clean = order_for(ORDER_ID, goal="Show the state of every order on the board.")
    pair = repo.base_head_pair({}, {f"{ORDER_DIR}/order.yaml": yaml_text(clean)})
    assert_passes("bus.no-handwritten-status", raw_context(repo, pair))


@pytest.mark.parametrize(
    ("key", "nested"),
    [("status", False), ("state", False), ("done", False), ("progress", False), ("status", True)],
)
def test_no_status_blocks_status_key(repo: RepoBuilder, key: str, nested: bool) -> None:
    data = order_for(ORDER_ID)
    if nested:
        data["locks"] = [{"id": "D1", "letter_tokens": ["railway"], "fidelity": "letter", key: "x"}]
    else:
        data[key] = "in progress"
    path = f"{ORDER_DIR}/order.yaml"
    pair = repo.base_head_pair({}, {path: yaml_text(data)})
    assert_blocks("bus.no-handwritten-status", raw_context(repo, pair), path, key)


def test_no_status_ignores_untouched_files(repo: RepoBuilder) -> None:
    """Changed scope: a bad file already on base is not this PR's change."""
    legacy = f"bus/orders/{oid('legacy')}/order.yaml"
    bad = order_for(oid("legacy"))
    bad["status"] = "done"
    pair = repo.base_head_pair({legacy: yaml_text(bad)}, {"README.md": "# edited\n"})
    assert_passes("bus.no-handwritten-status", raw_context(repo, pair))
