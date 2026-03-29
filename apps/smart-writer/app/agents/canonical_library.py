"""Canonical domain library: map catalog rows to composed pipeline types (design §4, §6)."""

from __future__ import annotations

from collections.abc import Sequence

from app.agents.canonical_library_ids import library_value_id
from app.agents.models import CanonicalValueEntry, ValueDefinition, ValueRubric


def value_definition_from_canonical_entry(entry: CanonicalValueEntry) -> ValueDefinition:
    """Build a ``ValueDefinition`` for ``compose_values`` from a catalog row.

    Field mapping (locked):
    - ``description`` ← ``short_description`` (assessor/writer copy).
    - ``raw_weight`` ← ``default_raw_weight``.
    - ``value_id`` ← ``library_value_id(canonical_id)``; ``canonical_id`` set; no ``craft_key``.
    """
    return ValueDefinition(
        value_id=library_value_id(entry.canonical_id),
        name=entry.name,
        description=entry.short_description,
        raw_weight=entry.default_raw_weight,
        canonical_id=entry.canonical_id,
    )


def ensure_rubric_aligns_canonical(rubric: ValueRubric, canonical_id: str) -> ValueRubric:
    """Return ``rubric`` with ``value_id`` aligned to ``library_value_id(canonical_id)``."""
    expected_id = library_value_id(canonical_id)
    if rubric.value_id == expected_id:
        return rubric
    return rubric.model_copy(update={"value_id": expected_id})


def library_rubric_map_from_entries(entries: Sequence[CanonicalValueEntry]) -> dict[str, ValueRubric]:
    """Map ``value_id`` → stored catalog rubric for :func:`run_build_rubrics`."""
    return {library_value_id(e.canonical_id): e.rubric for e in entries}
