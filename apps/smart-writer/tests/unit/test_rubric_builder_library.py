"""Library path for run_build_rubrics (clone / refresh)."""

import pytest

from app.agents.canonical_library import library_rubric_map_from_entries, value_definition_from_canonical_entry
from app.agents.models import CanonicalValueEntry, ComposedValues, ValueDefinition
from app.agents.rubric_builder import run_build_rubrics
from app.orchestrator.run import _resolve_library_rubric_map_for_build
from tests.fixtures.sample_payloads import make_value_rubric


def _entry(canonical_id: str = "grant_x") -> CanonicalValueEntry:
    rid = f"LIB_{canonical_id}"
    return CanonicalValueEntry(
        canonical_id=canonical_id,
        name="Grant",
        short_description="Short.",
        match_text="match text",
        rubric=make_value_rubric(rid, "Grant"),
    )


def test_library_rubric_map_from_entries() -> None:
    e = _entry()
    m = library_rubric_map_from_entries([e])
    assert list(m.keys()) == ["LIB_grant_x"]
    assert m["LIB_grant_x"].value_id == "LIB_grant_x"


@pytest.mark.asyncio
async def test_run_build_rubrics_library_clone_when_refresh_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_LIBRARY_REFRESH_ANCHORS", "false")
    e = _entry()
    vd = value_definition_from_canonical_entry(e)
    vd = vd.model_copy(update={"weight": 1.0})
    composed = ComposedValues(values=[vd])
    built = await run_build_rubrics(
        "Write a short appeal.",
        composed,
        library_rubric_by_value_id=library_rubric_map_from_entries([e]),
    )
    assert len(built.rubrics) == 1
    assert built.rubrics[0].value_id == "LIB_grant_x"
    assert built.rubrics[0].dimensions[0].name == e.rubric.dimensions[0].name


def test_resolve_library_rubric_map_prefers_explicit_over_entries() -> None:
    e = _entry()
    vd = value_definition_from_canonical_entry(e)
    vd = vd.model_copy(update={"weight": 1.0})
    composed = ComposedValues(values=[vd])
    alt = make_value_rubric("LIB_grant_x", "Override name")
    state = {
        "canonical_library_entries": [e.model_dump()],
        "library_rubric_by_value_id": {"LIB_grant_x": alt.model_dump()},
    }
    m = _resolve_library_rubric_map_for_build(state, composed)  # type: ignore[arg-type]
    assert m is not None
    assert m["LIB_grant_x"].value_name == "Override name"


def test_resolve_library_rubric_map_from_entries_only() -> None:
    e = _entry()
    vd = value_definition_from_canonical_entry(e)
    vd = vd.model_copy(update={"weight": 1.0})
    composed = ComposedValues(values=[vd])
    state: dict = {"canonical_library_entries": [e.model_dump()]}
    m = _resolve_library_rubric_map_for_build(state, composed)  # type: ignore[arg-type]
    assert m is not None and m["LIB_grant_x"].value_id == "LIB_grant_x"


def test_resolve_library_rubric_map_missing_raises() -> None:
    vd = ValueDefinition(
        value_id="LIB_orphan",
        name="o",
        description="d",
        raw_weight=1.0,
        canonical_id="orphan",
        weight=1.0,
    )
    composed = ComposedValues(values=[vd])
    with pytest.raises(ValueError, match="canonical_library_entries"):
        _resolve_library_rubric_map_for_build({}, composed)  # type: ignore[arg-type]
