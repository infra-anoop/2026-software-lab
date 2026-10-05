"""`order-blocked-on-open-human-od` (governor-only, I-X3).

The effective order at head (order + amendments) may depend only on closed decisions.
A decision is closed when its lock is on the base branch: a lock added by the PR itself
does not count. A decision with neither request nor lock cannot be shown closed.
"""

from __future__ import annotations

from factory.api import GateContext, GateResult
from factory.bus.models import DecisionLock, DecisionRequest
from factory.gates.pr._bus import effective_order, head_messages, load_tolerant
from factory.gates.repo._git import failed, outcome, passed

GATE_ID = "order-blocked-on-open-human-od"


def run(ctx: GateContext) -> GateResult:
    if ctx.order_id is None:
        return passed(GATE_ID, "not a work-order PR")
    head = head_messages(ctx)
    order = effective_order(head, ctx.order_id)
    if order is None:
        return failed(GATE_ID, [f"order {ctx.order_id} not found at head"])
    if not order.depends_on_decisions:
        return passed(GATE_ID, f"order {ctx.order_id} depends on no decision")
    base = load_tolerant(ctx.repo_path, ctx.base_sha, ctx.config)
    locked = {m.decision_id for m in base if isinstance(m, DecisionLock)}
    requested = {m.id for m in [*base, *head] if isinstance(m, DecisionRequest)}
    problems = []
    for decision in order.depends_on_decisions:
        if decision in locked:
            continue
        if decision in requested:
            problems.append(f"order {ctx.order_id} depends on open decision {decision!r}")
        else:
            problems.append(
                f"order {ctx.order_id} depends on unknown decision {decision!r}"
                " (no request, and no lock on the base branch)"
            )
    return outcome(GATE_ID, problems, "every decision the order depends on is locked")
