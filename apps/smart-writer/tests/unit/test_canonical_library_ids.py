"""Canonical library id helpers (Option A)."""

import pytest

from app.agents.canonical_library_ids import (
    LIBRARY_VALUE_ID_PREFIX,
    canonical_id_from_library_value_id,
    library_value_id,
)


def test_library_value_id_round_trip() -> None:
    cid = "grant_nonprofit_persuasion"
    vid = library_value_id(cid)
    assert vid == f"{LIBRARY_VALUE_ID_PREFIX}{cid}"
    assert canonical_id_from_library_value_id(vid) == cid


def test_canonical_id_from_library_value_id_non_library() -> None:
    assert canonical_id_from_library_value_id("V1") is None
    assert canonical_id_from_library_value_id("CRAFT_GRAMMAR") is None


def test_library_value_id_rejects_empty() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        library_value_id("")
