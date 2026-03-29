"""Pluggable web search → EvidenceBundle fragments (design §5.1)."""

from __future__ import annotations

import os
from typing import Protocol

import httpx

from app.agents.models import EvidenceChunk, EvidenceBundle, SourceRef
from app.retrieval.fetch_safe import utc_now_iso


class WebSearchBackend(Protocol):
    async def search(self, query: str, *, max_results: int = 5) -> EvidenceBundle: ...


class NoopWebSearch:
    async def search(self, query: str, *, max_results: int = 5) -> EvidenceBundle:
        return EvidenceBundle()


class TavilyWebSearch:
    """https://tavily.com — optional when ``TAVILY_API_KEY`` is set."""

    def __init__(self, api_key: str | None = None) -> None:
        self._key = (api_key or os.getenv("TAVILY_API_KEY") or "").strip()

    async def search(self, query: str, *, max_results: int = 5) -> EvidenceBundle:
        if not self._key:
            return EvidenceBundle()
        payload = {
            "api_key": self._key,
            "query": query,
            "max_results": max(1, min(max_results, 10)),
            "include_answer": False,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post("https://api.tavily.com/search", json=payload)
                r.raise_for_status()
                data = r.json()
        except httpx.HTTPError:
            return EvidenceBundle()

        results = data.get("results") or []
        if not isinstance(results, list):
            return EvidenceBundle()

        sources: list[SourceRef] = []
        chunks: list[EvidenceChunk] = []
        now = utc_now_iso()
        for i, item in enumerate(results):
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "")
            title = str(item.get("title") or url or f"hit-{i}")
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            sid = f"search_{i}"
            sources.append(
                SourceRef(
                    source_id=sid,
                    kind="search_hit",
                    title=title[:300],
                    url=url or None,
                    retrieved_at=now,
                    snippet=content[:240],
                )
            )
            chunks.append(
                EvidenceChunk(
                    chunk_id=f"{sid}_c0",
                    source_id=sid,
                    text=content,
                    query=query,
                    provenance="search_hit",
                )
            )
        return EvidenceBundle(chunks=chunks, sources=sources, retrieval_notes="")


def get_web_search_backend(provider: str) -> WebSearchBackend:
    p = (provider or "none").strip().lower()
    if p in ("", "none", "off"):
        return NoopWebSearch()
    if p == "tavily":
        return TavilyWebSearch()
    # openai_web, searxng, brave: wire when product adds them
    return NoopWebSearch()
