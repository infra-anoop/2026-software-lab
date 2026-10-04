"""T040 — `red-first-proof` edge cases (T042; FR-012; I-B7, I-P2).

Rule verbatim from research.md § Red-first (locked 2026-10-03, review P6): collect
test node ids on head; diff against base collection to get new and changed tests;
check out base app code with head test files overlaid; run those tests. Each must
fail with a real test failure (assertion or raised exception inside the test body).
A collection or import error counts as red only when the missing name is a module or
symbol the PR itself adds; any other base error is reported as "base broken", not
red. Then run them on head, where they must pass. A PR with no new or changed tests
passes this gate.

Fixture app: `apps/demo` (root `conftest.py`, package `app`, `app/calc.py::add`).
"""

from __future__ import annotations

from factory.api import GateContext
from tests.fixtures.repo_builder import RepoBuilder
from tests.unit.gates.drift.helpers import assert_blocks, assert_passes

GATE = "red-first-proof"
TESTS = "apps/demo/tests/test_calc.py"
CALC = "apps/demo/app/calc.py"
CALC_TEXT = "def add(a: int, b: int) -> int:\n    return a + b\n"
CLAMP = "apps/demo/app/clamp.py"
CLAMP_BUGGY = "def clamp(x: int, lo: int, hi: int) -> int:\n    return x\n"
CLAMP_FIXED = "def clamp(x: int, lo: int, hi: int) -> int:\n    return max(lo, min(x, hi))\n"
TEST_ADD = "def test_add() -> None:\n    assert add(1, 2) == 3\n"
TEST_CLAMP = "def test_clamp_caps_high() -> None:\n    assert clamp(5, 0, 3) == 3\n"


def red_ctx(
    repo: RepoBuilder, head_files: dict[str, str | None], base_files: dict[str, str] | None = None
) -> GateContext:
    repo.add_demo_feature()
    pair = repo.base_head_pair(base_files or {}, head_files)
    return repo.gate_context(pair, pr_number=1)


def module_with(*bodies: str, imports: str = "from app.calc import add\n") -> str:
    return imports + "".join(f"\n\n{body}" for body in bodies)


def test_new_test_passing_on_base_blocks(repo: RepoBuilder) -> None:
    ctx = red_ctx(repo, {TESTS: module_with(TEST_ADD)})
    assert_blocks(GATE, ctx, "test_add")


def test_assertion_failure_on_base_passes(repo: RepoBuilder) -> None:
    ctx = red_ctx(
        repo,
        {
            CLAMP: CLAMP_FIXED,
            TESTS: module_with(TEST_CLAMP, imports="from app.clamp import clamp\n"),
        },
        base_files={CLAMP: CLAMP_BUGGY},
    )
    assert_passes(GATE, ctx)


def test_exception_inside_the_test_body_on_base_counts_as_red(repo: RepoBuilder) -> None:
    parser = "apps/demo/app/parse.py"
    ctx = red_ctx(
        repo,
        {
            parser: "def parse_amount(text: str) -> int:\n    return int(text.strip('$'))\n",
            TESTS: module_with(
                "def test_parse_amount() -> None:\n    assert parse_amount('$7') == 7\n",
                imports="from app.parse import parse_amount\n",
            ),
        },
        base_files={parser: "def parse_amount(text: str) -> int:\n    raise NotImplementedError\n"},
    )
    assert_passes(GATE, ctx)


def test_import_error_for_a_symbol_the_pr_adds_counts_as_red(repo: RepoBuilder) -> None:
    sub = "\n\ndef sub(a: int, b: int) -> int:\n    return a - b\n"
    ctx = red_ctx(
        repo,
        {
            CALC: CALC_TEXT + sub,
            TESTS: module_with(
                "def test_sub() -> None:\n    assert sub(3, 1) == 2\n",
                imports="from app.calc import sub\n",
            ),
        },
    )
    assert_passes(GATE, ctx)


