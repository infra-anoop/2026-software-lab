"""LangGraph generate: infer → materials → web → write → provenance (P3)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from app.agents.infer import infer_grant_state
from app.agents.provenance import attach_provenance, coerce_claims
from app.agents.writer import write_grant_draft
from app.config import get_openai_api_key
from app.models import (
    ArtifactVersion,
    CitationMode,
    ClaimProvenance,
    MaterialRef,
    SourceRecord,
    WebSignal,
)
from app.retrieval.bundles import collect_bundles
from app.retrieval.url_fetch import FetchBudget


class GenerateState(TypedDict, total=False):
    """Graph state for one generate run."""

    conversation_id: str
    user_text: str
    materials_in: list[dict[str, str | None]]
    citation_mode_pref: CitationMode | None
    humor_enabled: bool
    web_research_enabled: bool
    property_ranking: list[str]
    search_query: str
    materials_sources: list[SourceRecord]
    web_sources: list[SourceRecord]
    body: str
    claims: list[ClaimProvenance]
    artifact: ArtifactVersion


class GenerateResult(TypedDict):
    """Return value for callers (T028 later)."""

    artifact: ArtifactVersion
    sources: list[SourceRecord]
    humor_enabled: bool


def decide_web_signal(*, web_research_enabled: bool, web_sources: list[SourceRecord]) -> WebSignal:
    """SC-004 structural: disabled vs used vs none_declared (not hardcoded none_declared)."""
    if not web_research_enabled:
        return "disabled"
    if web_sources:
        return "used"
    return "none_declared"


def assemble_artifact(
    *,
    conversation_id: str,
    body: str,
    materials: list[SourceRecord],
    web: list[SourceRecord],
    claims: list[ClaimProvenance],
    web_signal: WebSignal,
    citation_mode_pref: CitationMode | None,
    producing_mode: str = "generate",
    parent_artifact_id: str | None = None,
) -> ArtifactVersion:
    """Build ArtifactVersion with T1/T3 locks (panel when sources exist)."""
    sources = [*materials, *web]
    coerced = coerce_claims(body, claims, sources)
    citation: CitationMode = citation_mode_pref or "panel"
    if sources and citation_mode_pref is None:
        citation = "panel"
    now = datetime.now(UTC).isoformat()
    return ArtifactVersion(
        artifact_id=str(uuid4()),
        conversation_id=conversation_id,
        parent_artifact_id=parent_artifact_id,
        producing_mode="generate" if producing_mode == "generate" else "revise",
        body=body,
        citation_mode=citation,
        source_ids=[s.source_id for s in sources],
        claims=coerced,
        materials_bundle_ids=[s.source_id for s in materials],
        web_bundle_ids=[s.source_id for s in web],
        web_signal=web_signal,
        created_at=now,
        sources=sources,
    )


async def _node_infer(state: GenerateState) -> dict[str, Any]:
    labels = [str(m.get("label") or m.get("uri") or "") for m in state.get("materials_in") or []]
    inferred = await infer_grant_state(state["user_text"], labels)
    ranking = list(inferred.property_ranking or state.get("property_ranking") or [])
    return {
        "humor_enabled": inferred.humor_enabled,
        "web_research_enabled": inferred.web_research_enabled,
        "property_ranking": ranking,
        "search_query": inferred.search_query,
    }


async def _node_materials(state: GenerateState) -> dict[str, Any]:
    raw = state.get("materials_in") or []
    refs = [
        MaterialRef(uri=str(item["uri"]), label=item.get("label"), kind="link")
        for item in raw
        if item.get("uri")
    ]
    bundles = await collect_bundles(
        refs,
        search_query="",
        web_research_enabled=False,
    )
    return {"materials_sources": bundles.materials}


async def _node_web(state: GenerateState) -> dict[str, Any]:
    enabled = bool(state.get("web_research_enabled", True))
    if not enabled:
        return {"web_sources": []}
    query = state.get("search_query") or state["user_text"][:200]
    bundles = await collect_bundles(
        [],
        search_query=query,
        web_research_enabled=True,
    )
    return {"web_sources": bundles.web}


async def _node_write(state: GenerateState) -> dict[str, Any]:
    materials = state.get("materials_sources") or []
    web = state.get("web_sources") or []
    pref = state.get("citation_mode_pref")
    citation: CitationMode = pref or "panel"
    if (materials or web) and pref is None:
        citation = "panel"
    out = await write_grant_draft(
        user_text=state["user_text"],
        humor_enabled=bool(state.get("humor_enabled", False)),
        property_ranking=list(state.get("property_ranking") or []),
        materials=materials,
        web=web,
        citation_mode=citation,
    )
    return {"body": out.body}


async def _node_provenance(state: GenerateState) -> dict[str, Any]:
    materials = state.get("materials_sources") or []
    web = state.get("web_sources") or []
    body = state.get("body") or ""
    claims = await attach_provenance(
        body=body,
        user_text=state["user_text"],
        sources=[*materials, *web],
    )
    web_signal = decide_web_signal(
        web_research_enabled=bool(state.get("web_research_enabled", True)),
        web_sources=web,
    )
    artifact = assemble_artifact(
        conversation_id=state.get("conversation_id") or str(uuid4()),
        body=body,
        materials=materials,
        web=web,
        claims=claims,
        web_signal=web_signal,
        citation_mode_pref=state.get("citation_mode_pref"),
        producing_mode="generate",
        parent_artifact_id=None,
    )
    return {"claims": claims, "artifact": artifact}


def build_generate_graph() -> Any:
    """Compile infer → materials → web → write → provenance."""
    graph = StateGraph(GenerateState)
    graph.add_node("infer", _node_infer)
    graph.add_node("materials", _node_materials)
    graph.add_node("web", _node_web)
    graph.add_node("write", _node_write)
    graph.add_node("provenance", _node_provenance)
    graph.add_edge(START, "infer")
    graph.add_edge("infer", "materials")
    graph.add_edge("materials", "web")
    graph.add_edge("web", "write")
    graph.add_edge("write", "provenance")
    graph.add_edge("provenance", END)
    return graph.compile()


_GRAPH = None


def get_generate_graph() -> Any:
    """Lazy singleton compiled graph."""
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_generate_graph()
    return _GRAPH


def openai_generate_enabled() -> bool:
    """Live OpenAI only — skip LLM for unset/fake test keys (contract tests)."""
    key = get_openai_api_key()
    if key is None:
        return False
    lowered = key.lower()
    return not (lowered.startswith("sk-test") or "fake" in lowered)


def _compose_grant_body(user_text: str, sources: list[SourceRecord]) -> str:
    """Complete draft from the turn + retrieved excerpts (no LLM)."""
    parts = [user_text.strip()]
    for src in sources:
        span = (src.excerpt or src.title or "").strip()
        if span:
            parts.append(span[:500])
    body = "\n\n".join(p for p in parts if p)
    return body if body.strip() else "Draft pending additional detail."


def _claims_from_sources(body: str, sources: list[SourceRecord]) -> list[ClaimProvenance]:
    claims: list[ClaimProvenance] = []
    for src in sources:
        excerpt = (src.excerpt or src.title or "").strip()
        if not excerpt:
            continue
        span = excerpt[:120]
        if span in body:
            claims.append(
                ClaimProvenance(
                    excerpt=span,
                    source_id=src.source_id,
                    status="grounded",
                )
            )
    return coerce_claims(body, claims, sources)


async def _run_generate_without_llm(
    *,
    conversation_id: str,
    user_text: str,
    materials: list[MaterialRef] | None,
    citation_mode_pref: CitationMode | None,
    humor_enabled: bool,
    web_research_enabled: bool,
) -> GenerateResult:
    """Retrieve + assemble_artifact (T1/T3). Does not return canned assertion JSON."""
    refs = materials or []
    bundles = await collect_bundles(
        refs,
        search_query=user_text[:200],
        web_research_enabled=web_research_enabled,
        fetch_budget=FetchBudget(timeout_sec=3.0),
    )
    sources = [*bundles.materials, *bundles.web]
    body = _compose_grant_body(user_text, sources)
    claims = _claims_from_sources(body, sources)
    web_signal = decide_web_signal(
        web_research_enabled=web_research_enabled,
        web_sources=bundles.web,
    )
    artifact = assemble_artifact(
        conversation_id=conversation_id,
        body=body,
        materials=bundles.materials,
        web=bundles.web,
        claims=claims,
        web_signal=web_signal,
        citation_mode_pref=citation_mode_pref,
        producing_mode="generate",
        parent_artifact_id=None,
    )
    return GenerateResult(
        artifact=artifact,
        sources=list(artifact.sources),
        humor_enabled=humor_enabled,
    )


async def run_generate(
    *,
    conversation_id: str,
    user_text: str,
    materials: list[MaterialRef] | None = None,
    citation_mode_pref: CitationMode | None = None,
    humor_enabled: bool = False,
    web_research_enabled: bool = True,
    property_ranking: list[str] | None = None,
) -> GenerateResult:
    """Run generate for an enqueued job (T028). Ranking never disables retrieval (F3)."""
    ranking = list(property_ranking or [])
    if openai_generate_enabled():
        refs = materials or []
        final = await get_generate_graph().ainvoke(
            {
                "conversation_id": conversation_id,
                "user_text": user_text,
                "materials_in": [m.model_dump() for m in refs],
                "citation_mode_pref": citation_mode_pref,
                "humor_enabled": humor_enabled,
                "web_research_enabled": web_research_enabled,
                "property_ranking": ranking,
            }
        )
        artifact: ArtifactVersion = final["artifact"]
        return GenerateResult(
            artifact=artifact,
            sources=list(artifact.sources),
            humor_enabled=bool(final.get("humor_enabled", humor_enabled)),
        )
    return await _run_generate_without_llm(
        conversation_id=conversation_id,
        user_text=user_text,
        materials=materials,
        citation_mode_pref=citation_mode_pref,
        humor_enabled=humor_enabled,
        web_research_enabled=web_research_enabled,
    )

