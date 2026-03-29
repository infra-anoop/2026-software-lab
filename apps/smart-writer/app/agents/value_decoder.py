from functools import lru_cache

import logfire
from pydantic_ai import Agent

from app.agents.llm_settings import agent_llm_kwargs
from app.agents.models import DecodedValues, decoder_domain_slot_bounds
from app.llm.retry import with_transient_llm_retry
from app.prompts.loader import render_system_prompt
from app.prompts.models import PromptParameters


@lru_cache(maxsize=16)
def _value_decoder_agent(system_prompt: str) -> Agent:
    return Agent(
        **agent_llm_kwargs("decoder"),
        output_type=DecodedValues,
        system_prompt=system_prompt,
    )


def _decode_constraint_block(
    *,
    d_min: int,
    d_max: int,
    reserved: list[tuple[str, str]],
) -> str:
    lines = [
        "",
        "---",
        "Pipeline constraints:",
        f"- Emit between {d_min} and {d_max} domain values (inclusive).",
    ]
    if reserved:
        listed = "; ".join(f"{cid} — {name}" for cid, name in reserved)
        lines.append(
            f"- Already-selected canonical criteria from the product library (do NOT duplicate or overlap): {listed}."
        )
    else:
        lines.append("- No library canonical criteria were pre-selected for this run.")
    lines.append("---")
    return "\n".join(lines)


async def run_decode_values(
    user_prompt: str,
    *,
    library_domain_count: int = 0,
    reserved_canonical: list[tuple[str, str]] | None = None,
    prompt_parameters: PromptParameters | None = None,
    prompt_profile_id: str | None = None,
    prompt_program_id: str | None = None,
) -> DecodedValues:
    params = prompt_parameters or PromptParameters()
    sp = render_system_prompt(
        "decoder",
        params,
        program_id=prompt_program_id,
        profile_id=prompt_profile_id,
    )
    agent = _value_decoder_agent(sp)
    d_min, d_max = decoder_domain_slot_bounds(library_domain_count)
    reserved = list(reserved_canonical or [])
    message = user_prompt.strip() + _decode_constraint_block(d_min=d_min, d_max=d_max, reserved=reserved)

    async def _call():
        return await agent.run(message)

    with logfire.span(
        "llm.value_decoder",
        agent="value_decoder",
        library_domain_count=library_domain_count,
        d_min=d_min,
        d_max=d_max,
    ):
        result = await with_transient_llm_retry(_call, phase="decode_values")
    return result.output
