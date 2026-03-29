import asyncio
import json
from functools import lru_cache
from typing import Mapping

import logfire
from pydantic_ai import Agent

from app.agents.craft_values import build_craft_template
from app.agents.llm_settings import agent_llm_kwargs
from app.agents.models import BuiltRubrics, ComposedValues, ValueDefinition, ValueRubric
from app.agents.refresh_rubric_anchors import library_refresh_anchors_enabled, run_refresh_rubric_anchors
from app.config import DEFAULT_MAX_CONCURRENT_LLM
from app.llm.retry import with_transient_llm_retry
from app.prompts.loader import render_system_prompt
from app.prompts.models import PromptParameters


@lru_cache(maxsize=16)
def _rubric_per_value_agent(system_prompt: str) -> Agent:
    # One structured object per call — avoids models returning a single rubric when asked for a list.
    return Agent(
        **agent_llm_kwargs("rubric"),
        output_type=ValueRubric,
        retries=2,
        output_retries=3,
        system_prompt=system_prompt,
    )


async def _build_one_rubric(
    user_prompt: str,
    value: ValueDefinition,
    *,
    prompt_parameters: PromptParameters | None = None,
    prompt_profile_id: str | None = None,
    prompt_program_id: str | None = None,
) -> ValueRubric:
    params = prompt_parameters or PromptParameters()
    sp = render_system_prompt(
        "rubric",
        params,
        program_id=prompt_program_id,
        profile_id=prompt_profile_id,
    )
    agent = _rubric_per_value_agent(sp)
    payload = {"user_prompt": user_prompt, "value": value.model_dump()}
    message = (
        "Build the rubric for this single value only.\n"
        f"{json.dumps(payload, indent=2)}"
    )

    async def _call():
        return await agent.run(message)

    with logfire.span("llm.rubric_builder", agent="rubric_builder", value_id=value.value_id):
        result = await with_transient_llm_retry(_call, phase="rubric_builder")
    rubric = result.output
    if rubric.value_id != value.value_id:
        raise ValueError(f"Rubric value_id {rubric.value_id} != expected {value.value_id}.")
    if rubric.value_name.strip() != value.name.strip():
        rubric = rubric.model_copy(update={"value_name": value.name})
    return rubric


async def run_build_rubrics(
    user_prompt: str,
    composed: ComposedValues,
    max_concurrent_llm: int = DEFAULT_MAX_CONCURRENT_LLM,
    *,
    library_rubric_by_value_id: Mapping[str, ValueRubric] | None = None,
    prompt_parameters: PromptParameters | None = None,
    prompt_profile_id: str | None = None,
    prompt_program_id: str | None = None,
) -> BuiltRubrics:
    """Template rubrics for craft; clone + optional refresh for library; parallel LLM for task_derived.

    For ``library_canonical`` rows, pass catalog rubrics via ``library_rubric_by_value_id`` (keyed by
    ``value_id``). The orchestrator may build this map from ``canonical_library_entries`` in state
    (see ``run.build_rubrics_node``). If a library row has no rubric in the map, raises
    :class:`ValueError` (actionable message).
    """
    sem = asyncio.Semaphore(max(1, max_concurrent_llm))
    lib_map = dict(library_rubric_by_value_id) if library_rubric_by_value_id else {}

    async def one(v: ValueDefinition) -> ValueRubric:
        if v.provenance == "designer_craft":
            if not v.craft_key:
                raise ValueError(f"craft_key required for designer_craft value {v.value_id}")
            t = build_craft_template(v.craft_key)
            return t.rubric
        if v.provenance == "library_canonical":
            base = lib_map.get(v.value_id)
            if base is None:
                raise ValueError(
                    "library_canonical: provide catalog rubric in library_rubric_by_value_id, or wire "
                    f"match_canonical_library (docs/design-canonical-value-rubric-library.md §5.5); "
                    f"value_id={v.value_id}."
                )
            if not library_refresh_anchors_enabled():
                return base.model_copy(deep=True)
            async with sem:
                return await run_refresh_rubric_anchors(
                    user_prompt,
                    base,
                    prompt_parameters=prompt_parameters,
                    prompt_profile_id=prompt_profile_id,
                    prompt_program_id=prompt_program_id,
                )
        async with sem:
            return await _build_one_rubric(
                user_prompt,
                v,
                prompt_parameters=prompt_parameters,
                prompt_profile_id=prompt_profile_id,
                prompt_program_id=prompt_program_id,
            )

    rubrics = await asyncio.gather(*[one(v) for v in composed.values])
    composed_ids = {v.value_id for v in composed.values}
    built_ids = {r.value_id for r in rubrics}
    if composed_ids != built_ids:
        raise ValueError(f"Rubric value_ids {built_ids} must match composed {composed_ids}.")
    return BuiltRubrics(rubrics=list(rubrics))
