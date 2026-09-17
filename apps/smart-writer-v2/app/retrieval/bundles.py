"""Retrieval façade: materials_bundle vs web_bundle (F4 / P4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from app.models import MaterialRef, SourceRecord
from app.retrieval.tavily import tavily_search
from app.retrieval.url_fetch import fetch_url_text


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class BundleResult:
    """Two retrieval sides plus web_signal inputs."""

    materials: list[SourceRecord] = field(default_factory=list)
    web: list[SourceRecord] = field(default_factory=list)


async def collect_materials_bundle(materials: list[MaterialRef]) -> list[SourceRecord]:
    """Fetch user links into materials-side SourceRecords."""
    out: list[SourceRecord] = []
    for ref in materials:
        fetched = await fetch_url_text(ref.uri)
        sid = f"mat_{uuid4().hex[:10]}"
        if fetched is None:
            out.append(
                SourceRecord(
                    source_id=sid,
                    kind="user_material",
                    bundle="materials",
                    uri=ref.uri,
                    title=ref.label,
                    excerpt=None,
                    retrieved_at=_now(),
                )
            )
            continue
        final_url, title, text = fetched
        out.append(
            SourceRecord(
                source_id=sid,
                kind="user_material",
                bundle="materials",
                uri=final_url,
                title=ref.label or title,
                excerpt=text[:1500] if text else None,
                retrieved_at=_now(),
            )
        )
    return out


async def collect_web_bundle(search_query: str) -> list[SourceRecord]:
    """Tavily hits as web-side SourceRecords (empty if no key/hits)."""
    hits = await tavily_search(search_query)
    out: list[SourceRecord] = []
    for i, item in enumerate(hits):
        content = str(item.get("content") or "").strip()
        url = str(item.get("url") or "")
        title = str(item.get("title") or url or f"hit-{i}")
        if not content:
            continue
        out.append(
            SourceRecord(
                source_id=f"web_{uuid4().hex[:10]}",
                kind="web",
                bundle="web",
                uri=url or None,
                title=title[:300],
                excerpt=content[:1500],
                retrieved_at=_now(),
            )
        )
    return out


async def collect_bundles(
    materials: list[MaterialRef],
    *,
    search_query: str,
    web_research_enabled: bool,
) -> BundleResult:
    """Run materials fetch always; web search only when enabled."""
    material_records = await collect_materials_bundle(materials)
    web_records: list[SourceRecord] = []
    if web_research_enabled:
        web_records = await collect_web_bundle(search_query)
    return BundleResult(materials=material_records, web=web_records)
