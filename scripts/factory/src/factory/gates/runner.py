"""Gate runner (T055): run registered gates on one base/head pair, resolve overrides,
and build the per-gate and per-intent report.

Report (`factory gate run` JSON `data`, or `error.details` when a gate fails):
`gates: [{id, class, intents, outcome: pass|fail|overridden, messages, override}]`,
`intents: {<intent id>: [{gate, outcome}]}`, `override_counts: {<gate id>: n}`.
A gate whose entrypoint is missing or raises fails closed.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from factory.api import GateContext, GateEntrypointError, GateResult, run_gate
from factory.bus.models import Override
from factory.config.settings import Settings
from factory.gates.overrides import honored_overrides, order_overrides
from factory.gates.pr._bus import load_tolerant
from factory.gates.registry import Gate, Registry

Outcome = Literal["pass", "fail", "overridden"]
WORK_ORDER_REF = re.compile(r"^(?:refs/heads/|refs/remotes/[^/]+/|origin/)?wo/(?P<id>[^/]+)$")
STATUS_DESCRIPTION_LIMIT = 140


def ci_gates(registry: Registry) -> list[Gate]:
    """Every registered gate that CI runs (hook rows carry `hook_twin_of` and do not)."""
    return [gate for gate in registry.gates if gate.hook_twin_of is None]


def order_id_from_ref(ref: str | None) -> str | None:
    match = WORK_ORDER_REF.match(ref or "")
    return match["id"] if match else None


def build_context(
    repo: Path,
    settings: Settings,
    *,
    base_sha: str,
    head_sha: str,
    order_id: str | None,
    pr_number: int | None,
) -> GateContext:
    return GateContext(
        repo_path=repo,
        base_sha=base_sha,
        head_sha=head_sha,
        pr_number=pr_number,
        order_id=order_id,
        config=settings,
        bus_snapshot=load_tolerant(repo, head_sha, settings),
    )


def _call(gate: Gate, ctx: GateContext) -> GateResult:
    try:
        return run_gate(gate.id, ctx)
    except GateEntrypointError as exc:
        reason = f"not implemented ({exc})"
    except Exception as exc:
        reason = f"crashed ({type(exc).__name__}: {exc})"
    return GateResult(gate_id=gate.id, passed=False, messages=[f"{gate.id}: {reason}"])


def run_gates(
    gates: list[Gate], ctx: GateContext, *, verify: Callable[[Override], bool]
) -> dict[str, Any]:
    overrides = order_overrides(list(ctx.bus_snapshot), ctx.order_id)
    entries: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    intents: dict[str, list[dict[str, str]]] = {}
    for gate in gates:
        result = _call(gate, ctx)
        outcome: Outcome = "pass" if result.passed else "fail"
        messages = list(result.messages)
        summary = None
        if not result.passed:
            honored = honored_overrides(
                gate, overrides, settings=ctx.config, pr_number=ctx.pr_number, verify=verify
            )
            if honored:
                outcome = "overridden"
                summary = honored[-1].summary()
                counts[gate.id] = len(honored)
                messages.append(f"overridden: {honored[-1].message.reason}")
        entries.append(
            {
                "id": gate.id,
                "class": gate.gate_class,
                "intents": list(gate.intents),
                "outcome": outcome,
                "messages": messages,
                "override": summary,
            }
        )
        for intent in gate.intents:
            intents.setdefault(intent, []).append({"gate": gate.id, "outcome": outcome})
    return {
        "base": ctx.base_sha,
        "head": ctx.head_sha,
        "order_id": ctx.order_id,
        "pr": ctx.pr_number,
        "gates": entries,
        "intents": intents,
        "override_counts": counts,
    }


def failures(report: dict[str, Any]) -> list[str]:
    return [entry["id"] for entry in report["gates"] if entry["outcome"] == "fail"]


def commit_status(entry: dict[str, Any]) -> tuple[Literal["success", "failure"], str]:
    """The `factory/<gate-id>` commit status for one report entry."""
    if entry["outcome"] == "overridden":
        state: Literal["success", "failure"] = "success"
        description = f"overridden: {entry['override']['reason']}"
    elif entry["outcome"] == "pass":
        state, description = "success", "passed"
    else:
        state = "failure"
        description = entry["messages"][0] if entry["messages"] else "failed"
    if len(description) > STATUS_DESCRIPTION_LIMIT:
        description = description[: STATUS_DESCRIPTION_LIMIT - 1] + "…"
    return state, description


def render_text(report: dict[str, Any]) -> str:
    def short(sha: str | None) -> str:
        return (sha or "-")[:12]

    lines = [
        f"gate run: base {short(report['base'])}, head {short(report['head'])},"
        f" order {report['order_id'] or '-'}, PR {report['pr'] or '-'}"
    ]
    for entry in report["gates"]:
        lines.append(f"{entry['outcome']:<10} {entry['id']}  [{', '.join(entry['intents'])}]")
        if entry["outcome"] != "pass":
            lines += [f"    {message}" for message in entry["messages"]]
    lines.append("per intent:")
    for intent, results in sorted(report["intents"].items()):
        lines += [f"  {intent}: {r['gate']} {r['outcome']}" for r in results]
    tally = {word: 0 for word in ("fail", "overridden", "pass")}
    for entry in report["gates"]:
        tally[entry["outcome"]] += 1
    lines.append(
        f"result: {tally['fail']} failed, {tally['overridden']} overridden, {tally['pass']} passed"
    )
    return "\n".join(lines)
