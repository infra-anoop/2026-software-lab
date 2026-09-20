"""Shared dual-axis writer↔assessor inner loop (D8 / T083–T084)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.agents.assessor import assess_draft, targets_met
from app.agents.rubric_builder import build_dual_axis_rubric
from app.config import get_max_inner_assessor_turns
from app.models import LoopMetadata, LoopScoreEntry, Rubric, StopReason

WriteFn = Callable[[str | None, str | None], Awaitable[str]]


def loop_metadata_dict(meta: LoopMetadata) -> dict[str, Any]:
    """Serialize loop metadata for GenerateResult / job snapshot."""
    return meta.model_dump()


async def run_scored_inner_loop(
    *,
    intent_slots: dict[str, str | None] | None,
    property_ranking: list[str] | None,
    user_text: str,
    write_turn: WriteFn,
    initial_body: str | None = None,
) -> tuple[str, str, dict[str, Any]]:
    """Rubric → write ↔ assess ≤ Settings max (default 8).

    Returns ``(final_body, rubric_id, loop_dict)``. Always runs a real assess
    path (LLM or heuristic) — never attaches canned assertion JSON.
    """
    rubric: Rubric = build_dual_axis_rubric(
        intent_slots=intent_slots,
        property_ranking=property_ranking,
        user_text=user_text,
    )
    max_iterations = get_max_inner_assessor_turns()
    max_iterations = max(max_iterations, 1)

    scores: list[LoopScoreEntry] = []
    body = initial_body or ""
    stop_reason: StopReason = "max_iterations"
    feedback: str | None = None

    for iteration in range(1, max_iterations + 1):
        if iteration == 1 and body.strip():
            pass
        else:
            body = await write_turn(body if body.strip() else None, feedback)

        assessment = await assess_draft(body=body, rubric=rubric)
        scores.append(
            LoopScoreEntry(
                iteration=iteration,
                dimension_scores=list(assessment.dimension_scores),
                aggregate_score=float(assessment.aggregate_score),
                feedback=assessment.feedback.strip(),
            )
        )
        feedback = assessment.feedback
        if targets_met(assessment, rubric) and iteration < max_iterations:
            stop_reason = "targets_met"
            break
        if targets_met(assessment, rubric) and iteration == max_iterations:
            # Cap reached on the same turn targets would have stopped earlier.
            stop_reason = "max_iterations"
            break

    meta = LoopMetadata(
        iterations=len(scores),
        max_iterations=max_iterations,
        aggregate_score=float(scores[-1].aggregate_score) if scores else 0.0,
        stop_reason=stop_reason,
        axis_a_dimension_count=len(rubric.axis_a_dimensions),
        axis_b_dimension_count=len(rubric.axis_b_dimensions),
        scores=scores,
    )
    return body, rubric.rubric_id, loop_metadata_dict(meta)