def test_import_error_for_a_module_the_pr_adds_counts_as_red(repo: RepoBuilder) -> None:
    ctx = red_ctx(
        repo,
        {
            "apps/demo/app/money.py": "def cents(dollars: int) -> int:\n    return dollars * 100\n",
            TESTS: module_with(
                "def test_cents() -> None:\n    assert cents(2) == 200\n",
                imports="from app.money import cents\n",
            ),
        },
    )
    assert_passes(GATE, ctx)


def test_import_error_for_an_unrelated_broken_module_is_base_broken(repo: RepoBuilder) -> None:
    """The base fails to import a vendor module the PR does not add: not red."""
    legacy = "apps/demo/app/legacy.py"
    ctx = red_ctx(
        repo,
        {
            legacy: "def legacy_total() -> int:\n    return 1\n",
            TESTS: module_with(
                "def test_legacy_plus_one() -> None:\n    assert add(legacy_total(), 1) == 2\n",
                imports="from app.calc import add\nfrom app.legacy import legacy_total\n",
            ),
        },
        base_files={
            legacy: "import vendor_sdk_that_is_gone\n\n\ndef legacy_total() -> int:\n    return 1\n"
        },
    )
    assert_blocks(GATE, ctx, "base broken")


def test_pr_without_new_or_changed_tests_passes(repo: RepoBuilder) -> None:
    ctx = red_ctx(
        repo,
        {CALC: '"""Arithmetic."""\n\n' + CALC_TEXT, "docs/calc.md": "# Calc\n"},
        base_files={TESTS: module_with(TEST_ADD)},
    )
    assert_passes(GATE, ctx)


def test_changed_test_passing_on_base_blocks(repo: RepoBuilder) -> None:
    changed = "def test_add() -> None:\n    assert add(2, 2) == 4\n"
    ctx = red_ctx(repo, {TESTS: module_with(changed)}, base_files={TESTS: module_with(TEST_ADD)})
    assert_blocks(GATE, ctx, "test_add")


def test_unchanged_passing_test_in_a_changed_file_is_not_judged(repo: RepoBuilder) -> None:
    imports = "from app.calc import add\nfrom app.clamp import clamp\n"
    ctx = red_ctx(
        repo,
        {CLAMP: CLAMP_FIXED, TESTS: module_with(TEST_ADD, TEST_CLAMP, imports=imports)},
        base_files={CLAMP: CLAMP_BUGGY, TESTS: module_with(TEST_ADD, imports=imports)},
    )
    assert_passes(GATE, ctx)


def test_each_new_test_is_judged_on_its_own(repo: RepoBuilder) -> None:
    """One red and one already-green new test: the green one blocks the PR."""
    green = "def test_clamp_inside_range() -> None:\n    assert clamp(2, 0, 3) == 2\n"
    ctx = red_ctx(
        repo,
        {
            CLAMP: CLAMP_FIXED,
            TESTS: module_with(TEST_CLAMP, green, imports="from app.clamp import clamp\n"),
        },
        base_files={CLAMP: CLAMP_BUGGY},
    )
    assert_blocks(GATE, ctx, "test_clamp_inside_range")


def test_new_test_failing_on_head_blocks(repo: RepoBuilder) -> None:
    """Red on base is not enough: the test must pass on head."""
    still_buggy = "def clamp(x: int, lo: int, hi: int) -> int:\n    return min(x, lo)\n"
    ctx = red_ctx(
        repo,
        {
            CLAMP: still_buggy,
            TESTS: module_with(TEST_CLAMP, imports="from app.clamp import clamp\n"),
        },
        base_files={CLAMP: CLAMP_BUGGY},
    )
    assert_blocks(GATE, ctx, "test_clamp_caps_high")


def test_test_skipped_on_base_is_not_red(repo: RepoBuilder) -> None:
    """A skip is not a test failure, even when it hides a missing module."""
    skipping = (
        "import pytest\n\n\n"
        "def test_cents() -> None:\n"
        '    money = pytest.importorskip("app.money")\n'
        "    assert money.cents(2) == 200\n"
    )
    ctx = red_ctx(
        repo,
        {
            "apps/demo/app/money.py": "def cents(dollars: int) -> int:\n    return dollars * 100\n",
            TESTS: skipping,
        },
    )
    assert_blocks(GATE, ctx, "test_cents")
