"""T039 — `deferral-words-need-od` (T045; FR-015; I-B6).

Rule verbatim from contracts/gates.md § Deferral-words rule: in `specs/**` and
`notes/sprints/**`, the words *later, optional, deferred, TBD, future, stretch* need,
on the same line or table row, one of: an Open Decision id that exists (`D\\d+`), a
pointer `→ <artifact>` to an existing file or phase (`→ plan`, `→ sprint 03` with a
waived OD), or `[governor-judged]`. Spec-review tables ("Later → plan") satisfy it by
pointer. Words inside backtick code spans (enum values, quoted rule text) are exempt.

The gate is changed-scope: only added lines are judged.
"""

from __future__ import annotations

import pytest

from factory.api import GateContext
from tests.fixtures.repo_builder import RepoBuilder
from tests.unit.gates.drift.helpers import assert_blocks, assert_passes

GATE = "deferral-words-need-od"
PLAN = "specs/demo-feature/plan.md"
SPRINT = "notes/sprints/2026-10-sprint-02.md"
BASE_PLAN = "# Plan: demo\n\n## Scope\n\n- Add `add()`.\n"


def plan_ctx(
    repo: RepoBuilder,
    added: str,
    *,
    path: str = PLAN,
    base_text: str = BASE_PLAN,
    extra_head: dict[str, str] | None = None,
) -> GateContext:
    """Base has `path` = `base_text`; head appends `added` to it."""
    repo.add_demo_feature()
    pair = repo.base_head_pair({path: base_text}, {path: base_text + added, **(extra_head or {})})
    return repo.gate_context(pair, pr_number=1)


@pytest.mark.parametrize(
    ("word", "line"),
    [
        ("later", "- Retry on deploy failure comes later.\n"),
        ("optional", "- Rate limiting is optional for the first release.\n"),
        ("deferred", "- Deferred: export to CSV.\n"),
        ("TBD", "- Retention period: TBD.\n"),
        ("future", "- Multi-region is future work.\n"),
        ("stretch", "- Dark mode is a stretch goal.\n"),
    ],
    ids=["later", "optional", "deferred", "TBD", "future", "stretch"],
)
def test_blocks_each_deferral_word_without_a_reference(
    repo: RepoBuilder, word: str, line: str
) -> None:
    assert_blocks(GATE, plan_ctx(repo, line), word, PLAN)


def test_blocks_in_sprint_notes(repo: RepoBuilder) -> None:
    ctx = plan_ctx(repo, "- Board web view: later.\n", path=SPRINT, base_text="# Sprint 02\n")
    assert_blocks(GATE, ctx, SPRINT)


def test_word_match_is_case_insensitive(repo: RepoBuilder) -> None:
    assert_blocks(GATE, plan_ctx(repo, "- LATER: retries.\n"), "later")


def test_blocks_a_spec_table_row_without_a_reference(repo: RepoBuilder) -> None:
    table = "\n| id | note |\n|----|------|\n| F9 | Retries are optional for now |\n"
    assert_blocks(GATE, plan_ctx(repo, table), "optional")


def test_passes_with_an_existing_open_decision_id(repo: RepoBuilder) -> None:
    """D1 is a row of the demo feature's Open Decisions table."""
    assert_passes(GATE, plan_ctx(repo, "- Second deploy host is deferred (D1).\n"))


def test_blocks_with_an_open_decision_id_that_does_not_exist(repo: RepoBuilder) -> None:
    assert_blocks(GATE, plan_ctx(repo, "- Second deploy host is deferred (D9).\n"), "deferred")


