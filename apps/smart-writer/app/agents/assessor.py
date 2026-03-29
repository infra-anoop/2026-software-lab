import json
from functools import lru_cache

import logfire
from pydantic_ai import Agent

from app.agents.llm_settings import agent_llm_kwargs
from app.agents.models import AssessorResult, ValueDefinition, ValueRubric
from app.llm.retry import with_transient_llm_retry
from app.prompts.loader import render_system_prompt
from app.prompts.models import PromptParameters


@lru_cache(maxsize=16)
def _assessor_agent(system_prompt: str) -> Agent:
    return Agent(
        **agent_llm_kwargs("assessor"),
        output_type=AssessorResult,
        system_prompt=system_prompt,
    )


def _assessor_message(rubric: ValueRubric, value: ValueDefinition, draft: str) -> str:
    payload = {
        "value": value.model_dump(),
        "rubric": rubric.model_dump(),
        "draft": draft,
    }
    return json.dumps(payload, indent=2)


async def run_assess_one(
    rubric: ValueRubric,
    value: ValueDefinition,
    draft: str,
    *,
    prompt_parameters: PromptParameters | None = None,
    prompt_profile_id: str | None = None,
    prompt_program_id: str | None = None,
) -> AssessorResult:
    params = prompt_parameters or PromptParameters()
    sp = render_system_prompt(
        "assessor",
        params,
        program_id=prompt_program_id,
        profile_id=prompt_profile_id,
    )
    agent = _assessor_agent(sp)
    msg = _assessor_message(rubric, value, draft)

    async def _call():
        return await agent.run(msg)

    with logfire.span("llm.assessor", agent="assessor", value_id=rubric.value_id):
        result = await with_transient_llm_retry(_call, phase="assessor")
    out = result.output
    if out.value_id != rubric.value_id:
        raise ValueError(f"Assessor value_id {out.value_id} != rubric {rubric.value_id}.")
    if len(out.dimension_scores) != len(rubric.dimensions):
        raise ValueError("dimension_scores length must match rubric dimensions.")
    return out
