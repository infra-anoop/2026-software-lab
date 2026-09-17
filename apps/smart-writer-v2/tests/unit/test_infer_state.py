"""Infer-state slot extraction for the P5 turn router (no LLM)."""

from __future__ import annotations

from app.agents.clarify import clarify_text_for_missing
from app.agents.infer_state import (
    extract_intent_slots,
    merge_intent_slots,
    missing_grant_slots,
)
from app.store import IntentSlots
from tests.contract.grant_flow import (
    EMPTY_WHOM_ASK_PROMPT,
    GRANT_PROMPT,
    WHOM_ASK_FILLED_WHY_EMPTY_PROMPT,
)


def test_empty_whom_ask_prompt_missing_whom_and_ask() -> None:
    slots = merge_intent_slots(IntentSlots(), extract_intent_slots(EMPTY_WHOM_ASK_PROMPT))
    missing = missing_grant_slots(slots)
    assert "whom" in missing
    assert "ask" in missing
    assert slots.who
    assert slots.evidence


def test_whom_ask_filled_why_empty_still_missing_why_or_evidence() -> None:
    slots = merge_intent_slots(
        IntentSlots(),
        extract_intent_slots(WHOM_ASK_FILLED_WHY_EMPTY_PROMPT),
    )
    missing = missing_grant_slots(slots)
    assert slots.who
    assert slots.whom
    assert slots.ask
    assert "why_funder" in missing or "evidence" in missing


def test_filled_grant_prompt_has_no_missing_slots() -> None:
    slots = merge_intent_slots(IntentSlots(), extract_intent_slots(GRANT_PROMPT))
    assert missing_grant_slots(slots) == []


def test_clarify_copy_has_no_structured_labels() -> None:
    text = clarify_text_for_missing(["whom", "ask", "why_funder"])
    lowered = text.lower()
    assert "why_funder" not in lowered
    assert "intent_slots" not in lowered
    assert "axis" not in lowered
    assert "whom:" not in lowered
    assert "missing_hints" not in lowered
