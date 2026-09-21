"""D3 / T064: terminal job snapshots expose elapsed_ms + usage keys."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.contract.grant_flow import submit_grant_and_wait


def _assert_observability_keys(job: dict[str, Any]) -> None:
    assert "elapsed_ms" in job
    assert "usage" in job
    elapsed = job["elapsed_ms"]
    assert elapsed is None or (isinstance(elapsed, int) and not isinstance(elapsed, bool))
    if isinstance(elapsed, int):
        assert elapsed >= 0
    usage = job["usage"]
    assert usage is None or isinstance(usage, dict)
    if isinstance(usage, dict):
        assert "input_tokens" in usage
        assert "output_tokens" in usage
        for key in ("input_tokens", "output_tokens"):
            val = usage[key]
            assert val is None or (isinstance(val, int) and not isinstance(val, bool))
        if "estimated_cost_usd" in usage:
            cost = usage["estimated_cost_usd"]
            assert cost is None or isinstance(cost, (int, float))


def test_terminal_job_includes_elapsed_and_usage(client: TestClient) -> None:
    """Succeeded write job MUST expose D3 observability keys (contract http-api)."""
    _conversation_id, _accepted, job = submit_grant_and_wait(client)
    assert job["status"] == "succeeded"
    _assert_observability_keys(job)
