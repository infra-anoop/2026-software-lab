"""Orchestrate user reference text, URL fetch, and optional search → EvidenceBundle."""

from __future__ import annotations

import os
from typing import Literal

from app.agents.models import (
    MAX_CHUNK_CHARS,
    MAX_EVIDENCE_CHUNKS,
    MAX_EVIDENCE_TOTAL_CHARS,
    EvidenceBundle,
    EvidenceChunk,
    SourceRef,
)
from app.retrieval.fetch_safe import FetchBudget, fetch_url_text, utc_now_iso
from app.retrieval.search_backends import get_web_search_backend
from app.retrieval.url_extract import extract_urls

RetrievalMode = Literal["auto", "urls_only", "search_only", "none"]


def _trim(s: str, cap: int) -> str:
    s = s.strip()
    if len(s) <= cap:
        return s
    return s[: cap - 1] + "…"


def _append_chunk(
    bundle: EvidenceBundle,
    *,
    chunk_id: str,
    source_id: str,
    text: str,
    provenance: str,
    query: str | None = None,
) -> None:
    t = _trim(text, MAX_CHUNK_CHARS)
    if not t:
        return
    bundle.chunks.append(
        EvidenceChunk(
            chunk_id=chunk_id,
            source_id=source_id,
            text=t,
            provenance=provenance,
            query=query,
        )
    )


def _dedupe_sources(bundle: EvidenceBundle) -> None:
    seen: set[str] = set()
    uniq: list[SourceRef] = []
    for s in bundle.sources:
        if s.source_id in seen:
            continue
        seen.add(s.source_id)
        uniq.append(s)
    bundle.sources = uniq


def _enforce_budget(bundle: EvidenceBundle) -> None:
    """Trim chunks to ``MAX_EVIDENCE_CHUNKS`` and ``MAX_EVIDENCE_TOTAL_CHARS`` (deterministic order)."""
    total = 0
    kept: list[EvidenceChunk] = []
    for ch in bundle.chunks[:MAX_EVIDENCE_CHUNKS]:
        if total + len(ch.text) > MAX_EVIDENCE_TOTAL_CHARS:
            remain = MAX_EVIDENCE_TOTAL_CHARS - total
            if remain < 200:
                break
            ch = ch.model_copy(update={"text": _trim(ch.text, remain)})
        kept.append(ch)
        total += len(ch.text)
    bundle.chunks = kept
    sids = {c.source_id for c in kept}
    bundle.sources = [s for s in bundle.sources if s.source_id in sids]
    _dedupe_sources(bundle)


def _retrieval_query_from_prompt(raw_input: str) -> str:
    q = " ".join(raw_input.split())
    return _trim(q, 400)


def _merge_retrieval_query(
    raw_input: str,
    supplemental_queries: list[str] | None,
) -> str:
    """Base query from prompt plus optional planner ``suggested_research_queries`` (deterministic)."""
    base = _retrieval_query_from_prompt(raw_input)
    extra = [q.strip() for q in (supplemental_queries or []) if q and str(q).strip()]
    if not extra:
        return base
    merged = f"{base}\n" + "\n".join(extra[:8])
    return _trim(merged, 500)


async def build_bundle_from_prompt(
    raw_input: str,
    *,
    reference_material: str | None = None,
    mode: RetrievalMode = "auto",
    max_url_fetches: int | None = None,
    supplemental_queries: list[str] | None = None,
) -> tuple[EvidenceBundle, str]:
    """Build evidence bundle and return ``(bundle, retrieval_query)``.

    When ``supplemental_queries`` is set (e.g. from research planning), it is merged into the
    search query string used for web search (deterministic join); URL extraction still uses ``raw_input``.
    """
    notes: list[str] = []
    bundle = EvidenceBundle()

    if mode == "none":
        return bundle, _merge_retrieval_query(raw_input, supplemental_queries)

    ref = (reference_material or "").strip()
    if ref and mode != "search_only":
        now = utc_now_iso()
        sid = "user_ref"
        bundle.sources.append(
            SourceRef(
                source_id=sid,
                kind="upload",
                title="Reference material",
                url=None,
                retrieved_at=now,
                snippet=_trim(ref, 200),
            )
        )
        _append_chunk(bundle, chunk_id=f"{sid}_c0", source_id=sid, text=ref, provenance="user_supplied")

    cap_fetch = max_url_fetches
    if cap_fetch is None:
        try:
            cap_fetch = int(os.getenv("SMART_WRITER_MAX_URL_FETCHES", "6"))
        except ValueError:
            cap_fetch = 6
    cap_fetch = max(0, min(cap_fetch, 24))

    urls: list[str] = []
    if mode in ("auto", "urls_only"):
        urls = extract_urls(raw_input, max_urls=cap_fetch)

    if urls and mode != "search_only":
        budget = FetchBudget()
        for i, u in enumerate(urls[:cap_fetch]):
            fetched = await fetch_url_text(u, budget=budget)
            if not fetched:
                notes.append(f"fetch_failed:{u}")
                continue
            final_url, title, text = fetched
            if len(text.strip()) < 80:
                notes.append(f"thin_content:{final_url}")
            now = utc_now_iso()
            sid = f"url_{i}"
            bundle.sources.append(
                SourceRef(
                    source_id=sid,
                    kind="url",
                    title=_trim(title, 300),
                    url=final_url,
                    retrieved_at=now,
                    snippet=_trim(text, 240),
                )
            )
            _append_chunk(
                bundle,
                chunk_id=f"{sid}_c0",
                source_id=sid,
                text=text,
                provenance="url_fetch",
            )

    retrieval_query = _merge_retrieval_query(raw_input, supplemental_queries)
    provider = os.getenv("SMART_WRITER_SEARCH_PROVIDER", "none").strip().lower()
    want_search = mode == "search_only" or (
        mode == "auto"
        and not bundle.chunks
        and provider not in ("", "none", "off")
    )
    if want_search and retrieval_query:
        backend = get_web_search_backend(provider)
        extra = await backend.search(retrieval_query)
        bundle.chunks.extend(extra.chunks)
        bundle.sources.extend(extra.sources)
        if not extra.chunks and provider not in ("none", "off", ""):
            notes.append("search_no_results")

    if notes:
        bundle.retrieval_notes = "; ".join(notes)
    _dedupe_sources(bundle)
    _enforce_budget(bundle)
    return bundle, retrieval_query
