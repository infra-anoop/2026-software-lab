"""T039 — `catalog-test-linkage` (T048; FR-018; I-B7).

Every `how: auto` row in any `acceptance.md` carries `evidence`; rows whose id is in
the PR's effective order `checks` must name an existing pytest node id or eval case
(not the `planned` sentinel) before merge. Existence is judged at head in git.

Eval evidence (T-B5, governor 2026-10-04): `eval:<repo-relative path>#<case-id>` counts
only if the file exists at head and holds a case with `id == <case-id>`. YAML/JSON: a
top-level list, or a `cases:` list, of mappings with `id`; JSONL: one object per line
with `id`. No `#`, an absolute path, or a `..` segment is malformed. Markdown backticks
around an evidence value are presentation and are ignored.

Eval files fail closed (T-B2-2, orchestrator 2026-10-05): the file is read as the git
blob at head, never from the checkout. A tracked symlink (mode 120000) blocks wherever
it points. Malformed YAML, JSON or JSONL (any bad line), a wrong top-level shape, a
`cases` value that is not a list, and any entry that is not a mapping with `id` block,
even when the requested case is otherwise present.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

from factory.api import GateContext
from tests.fixtures.repo_builder import BaseHeadPair, RepoBuilder
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


def test_backticks_around_a_node_id_are_ignored(repo: RepoBuilder) -> None:
    linked = catalog(row("demo.adds", "auto", f"`{TEST_FILE}::test_add`"))
    ctx = linkage_ctx(repo, {TEST_FILE: TEST_TEXT, ACCEPTANCE: linked}, checks=["demo.adds"])
    assert_passes(GATE, ctx)


# --- eval evidence --------------------------------------------------------------------------

CASES = [{"id": "adds-small", "input": [2, 2]}, {"id": "adds-large", "input": [9, 9]}]
EVAL_FILES = {
    "yaml-list": ("apps/demo/evals/golden.yaml", yaml.safe_dump(CASES)),
    "yaml-cases": ("apps/demo/evals/golden.yml", yaml.safe_dump({"cases": CASES})),
    "json-list": ("apps/demo/evals/golden.json", json.dumps(CASES)),
    "json-cases": ("apps/demo/evals/golden.json", json.dumps({"cases": CASES})),
    "jsonl": ("apps/demo/evals/golden.jsonl", "".join(json.dumps(c) + "\n" for c in CASES)),
}
EVAL_PATH, EVAL_TEXT = EVAL_FILES["yaml-list"]


def eval_ctx(
    repo: RepoBuilder,
    evidence: str,
    eval_files: dict[str, str | None] | None = None,
    base_files: dict[str, str] | None = None,
) -> GateContext:
    files = {EVAL_PATH: EVAL_TEXT} if eval_files is None else eval_files
    linked = catalog(row("demo.adds", "auto", evidence))
    return linkage_ctx(
        repo, {**files, ACCEPTANCE: linked}, checks=["demo.adds"], base_files=base_files
    )


@pytest.mark.parametrize("form", sorted(EVAL_FILES))
def test_passes_when_evidence_names_an_existing_eval_case(repo: RepoBuilder, form: str) -> None:
    path, text = EVAL_FILES[form]
    assert_passes(GATE, eval_ctx(repo, f"eval:{path}#adds-small", {path: text}))


def test_backticks_around_an_eval_reference_are_ignored(repo: RepoBuilder) -> None:
    assert_passes(GATE, eval_ctx(repo, f"`eval:{EVAL_PATH}#adds-large`"))


def test_blocks_eval_evidence_naming_a_missing_file(repo: RepoBuilder) -> None:
    ctx = eval_ctx(repo, "eval:apps/demo/evals/gone.yaml#adds-small")
    assert_blocks(GATE, ctx, "demo.adds")


@pytest.mark.parametrize(
    "case_id",
    ["adds-huge", "adds", "small"],
    ids=["absent", "prefix-of-an-id", "suffix-of-an-id"],
)
def test_blocks_eval_evidence_naming_a_missing_case(repo: RepoBuilder, case_id: str) -> None:
    assert_blocks(GATE, eval_ctx(repo, f"eval:{EVAL_PATH}#{case_id}"), "demo.adds")


def test_blocks_eval_case_id_that_appears_only_outside_an_id_key(repo: RepoBuilder) -> None:
    """The file is parsed, not searched: `adds-small` is a note, not a case id."""
    text = yaml.safe_dump([{"id": "adds-large", "note": "unlike adds-small"}])
    ctx = eval_ctx(repo, f"eval:{EVAL_PATH}#adds-small", {EVAL_PATH: text})
    assert_blocks(GATE, ctx, "demo.adds")


def test_blocks_eval_file_of_an_unsupported_type(repo: RepoBuilder) -> None:
    path = "apps/demo/evals/golden.txt"
    ctx = eval_ctx(repo, f"eval:{path}#adds-small", {path: "id: adds-small\n"})
    assert_blocks(GATE, ctx, "demo.adds")


def test_blocks_eval_file_deleted_at_head(repo: RepoBuilder) -> None:
    """The working tree is the base, where the file still exists; head is judged."""
    ctx = eval_ctx(
        repo, f"eval:{EVAL_PATH}#adds-small", {EVAL_PATH: None}, base_files={EVAL_PATH: EVAL_TEXT}
    )
    assert_blocks(GATE, ctx, "demo.adds")


def test_blocks_eval_file_that_exists_only_outside_git(repo: RepoBuilder) -> None:
    ctx = eval_ctx(repo, f"eval:{EVAL_PATH}#adds-small", {})
    repo.write(EVAL_PATH, EVAL_TEXT)
    assert_blocks(GATE, ctx, "demo.adds")


@pytest.mark.parametrize(
    "reference",
    [
        f"eval:{EVAL_PATH}",
        f"eval:{EVAL_PATH}#",
        "eval:{root}/" + EVAL_PATH + "#adds-small",
        "eval:../{name}/" + EVAL_PATH + "#adds-small",
        "eval:apps/demo/../demo/evals/golden.yaml#adds-small",
    ],
    ids=["no-hash", "empty-case-id", "absolute-path", "leading-dotdot", "inner-dotdot"],
)
def test_blocks_malformed_eval_reference(repo: RepoBuilder, reference: str) -> None:
    """Each path form would resolve to the real case if it were followed."""
    evidence = reference.format(root=repo.path, name=repo.path.name)
    assert_blocks(GATE, eval_ctx(repo, evidence), "demo.adds")


def test_eval_file_is_read_from_the_head_blob_not_the_checkout(repo: RepoBuilder) -> None:
    """Tracked at head without the case; the checkout's copy holds it."""
    head_text = yaml.safe_dump([{"id": "adds-large"}])
    ctx = eval_ctx(repo, f"eval:{EVAL_PATH}#adds-small", {EVAL_PATH: head_text})
    repo.write(EVAL_PATH, EVAL_TEXT)
    assert_blocks(GATE, ctx, "demo.adds")


