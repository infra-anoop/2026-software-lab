"""D8: generate orchestrator must return scored loop metadata (unit seam).

T079 / T080: HTTP job snapshot is the D8 contract gate; this unit is a seam
landmine — when T081+ wires the loop, ``run_generate`` must return
``rubric_id`` + ``loop`` (same consistency locks as contract helper).
Uses canned no-LLM path (sk-test key); does not stub assertion JSON onto the graph.
"""

from __future__ import annotations

import pytest

from app.config import get_max_inner_assessor_turns, get_settings
from app.models import MaterialRef
from app.orchestrator.generate_graph import run_generate


@pytest.mark.asyncio
async def test_run_generate_includes_scored_loop_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GenerateResult must carry loop + rubric_id; iterations honor Settings max."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    get_settings.cache_clear()
    try:
        result = await run_generate(
            conversation_id="c-loop-unit",
            user_text=(
                "Literacy Partners asks the Ford Foundation for $50,000 for adult "
                "literacy in NYC."
            ),
            materials=[
                MaterialRef(
                    uri="https://example.org/ford-education-criteria",
                    label="Ford education criteria",
                )
            ],
            humor_enabled=False,
            web_research_enabled=False,
        )
        assert "rubric_id" in result
        assert isinstance(result["rubric_id"], str) and result["rubric_id"].strip()
        assert "loop" in result, "scored writer↔assessor loop missing from generate result"
        loop = result["loop"]
        assert isinstance(loop, dict)
        max_inner = get_max_inner_assessor_turns()
        assert loop.get("max_iterations") == max_inner
        iterations = loop.get("iterations")
        assert isinstance(iterations, int)
        assert 1 <= iterations <= max_inner
        scores = loop.get("scores")
        assert isinstance(scores, list) and len(scores) == iterations
        stop_reason = loop.get("stop_reason")
        assert stop_reason in {"max_iterations", "targets_met", "error"}
        if stop_reason == "max_iterations":
            assert iterations == max_inner
        elif stop_reason == "targets_met":
            assert iterations < max_inner
        assert isinstance(loop.get("aggregate_score"), (int, float))
        axis_a = int(loop.get("axis_a_dimension_count") or 0)
        axis_b = int(loop.get("axis_b_dimension_count") or 0)
        assert axis_a >= 1 and axis_b >= 1
        min_dims = axis_a + axis_b
        for entry in scores:
            dims = entry.get("dimension_scores")
            assert isinstance(dims, list) and len(dims) >= min_dims
    finally:
        get_settings.cache_clear()
