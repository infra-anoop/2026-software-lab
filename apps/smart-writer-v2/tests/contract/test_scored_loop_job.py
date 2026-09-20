"""D8 dual-axis scored inner loop on job snapshot (http-api hook 7; catalog loop.*).

T079 — red until T081–T085 wire rubric → write ↔ assess and persist loop metadata.
Public HTTP only; do not stub the graph to the assertion JSON.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import get_max_inner_assessor_turns, get_settings
from app.entrypoints.http import app
from tests.contract.grant_flow import (
    AUTH,
    SECRET,
    post_followup_turn,
    submit_grant_and_wait,
    wait_job_success,
)

_STOP_REASONS = frozenset({"max_iterations", "targets_met", "error"})


def _assert_scored_loop(job: dict[str, Any], *, max_inner: int) -> None:
    """Structural D8 / FR-022 checks (catalog loop.scores_and_stop, iterations_cap, dual_axis)."""
    assert job.get("status") == "succeeded"
    rubric_id = job.get("rubric_id")
    assert isinstance(rubric_id, str) and rubric_id.strip() != ""
    assert "loop" in job, "succeeded write job must expose loop metadata (D8)"
    loop = job["loop"]
    assert isinstance(loop, dict)

    iterations = loop.get("iterations")
    max_iterations = loop.get("max_iterations")
    assert isinstance(max_iterations, int)
    assert max_iterations == max_inner
    assert max_iterations <= 8
    assert isinstance(iterations, int)
    assert 1 <= iterations <= max_iterations

    aggregate = loop.get("aggregate_score")
    assert isinstance(aggregate, (int, float))
    assert not isinstance(aggregate, bool)

    stop_reason = loop.get("stop_reason")
    assert stop_reason in _STOP_REASONS

    axis_a = loop.get("axis_a_dimension_count")
    axis_b = loop.get("axis_b_dimension_count")
    assert isinstance(axis_a, int) and axis_a >= 1
    assert isinstance(axis_b, int) and axis_b >= 1

    scores = loop.get("scores")
    assert isinstance(scores, list) and len(scores) >= 1
    assert len(scores) == iterations
    for entry in scores:
        assert isinstance(entry, dict)
        turn = entry.get("iteration")
        assert isinstance(turn, int)
        assert 1 <= turn <= max_iterations
        dims = entry.get("dimension_scores")
        assert isinstance(dims, list) and len(dims) >= 1
        for dim in dims:
            assert isinstance(dim, dict)
            assert isinstance(dim.get("id"), str) and dim["id"].strip() != ""
            score = dim.get("score")
            assert isinstance(score, (int, float)) and not isinstance(score, bool)
        turn_agg = entry.get("aggregate_score")
        assert isinstance(turn_agg, (int, float)) and not isinstance(turn_agg, bool)
        feedback = entry.get("feedback")
        assert isinstance(feedback, str) and feedback.strip() != ""


def test_generate_job_exposes_dual_axis_scored_loop(client: TestClient) -> None:
    """Succeeded generate: rubric_id + scored loop ≤ Settings inner max."""
    _conversation_id, _accepted, job = submit_grant_and_wait(client)
    _assert_scored_loop(job, max_inner=get_max_inner_assessor_turns())


def test_revise_job_runs_same_scored_loop(client: TestClient) -> None:
    """Succeeded revise also carries dual-axis scored loop (D8 / T084)."""
    conversation_id, _accepted, first = submit_grant_and_wait(client)
    response = post_followup_turn(
        client,
        conversation_id,
        "Tighten the funder-fit paragraph and keep the ask concrete.",
        client_intent="auto",
    )
    assert response.status_code in {200, 202}, response.text
    accepted = response.json()
    assert accepted.get("type") == "job_accepted"
    job = wait_job_success(client, accepted["job_id"])
    assert job["mode"] == "revise"
    _assert_scored_loop(job, max_inner=get_max_inner_assessor_turns())


def test_loop_max_iterations_follows_settings_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inner cap is Settings-backed: max_iterations must equal override (≤8 enforcement)."""
    monkeypatch.setenv("SMART_WRITER_V2_AUDIT_SECRET", SECRET)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    monkeypatch.setenv("SMART_WRITER_V2_MAX_INNER_ASSESSOR_TURNS", "5")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            _conversation_id, _accepted, job = submit_grant_and_wait(client)
            assert get_max_inner_assessor_turns() == 5
            _assert_scored_loop(job, max_inner=5)
            assert job["loop"]["iterations"] <= 5
    finally:
        get_settings.cache_clear()
