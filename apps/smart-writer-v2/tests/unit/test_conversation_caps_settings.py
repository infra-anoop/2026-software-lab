"""D2 Settings knobs: locked defaults 3 / 10 / 8 (FR-022).

Inner max 8 is Settings-only until D8 graph enforcement (T083+); this unit test
documents the knob exists with the locked default.
"""

from __future__ import annotations

import pytest

from app.config import (
    DEFAULT_MAX_CLARIFY_TURNS_PER_CONVERSATION,
    DEFAULT_MAX_INNER_ASSESSOR_TURNS,
    DEFAULT_MAX_WRITE_JOBS_PER_CONVERSATION,
    get_max_clarify_turns_per_conversation,
    get_max_inner_assessor_turns,
    get_max_write_jobs_per_conversation,
    get_settings,
)


def test_d2_cap_defaults() -> None:
    get_settings.cache_clear()
    assert DEFAULT_MAX_WRITE_JOBS_PER_CONVERSATION == 3
    assert DEFAULT_MAX_CLARIFY_TURNS_PER_CONVERSATION == 10
    assert DEFAULT_MAX_INNER_ASSESSOR_TURNS == 8
    assert get_max_write_jobs_per_conversation() == 3
    assert get_max_clarify_turns_per_conversation() == 10
    assert get_max_inner_assessor_turns() == 8


def test_max_inner_assessor_turns_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inner max 8 is Settings-only until D8 loop; env override still works."""
    monkeypatch.setenv("SMART_WRITER_V2_MAX_INNER_ASSESSOR_TURNS", "5")
    get_settings.cache_clear()
    assert get_max_inner_assessor_turns() == 5
    get_settings.cache_clear()
