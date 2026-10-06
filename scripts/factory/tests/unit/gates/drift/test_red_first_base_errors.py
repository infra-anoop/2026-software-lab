"""Red-first base-side errors (W6 + W7, one root cause; orchestrator 2026-10-05, §J).

`red-first-proof` misclassifies base-side collection and import errors: one pytest run on
base collapses on a per-file error, and an import error is not attributed per test.
- W6: a sibling file failing import on base must not leave other tests "not collected".
- W7: a test importing a module the PR adds, as `from pkg import mod`, is red, not
  "base broken".

Each case is a valid PR, so the gate passes it. The raw facts from `collect_facts(ctx)`
(the Slice C evidence seam) then show each test's own base result.
"""

from __future__ import annotations

import importlib
from typing import Any

import pytest

from tests.fixtures.repo_builder import RepoBuilder
from tests.unit.gates.drift.helpers import assert_passes

GATE = "red-first-proof"
CLAMP = "apps/demo/app/clamp.py"
MONEY = "apps/demo/app/money.py"
CLAMP_TESTS = "apps/demo/tests/test_clamp.py"
MONEY_TESTS = "apps/demo/tests/test_money.py"
MONEY_TEXT = "def cents(dollars: int) -> int:\n    return dollars * 100\n"
TEST_CLAMP = (
    "from app.clamp import clamp\n\n\n"
    "def test_clamp_caps_high() -> None:\n    assert clamp(5, 0, 3) == 3\n"
)

CASES: dict[str, tuple[dict[str, str], dict[str, str], dict[str, dict[str, str]]]] = {
    "W6-sibling-import-error": (
        {CLAMP: "def clamp(x: int, lo: int, hi: int) -> int:\n    return x\n"},
        {
            CLAMP: "def clamp(x: int, lo: int, hi: int) -> int:\n    return max(lo, min(x, hi))\n",
            CLAMP_TESTS: TEST_CLAMP,
            MONEY: MONEY_TEXT,
            MONEY_TESTS: (
                "from app.money import cents\n\n\n"
                "def test_cents() -> None:\n    assert cents(2) == 200\n"
            ),
        },
        {
            f"{CLAMP_TESTS}::test_clamp_caps_high": {
                "base_outcome": "failed",
                "head_outcome": "passed",
            },
            f"{MONEY_TESTS}::test_cents": {
                "base_error": "No module named 'app.money'",
                "head_outcome": "passed",
            },
        },
    ),
    "W7-from-package-import-added-module": (
        {},
        {
            MONEY: MONEY_TEXT,
            MONEY_TESTS: (
                "from app import money\n\n\n"
                "def test_cents() -> None:\n    assert money.cents(2) == 200\n"
            ),
        },
        {
            f"{MONEY_TESTS}::test_cents": {
                "base_error": "cannot import name 'money' from 'app'",
                "head_outcome": "passed",
            },
        },
    ),
}


@pytest.mark.parametrize("case", list(CASES))
def test_base_errors_are_attributed_to_their_own_tests(repo: RepoBuilder, case: str) -> None:
    base_files, head_files, expected = CASES[case]
    repo.add_demo_feature()
    pair = repo.base_head_pair(base_files, head_files)
    ctx = repo.gate_context(pair, pr_number=1)
    assert_passes(GATE, ctx)

    # Imported in the test body: a base without the module must fail this test only,
    # not abort collection of every test the red-first run judges.
    red_first = importlib.import_module("factory.gates.drift.red_first")
    collect_facts = getattr(red_first, "collect_facts", None)
    assert collect_facts is not None, "red_first.collect_facts(ctx) is missing"
    facts: dict[str, Any] = {fact.node_id: fact for fact in collect_facts(ctx)}
    assert set(facts) == set(expected)
    for node_id, wanted in expected.items():
        fact = facts[node_id]
        for field, value in wanted.items():
            if field == "base_error":
                assert value in (fact.base_error or ""), (node_id, fact)
            else:
                assert getattr(fact, field) == value, (node_id, field, fact)
