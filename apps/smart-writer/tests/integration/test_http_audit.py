"""HTTP /audit contract tests (workflow mocked; no OpenAI)."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.null_repo import NullRepo
from app.entrypoints.http import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_audit_returns_run_id_and_persistence_flag(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")

    fake_state = {
        "iterations": 1,
        "max_iterations": 1,
        "aggregate_value_score": 12.0,
        "aggregate_history": [12.0],
        "draft": "Final text.",
        "run_id": "00000000-0000-0000-0000-000000000099",
        "last_assessments": [],
        "composed_values": None,
        "merged_feedback": "",
    }

    with (
        patch("app.orchestrator.run.run_workflow", new_callable=AsyncMock, return_value=fake_state),
        patch("app.orchestrator.run.get_repo", return_value=NullRepo()),
    ):
        r = client.post(
            "/audit",
            json={
                "raw_input": "Write one sentence about testing.",
                "max_iterations": 1,
            },
        )

    assert r.status_code == 200
    data = r.json()
    assert data["stop_reason"] == "max_iterations"
    assert data["iterations"] == 1
    assert data["draft"] == "Final text."
    assert data["run_id"] == fake_state["run_id"]
    assert data["persistence_enabled"] is False


def test_audit_504_on_timeout(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    monkeypatch.setenv("SMART_WRITER_AUDIT_TIMEOUT_SEC", "0.05")

    async def slow(_initial: dict) -> dict:
        import asyncio

        await asyncio.sleep(60)
        return {}

    with patch("app.orchestrator.run.run_workflow", side_effect=slow):
        r = client.post(
            "/audit",
            json={"raw_input": "x", "max_iterations": 1},
        )

    assert r.status_code == 504
    assert "timeout" in r.json()["detail"].lower()
