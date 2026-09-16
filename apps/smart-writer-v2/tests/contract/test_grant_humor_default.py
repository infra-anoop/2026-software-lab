"""Grant default humor_enabled is false (catalog grant.default_humor_low structural)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.entrypoints.http import app
from tests.contract.grant_flow import AUTH, SECRET, submit_grant_and_wait


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SMART_WRITER_V2_AUDIT_SECRET", SECRET)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


def _humor_enabled(snapshot: dict) -> bool | None:
    """Read humor flag from conversation snapshot (top-level or run_state)."""
    if "humor_enabled" in snapshot:
        value = snapshot["humor_enabled"]
        return value if isinstance(value, bool) else None
    run_state = snapshot.get("run_state")
    if isinstance(run_state, dict) and "humor_enabled" in run_state:
        value = run_state["humor_enabled"]
        return value if isinstance(value, bool) else None
    return None


def test_grant_default_humor_off_after_generate(client: TestClient) -> None:
    """Grant generate without user enabling humor → humor_enabled is false."""
    conversation_id, _accepted, job = submit_grant_and_wait(client)
    assert job["status"] == "succeeded"
    snapshot = client.get(f"/v1/conversations/{conversation_id}", headers=AUTH)
    assert snapshot.status_code == 200, snapshot.text
    assert _humor_enabled(snapshot.json()) is False
