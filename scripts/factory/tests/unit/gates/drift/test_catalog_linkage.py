"""T039 — `catalog-test-linkage` (T048; FR-018; I-B7).

Every `how: auto` row in any `acceptance.md` carries `evidence`; rows whose id is in
the PR's effective order `checks` must name an existing pytest node id (not the
`planned` sentinel) before merge. Existence is judged at head.
"""

from __future__ import annotations

from factory.api import GateContext
from tests.fixtures.repo_builder import RepoBuilder
from tests.unit.gates.drift.helpers import (
    ORDER_ID,
    amendment_for,
    assert_blocks,
    assert_passes,
    order_ctx,
    order_for,
    order_pair,
)

GATE = "catalog-test-linkage"
ACCEPTANCE = "specs/demo-feature/acceptance.md"
HEADER = "| id | class | intents | severity | when | shall | how | evidence |\n"
RULE = "|----|-------|---------|----------|------|-------|-----|----------|\n"
TEST_FILE = "apps/demo/tests/test_calc.py"
TEST_TEXT = "from app.calc import add\n\n\ndef test_add() -> None:\n    assert add(2, 2) == 4\n"


def catalog(*rows: str) -> str:
    return "# Acceptance catalog — demo\n\n" + HEADER + RULE + "".join(rows)


def row(row_id: str, how: str, evidence: str) -> str:
    cells = [row_id, "SC-001", "I-D1", "must", "two integers", "add returns the sum", how, evidence]
    return "| " + " | ".join(cells) + " |\n"


def linkage_ctx(
    repo: RepoBuilder,
    head_files: dict[str, str | None],
    *,
    checks: list[str],
    base_files: dict[str, str] | None = None,
    amendments: tuple[dict[str, object], ...] = (),
) -> GateContext:
    repo.add_demo_feature()
    data = order_for(owned_paths=["apps/demo/**", "specs/demo-feature/**"], checks=checks)
    pair = order_pair(repo, base_files or {}, head_files, data, *amendments)
    return order_ctx(repo, pair)


def test_blocks_order_check_row_still_planned(repo: RepoBuilder) -> None:
    ctx = linkage_ctx(repo, {TEST_FILE: TEST_TEXT}, checks=["demo.adds"])
    assert_blocks(GATE, ctx, "demo.adds")


def test_passes_when_order_check_row_names_an_existing_test(repo: RepoBuilder) -> None:
    linked = catalog(row("demo.adds", "auto", f"{TEST_FILE}::test_add"))
    ctx = linkage_ctx(repo, {TEST_FILE: TEST_TEXT, ACCEPTANCE: linked}, checks=["demo.adds"])
    assert_passes(GATE, ctx)


def test_blocks_evidence_naming_a_missing_test_file(repo: RepoBuilder) -> None:
    linked = catalog(row("demo.adds", "auto", "apps/demo/tests/test_gone.py::test_add"))
    ctx = linkage_ctx(repo, {ACCEPTANCE: linked}, checks=["demo.adds"])
    assert_blocks(GATE, ctx, "demo.adds")


def test_blocks_evidence_naming_a_missing_test_function(repo: RepoBuilder) -> None:
    linked = catalog(row("demo.adds", "auto", f"{TEST_FILE}::test_add_overflow"))
    ctx = linkage_ctx(repo, {TEST_FILE: TEST_TEXT, ACCEPTANCE: linked}, checks=["demo.adds"])
    assert_blocks(GATE, ctx, "demo.adds")


def test_blocks_evidence_whose_test_exists_only_on_base(repo: RepoBuilder) -> None:
    """Existence is judged at head: the PR deleted the test its row points at."""
    linked = catalog(row("demo.adds", "auto", f"{TEST_FILE}::test_add"))
    ctx = linkage_ctx(
        repo,
        {TEST_FILE: None, ACCEPTANCE: linked},
        checks=["demo.adds"],
        base_files={TEST_FILE: TEST_TEXT},
    )
    assert_blocks(GATE, ctx, "demo.adds")


