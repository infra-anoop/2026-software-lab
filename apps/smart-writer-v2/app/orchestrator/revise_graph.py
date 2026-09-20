"""LangGraph-shaped revise: prior artifact + feedback; scored inner loop (D8 / T084)."""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.infer_state import extract_intent_slots
from app.agents.writer import write_grant_draft
from app.config import get_openai_api_key
from app.models import ArtifactVersion, CitationMode, ClaimProvenance
from app.orchestrator.generate_graph import (
    GenerateResult,
    assemble_artifact,
    decide_web_signal,
)
from app.orchestrator.scored_loop import run_scored_inner_loop


class ReviseState(TypedDict, total=False):
    """Graph state for one revise run."""

    conversation_id: str
    feedback: str
    parent: ArtifactVersion
    citation_mode_pref: CitationMode | None
    humor_enabled: bool
    property_ranking: list[str]
    body: str
    rubric_id: str
    loop: dict[str, Any]
    artifact: ArtifactVersion


def _revise_body(parent: ArtifactVersion, feedback: str) -> str:
    """Keep prior draft in context and append the feedback (not a silent regen)."""
    prior = (parent.body or "").strip()
    note = feedback.strip()
    if prior and note:
        return f"{prior}\n\nRevision requested: {note}"
    return prior or note or "Revised draft pending additional detail."


def _apply_assessor_feedback(body: str, feedback: str | None) -> str:
    note = (feedback or "").strip()
    if not note:
        return body
    if note in body:
        return body
    return f"{body.rstrip()}\n\nRevision note: {note}"


def _revise_claims(body: str, parent: ArtifactVersion) -> list[ClaimProvenance]:
    claims: list[ClaimProvenance] = []
    for claim in parent.claims:
        excerpt = (claim.excerpt or "").strip()
        if excerpt and excerpt in body:
            claims.append(claim)
    return claims


def _slots_from_revise(parent: ArtifactVersion, feedback: str) -> dict[str, str | None]:
    inferred = extract_intent_slots(f"{parent.body}\n{feedback}")
    return {
        "who": inferred.who,
        "whom": inferred.whom,
        "ask": inferred.ask,
        "why_funder": inferred.why_funder,
        "evidence": inferred.evidence,
    }


def openai_revise_enabled() -> bool:
    key = get_openai_api_key()
    if key is None:
        return False
    lowered = key.lower()
    return not (lowered.startswith("sk-test") or "fake" in lowered)


async def _node_scored_revise(state: ReviseState) -> dict[str, Any]:
    """Revise path: skip/narrow research; still run dual-axis scored loop."""
    parent = state["parent"]
    feedback = state.get("feedback") or ""
    ranking = list(state.get("property_ranking") or [])
    humor = bool(state.get("humor_enabled", False))
    sources = list(parent.sources)
    materials = [s for s in sources if s.bundle == "materials"]
    web = [s for s in sources if s.bundle == "web"]
    citation: CitationMode = state.get("citation_mode_pref") or parent.citation_mode
    seed = _revise_body(parent, feedback)
    slots = _slots_from_revise(parent, feedback)

    if openai_revise_enabled():

        async def write_turn(prior: str | None, assessor_fb: str | None) -> str:
            out = await write_grant_draft(
                user_text=feedback or parent.body,
                humor_enabled=humor,
                property_ranking=ranking,
                materials=materials,
                web=web,
                citation_mode=citation,
                prior_body=prior or seed,
                assessor_feedback=assessor_fb or feedback,
            )
            return out.body

        body, rubric_id, loop = await run_scored_inner_loop(
            intent_slots=slots,
            property_ranking=ranking,
            user_text=feedback or parent.body,
            write_turn=write_turn,
            initial_body=seed,
        )
    else:

        async def write_turn_canned(prior: str | None, assessor_fb: str | None) -> str:
            base = prior or seed
            if assessor_fb:
                return _apply_assessor_feedback(base, assessor_fb)
            return base

        body, rubric_id, loop = await run_scored_inner_loop(
            intent_slots=slots,
            property_ranking=ranking,
            user_text=feedback or parent.body,
            write_turn=write_turn_canned,
            initial_body=seed,
        )

    artifact = assemble_artifact(
        conversation_id=state.get("conversation_id") or parent.conversation_id,
        body=body,
        materials=materials,
        web=web,
        claims=_revise_claims(body, parent),
        web_signal=decide_web_signal(web_research_enabled=False, web_sources=web),
        citation_mode_pref=state.get("citation_mode_pref") or parent.citation_mode,
        producing_mode="revise",
        parent_artifact_id=parent.artifact_id,
    )
    return {
        "body": body,
        "rubric_id": rubric_id,
        "loop": loop,
        "artifact": artifact,
    }


def build_revise_graph() -> Any:
    """Compile scored revise node (web skipped; D8 loop required)."""
    graph = StateGraph(ReviseState)
    graph.add_node("scored_revise", _node_scored_revise)
    graph.add_edge(START, "scored_revise")
    graph.add_edge("scored_revise", END)
    return graph.compile()


_GRAPH = None


def get_revise_graph() -> Any:
    """Lazy singleton compiled revise graph."""
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_revise_graph()
    return _GRAPH


async def run_revise(
    *,
    conversation_id: str,
    feedback: str,
    parent: ArtifactVersion,
    citation_mode_pref: CitationMode | None = None,
    humor_enabled: bool = False,
    property_ranking: list[str] | None = None,
) -> GenerateResult:
    """Revise from stored parent + this turn's feedback; dual-axis scored loop (T084)."""
    final = await get_revise_graph().ainvoke(
        {
            "conversation_id": conversation_id,
            "feedback": feedback,
            "parent": parent,
            "citation_mode_pref": citation_mode_pref,
            "humor_enabled": humor_enabled,
            "property_ranking": list(property_ranking or []),
        }
    )
    artifact: ArtifactVersion = final["artifact"]
    return GenerateResult(
        artifact=artifact,
        sources=list(artifact.sources),
        humor_enabled=humor_enabled,
        rubric_id=str(final.get("rubric_id") or ""),
        loop=dict(final.get("loop") or {}),
    )