LINK_PATH = "apps/demo/evals/linked.yaml"


@pytest.mark.parametrize("target", ["inside", "outside"])
def test_blocks_eval_file_tracked_as_a_symlink(
    repo: RepoBuilder, tmp_path: Path, target: str
) -> None:
    """Both targets hold the requested case; the checkout is left on head so a
    checkout read would follow the link."""
    if target == "outside":
        outside = tmp_path / "outside" / "golden.yaml"
        outside.parent.mkdir()
        outside.write_text(EVAL_TEXT, encoding="utf-8")
        link_target = str(outside)
    else:
        link_target = Path(EVAL_PATH).name
    base_sha = eval_ctx(repo, f"eval:{LINK_PATH}#adds-small").base_sha
    repo.checkout(f"wo/{ORDER_ID}")
    os.symlink(link_target, repo.path / LINK_PATH)
    head_sha = repo.commit("symlinked eval file")
    repo.push()
    assert repo.git("ls-tree", head_sha, LINK_PATH).startswith("120000 ")
    pair = BaseHeadPair(base_sha, head_sha, f"wo/{ORDER_ID}")
    assert_blocks(GATE, order_ctx(repo, pair), "demo.adds")


ADDS_SMALL = {"id": "adds-small"}
BAD_EVAL_FILES = {
    "yaml-syntax": ("golden.yaml", "- id: adds-small\n  input: [2, 2\n"),
    "json-syntax": ("golden.json", '[{"id": "adds-small", "input": [2, 2]},]'),
    "jsonl-one-bad-line": ("golden.jsonl", '{"id": "adds-small"}\n{"id": "adds-large",\n'),
    "yaml-empty": ("golden.yaml", ""),
    "yaml-scalar": ("golden.yaml", "adds-small\n"),
    "yaml-mapping-without-cases": ("golden.yaml", yaml.safe_dump({"adds-small": {"input": 1}})),
    "json-single-mapping": ("golden.json", json.dumps(ADDS_SMALL)),
    "jsonl-line-not-an-object": ("golden.jsonl", '{"id": "adds-small"}\n["adds-large"]\n'),
    "yaml-cases-mapping": ("golden.yaml", yaml.safe_dump({"cases": {"adds-small": {}}})),
    "json-cases-string": ("golden.json", json.dumps({"cases": "adds-small"})),
    "yaml-entries-strings": ("golden.yaml", yaml.safe_dump(["adds-small", "adds-large"])),
    "json-cases-mixed-entries": ("golden.json", json.dumps({"cases": [ADDS_SMALL, "adds-large"]})),
    "yaml-entry-without-id": ("golden.yaml", yaml.safe_dump([ADDS_SMALL, {"name": "adds-large"}])),
    "jsonl-line-without-id": ("golden.jsonl", '{"id": "adds-small"}\n{"name": "adds-large"}\n'),
}


@pytest.mark.parametrize("form", list(BAD_EVAL_FILES))
def test_blocks_malformed_or_wrong_shape_eval_file(repo: RepoBuilder, form: str) -> None:
    """Every non-empty file mentions `adds-small`, so a parser that skips what it cannot
    read would find it."""
    name, text = BAD_EVAL_FILES[form]
    path = f"apps/demo/evals/{name}"
    assert_blocks(GATE, eval_ctx(repo, f"eval:{path}#adds-small", {path: text}), "demo.adds")


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