def test_planned_row_outside_the_orders_checks_passes(repo: RepoBuilder) -> None:
    """`planned` stays legal until the implementing order (FR-018)."""
    ctx = linkage_ctx(repo, {TEST_FILE: TEST_TEXT}, checks=[])
    assert_passes(GATE, ctx)


def test_checks_come_from_the_effective_order(repo: RepoBuilder) -> None:
    amendment = amendment_for(ORDER_ID, 1, checks=["demo.adds"])
    ctx = linkage_ctx(repo, {TEST_FILE: TEST_TEXT}, checks=[], amendments=(amendment,))
    assert_blocks(GATE, ctx, "demo.adds")


def test_blocks_auto_row_without_evidence_in_any_catalog(repo: RepoBuilder) -> None:
    other = "specs/other-feature/acceptance.md"
    text = catalog(row("other.renders", "auto", ""))
    ctx = linkage_ctx(repo, {other: text}, checks=[])
    assert_blocks(GATE, ctx, "other.renders")


def test_human_row_without_evidence_passes(repo: RepoBuilder) -> None:
    text = catalog(row("demo.looks_right", "human", ""))
    ctx = linkage_ctx(repo, {"specs/other-feature/acceptance.md": text}, checks=[])
    assert_passes(GATE, ctx)


def test_blocks_when_the_orders_catalog_row_is_deleted(repo: RepoBuilder) -> None:
    """Fail closed: deleting the row (or its catalog) does not escape the linkage."""
    ctx = linkage_ctx(repo, {ACCEPTANCE: None}, checks=["demo.adds"])
    assert_blocks(GATE, ctx, "demo.adds")


def test_columns_are_found_by_header_not_position(repo: RepoBuilder) -> None:
    reordered = (
        "| id | how | evidence | class | intents | severity | when | shall |\n"
        "|----|-----|----------|-------|---------|----------|------|-------|\n"
        "| other.reordered | auto |  | SC-001 | I-D1 | must | always | holds |\n"
    )
    ctx = linkage_ctx(repo, {"specs/other-feature/acceptance.md": reordered}, checks=[])
    assert_blocks(GATE, ctx, "other.reordered")


LEGACY = "specs/legacy-feature/acceptance.md"
LEGACY_HEAD = (
    "| id | class | severity | when | shall | how |\n"
    "|----|-------|----------|------|-------|-----|\n"
)
LEGACY_ROW = "| legacy.length | SC-001 | must | no override | Draft is 1-3 pages | auto |\n"


def test_blocks_auto_rows_in_a_catalog_without_an_evidence_column(repo: RepoBuilder) -> None:
    ctx = linkage_ctx(repo, {LEGACY: LEGACY_HEAD + LEGACY_ROW}, checks=[])
    assert_blocks(GATE, ctx, "legacy.length")


def test_untouched_legacy_rows_are_not_this_prs_violation(repo: RepoBuilder) -> None:
    """Changed scope (registry `changed_lines`): a pre-evidence catalog on the base
    (like `specs/smart-writer-v2/acceptance.md`) does not block unrelated PRs."""
    ctx = linkage_ctx(
        repo, {TEST_FILE: TEST_TEXT}, checks=[], base_files={LEGACY: LEGACY_HEAD + LEGACY_ROW}
    )
    assert_passes(GATE, ctx)


def test_editing_a_legacy_auto_row_requires_evidence(repo: RepoBuilder) -> None:
    edited = LEGACY_ROW.replace("1-3 pages", "1-2 pages")
    ctx = linkage_ctx(
        repo,
        {LEGACY: LEGACY_HEAD + edited},
        checks=[],
        base_files={LEGACY: LEGACY_HEAD + LEGACY_ROW},
    )
    assert_blocks(GATE, ctx, "legacy.length")
