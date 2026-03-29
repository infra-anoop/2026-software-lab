"""Canonical library mapping and catalog validation."""

import pytest

from app.agents.canonical_library import value_definition_from_canonical_entry
from app.agents.models import CanonicalValueEntry, ValueRubric
from tests.fixtures.sample_payloads import make_value_rubric


def _minimal_rubric(value_id: str) -> ValueRubric:
    return make_value_rubric(value_id, "Lib name")


def test_value_definition_from_canonical_entry_mapping() -> None:
    entry = CanonicalValueEntry(
        canonical_id="grant_x",
        name="Grant X",
        short_description="Short copy for assessors.",
        match_text="grant nonprofit annual appeal",
        rubric=_minimal_rubric("LIB_grant_x"),
    )
    vd = value_definition_from_canonical_entry(entry)
    assert vd.value_id == "LIB_grant_x"
    assert vd.name == "Grant X"
    assert vd.description == "Short copy for assessors."
    assert vd.canonical_id == "grant_x"
    assert vd.raw_weight == 1.0


def test_canonical_entry_rejects_mismatched_rubric_value_id() -> None:
    with pytest.raises(ValueError, match="rubric.value_id"):
        CanonicalValueEntry(
            canonical_id="grant_x",
            name="Grant X",
            short_description="s",
            match_text="m",
            rubric=_minimal_rubric("WRONG_ID"),
        )
