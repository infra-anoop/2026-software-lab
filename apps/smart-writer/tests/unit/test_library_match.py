"""Unit tests for canonical library similarity selection (design §5.2)."""

import json
from pathlib import Path

import pytest

from app.agents.canonical_library import value_definition_from_canonical_entry
from app.agents.library_match import (
    build_library_matches,
    default_canonical_library_path,
    get_library_match_threshold,
    get_library_max_matches,
    load_canonical_catalog,
    run_library_match,
    score_catalog_against_query,
    select_matched_entries,
)
from app.agents.models import CanonicalValueEntry, LibraryMatch, decoder_domain_slot_bounds
from app.orchestrator.run import match_canonical_library_node
from tests.fixtures.sample_payloads import make_value_rubric


def _entry(cid: str, sim_axis: float = 0.0) -> CanonicalValueEntry:
    """sim_axis unused except for test naming; embedding uses match_text."""
    return CanonicalValueEntry(
        canonical_id=cid,
        name=cid,
        short_description="d",
        match_text=f"text for {cid}",
        rubric=make_value_rubric(f"LIB_{cid}", cid),
        enabled=True,
    )


def test_decoder_domain_slot_bounds_k_zero() -> None:
    assert decoder_domain_slot_bounds(0) == (5, 8)


def test_decoder_domain_slot_bounds_k_two() -> None:
    assert decoder_domain_slot_bounds(2) == (3, 6)


def test_decoder_domain_slot_bounds_k_eight() -> None:
    assert decoder_domain_slot_bounds(8) == (0, 0)


def test_decoder_domain_slot_bounds_invalid_k() -> None:
    with pytest.raises(ValueError, match="library_domain_count"):
        decoder_domain_slot_bounds(9)


def test_score_catalog_against_query_ordering() -> None:
    e1, e2, e3 = _entry("a"), _entry("b"), _entry("c")
    q = [1.0, 0.0, 0.0]
    # a: 1, b: 0, c: 0 — tie b,c broken by canonical_id
    va = [1.0, 0.0, 0.0]
    vb = [0.0, 1.0, 0.0]
    vc = [0.0, 0.0, 1.0]
    scored = score_catalog_against_query(q, [e1, e2, e3], [va, vb, vc])
    ids = [e.canonical_id for e, _ in scored]
    assert ids[0] == "a"
    assert set(ids[1:]) == {"b", "c"}


def test_select_matched_entries_threshold_and_trim() -> None:
    e1, e2, e3 = _entry("z_high"), _entry("y_mid"), _entry("x_low")
    scored = [(e1, 0.9), (e2, 0.85), (e3, 0.5)]
    picked, note = select_matched_entries(
        scored,
        threshold=0.82,
        margin=0.0,
        max_matches=2,
        max_domain=2,
    )
    assert [e.canonical_id for e in picked] == ["z_high", "y_mid"]
    assert note is None


def test_select_matched_entries_margin_rejects() -> None:
    e1, e2 = _entry("a"), _entry("b")
    scored = [(e1, 0.9), (e2, 0.89)]
    picked, note = select_matched_entries(
        scored,
        threshold=0.5,
        margin=0.05,
        max_matches=3,
        max_domain=8,
    )
    assert picked == []
    assert note == "margin_gate_rejected_top_two_too_close"


def test_select_matched_entries_margin_single_passer() -> None:
    e1, e2 = _entry("a"), _entry("b")
    scored = [(e1, 0.9), (e2, 0.3)]
    picked, _note = select_matched_entries(
        scored,
        threshold=0.82,
        margin=0.1,
        max_matches=3,
        max_domain=8,
    )
    assert [e.canonical_id for e in picked] == ["a"]


def test_select_matched_entries_trims_to_max_domain() -> None:
    entries = [_entry(f"v{i}") for i in range(4)]
    scored = [(e, 0.95 - i * 0.01) for i, e in enumerate(entries)]
    picked, note = select_matched_entries(
        scored,
        threshold=0.5,
        margin=0.0,
        max_matches=10,
        max_domain=2,
    )
    assert len(picked) == 2
    assert note is not None and "trimmed_to_max_domain" in note


def test_build_library_matches_matched_flag() -> None:
    e1, e2 = _entry("a"), _entry("b")
    scored = [(e1, 0.9), (e2, 0.7)]
    lm = build_library_matches(scored, {"a"})
    assert lm == [
        LibraryMatch(canonical_id="a", similarity=0.9, rank=1, matched=True),
        LibraryMatch(canonical_id="b", similarity=0.7, rank=2, matched=False),
    ]


def test_get_library_match_threshold_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_LIBRARY_MATCH_THRESHOLD", "0.9")
    assert get_library_match_threshold(override=0.1) == 0.1
    assert abs(get_library_match_threshold(override=None) - 0.9) < 1e-9


