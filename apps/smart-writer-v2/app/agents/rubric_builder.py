"""Dual-axis rubric builder (T081 / D8): Axis A intent + Axis B properties."""

from __future__ import annotations

from uuid import uuid4

from app.agents.infer_state import SLOT_ORDER
from app.models import Rubric, RubricDimension
from app.properties import SEED_PROPERTIES, filter_closed_ranking

_AXIS_A_LABELS: dict[str, str] = {
    "who": "Applicant clarity",
    "whom": "Funder fit",
    "ask": "Ask concreteness",
    "why_funder": "Why-this-funder rationale",
    "evidence": "Evidence strength",
}

_AXIS_A_DESCRIPTIONS: dict[str, str] = {
    "who": "Draft clearly identifies the applicant organization and role.",
    "whom": "Draft addresses the named funder or audience with fit.",
    "ask": "Draft states a concrete ask (amount and/or request).",
    "why_funder": "Draft explains why this funder or audience.",
    "evidence": "Draft includes results, proof, or criteria-tied evidence.",
}

_DEFAULT_AXIS_B: tuple[str, ...] = ("persuasive", "specific")


def build_dual_axis_rubric(
    *,
    intent_slots: dict[str, str | None] | None,
    property_ranking: list[str] | None,
    user_text: str = "",
) -> Rubric:
    """Build a rubric covering both F6 axes — not thinner than V1 scored capability.

    Axis A dimensions come from filled grant intent slots (substance criteria).
    Axis B dimensions come from closed property ranking / steering.
    Always returns ≥1 dimension per axis.
    """
    slots = intent_slots or {}
    axis_a: list[RubricDimension] = []
    for slot in SLOT_ORDER:
        value = slots.get(slot)
        if value is None or not str(value).strip():
            continue
        axis_a.append(
            RubricDimension(
                id=f"axis_a.{slot}",
                axis="a",
                label=_AXIS_A_LABELS.get(slot, slot),
                description=(
                    f"{_AXIS_A_DESCRIPTIONS.get(slot, slot)} "
                    f"Slot substance: {str(value).strip()[:200]}"
                ),
            )
        )
    if not axis_a:
        # Non-grant / sparse slots: still require Axis A substance criterion.
        snippet = (user_text or "writing goal").strip()[:160] or "writing goal"
        axis_a.append(
            RubricDimension(
                id="axis_a.intent_substance",
                axis="a",
                label="Intent substance",
                description=f"Draft fulfills the user's stated writing goal: {snippet}",
            )
        )

    ranking = filter_closed_ranking(list(property_ranking or []))
    if not ranking:
        ranking = list(_DEFAULT_AXIS_B)
    axis_b: list[RubricDimension] = []
    for prop in ranking:
        if prop not in SEED_PROPERTIES:
            continue
        axis_b.append(
            RubricDimension(
                id=f"axis_b.{prop}",
                axis="b",
                label=prop,
                description=f"Draft exhibits the '{prop}' property from Axis B steering.",
            )
        )
    if not axis_b:
        axis_b.append(
            RubricDimension(
                id="axis_b.persuasive",
                axis="b",
                label="persuasive",
                description="Draft exhibits persuasive property steering.",
            )
        )

    return Rubric(
        rubric_id=f"rub_{uuid4().hex[:12]}",
        axis_a_dimensions=axis_a,
        axis_b_dimensions=axis_b,
    )
