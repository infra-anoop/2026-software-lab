"""NL-only clarify questions (FR-021 / T9 / T044)."""

from __future__ import annotations

_QUESTIONS = {
    "who": "Which organization is making this request?",
    "whom": "Who is the funder or audience for this request?",
    "ask": "What should we ask for, including any amount?",
    "why_funder": "Why this funder in particular—what do they care about that you meet?",
    "evidence": "What results or proof of fit can we point to?",
}


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
