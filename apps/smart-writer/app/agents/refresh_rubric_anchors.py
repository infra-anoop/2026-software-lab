"""One LLM pass to align rubric anchors to ``raw_input`` without changing geometry (§5.5)."""

from __future__ import annotations

import json
import os
from functools import lru_cache

import logfire
from pydantic_ai import Agent

from app.agents.llm_settings import agent_llm_kwargs
from app.agents.models import ValueRubric
from app.llm.retry import with_transient_llm_retry
from app.prompts.loader import render_system_prompt
from app.prompts.models import PromptParameters


@lru_cache(maxsize=16)
def _refresh_rubric_anchors_agent(system_prompt: str) -> Agent:
    return Agent(
        **agent_llm_kwargs("rubric"),
        output_type=ValueRubric,
        retries=2,
        output_retries=3,
        system_prompt=system_prompt,
    )


def library_refresh_anchors_enabled() -> bool:
    """``SMART_WRITER_LIBRARY_REFRESH_ANCHORS`` — default on; when false, use cloned catalog rubric only."""
    raw = os.getenv("SMART_WRITER_LIBRARY_REFRESH_ANCHORS", "true")
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


async def run_refresh_rubric_anchors(
    user_prompt: str,
    base_rubric: ValueRubric,
    *,
    prompt_parameters: PromptParameters | None = None,
    prompt_profile_id: str | None = None,
    prompt_program_id: str | None = None,
) -> ValueRubric:
    """Clone semantics: output must preserve dimension **names** and order; ``value_id`` unchanged.

    Use the same ``result_type`` as full rubric build (:class:`ValueRubric`) for one structured object per call.
    """
    params = prompt_parameters or PromptParameters()
    sp = render_system_prompt(
        "refresh_rubric_anchors",
        params,
        program_id=prompt_program_id,
        profile_id=prompt_profile_id,
    )
    agent = _refresh_rubric_anchors_agent(sp)
    payload = {"user_prompt": user_prompt, "rubric": base_rubric.model_dump()}
    message = f"Refresh rubric anchors for this task.\n{json.dumps(payload, indent=2)}"

    async def _call():
        return await agent.run(message)

    with logfire.span(
        "llm.refresh_rubric_anchors",
        agent="refresh_rubric_anchors",
        value_id=base_rubric.value_id,
    ):
        result = await with_transient_llm_retry(_call, phase="refresh_rubric_anchors")
    out = result.output
    if len(out.dimensions) != len(base_rubric.dimensions):
        raise ValueError("Refreshed rubric must keep five dimensions.")
    for new_d, base_d in zip(out.dimensions, base_rubric.dimensions, strict=True):
        if new_d.name.strip() != base_d.name.strip():
            raise ValueError(
                f"Dimension name must stay {base_d.name!r} for refresh-anchors; got {new_d.name!r}."
            )
    fixes: dict[str, str] = {}
    if out.value_id != base_rubric.value_id:
        fixes["value_id"] = base_rubric.value_id
    if out.value_name.strip() != base_rubric.value_name.strip():
        fixes["value_name"] = base_rubric.value_name
    if fixes:
        out = out.model_copy(update=fixes)
    return out
