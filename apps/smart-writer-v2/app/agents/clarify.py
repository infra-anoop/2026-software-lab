"""NL-only clarify questions (FR-021 / T9 / T044). FR-003c: intent before steering."""

from __future__ import annotations

_QUESTIONS = {
    "who": "Which organization is making this request?",
    "whom": "Who is the funder or audience for this request?",
    "ask": "What should we ask for, including any amount?",
    "why_funder": "Why this funder in particular—what do they care about that you meet?",
    "evidence": "What results or proof of fit can we point to?",
}

_PROPERTY_CLARIFIER = (
    "If you want a tone emphasis, mention it in a few words "
    "(for example warm, persuasive, concise, or formal). "
    "You can also skip this and we'll draft."
)


def clarify_text_for_missing(missing: list[str]) -> str:
    """NL questions for missing slots — no Axis / why_funder / Whom: labels."""
    questions: list[str] = []
    for name in missing:
        line = _QUESTIONS.get(name)
        if line:
            questions.append(line)
    if not questions:
        return "Could you share a bit more so the draft can be specific?"
    return " ".join(questions)


def ranking_is_weak(ranking: list[str]) -> bool:
    """Empty ranking is a steering hole (FR-003b); it must not block grant write."""
    return len(ranking) == 0


def clarify_text_for_turn(missing_slots: list[str], ranking: list[str]) -> str:
    """Intent-slot questions before property clarifiers when both incomplete (FR-003c)."""
    if missing_slots:
        return clarify_text_for_missing(missing_slots)
    if ranking_is_weak(ranking):
        return _PROPERTY_CLARIFIER
    return "Could you share a bit more so the draft can be specific?"
