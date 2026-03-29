"""ValueDefinition provenance derivation (Option B)."""

import pytest

from app.agents.models import ValueDefinition


def test_provenance_task_derived_when_no_keys() -> None:
    v = ValueDefinition(value_id="V1", name="n", description="d", raw_weight=1.0)
    assert v.provenance == "task_derived"
    assert v.craft_key is None
    assert v.canonical_id is None


def test_provenance_designer_craft_when_craft_key() -> None:
    v = ValueDefinition(
        value_id="CRAFT_GRAMMAR",
        name="g",
        description="d",
        raw_weight=1.0,
        craft_key="grammar_mechanics",
    )
    assert v.provenance == "designer_craft"


def test_provenance_library_canonical_when_canonical_id() -> None:
    v = ValueDefinition(
        value_id="LIB_grant_nonprofit_persuasion",
        name="g",
        description="d",
        raw_weight=1.0,
        canonical_id="grant_nonprofit_persuasion",
    )
    assert v.provenance == "library_canonical"


def test_craft_and_canonical_mutex() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        ValueDefinition(
            value_id="X",
            name="n",
            description="d",
            raw_weight=1.0,
            craft_key="grammar_mechanics",
            canonical_id="foo",
        )


def test_library_value_id_must_match_option_a() -> None:
    with pytest.raises(ValueError, match="library_canonical row"):
        ValueDefinition(
            value_id="LIB_wrong",
            name="g",
            description="d",
            raw_weight=1.0,
            canonical_id="grant_nonprofit_persuasion",
        )
