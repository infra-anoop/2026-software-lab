"""PR review W1 — `catalog-test-linkage` judges only catalog-row `checks` (amendment-06).

`data-model.md` § WorkOrder: `checks` holds "gate ids or catalog row ids; each exists".
Orchestrator decision (2026-10-05): each consumer judges only its own kind. This gate
judges the ids that are catalog rows. An id registered as a gate (in the installed
registry, `main`'s under D5) is not a catalog miss. An id that is neither a registered
gate nor a catalog row at head still blocks, naming the id.

The demo catalog has one row, `demo.adds` (`auto`, evidence `planned`).
"""

from __future__ import annotations

from factory.api import GateContext
from factory.gates.registry import load_registry
from tests.fixtures.repo_builder import RepoBuilder
from tests.unit.gates.drift.helpers import (
    assert_blocks,
    assert_passes,
    order_ctx,
    order_for,
    order_pair,
)

GATE = "catalog-test-linkage"
ACCEPTANCE = "specs/demo-feature/acceptance.md"
TEST_FILE = "apps/demo/tests/test_calc.py"
TEST_TEXT = "from app.calc import add\n\n\ndef test_add() -> None:\n    assert add(2, 2) == 4\n"
LINKED = (
    "# Acceptance catalog — demo\n\n"
    "| id | class | intents | severity | when | shall | how | evidence |\n"
    "|----|-------|---------|----------|------|-------|-----|----------|\n"
    f"| demo.adds | SC-001 | I-D1 | must | two integers | add returns their sum | auto"
    f" | {TEST_FILE}::test_add |\n"
)
GATE_IDS = ["red-first-proof", "pr-links-order"]
PLANNED = "planned"


def checks_ctx(repo: RepoBuilder, checks: list[str], *, link: bool = False) -> GateContext:
    registered = set(load_registry().ids())
    assert set(GATE_IDS) <= registered, f"fixture gate ids are not registered: {GATE_IDS}"
    assert "demo.adds" not in registered
    repo.add_demo_feature()
    data = order_for(owned_paths=["apps/demo/**", "specs/demo-feature/**"], checks=checks)
    head = {TEST_FILE: TEST_TEXT, **({ACCEPTANCE: LINKED} if link else {})}
    return order_ctx(repo, order_pair(repo, {}, head, data))


def assert_not_named(ctx: GateContext, *ids: str) -> None:
    result = assert_blocks(GATE, ctx)
    text = "\n".join(result.messages)
    for gate_id in ids:
        assert gate_id not in text, f"{GATE} judged gate id {gate_id!r}: {result.messages}"


def test_registered_gate_ids_are_not_catalog_misses(repo: RepoBuilder) -> None:
    assert_passes(GATE, checks_ctx(repo, GATE_IDS))


def test_gate_ids_beside_a_linked_catalog_row_pass(repo: RepoBuilder) -> None:
    assert_passes(GATE, checks_ctx(repo, ["demo.adds", *GATE_IDS], link=True))


def test_a_planned_catalog_row_still_blocks_beside_gate_ids(repo: RepoBuilder) -> None:
    ctx = checks_ctx(repo, ["demo.adds", *GATE_IDS])
    assert_blocks(GATE, ctx, "demo.adds")
    assert_not_named(ctx, *GATE_IDS)


def test_an_id_that_is_neither_a_gate_nor_a_row_blocks(repo: RepoBuilder) -> None:
    assert_blocks(GATE, checks_ctx(repo, ["demo.adds-typo"]), "demo.adds-typo")


def test_an_unknown_id_beside_gate_ids_blocks_naming_only_the_unknown(
    repo: RepoBuilder,
) -> None:
    ctx = checks_ctx(repo, ["demo.adds-typo", *GATE_IDS])
    assert_blocks(GATE, ctx, "demo.adds-typo")
    assert_not_named(ctx, *GATE_IDS)


def test_a_catalog_row_sharing_a_gate_id_is_still_judged(repo: RepoBuilder) -> None:
    """T-B4-1 (round 4, amendment-08): catalog rows are classified first, so an id that
    is both a registered gate and an unlinked catalog row blocks naming that row."""
    shared, gate_only = GATE_IDS
    repo.add_demo_feature()
    catalog = LINKED + f"| {shared} | SC-001 | I-D1 | must | always | holds | auto | planned |\n"
    data = order_for(
        owned_paths=["apps/demo/**", "specs/demo-feature/**"], checks=["demo.adds", *GATE_IDS]
    )
    ctx = order_ctx(repo, order_pair(repo, {}, {TEST_FILE: TEST_TEXT, ACCEPTANCE: catalog}, data))
    result = assert_blocks(GATE, ctx, shared)
    assert any(shared in line and PLANNED in line for line in result.messages), (
        f"{GATE} did not judge catalog row {shared!r} as planned: {result.messages}"
    )
    assert_not_named(ctx, gate_only, "demo.adds")
