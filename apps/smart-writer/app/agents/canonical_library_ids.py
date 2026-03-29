"""Canonical library id conventions (design: Option A for value_id vs canonical_id)."""

from __future__ import annotations

# Pipeline namespace for matched library rows; decoder output must not use this prefix.
LIBRARY_VALUE_ID_PREFIX = "LIB_"


def library_value_id(canonical_id: str) -> str:
    """Return ``value_id`` for a composed library row: ``LIB_<canonical_id>``.

    ``canonical_id`` is the stable catalog primary key (slug). No extra sanitization
    in v1 — operators must use slug-safe ids (e.g. ``[a-z0-9_]+``).
    """
    cid = canonical_id.strip()
    if not cid:
        raise ValueError("canonical_id must be non-empty")
    return f"{LIBRARY_VALUE_ID_PREFIX}{cid}"


def canonical_id_from_library_value_id(value_id: str) -> str | None:
    """If ``value_id`` is a library pipeline id, return ``canonical_id``; else ``None``."""
    if not value_id.startswith(LIBRARY_VALUE_ID_PREFIX):
        return None
    rest = value_id[len(LIBRARY_VALUE_ID_PREFIX) :]
    return rest if rest else None
