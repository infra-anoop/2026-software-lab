"""T107 — the `factory/gates` summary status, as a pure function of the run report.

`factory.gates.runner.summary_status(report, gates)` returns the `(state, description)` of
the one summary status `factory gate run --pr` posts after the per-gate statuses
(governor 2026-10-06, `PLAN_DELTA.md` Round 5). `gates` is the installed (`main`'s) list of
CI gates. `success` only when every one of them has a report entry whose outcome is `pass`
or `overridden`; otherwise `failure`, naming the failing gate ids, with the description no
longer than the per-gate status limit. The CLI behaviour is pinned in
`tests/contract/test_gate_run.py`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from factory.gates import runner
from factory.gates.registry import Gate, load_registry
from factory.gates.runner import STATUS_DESCRIPTION_LIMIT, ci_gates

Summary = Callable[[dict[str, Any], list[Gate]], tuple[str, str]]


def summary_status() -> Summary:
    function = getattr(runner, "summary_status", None)
    assert callable(function), "factory.gates.runner.summary_status(report, gates) is missing"
    return function


def installed_ci_gates() -> list[Gate]:
    gates = ci_gates(load_registry())
    assert len(gates) > 1, "the installed registry needs more than one CI gate"
    return gates


def run_report(gates: list[Gate], outcome: str) -> dict[str, Any]:
    return {
        "gates": [
            {
                "id": gate.id,
                "class": gate.gate_class,
                "intents": list(gate.intents),
                "outcome": outcome,
                "messages": [] if outcome == "pass" else [f"{gate.id}: {outcome}"],
                "override": None,
            }
            for gate in gates
        ],
        "intents": {},
        "override_counts": {},
    }


def test_summary_fails_naming_a_registered_ci_gate_that_did_not_run() -> None:
    gates = installed_ci_gates()
    missing = gates[-1]
    state, description = summary_status()(run_report(gates[:-1], "pass"), gates)
    assert state == "failure", (state, description)
    assert missing.id in description, description


def test_summary_description_fits_the_status_limit_when_every_gate_fails() -> None:
    gates = installed_ci_gates()
    assert len(", ".join(gate.id for gate in gates)) > STATUS_DESCRIPTION_LIMIT
    state, description = summary_status()(run_report(gates, "fail"), gates)
    assert state == "failure", (state, description)
    assert len(description) <= STATUS_DESCRIPTION_LIMIT, (len(description), description)
    assert gates[0].id in description, description
