"""Schema-first dual-axis assessor (T082 / D8)."""

from __future__ import annotations

import json
from functools import lru_cache

from pydantic_ai import Agent

from app.config import get_openai_api_key
from app.models import AssessorOutput, DimensionScore, Rubric

_ASSESSOR_SYSTEM = """\
You score a draft against a dual-axis rubric (Axis A = intent substance, Axis B = properties).
Return one score per rubric dimension id (cover EVERY id in the rubric).
Scores are numeric 1.0–5.0. aggregate_score is the sum of dimension scores.
feedback is concrete revision guidance for the next writer turn (nonempty).
Do not invent dimension ids that are not in the rubric.
"""

TARGET_SCORE_PER_DIMENSION = 4.0


@lru_cache(maxsize=4)
def _assessor_agent() -> Agent[None, AssessorOutput]:
    return Agent(
        "openai:gpt-4o",
        output_type=AssessorOutput,
        system_prompt=_ASSESSOR_SYSTEM,
    )


def openai_assess_enabled() -> bool:
    """Live OpenAI only — skip LLM for unset/fake test keys."""
    key = get_openai_api_key()
    if key is None:
        return False
    lowered = key.lower()
    return not (lowered.startswith("sk-test") or "fake" in lowered)


def _normalize_scores(rubric: Rubric, raw: AssessorOutput) -> AssessorOutput:
    """Ensure every rubric dimension is scored (T48 dual-axis coverage)."""
    by_id = {d.id.strip(): d.score for d in raw.dimension_scores if d.id.strip()}
    dims: list[DimensionScore] = []
    for dim in rubric.all_dimensions():
        score = by_id.get(dim.id)
        if score is None or isinstance(score, bool):
            score = 1.0
        dims.append(DimensionScore(id=dim.id, score=float(score)))
    aggregate = float(sum(d.score for d in dims))
    feedback = (raw.feedback or "").strip() or (
        "Revise toward unmet dual-axis rubric dimensions."
    )
    return AssessorOutput(
        dimension_scores=dims,
        aggregate_score=aggregate,
        feedback=feedback,
    )


def assess_draft_heuristic(body: str, rubric: Rubric) -> AssessorOutput:
    """Deterministic assess path used when LLM is disabled (same coverage contract)."""
    text = (body or "").lower()
    dims: list[DimensionScore] = []
    for dim in rubric.all_dimensions():
        tokens = [t for t in dim.id.replace(".", " ").split() if len(t) > 2]
        label_bits = [t.lower() for t in dim.label.replace("/", " ").split() if len(t) > 2]
        needles = [*tokens, *label_bits]
        hits = sum(1 for n in needles if n in text)
        if not text.strip():
            score = 1.0
        elif hits >= 1 or len(text) >= 80:
            score = 4.5
        else:
            score = 3.0
        dims.append(DimensionScore(id=dim.id, score=score))
    aggregate = float(sum(d.score for d in dims))
    unmet = [d.id for d in dims if d.score < TARGET_SCORE_PER_DIMENSION]
    if unmet:
        feedback = (
            "Strengthen these rubric dimensions before the next draft: "
            + ", ".join(unmet)
            + "."
        )
    else:
        feedback = "Dual-axis targets met; preserve strengths on the next pass."
    return AssessorOutput(
        dimension_scores=dims,
        aggregate_score=aggregate,
        feedback=feedback,
    )


def targets_met(assessment: AssessorOutput, rubric: Rubric) -> bool:
    """Score gate: every rubric dimension at or above target."""
    by_id = {d.id: d.score for d in assessment.dimension_scores}
    for dim in rubric.all_dimensions():
        if float(by_id.get(dim.id, 0.0)) < TARGET_SCORE_PER_DIMENSION:
            return False
    return True


async def assess_draft(*, body: str, rubric: Rubric) -> AssessorOutput:
    """Score draft against rubric; LLM when enabled, else heuristic assess path."""
    if not openai_assess_enabled():
        return assess_draft_heuristic(body, rubric)
    payload = {
        "draft": body,
        "rubric": {
            "rubric_id": rubric.rubric_id,
            "dimensions": [d.model_dump() for d in rubric.all_dimensions()],
        },
        "instruction": (
            "Score every dimension id. Cover both Axis A and Axis B. "
            "aggregate_score must be the sum of dimension scores."
        ),
    }
    result = await _assessor_agent().run(json.dumps(payload, indent=2))
    return _normalize_scores(rubric, result.output)
