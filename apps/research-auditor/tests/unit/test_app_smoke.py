"""Minimal unit smoke test so pytest and coverage run. Expand with real tests."""

import pytest


def test_workflow_entrypoint_importable() -> None:
    """Workflow entrypoint (run_workflow) is importable and callable."""
    from app.orchestrator.run import run_workflow

    assert run_workflow is not None
    assert callable(run_workflow)
