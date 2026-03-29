"""Minimal valid ``DecodedValues`` / ``BuiltRubrics`` / assessor outputs for graph tests."""

from app.agents.compose_values import compose_values
from app.agents.models import (
    AssessorResult,
    BuiltRubrics,
    ComposedValues,
    DecodedValues,
    RubricDimension,
    ValueDefinition,
    ValueRubric,
    WriterOutput,
)


def _dim(prefix: str, i: int) -> RubricDimension:
    return RubricDimension(
        name=f"{prefix}_d{i}",
        description="Test dimension.",
        score_1="1",
        score_2="2",
        score_3="3",
        score_4="4",
        score_5="5",
    )


def make_value_rubric(value_id: str, name: str) -> ValueRubric:
    dims = [_dim(value_id, i) for i in range(5)]
    return ValueRubric(value_id=value_id, value_name=name, dimensions=dims)


def sample_decoded_values() -> DecodedValues:
    values = [
        ValueDefinition(
            value_id=f"V{i}",
            name=f"Value {i}",
            description="Test value.",
            raw_weight=1.0,
        )
        for i in range(1, 6)
    ]
    return DecodedValues(values=values, rationale="Fixture rationale for tests.")


def sample_composed_values() -> ComposedValues:
    """Domain-only composition (no craft) for tests that expect five value assessors."""
    return compose_values(sample_decoded_values(), craft_enabled=False)


def sample_built_rubrics() -> BuiltRubrics:
    rubrics = [make_value_rubric(f"V{i}", f"Value {i}") for i in range(1, 6)]
    return BuiltRubrics(rubrics=rubrics)


def sample_writer_output(text: str = "Fixture draft paragraph.") -> WriterOutput:
    return WriterOutput(draft_text=text)


def sample_assessor_result(value_id: str, scores: list[int] | None = None) -> AssessorResult:
    s = scores if scores is not None else [3, 3, 3, 3, 3]
    return AssessorResult(
        value_id=value_id,
        dimension_scores=s,
        keep=["fixture keep"],
        change=["fixture change"],
    )
