"""Revise without a stored parent is 409 (T17 — helper, not MessageTurnIn)."""

from __future__ import annotations

import pytest

from app.orchestrator.turn_mode import (
    ReviseWithoutParentError,
    require_revise_parent,
    resolve_write_mode,
)


def test_require_revise_parent_missing_id() -> None:
    with pytest.raises(ReviseWithoutParentError):
        require_revise_parent(None, parent_exists=False)


def test_require_revise_parent_unknown_id() -> None:
    with pytest.raises(ReviseWithoutParentError):
        require_revise_parent("does-not-exist", parent_exists=False)


def test_require_revise_parent_ok() -> None:
    assert require_revise_parent("art_1", parent_exists=True) == "art_1"


def test_auto_without_last_artifact_is_generate() -> None:
    mode, parent = resolve_write_mode(client_intent="auto", last_artifact_id=None)
    assert mode == "generate"
    assert parent is None


def test_auto_with_last_artifact_is_revise() -> None:
    mode, parent = resolve_write_mode(client_intent="auto", last_artifact_id="art_1")
    assert mode == "revise"
    assert parent == "art_1"


def test_regenerate_forces_generate() -> None:
    mode, parent = resolve_write_mode(
        client_intent="regenerate",
        last_artifact_id="art_1",
    )
    assert mode == "generate"
    assert parent is None
