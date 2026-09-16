"""Protected POST /v1/conversations rejects missing/wrong X-Audit-Secret (hook 3)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.entrypoints.http import app


def test_create_conversation_401_without_secret(client: TestClient) -> None:
    response = client.post("/v1/conversations")
    assert response.status_code == 401


def test_create_conversation_401_wrong_secret(client: TestClient) -> None:
    response = client.post(
        "/v1/conversations",
        headers={"X-Audit-Secret": "nope"},
    )
    assert response.status_code == 401


def test_create_conversation_503_when_secret_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SMART_WRITER_V2_AUDIT_SECRET", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        response = test_client.post("/v1/conversations")
    get_settings.cache_clear()
    assert response.status_code == 503
