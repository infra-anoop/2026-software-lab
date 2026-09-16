"""Protected POST /v1/conversations rejects missing/wrong X-Audit-Secret (hook 3)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.entrypoints.http import app

SECRET = "test-preview-secret"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SMART_WRITER_V2_AUDIT_SECRET", SECRET)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


def test_create_conversation_401_without_secret(client: TestClient) -> None:
    response = client.post("/v1/conversations")
    assert response.status_code == 401


def test_create_conversation_401_wrong_secret(client: TestClient) -> None:
    response = client.post(
        "/v1/conversations",
        headers={"X-Audit-Secret": "nope"},
    )
    assert response.status_code == 401
