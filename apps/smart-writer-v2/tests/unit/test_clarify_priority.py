"""FR-003c: intent-slot questions before property clarifiers."""

from __future__ import annotations

from app.agents.clarify import clarify_text_for_turn


def test_intent_questions_omit_property_clarifier_when_slots_missing() -> None:
    text = clarify_text_for_turn(["whom", "ask"], ranking=[])
    lowered = text.lower()
    assert "funder" in lowered or "ask" in lowered
    assert "warm" not in lowered
    assert "persuasive" not in lowered
    assert "tone emphasis" not in lowered


def test_property_clarifier_only_when_slots_complete() -> None:
    text = clarify_text_for_turn([], ranking=[])
    lowered = text.lower()
    assert "tone" in lowered or "warm" in lowered
    assert "organization is making this request" not in lowered
