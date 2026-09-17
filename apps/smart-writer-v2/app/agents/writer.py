"""PydanticAI writer node."""

from __future__ import annotations

import json
from functools import lru_cache

from pydantic_ai import Agent

from app.models import SourceRecord, WriterOutput
from app.prompts.loader import load_role_prompt

PROGRAM = "grant_default"


@lru_cache(maxsize=4)
def _writer_agent() -> Agent[None, WriterOutput]:
    return Agent(
        "openai:gpt-4o",
        output_type=WriterOutput,
        system_prompt=load_role_prompt(PROGRAM, "writer"),
    )


async def write_grant_draft(
    *,
    user_text: str,
    humor_enabled: bool,
    property_ranking: list[str],
    materials: list[SourceRecord],
    web: list[SourceRecord],
    citation_mode: str,
) -> WriterOutput:
    """Write a complete draft using materials first, then web."""
    payload = {
        "user_prompt": user_text,
        "humor_enabled": humor_enabled,
        "property_ranking": property_ranking,
        "citation_mode": citation_mode,
        "materials_bundle": [s.model_dump() for s in materials],
        "web_bundle": [s.model_dump() for s in web],
        "instruction": "Prefer materials_bundle for criteria/org evidence; web_bundle only for differentiating public signal.",
    }
    result = await _writer_agent().run(json.dumps(payload, indent=2))
    return result.output
