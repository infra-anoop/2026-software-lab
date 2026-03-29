"""Canonical library similarity matching (design §5.2–5.3, §10.1.1 P0)."""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import logfire

from app.agents.canonical_library import value_definition_from_canonical_entry
from app.agents.embeddings import (
    cosine_similarity,
    embed_texts,
    get_embedding_failure_policy,
    get_embedding_model_id,
)
from app.agents.models import (
    DEFAULT_MAX_VALUES,
    CanonicalValueEntry,
    LibraryMatch,
    ValueDefinition,
)

DEFAULT_LIBRARY_MATCH_THRESHOLD = 0.82
DEFAULT_LIBRARY_MAX_MATCHES = 3
DEFAULT_QUERY_EMBED_MAX_CHARS = 8_000


def _smart_writer_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_canonical_library_path() -> Path:
    """Default seed JSON: ``app/data/canonical_values.json`` under the smart-writer app root."""
    return _smart_writer_root() / "app" / "data" / "canonical_values.json"


def get_canonical_library_path() -> Path:
    raw = os.getenv("SMART_WRITER_CANONICAL_LIBRARY_PATH")
    if raw and str(raw).strip():
        return Path(str(raw).strip()).expanduser()
    return default_canonical_library_path()


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(str(raw).strip())
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(str(raw).strip(), 10)
    except ValueError:
        return default


def get_library_match_threshold(*, override: float | None = None) -> float:
    if override is not None:
        return max(-1.0, min(1.0, float(override)))
    return max(-1.0, min(1.0, _env_float("SMART_WRITER_LIBRARY_MATCH_THRESHOLD", DEFAULT_LIBRARY_MATCH_THRESHOLD)))


def get_library_match_margin() -> float:
    return max(0.0, _env_float("SMART_WRITER_LIBRARY_MATCH_MARGIN", 0.0))


def get_library_max_matches(*, override: int | None = None) -> int:
    if override is not None:
        return max(1, min(32, int(override)))
    return max(1, min(32, _env_int("SMART_WRITER_LIBRARY_MAX_MATCHES", DEFAULT_LIBRARY_MAX_MATCHES)))


def normalize_query_for_embedding(raw_input: str) -> str:
    s = (raw_input or "").strip()
    if len(s) > DEFAULT_QUERY_EMBED_MAX_CHARS:
        s = s[:DEFAULT_QUERY_EMBED_MAX_CHARS]
    return s


def _backfill_match_text(entry: CanonicalValueEntry) -> CanonicalValueEntry:
    mt = (entry.match_text or "").strip()
    if mt:
        return entry
    merged = f"{entry.name.strip()}\n\n{entry.short_description.strip()}".strip()
    if not merged:
        raise ValueError(f"Canonical entry {entry.canonical_id!r} has empty match_text and no backfill.")
    return entry.model_copy(update={"match_text": merged})


def load_canonical_catalog(path: Path | None = None) -> list[CanonicalValueEntry]:
    """Load and validate catalog JSON (list of :class:`CanonicalValueEntry`)."""
    p = path or get_canonical_library_path()
    if not p.is_file():
        logfire.warning("canonical_library.missing_file", path=str(p))
        return []
    raw_text = p.read_text(encoding="utf-8")
    data: Any = json.loads(raw_text)
    if not isinstance(data, list):
        raise ValueError(f"Canonical library JSON must be a list; got {type(data).__name__}")
    out: list[CanonicalValueEntry] = []
    for row in data:
        e = CanonicalValueEntry.model_validate(row)
        e = _backfill_match_text(e)
        out.append(e)
    return out


def _warn_model_mismatch(entries: Sequence[CanonicalValueEntry]) -> None:
    expected = get_embedding_model_id()
    for e in entries:
        if e.embedding_model_id != expected:
            logfire.warning(
                "canonical_library.embedding_model_mismatch",
                canonical_id=e.canonical_id,
                entry_model=e.embedding_model_id,
                env_model=expected,
            )


def score_catalog_against_query(
    query_vec: list[float],
    entries: list[CanonicalValueEntry],
    corpus_vecs: list[list[float]],
) -> list[tuple[CanonicalValueEntry, float]]:
    """Pair each enabled entry with cosine similarity to the query (pre-normalized vectors)."""
    if len(entries) != len(corpus_vecs):
        raise ValueError("entries and corpus_vecs length mismatch")
    scored: list[tuple[CanonicalValueEntry, float]] = []
    for e, cv in zip(entries, corpus_vecs, strict=True):
        if not e.enabled:
            continue
        scored.append((e, cosine_similarity(query_vec, cv)))
    scored.sort(key=lambda t: (-t[1], t[0].canonical_id))
    return scored


