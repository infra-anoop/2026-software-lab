"""PydanticAI writer node."""

from __future__ import annotations

import json
from functools import lru_cache

from pydantic_ai import Agent

from app.models import SourceRecord, WriterOutput
from app.prompts.loader import load_role_prompt
from app.prompts.render import weave_property_ranking

PROGRAM = "grant_default"


@lru_cache(maxsize=16)
def _writer_agent(ranking: tuple[str, ...]) -> Agent[None, WriterOutput]:
    return Agent(
        "openai:gpt-4o",
        output_type=WriterOutput,
        system_prompt=weave_property_ranking(
            load_role_prompt(PROGRAM, "writer"),
            list(ranking),
        ),
    )


async def write_grant_draft(
    *,
    user_text: str,
    humor_enabled: bool,
    property_ranking: list[str],
    materials: list[SourceRecord],
    web: list[SourceRecord],
    citation_mode: str,
    prior_body: str | None = None,
    assessor_feedback: str | None = None,
) -> WriterOutput:
    """Write a complete draft using materials first, then web.

    When ``assessor_feedback`` is set, revise ``prior_body`` toward those scores.
    """
    payload: dict[str, object] = {
        "user_prompt": user_text,
        "humor_enabled": humor_enabled,
        "property_ranking": property_ranking,
        "citation_mode": citation_mode,
        "materials_bundle": [s.model_dump() for s in materials],
        "web_bundle": [s.model_dump() for s in web],
        "instruction": (
            "Prefer materials_bundle for criteria/org evidence; "
            "web_bundle only for differentiating public signal."
        ),
    }
    if assessor_feedback and prior_body:
        payload["prior_draft"] = prior_body
        payload["assessor_feedback"] = assessor_feedback
        payload["instruction"] = (
            "Revise prior_draft using assessor_feedback. Preserve strengths; "
            "fix weak dual-axis rubric dimensions. Prefer materials_bundle."
        )
    result = await _writer_agent(tuple(property_ranking)).run(
        json.dumps(payload, indent=2)
    )
    return result.output