def test_open_decision_added_in_the_same_change_counts(repo: RepoBuilder) -> None:
    """Existence is judged at head: the PR may add the OD row that it cites."""
    repo.add_demo_feature()
    spec_path = "specs/demo-feature/spec.md"
    spec = (repo.path / spec_path).read_text(encoding="utf-8")
    new_row = (
        "| **D2** | Retries exist | How many | human | Before deploy | open | content-only"
        " | letter |\n"
    )
    pair = repo.base_head_pair(
        {PLAN: BASE_PLAN},
        {spec_path: spec + new_row, PLAN: BASE_PLAN + "- Retry count is deferred (D2).\n"},
    )
    assert_passes(GATE, repo.gate_context(pair, pr_number=1))


def test_passes_with_a_phase_pointer(repo: RepoBuilder) -> None:
    table = "\n| id | disposition |\n|----|-------------|\n| F9 | Later → plan |\n"
    assert_passes(GATE, plan_ctx(repo, table))


def test_passes_with_a_pointer_to_an_existing_file(repo: RepoBuilder) -> None:
    line = "- Export is deferred → specs/demo-feature/tasks.md\n"
    assert_passes(GATE, plan_ctx(repo, line))


def test_blocks_with_a_pointer_to_a_missing_file(repo: RepoBuilder) -> None:
    line = "- Export is deferred → notes/missing-follow-up.md\n"
    assert_blocks(GATE, plan_ctx(repo, line), "deferred")


def test_passes_with_governor_judged_tag(repo: RepoBuilder) -> None:
    assert_passes(GATE, plan_ctx(repo, "- Polish is optional [governor-judged].\n"))


def test_reference_on_another_line_does_not_count(repo: RepoBuilder) -> None:
    """Same line or table row only: a reference on the next line does not cover it."""
    lines = "- Export to CSV comes later.\n- See D1 for the deploy host.\n"
    assert_blocks(GATE, plan_ctx(repo, lines), "later")


def test_words_inside_code_spans_are_exempt(repo: RepoBuilder) -> None:
    line = "- Finding severities are `blocker`, `debate`, `later`, `nit`; status `TBD` is gone.\n"
    assert_passes(GATE, plan_ctx(repo, line))


def test_word_outside_the_code_span_on_the_same_line_still_blocks(repo: RepoBuilder) -> None:
    line = "- Findings with severity `nit` are deferred.\n"
    assert_blocks(GATE, plan_ctx(repo, line), "deferred")


@pytest.mark.parametrize(
    "line",
    [
        "- Use the deploy token as collateral for the rollback check.\n",
        "- The outstretched timeline covers two weeks.\n",
        "- The tbdx parser is in the vendor folder.\n",
    ],
    ids=["collateral", "outstretched", "tbdx"],
)
def test_words_that_merely_contain_a_deferral_word_pass(repo: RepoBuilder, line: str) -> None:
    """Whole words only: `collateral` contains `later` but is not a deferral."""
    assert_passes(GATE, plan_ctx(repo, line))


def test_legacy_deferral_on_base_is_not_this_prs_violation(repo: RepoBuilder) -> None:
    """Changed lines only: an unrelated edit to a file that already says `later` passes."""
    legacy = BASE_PLAN + "- Retries come later.\n"
    ctx = plan_ctx(repo, "- Add `sub()`.\n", base_text=legacy)
    assert_passes(GATE, ctx)


def test_removing_a_deferral_line_passes(repo: RepoBuilder) -> None:
    repo.add_demo_feature()
    legacy = BASE_PLAN + "- Retries come later.\n"
    pair = repo.base_head_pair({PLAN: legacy}, {PLAN: BASE_PLAN})
    assert_passes(GATE, repo.gate_context(pair, pr_number=1))


@pytest.mark.parametrize(
    "path",
    ["docs/guide.md", "notes/packets/2026-10-06-demo.md", "apps/demo/README.md"],
    ids=["docs", "packets", "app-readme"],
)
def test_outside_specs_and_sprint_notes_passes(repo: RepoBuilder, path: str) -> None:
    ctx = plan_ctx(repo, "- Retries come later.\n", path=path, base_text="# Notes\n")
    assert_passes(GATE, ctx)
