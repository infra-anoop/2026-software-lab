"""GET /ready checks OPENAI_API_KEY without calling OpenAI."""

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.entrypoints.http import app


def test_ready_200_when_key_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    get_settings.cache_clear()
    with TestClient(app) as client:
        r = client.get("/ready")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "openai_api_key": "set"}
    assert "sk-test-fake" not in r.text


def test_ready_503_when_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()
    with TestClient(app) as client:
        r = client.get("/ready")
    assert r.status_code == 503
    assert r.json() == {"ok": False, "openai_api_key": "missing"}


def test_health_200_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_audit_503_when_openai_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESEARCH_AUDITOR_AUDIT_SECRET", "test-secret")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()
    with TestClient(app) as client:
        r = client.post(
            "/audit",
            headers={"X-Audit-Secret": "test-secret"},
            json={"raw_input": "hello world", "max_iterations": 1},
        )
    assert r.status_code == 503
    assert "OPENAI_API_KEY" in r.json()["detail"]
