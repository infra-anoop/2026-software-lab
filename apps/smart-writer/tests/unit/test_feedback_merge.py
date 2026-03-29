"""Pure-function tests (no LLM, no heavy imports)."""

from app.agents.feedback_merge import (
    aggregate_sum_scores,
    craft_aggregate,
    domain_aggregate,
    merge_assessor_feedback,
    merge_value_and_grounding_feedback,
    weighted_mean_aggregate,
)
from app.agents.models import AssessorResult, ComposedValues, GroundingAssessment, GroundingIssue, ValueDefinition


def _two_value_composed() -> ComposedValues:
    return ComposedValues(
        values=[
            ValueDefinition(
                value_id="V_LOW",
                name="a",
                description="b",
                raw_weight=1.0,
                weight=0.5,
            ),
            ValueDefinition(
                value_id="V_HIGH",
                name="c",
                description="d",
                raw_weight=1.0,
                weight=0.5,
            ),
        ]
    )


def test_aggregate_sum_scores() -> None:
    results = [
        AssessorResult(
            value_id="V1",
            dimension_scores=[5, 5, 5, 5, 5],
            keep=["a"],
            change=["b"],
        ),
        AssessorResult(
            value_id="V2",
            dimension_scores=[1, 1, 1, 1, 1],
            keep=["c"],
            change=["d"],
        ),
    ]
    assert aggregate_sum_scores(results) == 25.0 + 5.0


def test_weighted_mean_with_equal_weights_matches_mean_of_totals() -> None:
    composed = _two_value_composed()
    results = [
        AssessorResult(
            value_id="V_LOW",
            dimension_scores=[1, 1, 1, 1, 1],
            keep=["k1"],
            change=["c1"],
        ),
        AssessorResult(
            value_id="V_HIGH",
            dimension_scores=[5, 5, 5, 5, 5],
            keep=["k2"],
            change=["c2"],
        ),
    ]
    assert weighted_mean_aggregate(results, composed) == (5.0 + 25.0) / 2


def test_merge_orders_lowest_total_first_when_weights_equal() -> None:
    low = AssessorResult(
        value_id="V_LOW",
        dimension_scores=[1, 1, 1, 1, 1],
        keep=["k1"],
        change=["c1"],
    )
    high = AssessorResult(
        value_id="V_HIGH",
        dimension_scores=[5, 5, 5, 5, 5],
        keep=["k2"],
        change=["c2"],
    )
    text = merge_assessor_feedback([high, low], _two_value_composed())
    assert text.index("V_LOW") < text.index("V_HIGH")


def test_merge_prefers_higher_weight_on_same_total() -> None:
    """Same rubric total; larger weight × gap should appear first."""
    composed = ComposedValues(
        values=[
            ValueDefinition(
                value_id="A",
                name="a",
                description="b",
                raw_weight=1.0,
                weight=0.8,
            ),
            ValueDefinition(
                value_id="B",
                name="c",
                description="d",
                raw_weight=1.0,
                weight=0.2,
            ),
        ]
    )
    same = [3, 3, 3, 3, 3]
    ra = AssessorResult(value_id="A", dimension_scores=list(same), keep=["k"], change=["c"])
    rb = AssessorResult(value_id="B", dimension_scores=list(same), keep=["k"], change=["c"])
    text = merge_assessor_feedback([rb, ra], composed)
    assert text.index("A") < text.index("B")


def test_merge_tie_break_task_derived_before_craft() -> None:
    composed = ComposedValues(
        values=[
            ValueDefinition(
                value_id="CRAFT_X",
                name="craft",
                description="c",
                raw_weight=1.0,
                weight=0.5,
                craft_key="grammar_mechanics",
            ),
            ValueDefinition(
                value_id="V1",
                name="dom",
                description="d",
                raw_weight=1.0,
                weight=0.5,
            ),
        ]
    )
    same = [3, 3, 3, 3, 3]
    rc = AssessorResult(value_id="CRAFT_X", dimension_scores=list(same), keep=["k"], change=["c"])
    rd = AssessorResult(value_id="V1", dimension_scores=list(same), keep=["k"], change=["c"])
    text = merge_assessor_feedback([rc, rd], composed)
    assert text.index("V1") < text.index("CRAFT_X")


def test_domain_and_craft_aggregates_renormalize() -> None:
    composed = ComposedValues(
        values=[
            ValueDefinition(
                value_id="CRAFT_GRAMMAR",
                name="g",
                description="d",
                raw_weight=1.0,
                weight=0.175,
                craft_key="grammar_mechanics",
            ),
            ValueDefinition(
                value_id="CRAFT_CLARITY",
                name="c",
                description="d",
                raw_weight=1.0,
                weight=0.175,
                craft_key="clarity_coherence",
            ),
            ValueDefinition(
                value_id="V1",
                name="d1",
                description="d",
                raw_weight=1.5,
                weight=0.39,
            ),
            ValueDefinition(
                value_id="V2",
                name="d2",
                description="d",
                raw_weight=1.0,
                weight=0.26,
            ),
        ]
    )
    results = [
        AssessorResult(
            value_id="CRAFT_GRAMMAR",
            dimension_scores=[4, 4, 4, 4, 4],
            keep=["k"],
            change=["c"],
        ),
        AssessorResult(
            value_id="CRAFT_CLARITY",
            dimension_scores=[4, 3, 4, 4, 3],
            keep=["k"],
            change=["c"],
        ),
        AssessorResult(
            value_id="V1",
            dimension_scores=[3, 4, 3, 4, 3],
            keep=["k"],
            change=["c"],
        ),
        AssessorResult(
            value_id="V2",
            dimension_scores=[5, 5, 4, 4, 4],
            keep=["k"],
            change=["c"],
        ),
    ]
    assert abs(domain_aggregate(results, composed) - (0.6 * 17 + 0.4 * 22)) < 0.01
    assert abs(craft_aggregate(results, composed) - (0.5 * 20 + 0.5 * 18)) < 0.01


def test_merge_grounding_orders_must_before_value_then_should() -> None:
    composed = ComposedValues(
        values=[
            ValueDefinition(
                value_id="V1",
                name="n",
                description="d",
                raw_weight=1.0,
                weight=1.0,
            )
        ]
    )
    low = AssessorResult(
        value_id="V1",
        dimension_scores=[3, 3, 3, 3, 3],
        keep=["k"],
        change=["c"],
    )
    g = GroundingAssessment(
        grounding_score=0.5,
        issues=[
            GroundingIssue(
                severity="MUST_FIX",
                category="LIKELY_INVENTED_DETAIL",
                fix_guidance="Remove invented org name.",
            ),
            GroundingIssue(
                severity="SHOULD_FIX",
                category="TOO_GENERIC",
                fix_guidance="Add concrete program detail from evidence.",
            ),
        ],
        summary="s",
        writer_instructions="Align with retrieved donor name.",
    )
    text = merge_value_and_grounding_feedback([low], g, composed)
    assert "Grounding — must address" in text
    assert "Grounding — should fix" in text
    assert text.index("must address") < text.index("V1")
    assert text.index("V1") < text.index("should fix")
