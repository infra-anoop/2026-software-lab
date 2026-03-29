"""Grounding assessor: draft vs evidence bundle + user intent (editorial QA)."""

from __future__ import annotations

import json
from functools import lru_cache

import logfire
from pydantic_ai import Agent

from app.agents.llm_settings import agent_llm_kwargs
from app.agents.models import (
    GROUNDING_ASSESSOR_RAW_INPUT_CAP,
    EvidenceBundle,
    GroundingAssessment,
)
from app.llm.retry import with_transient_llm_retry
from app.prompts.loader import render_system_prompt
from app.prompts.models import PromptParameters


@lru_cache(maxsize=16)
def _grounding_agent(system_prompt: str) -> Agent:
    return Agent(
        **agent_llm_kwargs("grounding"),
        output_type=GroundingAssessment,
        system_prompt=system_prompt,
    )


def _clip_raw_input(raw_input: str) -> str:
    if len(raw_input) <= GROUNDING_ASSESSOR_RAW_INPUT_CAP:
        return raw_input
    head = GROUNDING_ASSESSOR_RAW_INPUT_CAP // 2
    tail = GROUNDING_ASSESSOR_RAW_INPUT_CAP - head - 40
    return raw_input[:head] + "\n…[truncated]…\n" + raw_input[-tail:]


def _bundle_compact(bundle: EvidenceBundle) -> dict:
    return {
        "retrieval_notes": bundle.retrieval_notes,
        "sources": [s.model_dump() for s in bundle.sources],
        "chunks": [
            {
                "chunk_id": c.chunk_id,
                "source_id": c.source_id,
                "provenance": c.provenance,
                "text": c.text,
            }
            for c in bundle.chunks
        ],
    }


def _grounding_user_message(raw_input: str, bundle: EvidenceBundle, draft: str) -> str:
    payload = {
        "user_prompt": _clip_raw_input(raw_input),
        "evidence_bundle": _bundle_compact(bundle),
        "draft": draft,
    }
    return json.dumps(payload, indent=2)


async def run_grounding_assess(
    raw_input: str,
    bundle: EvidenceBundle,
    draft: str,
    *,
    prompt_parameters: PromptParameters | None = None,
    prompt_profile_id: str | None = None,
    prompt_program_id: str | None = None,
) -> GroundingAssessment:
    params = prompt_parameters or PromptParameters()
    sp = render_system_prompt(
        "grounding",
        params,
        program_id=prompt_program_id,
        profile_id=prompt_profile_id,
    )
    agent = _grounding_agent(sp)
    msg = _grounding_user_message(raw_input, bundle, draft)

    async def _call():
        return await agent.run(msg)

    with logfire.span("llm.grounding_assess", chunk_count=len(bundle.chunks)):
        result = await with_transient_llm_retry(_call, phase="grounding_assess")
    return result.output
