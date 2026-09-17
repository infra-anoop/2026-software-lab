"""PydanticAI infer node — grant slots and defaults."""

from __future__ import annotations

from functools import lru_cache

from pydantic_ai import Agent

from app.models import InferOutput
from app.prompts.loader import load_role_prompt
from app.properties import filter_closed_ranking

PROGRAM = "grant_default"


@lru_cache(maxsize=4)
def _infer_agent() -> Agent[None, InferOutput]:
    return Agent(
        "openai:gpt-4o",
        output_type=InferOutput,
        system_prompt=load_role_prompt(PROGRAM, "infer"),
    )


async def infer_grant_state(user_text: str, material_labels: list[str]) -> InferOutput:
    """Run infer agent; clamp ranking to closed vocab; force grant humor default off unless user enabled."""
    labels = ", ".join(material_labels) if material_labels else "(none)"
    prompt = f"User message:\n{user_text}\n\nMaterial labels: {labels}"
    result = await _infer_agent().run(prompt)
    out = result.output
    ranking = filter_closed_ranking(out.property_ranking)
    humor = bool(out.humor_enabled)
    lowered = user_text.lower()
    if not any(tok in lowered for tok in ("humor", "funny", "joke", "witty")):
        humor = False
    return InferOutput(
        who=out.who,
        whom=out.whom,
        ask=out.ask,
        why_funder=out.why_funder,
        evidence=out.evidence,
        humor_enabled=humor,
        web_research_enabled=out.web_research_enabled,
        property_ranking=ranking,
        search_query=out.search_query.strip(),
    )
