"""Web enabled + empty Tavily/noop → web_signal=none_declared (hook 5)."""

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


def test_web_enabled_empty_search_declares_none(client: TestClient) -> None:
    """TAVILY unset (noop) with default web_research_enabled → none_declared."""
    _conversation_id, _accepted, job = submit_grant_and_wait(client)
    assert job["artifact"]["web_signal"] == "none_declared"
