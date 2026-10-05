"""`verdict.reviewer-family-differs` and `verdict.inputs-isolated` (I-P3, FR-011/011a).

Both judge the order's latest verdict at head (highest `verdict-NN`). A work-order PR
with no verdict is not reviewed and is blocked.

- family: the reviewer family is derived from `reviewer_model` through
  `factory.toml [families]`; it must be known, equal the declared `reviewer_family`,
  and differ from the family of the handoff's `author_model`.
- isolation: every input is a path that exists in git at its sha.
"""

from __future__ import annotations

from collections.abc import Callable

from factory.api import GateContext, GateResult
from factory.bus.models import Handoff, Verdict
from factory.gates.pr._bus import head_messages, order_messages, suffix_number
from factory.gates.repo._git import failed, object_type, outcome, passed

FAMILY_GATE = "verdict.reviewer-family-differs"
ISOLATED_GATE = "verdict.inputs-isolated"


def _latest(ctx: GateContext, order_id: str) -> tuple[Verdict | None, Handoff | None]:
    own = order_messages(head_messages(ctx), order_id)
    verdicts = sorted((m for m in own if isinstance(m, Verdict)), key=lambda m: suffix_number(m.id))
    handoffs = [m for m in own if isinstance(m, Handoff)]
    return (verdicts[-1] if verdicts else None), (handoffs[0] if handoffs else None)


def _with_verdict(
    gate_id: str, ctx: GateContext, judge: Callable[[Verdict, Handoff | None], GateResult]
) -> GateResult:
    if ctx.order_id is None:
        return passed(gate_id, "not a work-order PR")
    latest, handoff = _latest(ctx, ctx.order_id)
    if latest is None:
        return failed(gate_id, [f"order {ctx.order_id} has no verdict at head (not reviewed)"])
    return judge(latest, handoff)


def run_reviewer_family_differs(ctx: GateContext) -> GateResult:
    def judge(latest: Verdict, handoff: Handoff | None) -> GateResult:
        if handoff is None:
            return failed(FAMILY_GATE, [f"order {ctx.order_id} has no handoff at head"])
        settings = ctx.config
        reviewer = settings.family_of(latest.reviewer_model)
        author = settings.family_of(handoff.author_model)
        problems = []
        if reviewer is None:
            problems.append(
                f"{latest.id}: reviewer model {latest.reviewer_model!r} has no family in"
                " factory.toml [families]"
            )
        elif reviewer != latest.reviewer_family:
            problems.append(
                f"{latest.id}: reviewer model {latest.reviewer_model!r} is family {reviewer!r},"
                f" not the declared {latest.reviewer_family!r}"
            )
        if reviewer is not None and reviewer == author:
            problems.append(
                f"{latest.id}: reviewer family {reviewer!r} is the author's family"
                f" ({handoff.author_model!r})"
            )
        return outcome(
            FAMILY_GATE, problems, f"{latest.id}: reviewer family {reviewer} differs from {author}"
        )

    return _with_verdict(FAMILY_GATE, ctx, judge)


def run_inputs_isolated(ctx: GateContext) -> GateResult:
    def judge(latest: Verdict, handoff: Handoff | None) -> GateResult:
        problems = []
        for item in latest.inputs:
            if object_type(ctx.repo_path, f"{item.sha}^{{commit}}") != "commit":
                problems.append(f"{latest.id}: input sha {item.sha} is not a commit in the repo")
            elif object_type(ctx.repo_path, f"{item.sha}:{item.path}") is None:
                problems.append(f"{latest.id}: input {item.path} does not exist at {item.sha}")
        if not latest.inputs:
            problems.append(f"{latest.id}: lists no inputs")
        return outcome(ISOLATED_GATE, problems, f"{latest.id}: every input is in git at its sha")

    return _with_verdict(ISOLATED_GATE, ctx, judge)
