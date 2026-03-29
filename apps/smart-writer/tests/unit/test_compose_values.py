"""Tests for compose_values weight normalization (design §7.5)."""

import pytest

from app.agents.compose_values import compose_values
from app.agents.models import DecodedValues, ValueDefinition, validate_decoded_domain_slot_count


def _five_domain() -> DecodedValues:
    return DecodedValues(
        values=[
            ValueDefinition(
                value_id=f"V{i}",
                name="n",
                description="d",
                raw_weight=1.0,
            )
            for i in range(1, 6)
        ],
        rationale="r",
    )


def test_compose_domain_only_normalizes_to_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_CRAFT_ENABLED", "0")
    c = compose_values(_five_domain(), craft_enabled=False)
    assert len(c.values) == 5
    s = sum(v.weight or 0 for v in c.values)
    assert abs(s - 1.0) < 1e-9
    assert all(v.provenance == "task_derived" for v in c.values)


def test_compose_craft_and_domain_splits_alpha(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_CRAFT_ENABLED", "1")
    monkeypatch.setenv("SMART_WRITER_CRAFT_WEIGHT_MASS", "0.35")
    c = compose_values(_five_domain(), craft_enabled=True)
    assert len(c.values) == 5 + 4
    craft_w = sum(v.weight or 0 for v in c.values if v.provenance == "designer_craft")
    dom_w = sum(v.weight or 0 for v in c.values if v.provenance == "task_derived")
    assert abs(craft_w - 0.35) < 1e-6
    assert abs(dom_w - 0.65) < 1e-6
    assert abs(sum(v.weight or 0 for v in c.values) - 1.0) < 1e-9


def test_compose_subset_craft_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_CRAFT_ENABLED", "1")
    monkeypatch.setenv("SMART_WRITER_CRAFT_KEYS", "grammar_mechanics,clarity_coherence")
    monkeypatch.setenv("SMART_WRITER_CRAFT_WEIGHT_MASS", "0.35")
    c = compose_values(_five_domain(), craft_enabled=True)
    assert len(c.values) == 5 + 2
    ids = {v.value_id for v in c.values}
    assert "CRAFT_GRAMMAR" in ids and "CRAFT_CLARITY" in ids
    assert "CRAFT_STRUCTURE" not in ids


def test_compose_library_rows_precede_task_derived(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_CRAFT_ENABLED", "0")
    lib = ValueDefinition(
        value_id="LIB_c1",
        name="Library",
        description="ld",
        raw_weight=2.0,
        canonical_id="c1",
    )
    decoded = DecodedValues(
        values=[
            ValueDefinition(value_id=f"V{i}", name="n", description="d", raw_weight=1.0)
            for i in range(1, 5)
        ],
        rationale="r",
    )
    c = compose_values(decoded, craft_enabled=False, library_domain_rows=[lib])
    assert [v.value_id for v in c.values] == ["LIB_c1", "V1", "V2", "V3", "V4"]
    assert c.values[0].provenance == "library_canonical"
    assert abs(sum(v.weight or 0 for v in c.values) - 1.0) < 1e-9


def test_validate_decoded_domain_slot_count_k_zero() -> None:
    vals = [ValueDefinition(value_id=f"V{i}", name="n", description="d", raw_weight=1.0) for i in range(5)]
    validate_decoded_domain_slot_count(vals, library_domain_count=0)
    with pytest.raises(ValueError, match="k=0"):
        validate_decoded_domain_slot_count(vals[:4], library_domain_count=0)


def test_validate_decoded_domain_slot_count_with_library() -> None:
    vals = [ValueDefinition(value_id=f"V{i}", name="n", description="d", raw_weight=1.0) for i in range(1, 5)]
    validate_decoded_domain_slot_count(vals, library_domain_count=1)
    with pytest.raises(ValueError, match="k=1"):
        validate_decoded_domain_slot_count(vals[:3], library_domain_count=1)
