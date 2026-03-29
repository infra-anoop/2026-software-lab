"""Research / document planning agent (schema-first) after rubrics, before retrieval or writer."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

import logfire
from pydantic import ValidationError
from pydantic_ai import Agent

from app.agents.llm_settings import agent_llm_kwargs
from app.agents.models import ComposedValues, ResearchPlan, ResearchPlanningOutput
from app.llm.retry import with_transient_llm_retry
from app.prompts.loader import render_system_prompt
from app.prompts.models import PromptParameters


def _valid_value_ids(composed: ComposedValues) -> set[str]:
    return {v.value_id for v in composed.values}


def sanitize_research_planning_output(
    raw: ResearchPlanningOutput,
    composed: ComposedValues,
) -> ResearchPlanningOutput | None:
    """Strip invalid value_ids; clamp lists. Returns None if still unusable (§6.5.1)."""
    valid = _valid_value_ids(composed)
    rp = raw.research_plan
    kpts = [kp for kp in rp.key_points if kp.value_id in valid]
    facts = list(rp.facts_to_include)[:12]
    oq = list(rp.open_questions)[:12]
    risks = list(rp.risks_or_caveats)[:12]
    queries = list(rp.suggested_research_queries)[:8]
    checklist = list(rp.coverage_checklist)[:12]

    try:
        plan = ResearchPlan(
            intent_summary=rp.intent_summary.strip() or "(unspecified)",
            audience_and_constraints=rp.audience_and_constraints.strip() or "(unspecified)",
            key_points=kpts,
            facts_to_include=facts,
            open_questions=oq,
            risks_or_caveats=risks,
            suggested_research_queries=queries,
            coverage_checklist=checklist,
        )
        outline = raw.outline
        if not outline.sections:
            return None
        return ResearchPlanningOutput(research_plan=plan, outline=outline)
    except ValidationError:
        return None


@lru_cache(maxsize=16)
def _planner_agent(system_prompt: str) -> Agent:
    return Agent(
        **agent_llm_kwargs("planner"),
        output_type=ResearchPlanningOutput,
        system_prompt=system_prompt,
    )


def _library_canonical_value_ids(composed: ComposedValues) -> list[str]:
    return [v.value_id for v in composed.values if v.provenance == "library_canonical"]


async def run_research_planning(
    user_prompt: str,
    composed: ComposedValues,
    rubric_digest: str,
    *,
    prompt_parameters: PromptParameters | None = None,
    prompt_profile_id: str | None = None,
    prompt_program_id: str | None = None,
) -> ResearchPlanningOutput:
    """Run planner LLM; caller handles sanitization and skip-on-failure policy."""
    params = prompt_parameters or PromptParameters()
    sp = render_system_prompt(
        "planner",
        params,
        program_id=prompt_program_id,
        profile_id=prompt_profile_id,
    )
    agent = _planner_agent(sp)
    payload: dict[str, Any] = {
        "user_prompt": user_prompt,
        "composed_values_summary": [
            {"value_id": v.value_id, "name": v.name, "description": v.description[:500]}
            for v in composed.values
        ],
        "library_canonical_value_ids": _library_canonical_value_ids(composed),
        "rubric_digest": rubric_digest,
        "prompt_parameters": params.model_dump(),
    }
    message = (
        "Plan the document and produce research_plan + outline as structured output.\n"
        f"{json.dumps(payload, indent=2)}"
    )

    async def _call():
        return await agent.run(message)

    with logfire.span("llm.research_planning", agent="research_planning"):
        result = await with_transient_llm_retry(_call, phase="research_planning")
    return result.output
