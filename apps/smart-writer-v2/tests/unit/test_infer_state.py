"""Infer-state slot extraction for the P5 turn router (no LLM)."""

from __future__ import annotations

from app.agents.clarify import clarify_text_for_missing
from app.agents.infer_state import (
    classify_grant_beachhead,
    extract_intent_slots,
    infer_web_research_enabled,
    merge_intent_slots,
    missing_grant_slots,
    next_grant_beachhead,
)
from app.store import IntentSlots
from tests.contract.grant_flow import (
    EMPTY_WHOM_ASK_PROMPT,
    FACTUAL_LOW_PROMPT,
    GRANT_PROMPT,
    NONGRANT_PROMPT,
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


def test_infer_web_research_defaults_on_and_disable_phrase_offs() -> None:
    assert infer_web_research_enabled(GRANT_PROMPT) is True
    assert infer_web_research_enabled(FACTUAL_LOW_PROMPT) is True
    assert infer_web_research_enabled(GRANT_PROMPT + " Do not use web research.") is False


def test_classify_grant_beachhead_f2_and_nongrant_genre() -> None:
    assert classify_grant_beachhead(GRANT_PROMPT) == "grant"
    assert classify_grant_beachhead(EMPTY_WHOM_ASK_PROMPT) == "unknown"
    assert classify_grant_beachhead(WHOM_ASK_FILLED_WHY_EMPTY_PROMPT) == "grant"
    assert classify_grant_beachhead(NONGRANT_PROMPT) == "nongrant"
    assert classify_grant_beachhead("Write a fundraising letter for our work") == "grant"
    assert classify_grant_beachhead("hello") == "unknown"
    # F2: grant-positive wins over explainer genre
    assert (
        classify_grant_beachhead(
            "Write an explainer asking the Ford Foundation for $50,000"
        )
        == "grant"
    )


def test_next_grant_beachhead_unknown_keeps_current() -> None:
    assert next_grant_beachhead(True, "hello") is True
    assert next_grant_beachhead(False, "make it warmer") is False
    assert next_grant_beachhead(True, NONGRANT_PROMPT) is False
    assert next_grant_beachhead(False, GRANT_PROMPT) is True
