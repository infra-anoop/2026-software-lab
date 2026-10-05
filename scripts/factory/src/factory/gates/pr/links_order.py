"""`pr-links-order` (I-P1): every PR is a work-order PR or a bus PR.

A work-order PR (head `wo/<order-id>`, so `ctx.order_id` is set) carries that order at
head. Any other head is a bus PR only when every change is under `bus/decisions/`,
`bus/corrections/` or `bus/postmortems/`.
"""

from __future__ import annotations

from factory.api import GateContext, GateResult
from factory.bus.models import WorkOrder
from factory.gates.pr._bus import head_messages
from factory.gates.repo._git import changed, failed, passed

GATE_ID = "pr-links-order"
BUS_PR_DIRS = ("decisions", "corrections", "postmortems")


def run(ctx: GateContext) -> GateResult:
    if ctx.order_id is not None:
        orders = [m for m in head_messages(ctx) if isinstance(m, WorkOrder)]
        if any(m.id == ctx.order_id for m in orders):
            return passed(GATE_ID, f"PR carries order {ctx.order_id}")
        return failed(
            GATE_ID,
            [f"head branch wo/{ctx.order_id} does not carry order {ctx.order_id} at head"],
        )
    prefixes = tuple(f"{ctx.config.bus_dir}/{name}/" for name in BUS_PR_DIRS)
    paths = [path for _, path in changed(ctx.repo_path, ctx.base_sha, ctx.head_sha)]
    outside = [path for path in paths if not path.startswith(prefixes)]
    if paths and not outside:
        return passed(GATE_ID, "bus PR (decisions, corrections, post-mortems only)")
    detail = f"; changes outside the bus PR folders: {', '.join(outside[:10])}" if outside else ""
    return failed(
        GATE_ID,
        [f"PR head is not a wo/<order-id> branch and the PR is not a bus-only PR{detail}"],
    )
