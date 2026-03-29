"""Sanitization of planner output (invalid value_id stripping)."""

from app.agents.models import (
    ComposedValues,
    DocumentOutline,
    KeyPoint,
    OutlineSection,
    ResearchPlan,
    ResearchPlanningOutput,
    ValueDefinition,
)
from app.agents.research_planning import sanitize_research_planning_output


def _composed() -> ComposedValues:
    return ComposedValues(
        values=[
            ValueDefinition(
                value_id="V1",
                name="One",
                description="d",
                raw_weight=1.0,
                weight=1.0,
            ),
        ]
    )


def _valid_outline() -> DocumentOutline:
    return DocumentOutline(sections=[OutlineSection(heading="A", bullets=["b"])])


def test_sanitize_strips_unknown_value_ids() -> None:
    raw = ResearchPlanningOutput(
        research_plan=ResearchPlan(
            intent_summary="i",
            audience_and_constraints="a",
            key_points=[
                KeyPoint(value_id="V1", text="ok"),
                KeyPoint(value_id="BAD", text="drop"),
            ],
            facts_to_include=[],
            open_questions=[],
            risks_or_caveats=[],
            suggested_research_queries=[],
            coverage_checklist=[],
        ),
        outline=_valid_outline(),
    )
    out = sanitize_research_planning_output(raw, _composed())
    assert out is not None
    assert [kp.value_id for kp in out.research_plan.key_points] == ["V1"]


def test_sanitize_returns_none_when_outline_empty() -> None:
    """Malformed planner output can carry an empty sections list (bypass normal validation)."""
    outline = DocumentOutline.model_construct(title=None, sections=[])
    raw = ResearchPlanningOutput.model_construct(
        research_plan=ResearchPlan(
            intent_summary="i",
            audience_and_constraints="a",
            key_points=[KeyPoint(value_id="V1", text="k")],
            facts_to_include=[],
            open_questions=[],
            risks_or_caveats=[],
            suggested_research_queries=[],
            coverage_checklist=[],
        ),
        outline=outline,
    )
    assert sanitize_research_planning_output(raw, _composed()) is None