def select_matched_entries(
    scored: list[tuple[CanonicalValueEntry, float]],
    *,
    threshold: float,
    margin: float,
    max_matches: int,
    max_domain: int = DEFAULT_MAX_VALUES,
) -> tuple[list[CanonicalValueEntry], str | None]:
    """Return selected entries and optional trim/fail note (deterministic)."""
    note: str | None = None
    over_tau = [(e, s) for e, s in scored if s >= threshold]
    if margin > 0.0 and len(over_tau) >= 2:
        best, second = over_tau[0][1], over_tau[1][1]
        if best - second < margin:
            return [], "margin_gate_rejected_top_two_too_close"

    picked = [e for e, _ in over_tau[:max_matches]]
    if len(picked) > max_domain:
        # Trim lowest similarity first (tail of list — over_tau is sorted desc by score).
        drop = len(picked) - max_domain
        removed = [e.canonical_id for e in picked[-drop:]]
        picked = picked[:max_domain]
        note = f"trimmed_to_max_domain_removed={removed}"

    return picked, note


def build_library_matches(
    scored: list[tuple[CanonicalValueEntry, float]],
    selected_ids: set[str],
) -> list[LibraryMatch]:
    """All enabled-scored rows get a rank; ``matched`` iff ``canonical_id`` in ``selected_ids``."""
    matches: list[LibraryMatch] = []
    for rank, (e, sim) in enumerate(scored, start=1):
        matches.append(
            LibraryMatch(
                canonical_id=e.canonical_id,
                similarity=sim,
                rank=rank,
                matched=(e.canonical_id in selected_ids),
            )
        )
    return matches


def library_version_aggregate(entries: list[CanonicalValueEntry]) -> str | None:
    if not entries:
        return None
    parts = [f"{e.canonical_id}:{e.library_version}" for e in sorted(entries, key=lambda x: x.canonical_id)]
    return ";".join(parts)


def run_library_match(
    raw_input: str,
    *,
    catalog: list[CanonicalValueEntry] | None = None,
    threshold: float,
    margin: float,
    max_matches: int,
    max_domain: int = DEFAULT_MAX_VALUES,
) -> dict[str, Any]:
    """Synchronous match: embed query + corpus ``match_text``; return state patch fields.

    On embedding failure with policy ``skip_library``, returns empty selection and logs.
    """
    catalog_in = list(catalog) if catalog is not None else load_canonical_catalog()
    enabled = [e for e in catalog_in if e.enabled]
    if not enabled:
        return {
            "library_matches": [],
            "library_domain_rows": [],
            "canonical_library_entries": [],
            "canonical_ids_used": [],
            "library_domain_count": 0,
            "library_version_aggregate": None,
            "library_resolution_notes": None,
        }

    _warn_model_mismatch(enabled)
    qtext = normalize_query_for_embedding(raw_input)
    texts = [qtext] + [e.match_text.strip() for e in enabled]

    try:
        vectors = embed_texts(texts)
    except Exception as e:
        policy = get_embedding_failure_policy()
        logfire.exception("canonical_library.embedding_failed", policy=policy, error=str(e))
        if policy == "fail_run":
            raise
        return {
            "library_matches": [],
            "library_domain_rows": [],
            "canonical_library_entries": [],
            "canonical_ids_used": [],
            "library_domain_count": 0,
            "library_version_aggregate": None,
            "library_resolution_notes": f"embedding_failed_skip_library:{type(e).__name__}",
        }

    qvec, corpus = vectors[0], vectors[1:]
    scored = score_catalog_against_query(qvec, enabled, corpus)
    selected, note = select_matched_entries(
        scored,
        threshold=threshold,
        margin=margin,
        max_matches=max_matches,
        max_domain=max_domain,
    )
    selected_ids = {e.canonical_id for e in selected}
    library_matches = build_library_matches(scored, selected_ids)
    rows: list[ValueDefinition] = [value_definition_from_canonical_entry(e) for e in selected]

    top2_gap: float | None = None
    if len(scored) >= 2:
        top2_gap = scored[0][1] - scored[1][1]

    logfire.info(
        "canonical_library.match",
        k=len(selected),
        threshold=threshold,
        margin=margin,
        max_matches=max_matches,
        top2_gap=top2_gap,
        canonical_ids=list(selected_ids),
        resolution_note=note,
    )

    return {
        "library_matches": library_matches,
        "library_domain_rows": rows,
        "canonical_library_entries": selected,
        "canonical_ids_used": [e.canonical_id for e in selected],
        "library_domain_count": len(selected),
        "library_version_aggregate": library_version_aggregate(selected),
        "library_resolution_notes": note,
    }
