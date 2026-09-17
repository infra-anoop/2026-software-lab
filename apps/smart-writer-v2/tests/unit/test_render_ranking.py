"""T050 weave ranking into writer program text."""

from __future__ import annotations

from app.prompts.render import weave_property_ranking


def test_weave_includes_closed_ids_and_factual_tone_only() -> None:
    weaved = weave_property_ranking("Base writer.", ["warm", "factual"])
    assert "warm" in weaved
    assert "factual" in weaved
    assert "tone" in weaved.lower() or "emphasis" in weaved.lower()
    assert "disable" in weaved.lower()
    assert "materials_bundle" in weaved
    assert weaved.startswith("Base writer.")
