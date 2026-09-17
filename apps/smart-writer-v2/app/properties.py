"""Closed property vocabulary (research.md R8). ``factual`` is tone-only, not a grounding off-switch."""

from __future__ import annotations

SEED_PROPERTIES: tuple[str, ...] = (
    "factual",
    "persuasive",
    "concise",
    "warm",
    "formal",
    "humorous",
    "specific",
    "urgent",
)

_SEED_SET = frozenset(SEED_PROPERTIES)


def is_closed_property(property_id: str) -> bool:
    """Return True if ``property_id`` is in the seed closed list."""
    return property_id in _SEED_SET


def filter_closed_ranking(ranking: list[str]) -> list[str]:
    """Keep only closed ids, preserve order, drop duplicates."""
    seen: set[str] = set()
    out: list[str] = []
    for item in ranking:
        if item not in _SEED_SET or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out
