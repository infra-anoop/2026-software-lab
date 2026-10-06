"""Gate `diff-within-owned-paths` (T044; FR-014; contracts/messages.md § Invariants).

Every changed path (added, modified or deleted; renames off) matches the effective
order's `owned_paths` or sits under the order's own `bus/orders/<order-id>/`.
"""

from __future__ import annotations

from factory.api import GateContext, GateResult
from factory.gates.drift._common import (
    OrderMissing,
    effective_order,
    failed,
    matches_any,
    passed,
    verdict,
)
from factory.gates.drift._git import Change

GATE = "diff-within-owned-paths"


def run(ctx: GateContext) -> GateResult:
    try:
        order = effective_order(ctx)
    except OrderMissing as exc:
        return failed(GATE, [f"{exc}; there are no owned paths to honor"])
    if order is None:
        return passed(GATE, "no order linked; ownership is checked on order PRs")
    own_dir = f"{ctx.config.bus_dir}/orders/{ctx.order_id}/"
    problems = [
        f"{change.path} ({change.status}) is outside the owned paths of {ctx.order_id}"
        for change in Change.of(ctx).files
        if not change.path.startswith(own_dir) and not matches_any(change.path, order.owned_paths)
    ]
    return verdict(GATE, problems, "every changed path is owned")
