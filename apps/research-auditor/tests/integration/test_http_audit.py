"""HTTP /audit job contract tests (workflow mocked; no OpenAI).

Live Pydantic models in ``app.entrypoints.http`` are the contract.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.agents.models import AuditFeedback, Claim, Evidence, ResearchOutput
from app.config import get_settings
from app.entrypoints.http import AuditResponse, EnqueueResponse, JobView, app

SECRET = "test-secret"
AUTH = {"X-Audit-Secret": SECRET}

# Locked to live models — if these fail, update tests to match http.py (not the reverse).
AUDIT_RESPONSE_KEYS = frozenset(AuditResponse.model_fields)
ENQUEUE_RESPONSE_KEYS = frozenset(EnqueueResponse.model_fields)
JOB_VIEW_KEYS = frozenset(JobView.model_fields)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("RESEARCH_AUDITOR_AUDIT_SECRET", SECRET)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
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


def _fake_workflow_state() -> dict:
    """Orchestrator/state field names so ``_audit_response_from_state`` is exercised."""
    research = ResearchOutput(
        source_material_title="Title",
        executive_summary=["finding one", "finding two", "finding three"],
        claims=[
            Claim(
                claim_id="C1",
                claim="Claim one",
                evidence=[Evidence(quote="quote one")],
            ),
            Claim(
                claim_id="C2",
                claim="Claim two",
                evidence=[Evidence(quote="quote two")],
            ),
            Claim(
                claim_id="C3",
                claim="Claim three",
                evidence=[Evidence(quote="quote three")],
            ),
        ],
    )
    feedback = AuditFeedback(
        verdict="PASS",
        supported_claim_ratio=1.0,
        confidence_score=0.9,
        summary="Looks good.",
        next_action="None.",
    )
    return {
        "research": research,
        "feedback": feedback,
        "iterations": 1,
    }


def test_live_model_keys_locked() -> None:
    assert AUDIT_RESPONSE_KEYS == {
        "verdict",
        "iterations",
        "title",
        "summary",
        "findings",
    }
    assert ENQUEUE_RESPONSE_KEYS == {"job_id", "status", "location"}
    assert JOB_VIEW_KEYS == {
        "job_id",
        "status",
        "created_at",
        "started_at",
        "finished_at",
        "error",
        "result",
    }


def test_openapi_schemas_match_live_models(client: TestClient) -> None:
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert set(schemas["AuditResponse"]["properties"]) == AUDIT_RESPONSE_KEYS
    assert set(schemas["EnqueueResponse"]["properties"]) == ENQUEUE_RESPONSE_KEYS
    assert set(schemas["JobView"]["properties"]) == JOB_VIEW_KEYS


def test_health_public(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_health_public_when_secret_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RESEARCH_AUDITOR_AUDIT_SECRET", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    get_settings.cache_clear()
    with TestClient(app) as c:
        r = c.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_form_page_public(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")


def test_audit_enqueues_and_get_returns_result(client: TestClient) -> None:
    fake_state = _fake_workflow_state()

    with patch("app.orchestrator.run.run_workflow", new_callable=AsyncMock, return_value=fake_state):
        r = client.post(
            "/audit",
            headers=AUTH,
            json={"raw_input": "Some topic to audit", "max_iterations": 1},
        )
        assert r.status_code == 202
        body = r.json()
        assert set(body) == ENQUEUE_RESPONSE_KEYS
        assert body["status"] == "queued"
        assert "verdict" not in body
        assert "title" not in body
        job_id = body["job_id"]
        assert body["location"] == f"/jobs/{job_id}"
        assert r.headers.get("location") == f"/jobs/{job_id}"

        done = _wait_terminal(client, job_id)
        data = done.json()
        assert set(data) == JOB_VIEW_KEYS
        assert data["status"] == "succeeded"
        result = data["result"]
        assert set(result) == AUDIT_RESPONSE_KEYS
        assert result["verdict"] == "PASS"
        assert result["title"] == "Title"
        assert result["findings"] == ["finding one", "finding two", "finding three"]
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


def test_get_job_404(client: TestClient) -> None:
    r = client.get("/jobs/00000000-0000-0000-0000-000000000001", headers=AUTH)
    assert r.status_code == 404


def test_audit_503_when_secret_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RESEARCH_AUDITOR_AUDIT_SECRET", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    get_settings.cache_clear()
    with TestClient(app) as c:
        r = c.post("/audit", json={"raw_input": "hello world", "max_iterations": 1})
    assert r.status_code == 503


def test_audit_422_max_iterations_above_cap(client: TestClient) -> None:
    r = client.post(
        "/audit",
        headers=AUTH,
        json={"raw_input": "hello world", "max_iterations": 9},
    )
    assert r.status_code == 422


def test_audit_422_empty_raw_input(client: TestClient) -> None:
    r = client.post(
        "/audit",
        headers=AUTH,
        json={"raw_input": "", "max_iterations": 1},
    )
    assert r.status_code == 422


def test_audit_422_whitespace_only_raw_input(client: TestClient) -> None:
    r = client.post(
        "/audit",
        headers=AUTH,
        json={"raw_input": "   \n\t  ", "max_iterations": 1},
    )
    assert r.status_code == 422


def test_audit_429_queue_full(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESEARCH_AUDITOR_AUDIT_SECRET", SECRET)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    monkeypatch.setenv("RESEARCH_AUDITOR_JOB_QUEUE_MAX", "1")
    monkeypatch.setenv("RESEARCH_AUDITOR_JOB_CONCURRENCY", "1")
    get_settings.cache_clear()

    async def slow(_initial: dict) -> dict:
        import asyncio

        await asyncio.sleep(30)
        return {}

    with (
        TestClient(app) as c,
        patch("app.orchestrator.run.run_workflow", side_effect=slow),
    ):
        first = c.post("/audit", headers=AUTH, json={"raw_input": "job one", "max_iterations": 1})
        assert first.status_code == 202
        second = c.post("/audit", headers=AUTH, json={"raw_input": "job two", "max_iterations": 1})
        assert second.status_code == 202
        third = c.post("/audit", headers=AUTH, json={"raw_input": "job three", "max_iterations": 1})
        assert third.status_code == 429


def test_audit_429_when_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sliding-window POST rate limit (B5), distinct from queue-full 429."""
    monkeypatch.setenv("RESEARCH_AUDITOR_AUDIT_SECRET", SECRET)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    monkeypatch.setenv("RESEARCH_AUDITOR_AUDIT_RATE_LIMIT_PER_MIN", "1")
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


def test_job_timed_out(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESEARCH_AUDITOR_AUDIT_TIMEOUT_SEC", "0.05")
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
