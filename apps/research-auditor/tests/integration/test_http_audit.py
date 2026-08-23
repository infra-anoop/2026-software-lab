"""HTTP /audit job contract tests (workflow mocked; no OpenAI)."""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.entrypoints.http import app

SECRET = "test-secret"
AUTH = {"X-Audit-Secret": SECRET}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("RESEARCH_AUDITOR_AUDIT_SECRET", SECRET)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    from app.config import get_settings

    get_settings.cache_clear()
    with TestClient(app) as c:
        yield c


def _wait_terminal(client: TestClient, job_id: str, timeout: float = 5.0):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = client.get(f"/jobs/{job_id}", headers=AUTH)
        if last.status_code == 200 and last.json()["status"] not in ("queued", "running"):
            return last
        time.sleep(0.05)
    raise AssertionError(last.text if last is not None else "no job response")


def test_health_public(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_audit_enqueues_and_get_returns_result(client: TestClient) -> None:
    fake_state = {
        "research": SimpleNamespace(source_material_title="Title", executive_summary=["finding"]),
        "feedback": SimpleNamespace(verdict="PASS", summary="Looks good."),
        "iterations": 1,
    }

    with patch("app.orchestrator.run.run_workflow", new_callable=AsyncMock, return_value=fake_state):
        r = client.post(
            "/audit",
            headers=AUTH,
            json={"raw_input": "Some topic to audit", "max_iterations": 1},
        )
        assert r.status_code == 202
        body = r.json()
        assert body["status"] == "queued"
        assert "verdict" not in body
        job_id = body["job_id"]
        done = _wait_terminal(client, job_id)
        data = done.json()
        assert data["status"] == "succeeded"
        result = data["result"]
        assert result["verdict"] == "PASS"
        assert result["title"] == "Title"
        assert result["findings"] == ["finding"]
        assert result["summary"] == "Looks good."
        assert result["iterations"] == 1


def test_audit_401_without_secret(client: TestClient) -> None:
    r = client.post("/audit", json={"raw_input": "hello world", "max_iterations": 1})
    assert r.status_code == 401


def test_audit_401_wrong_secret(client: TestClient) -> None:
    r = client.post(
        "/audit",
        headers={"X-Audit-Secret": "nope"},
        json={"raw_input": "hello world", "max_iterations": 1},
    )
    assert r.status_code == 401


def test_get_job_401_without_secret(client: TestClient) -> None:
    r = client.get("/jobs/00000000-0000-0000-0000-000000000001")
    assert r.status_code == 401


def test_audit_max_iterations_99_is_422(client: TestClient) -> None:
    r = client.post(
        "/audit",
        headers=AUTH,
        json={"raw_input": "hello world", "max_iterations": 99},
    )
    assert r.status_code == 422


def test_get_job_404(client: TestClient) -> None:
    r = client.get("/jobs/00000000-0000-0000-0000-000000000001", headers=AUTH)
    assert r.status_code == 404


def test_audit_503_when_secret_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RESEARCH_AUDITOR_AUDIT_SECRET", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    with TestClient(app) as c:
        r = c.post("/audit", json={"raw_input": "hello world", "max_iterations": 1})
    assert r.status_code == 503


def test_job_timed_out(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESEARCH_AUDITOR_AUDIT_TIMEOUT_SEC", "0.05")
    from app.config import get_settings

    get_settings.cache_clear()

    async def slow(_initial: dict) -> dict:
        import asyncio

        await asyncio.sleep(30)
        return {}

    with patch("app.orchestrator.run.run_workflow", side_effect=slow):
        r = client.post("/audit", headers=AUTH, json={"raw_input": "x", "max_iterations": 1})
        assert r.status_code == 202
        done = _wait_terminal(client, r.json()["job_id"], timeout=8.0)
    assert done.json()["status"] == "timed_out"


def test_audit_429_when_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESEARCH_AUDITOR_AUDIT_SECRET", SECRET)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    monkeypatch.setenv("RESEARCH_AUDITOR_AUDIT_RATE_LIMIT_PER_MIN", "1")
    from app.config import get_settings

    get_settings.cache_clear()
    body = {"raw_input": "hello world", "max_iterations": 1}
    with (
        patch("app.orchestrator.run.run_workflow", new_callable=AsyncMock, return_value={}),
        TestClient(app) as c,
    ):
        first = c.post("/audit", headers=AUTH, json=body)
        assert first.status_code == 202
        second = c.post("/audit", headers=AUTH, json=body)
        assert second.status_code == 429
