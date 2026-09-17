"""Infer and merge grant intent slots from free-form text (T042).

HTTP uses deterministic extraction so contract tests do not call OpenAI.
The PydanticAI agent (`result_type=IntentSlotInference`) is the schema-first
path for later LLM-backed inference.
"""

from __future__ import annotations

import re
from functools import lru_cache

from pydantic import BaseModel
from pydantic_ai import Agent

from app.store import IntentSlots

SLOT_ORDER: tuple[str, ...] = ("who", "whom", "ask", "why_funder", "evidence")

_INTENT_SLOT_SYSTEM = """\
Extract internal grant intent slots from free-form user text.
who = applicant organization; whom = funder or audience; ask = what is requested
(including amount); why_funder = why this funder; evidence = results or proof of fit.
Leave a field null if the text does not support it. Do not guess.
This output is internal — never invent user-facing slot names.
"""


class IntentSlotInference(BaseModel):
    """PydanticAI result_type for grant intent slots."""

    who: str | None = None
    whom: str | None = None
    ask: str | None = None
    why_funder: str | None = None
    evidence: str | None = None


@lru_cache(maxsize=4)
def intent_slot_agent() -> Agent[None, IntentSlotInference]:
    """Schema-first slot agent (T042). HTTP turn router does not call this yet."""
    return Agent(
        "openai:gpt-4o",
        output_type=IntentSlotInference,
        system_prompt=_INTENT_SLOT_SYSTEM,
    )


def _clip(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip().strip(" ,;")
    return stripped or None


def extract_intent_slots(text: str) -> IntentSlotInference:
    """Deterministic slot fill from free-form text (no LLM)."""
    return IntentSlotInference(
        who=_extract_who(text),
        whom=_extract_whom(text),
        ask=_extract_ask(text),
        why_funder=_extract_why_funder(text),
        evidence=_extract_evidence(text),
    )


def _extract_who(text: str) -> str | None:
    org = re.search(r"([^.\n]+?)\s*\(\s*our org\s*\)", text, flags=re.IGNORECASE)
    if org:
        return _clip(org.group(1))
    we = re.search(
        r"(?:we're|we are)\s+([^,.]+?)(?:,|\.|$)",
        text,
        flags=re.IGNORECASE,
    )
    if we:
        return _clip(we.group(1))
    return None


def _extract_whom(text: str) -> str | None:
    asking = re.search(
        r"asking the\s+(.+?)\s+for\b",
        text,
        flags=re.IGNORECASE,
    )
    if asking:
        return _clip(asking.group(1))
    foundation = re.search(
        r"\b([A-Z][\w']*(?:\s+[A-Z][\w']*)*\s+Foundation)\b",
        text,
    )
    if foundation:
        return _clip(foundation.group(1))
    return None


def _extract_ask(text: str) -> str | None:
    amount = re.search(r"\$[\d,]+(?:\.\d+)?", text)
    if amount:
        return _clip(amount.group(0))
    return None


def _extract_why_funder(text: str) -> str | None:
    span = re.search(
        r"[^.]*\b(strateg(?:y|ies)|priorit(?:y|ies)|criteria|mission)\b[^.]*",
        text,
        flags=re.IGNORECASE,
    )
    if span:
        return _clip(span.group(0))
    return None


def _extract_evidence(text: str) -> str | None:
    span = re.search(
        r"[^.]*\b(report|evaluation|shows|gained|served)\b[^.]*",
        text,
        flags=re.IGNORECASE,
    )
    if span:
        return _clip(span.group(0))
    return None


def merge_intent_slots(current: IntentSlots, incoming: IntentSlotInference) -> IntentSlots:
    """Keep existing non-null slots; fill holes from incoming."""
    return IntentSlots(
        who=current.who or _clip(incoming.who),
        whom=current.whom or _clip(incoming.whom),
        ask=current.ask or _clip(incoming.ask),
        why_funder=current.why_funder or _clip(incoming.why_funder),
        evidence=current.evidence or _clip(incoming.evidence),
    )


def missing_grant_slots(slots: IntentSlots) -> list[str]:
    """Internal ids of grant slots that are still empty (FR-003a)."""
    missing: list[str] = []
    for name in SLOT_ORDER:
        if not _clip(getattr(slots, name)):
            missing.append(name)
    return missing


def clarify_text_for_missing(missing: list[str]) -> str:
    """NL questions for missing slots — no Axis / why_funder / Whom: labels (T9)."""
    questions: list[str] = []
    mapping = {
        "who": "Which organization is making this request?",
        "whom": "Who is the funder or audience for this request?",
        "ask": "What should we ask for, including any amount?",
        "why_funder": "Why this funder in particular—what do they care about that you meet?",
        "evidence": "What results or proof of fit can we point to?",
    }
    for name in missing:
        line = mapping.get(name)
        if line:
            questions.append(line)
    if not questions:
        return "Could you share a bit more so the draft can be specific?"
    return " ".join(questions)