def test_get_library_max_matches_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_LIBRARY_MAX_MATCHES", "5")
    assert get_library_max_matches(override=2) == 2
    assert get_library_max_matches(override=None) == 5


def test_load_canonical_catalog_default_file_exists() -> None:
    p = default_canonical_library_path()
    assert p.is_file(), f"missing seed {p}"
    rows = load_canonical_catalog(p)
    assert len(rows) >= 3
    assert all(isinstance(r, CanonicalValueEntry) for r in rows)


def test_run_library_match_with_fixed_vectors(monkeypatch: pytest.MonkeyPatch) -> None:
    """No HTTP: stub ``embed_texts`` to return orthogonal one-hot vectors."""
    e_grant = _entry("grant_nonprofit_persuasion")
    e_other = _entry("other")
    catalog = [e_grant, e_other]

    def fake_embed(texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for t in texts:
            if "grant" in t.lower() or "nonprofit" in t.lower():
                out.append([1.0, 0.0, 0.0])
            else:
                out.append([0.0, 1.0, 0.0])
        return out

    monkeypatch.setattr("app.agents.library_match.embed_texts", fake_embed)

    raw = run_library_match(
        "Write a nonprofit grant proposal for literacy funding.",
        catalog=catalog,
        threshold=0.5,
        margin=0.0,
        max_matches=2,
    )
    assert raw["library_domain_count"] == 1
    assert raw["canonical_ids_used"] == ["grant_nonprofit_persuasion"]
    assert len(raw["library_domain_rows"]) == 1
    assert raw["library_domain_rows"][0].value_id == "LIB_grant_nonprofit_persuasion"


def test_run_library_match_skip_on_embedding_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_EMBEDDING_ON_FAILURE", "skip_library")

    def boom(_texts: list[str]) -> list[list[float]]:
        raise RuntimeError("api down")

    monkeypatch.setattr("app.agents.library_match.embed_texts", boom)
    raw = run_library_match(
        "x",
        catalog=[_entry("a")],
        threshold=0.5,
        margin=0.0,
        max_matches=3,
    )
    assert raw["library_domain_count"] == 0
    assert "embedding_failed" in (raw.get("library_resolution_notes") or "")


def test_run_library_match_fail_run_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_EMBEDDING_ON_FAILURE", "fail_run")

    def boom(_texts: list[str]) -> list[list[float]]:
        raise RuntimeError("api down")

    monkeypatch.setattr("app.agents.library_match.embed_texts", boom)
    with pytest.raises(RuntimeError, match="api down"):
        run_library_match(
            "x",
            catalog=[_entry("a")],
            threshold=0.5,
            margin=0.0,
            max_matches=3,
        )


@pytest.mark.asyncio
async def test_match_canonical_library_node_disabled() -> None:
    out = await match_canonical_library_node(
        {"library_enabled": False, "raw_input": "x", "history": [], "run_id": None, "step": 1},
    )
    assert out["library_domain_count"] == 0
    assert out["canonical_ids_used"] == []
    assert out["library_matches"] == []


@pytest.mark.asyncio
async def test_match_canonical_library_node_enabled_uses_threaded_match(monkeypatch: pytest.MonkeyPatch) -> None:
    e = _entry("matched_one")

    def fake_match(
        _raw: str,
        *,
        catalog: list[CanonicalValueEntry] | None = None,
        threshold: float,
        margin: float,
        max_matches: int,
        max_domain: int = 8,
    ) -> dict:
        return {
            "library_matches": [],
            "library_domain_rows": [value_definition_from_canonical_entry(e)],
            "canonical_library_entries": [e],
            "canonical_ids_used": [e.canonical_id],
            "library_domain_count": 1,
            "library_version_aggregate": "matched_one:1",
            "library_resolution_notes": None,
        }

    monkeypatch.setattr("app.orchestrator.run.run_library_match", fake_match)

    out = await match_canonical_library_node(
        {
            "library_enabled": True,
            "raw_input": "prompt",
            "history": [],
            "run_id": None,
            "step": 1,
            "library_match_threshold": None,
            "library_max_matches": None,
        },
    )
    assert out["library_domain_count"] == 1
    assert out["canonical_ids_used"] == ["matched_one"]
    assert len(out["library_domain_rows"]) == 1


def test_load_canonical_catalog_backfills_empty_match_text(tmp_path: Path) -> None:
    rid = "LIB_tmp_x"
    row = {
        "canonical_id": "tmp_x",
        "name": "Tmp Name",
        "short_description": "Tmp desc",
        "match_text": "",
        "rubric": make_value_rubric(rid, "Tmp").model_dump(),
    }
    p = tmp_path / "c.json"
    p.write_text(json.dumps([row]), encoding="utf-8")
    loaded = load_canonical_catalog(p)
    assert len(loaded) == 1
    assert "Tmp Name" in loaded[0].match_text and "Tmp desc" in loaded[0].match_text
