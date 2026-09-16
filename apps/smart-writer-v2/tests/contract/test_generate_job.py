"""Generate job success shape (http-api.md hook 2)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.entrypoints.http import app
from tests.contract.grant_flow import SECRET, submit_grant_and_wait


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SMART_WRITER_V2_AUDIT_SECRET", SECRET)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


def test_generate_job_mode_and_complete_body(client: TestClient) -> None:
    """Fresh generate: mode=generate, parent_artifact_id null, nonempty body."""
    _conversation_id, accepted, job = submit_grant_and_wait(client)
    assert accepted["mode"] == "generate"
    assert accepted.get("parent_artifact_id") is None
    assert job["status"] == "succeeded"
    assert job["mode"] == "generate"
    artifact = job["artifact"]
    assert artifact["parent_artifact_id"] is None
    assert artifact["producing_mode"] == "generate"
    body = artifact["body"]
    assert isinstance(body, str) and body.strip() != ""
