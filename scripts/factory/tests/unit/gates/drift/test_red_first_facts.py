"""PR review PR-B3 seam — `red_first` exposes raw per-test facts (amendment-06).

Orchestrator decision (2026-10-05): the evidence bundle (model, serialization, workflow,
trusted judge) is Slice C's (T097). Slice B's `red_first` only returns raw facts as a
plain value: `collect_facts(ctx)` gives one record per new or changed test with its
repo-relative `node_id`, pytest's `base_outcome` and `head_outcome`, and the raw
`base_error` text. It classifies nothing: "red", "base broken" and the added-name rule
stay with the judge. This file pins only that seam, not any bundle shape.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any

from tests.fixtures.repo_builder import RepoBuilder

TESTS = "apps/demo/tests/test_clamp.py"
CLAMP = "apps/demo/app/clamp.py"
LEGACY = "apps/demo/app/legacy.py"
JUDGMENTS = ("base broken", "red first", "not red")


def facts_for(
    repo: RepoBuilder, base_files: dict[str, str], head_files: dict[str, str]
) -> dict[str, Any]:
    # Imported in the test body: a base without the module must fail these tests only,
    # not abort collection of every test the red-first run judges.
    red_first = importlib.import_module("factory.gates.drift.red_first")
    collect_facts: Callable[..., Any] | None = getattr(red_first, "collect_facts", None)
    assert collect_facts is not None, "red_first.collect_facts(ctx) is missing"
    repo.add_demo_feature()
    pair = repo.base_head_pair(base_files, head_files)
    facts = {fact.node_id: fact for fact in collect_facts(repo.gate_context(pair, pr_number=1))}
    for fact in facts.values():
        assert not any(word in repr(fact).lower() for word in JUDGMENTS), fact
    return facts


def test_collect_facts_reports_pytest_outcomes_per_side(repo: RepoBuilder) -> None:
    facts = facts_for(
        repo,
        {CLAMP: "def clamp(x: int, lo: int, hi: int) -> int:\n    return x\n"},
        {
            CLAMP: "def clamp(x: int, lo: int, hi: int) -> int:\n    return max(lo, min(x, hi))\n",
            TESTS: (
                "from app.clamp import clamp\n\n\n"
                "def test_clamp_caps_high() -> None:\n    assert clamp(5, 0, 3) == 3\n"
            ),
        },
    )
    assert set(facts) == {f"{TESTS}::test_clamp_caps_high"}
    fact = facts[f"{TESTS}::test_clamp_caps_high"]
    assert (fact.base_outcome, fact.head_outcome) == ("failed", "passed")


def test_collect_facts_carries_the_raw_base_error_text(repo: RepoBuilder) -> None:
    """The base cannot import a vendor module the PR does not add; no class is assigned."""
    facts = facts_for(
        repo,
        {LEGACY: "import vendor_sdk_that_is_gone\n\n\ndef total() -> int:\n    return 1\n"},
        {
            LEGACY: "def total() -> int:\n    return 1\n",
            TESTS: (
                "from app.legacy import total\n\n\n"
                "def test_total() -> None:\n    assert total() == 1\n"
            ),
        },
    )
    assert set(facts) == {f"{TESTS}::test_total"}
    fact = facts[f"{TESTS}::test_total"]
    assert "No module named 'vendor_sdk_that_is_gone'" in (fact.base_error or "")
    assert fact.head_outcome == "passed"
