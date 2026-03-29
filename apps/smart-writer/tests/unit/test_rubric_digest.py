"""Deterministic rubric digest for planner input (golden / snapshot-style)."""

from app.agents.models import BuiltRubrics, ComposedValues, RubricDimension, ValueDefinition, ValueRubric
from app.agents.rubric_digest import build_rubric_digest_for_planner


def _sample_composed() -> ComposedValues:
    return ComposedValues(
        values=[
            ValueDefinition(
                value_id="V1",
                name="Clarity",
                description="Clear communication.",
                raw_weight=1.0,
                weight=1.0,
            ),
            ValueDefinition(
                value_id="V2",
                name="Brevity",
                description="Concise prose.",
                raw_weight=1.0,
                weight=1.0,
            ),
        ]
    )


def _dim(name: str, desc: str) -> RubricDimension:
    return RubricDimension(
        name=name,
        description=desc,
        score_1="1",
        score_2="2",
        score_3="3",
        score_4="4",
        score_5="5",
    )


def _sample_rubrics() -> BuiltRubrics:
    return BuiltRubrics(
        rubrics=[
            ValueRubric(
                value_id="V1",
                value_name="Clarity",
                dimensions=[
                    _dim("Structure", "First sentence of structure description. Rest is noise."),
                    _dim("Tone", "Tone guidance here."),
                    _dim("Precision", "Precise wording."),
                    _dim("Flow", "Logical flow."),
                    _dim("Accessibility", "Readable by target audience."),
                ],
            ),
            ValueRubric(
                value_id="V2",
                value_name="Brevity",
                dimensions=[
                    _dim("Economy", "Word economy."),
                    _dim("Focus", "Stay on topic."),
                    _dim("Pacing", "Good pacing."),
                    _dim("Redundancy", "Avoid repetition."),
                    _dim("Density", "Information density."),
                ],
            ),
        ]
    )


def test_build_rubric_digest_deterministic_snapshot() -> None:
    c = _sample_composed()
    r = _sample_rubrics()
    d1 = build_rubric_digest_for_planner(c, r)
    d2 = build_rubric_digest_for_planner(c, r)
    assert d1 == d2
    assert "### V1 — Clarity" in d1
    assert "### V2 — Brevity" in d1
    assert "**Structure**" in d1
    assert "First sentence of structure description." in d1 or "First sentence" in d1


def test_digest_respects_total_cap() -> None:
    c = _sample_composed()
    r = _sample_rubrics()
    short = build_rubric_digest_for_planner(c, r, max_total_digest_chars=120)
    assert len(short) <= 200

