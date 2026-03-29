"""
End-to-end workflow test with LLM calls mocked.

Preserves refactor safety: graph wiring, iteration counts, and assessor fan-out (5 values × N rounds)
without OpenAI or Supabase.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.orchestrator.run import run_workflow
from app.agents.models import (
    DocumentOutline,
    KeyPoint,
    OutlineSection,
    ResearchPlan,
    ResearchPlanningOutput,
)
from tests.fixtures.sample_payloads import (
    sample_assessor_result,
    sample_built_rubrics,
    sample_decoded_values,
    sample_writer_output,
)

# Craft off so composed value count matches mocked ``sample_built_rubrics`` (five rubrics).
_WORKFLOW_KWARGS = {
    "max_concurrent_llm": 2,
    "assess_parallel": False,
    "grounding_enabled": False,
    "craft_enabled": False,
    # Mocked tests do not patch the planner LLM; disable explicit planning for stable wiring tests.
    "research_planning_enabled": False,
}


@pytest.mark.asyncio
async def test_run_workflow_honors_max_iterations_with_mocks() -> None:
    decoded = sample_decoded_values()
    rubrics = sample_built_rubrics()
    draft = sample_writer_output("Round draft.")

    async def assess_side_effect(_rub: object, val: object, _draft: str, **_kw: object) -> object:
        return sample_assessor_result(val.value_id)

    with (
        patch("app.orchestrator.run.run_decode_values", new_callable=AsyncMock) as m_dec,
        patch("app.orchestrator.run.run_build_rubrics", new_callable=AsyncMock) as m_br,
        patch("app.orchestrator.run.run_writer", new_callable=AsyncMock) as m_w,
        patch("app.orchestrator.run.run_assess_one", new_callable=AsyncMock) as m_as,
    ):
        m_dec.return_value = decoded
        m_br.return_value = rubrics
        m_w.return_value = draft
        m_as.side_effect = assess_side_effect

        final = await run_workflow(
            {
                "raw_input": "fixture prompt for integration test",
                "max_iterations": 2,
                **_WORKFLOW_KWARGS,
            }
        )

        assert final["iterations"] == 2
        assert final["draft"] == draft.draft_text
        assert final["run_id"] is not None
        assert len(final.get("last_assessments") or []) == 5
        assert final.get("prompt_program_id") == "smart_writer_default"
        assert final.get("prompt_program_version") == "1.1.0"

        m_dec.assert_awaited_once()
        m_br.assert_awaited_once()
        assert m_w.await_count == 2
        assert m_as.await_count == 10


@pytest.mark.asyncio
async def test_run_workflow_single_iteration_stops() -> None:
    with (
        patch("app.orchestrator.run.run_decode_values", new_callable=AsyncMock) as m_dec,
        patch("app.orchestrator.run.run_build_rubrics", new_callable=AsyncMock) as m_br,
        patch("app.orchestrator.run.run_writer", new_callable=AsyncMock) as m_w,
        patch("app.orchestrator.run.run_assess_one", new_callable=AsyncMock) as m_as,
    ):
        m_dec.return_value = sample_decoded_values()
        m_br.return_value = sample_built_rubrics()
        m_w.return_value = sample_writer_output("Once.")

        async def assess_once(_r: object, val: object, _d: str, **_kw: object) -> object:
            return sample_assessor_result(val.value_id)

        m_as.side_effect = assess_once

        final = await run_workflow(
            {
                "raw_input": "x",
                "max_iterations": 1,
                **_WORKFLOW_KWARGS,
                "max_concurrent_llm": 1,
            }
        )

        assert final["iterations"] == 1
        assert m_w.await_count == 1
        assert m_as.await_count == 5


@pytest.mark.asyncio
async def test_run_workflow_resolves_prompt_parameters_and_profile_for_agents() -> None:
    """Versioned prompt program state is stored and passed into pipeline agents."""
    with (
        patch("app.orchestrator.run.run_decode_values", new_callable=AsyncMock) as m_dec,
        patch("app.orchestrator.run.run_build_rubrics", new_callable=AsyncMock) as m_br,
        patch("app.orchestrator.run.run_writer", new_callable=AsyncMock) as m_w,
        patch("app.orchestrator.run.run_assess_one", new_callable=AsyncMock) as m_as,
    ):
        m_dec.return_value = sample_decoded_values()
        m_br.return_value = sample_built_rubrics()
        m_w.return_value = sample_writer_output("ok")
        m_as.side_effect = lambda _r, val, _d, **_kw: sample_assessor_result(val.value_id)

        final = await run_workflow(
            {
                "raw_input": "task",
                "max_iterations": 1,
                **_WORKFLOW_KWARGS,
                "max_concurrent_llm": 1,
                "prompt_parameters": {"audience": "board_members", "length_target": "short"},
                "prompt_profile_id": "test_profile",
            }
        )

        assert final.get("prompt_profile_id") == "test_profile"
        pp = final.get("prompt_parameters") or {}
        assert pp.get("audience") == "board_members"
        assert pp.get("length_target") == "short"

        dec_kw = m_dec.await_args.kwargs
        assert dec_kw.get("prompt_profile_id") == "test_profile"
        assert dec_kw.get("prompt_parameters").audience == "board_members"

        w_kw = m_w.await_args.kwargs
        assert w_kw.get("prompt_profile_id") == "test_profile"
        assert w_kw.get("prompt_parameters").length_target == "short"


@pytest.mark.asyncio
async def test_run_workflow_passes_research_plan_to_writer_when_planning_mocked() -> None:
    """Planning on → mocked planner output → writer receives research_plan + document_outline."""
    decoded = sample_decoded_values()
    rubrics = sample_built_rubrics()
    draft = sample_writer_output("With plan.")
    plan_fix = ResearchPlanningOutput(
        research_plan=ResearchPlan(
            intent_summary="Cover the ask.",
            audience_and_constraints="General readers.",
            key_points=[KeyPoint(value_id="V1", text="Lead with impact.")],
            facts_to_include=["Stat X"],
            open_questions=["Q1"],
            risks_or_caveats=[],
            suggested_research_queries=["topic overview"],
            coverage_checklist=[],
        ),
        outline=DocumentOutline(
            title="T",
            sections=[OutlineSection(heading="Introduction", bullets=["Hook", "Thesis"])],
        ),
    )

    async def assess_side_effect(_rub: object, val: object, _draft: str, **_kw: object) -> object:
        return sample_assessor_result(val.value_id)

    with (
        patch("app.orchestrator.run.run_decode_values", new_callable=AsyncMock) as m_dec,
        patch("app.orchestrator.run.run_build_rubrics", new_callable=AsyncMock) as m_br,
        patch("app.orchestrator.run.run_research_planning", new_callable=AsyncMock) as m_rp,
        patch("app.orchestrator.run.run_writer", new_callable=AsyncMock) as m_w,
        patch("app.orchestrator.run.run_assess_one", new_callable=AsyncMock) as m_as,
    ):
        m_dec.return_value = decoded
        m_br.return_value = rubrics
        m_rp.return_value = plan_fix
        m_w.return_value = draft
        m_as.side_effect = assess_side_effect

        await run_workflow(
            {
                "raw_input": "x" * 250,
                "max_iterations": 1,
                "max_concurrent_llm": 2,
                "assess_parallel": False,
                "grounding_enabled": False,
                "craft_enabled": False,
                "research_planning_enabled": True,
            }
        )

        m_rp.assert_awaited_once()
        kw = m_w.await_args.kwargs
        assert kw.get("research_plan") is not None
        assert kw.get("document_outline") is not None
        assert kw["research_plan"].intent_summary == "Cover the ask."
        assert kw["document_outline"].sections[0].heading == "Introduction"
