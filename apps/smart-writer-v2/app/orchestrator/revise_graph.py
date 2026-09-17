"""LangGraph-shaped revise: prior artifact + feedback; skip/narrow web (T035)."""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.models import ArtifactVersion, CitationMode, ClaimProvenance
from app.orchestrator.generate_graph import (
    GenerateResult,
    assemble_artifact,
    decide_web_signal,
)


class ReviseState(TypedDict, total=False):
    """Graph state for one revise run."""

    conversation_id: str
    feedback: str
    parent: ArtifactVersion
    citation_mode_pref: CitationMode | None
    humor_enabled: bool
    body: str
    artifact: ArtifactVersion


def _revise_body(parent: ArtifactVersion, feedback: str) -> str:
    """Keep prior draft in context and append the feedback (not a silent regen)."""
    prior = (parent.body or "").strip()
    note = feedback.strip()
    if prior and note:
        return f"{prior}\n\nRevision requested: {note}"
    return prior or note or "Revised draft pending additional detail."


def _revise_claims(body: str, parent: ArtifactVersion) -> list[ClaimProvenance]:
    claims: list[ClaimProvenance] = []
    for claim in parent.claims:
        excerpt = (claim.excerpt or "").strip()
        if excerpt and excerpt in body:
            claims.append(claim)
    return claims


async def _node_apply(state: ReviseState) -> dict[str, Any]:
    parent = state["parent"]
    body = _revise_body(parent, state.get("feedback") or "")
    sources = list(parent.sources)
    materials = [s for s in sources if s.bundle == "materials"]
    web = [s for s in sources if s.bundle == "web"]
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
    return {"body": body, "artifact": artifact}


def build_revise_graph() -> Any:
    """Compile apply-feedback node (web skipped on revise)."""
    graph = StateGraph(ReviseState)
    graph.add_node("apply", _node_apply)
    graph.add_edge(START, "apply")
    graph.add_edge("apply", END)
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
) -> GenerateResult:
    """Revise from stored parent + this turn's feedback (T035)."""
    final = await get_revise_graph().ainvoke(
        {
            "conversation_id": conversation_id,
            "feedback": feedback,
            "parent": parent,
            "citation_mode_pref": citation_mode_pref,
            "humor_enabled": humor_enabled,
        }
    )
    artifact: ArtifactVersion = final["artifact"]
    return GenerateResult(
        artifact=artifact,
        sources=list(artifact.sources),
        humor_enabled=humor_enabled,
    )
