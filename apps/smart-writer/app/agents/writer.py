import json
from functools import lru_cache

import logfire
from pydantic_ai import Agent

from app.agents.llm_settings import agent_llm_kwargs
from app.agents.models import (
    BuiltRubrics,
    ComposedValues,
    DocumentOutline,
    EvidenceBundle,
    ResearchPlan,
    WriterOutput,
)
from app.llm.retry import with_transient_llm_retry
from app.prompts.loader import render_system_prompt
from app.prompts.models import PromptParameters


@lru_cache(maxsize=16)
def _writer_agent(system_prompt: str) -> Agent:
    return Agent(
        **agent_llm_kwargs("writer"),
        output_type=WriterOutput,
        system_prompt=system_prompt,
    )


def _writer_user_message(
    user_prompt: str,
    composed: ComposedValues,
    rubrics: BuiltRubrics,
    merged_feedback: str | None,
    iteration: int,
    evidence_bundle: EvidenceBundle | None,
    research_plan: ResearchPlan | None,
    document_outline: DocumentOutline | None,
) -> str:
    priority_table = [
        {
            "value_id": v.value_id,
            "name": v.name,
            "weight": v.weight,
            "provenance": v.provenance,
        }
        for v in composed.values
    ]
    ctx: dict = {
        "user_prompt": user_prompt,
        "values": [v.model_dump() for v in composed.values],
        "priority_table": priority_table,
        "rubrics": [r.model_dump() for r in rubrics.rubrics],
        "iteration": iteration,
    }
    if evidence_bundle is not None and evidence_bundle.chunks:
        ctx["evidence_bundle"] = {
            "retrieval_notes": evidence_bundle.retrieval_notes,
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "provenance": c.provenance,
                    "text": c.text,
                }
                for c in evidence_bundle.chunks
            ],
        }
    elif evidence_bundle is not None and evidence_bundle.retrieval_notes:
        ctx["evidence_bundle"] = {
            "retrieval_notes": evidence_bundle.retrieval_notes,
            "chunks": [],
        }
    if research_plan is not None:
        ctx["research_plan"] = research_plan.model_dump()
    if document_outline is not None:
        ctx["document_outline"] = document_outline.model_dump()
    base = json.dumps(ctx, indent=2)
    if not merged_feedback:
        return (
            f"{base}\n\n---\nProduce the best possible first draft for the user_prompt.\n"
            "Satisfy the values naturally; you will be scored later on each value."
        )
    return (
        f"{base}\n\n---\nMerged assessor feedback (prioritize weakest areas first):\n"
        f"{merged_feedback}\n\n---\nRevise the draft to address the feedback while preserving strengths."
    )


async def run_writer(
    user_prompt: str,
    composed: ComposedValues,
    rubrics: BuiltRubrics,
    merged_feedback: str | None,
    iteration: int,
    evidence_bundle: EvidenceBundle | None = None,
    research_plan: ResearchPlan | None = None,
    document_outline: DocumentOutline | None = None,
    *,
    prompt_parameters: PromptParameters | None = None,
    prompt_profile_id: str | None = None,
    prompt_program_id: str | None = None,
) -> WriterOutput:
    params = prompt_parameters or PromptParameters()
    sp = render_system_prompt(
        "writer",
        params,
        program_id=prompt_program_id,
        profile_id=prompt_profile_id,
    )
    agent = _writer_agent(sp)
    msg = _writer_user_message(
        user_prompt,
        composed,
        rubrics,
        merged_feedback,
        iteration,
        evidence_bundle,
        research_plan,
        document_outline,
    )

    async def _call():
        return await agent.run(msg)

    with logfire.span("llm.writer", agent="writer", iteration=iteration):
        result = await with_transient_llm_retry(_call, phase="writer")
    return result.output
