"""Minimal unit smoke test so pytest and coverage run. Expand with real tests."""

import pytest


def test_agent_models_importable() -> None:
    """Agent output schemas are importable (no OPENAI_API_KEY required)."""
    from app.agents.models import AssessorResult, DecodedValues, ValueDefinition

    assert DecodedValues is not None
    assert AssessorResult is not None
    assert ValueDefinition is not None
