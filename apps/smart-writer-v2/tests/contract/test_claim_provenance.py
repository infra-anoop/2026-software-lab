"""Grant artifact claim provenance shape (hook 4; catalog claim.provenance structural)."""

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


def test_grant_claims_are_grounded_or_uncertain(client: TestClient) -> None:
    """Each org/funder claim is grounded+source_id or uncertain with null source_id."""
    _conversation_id, _accepted, job = submit_grant_and_wait(client)
    claims = job["artifact"]["claims"]
    assert isinstance(claims, list)
    assert len(claims) >= 1, "grant fixture asserts org/funder facts; claims[] must not be empty"
    for claim in claims:
        status = claim["status"]
        source_id = claim.get("source_id")
        assert status in {"grounded", "uncertain"}, claim
        if status == "grounded":
            assert isinstance(source_id, str) and source_id.strip() != "", claim
        else:
            assert source_id is None, claim
        assert isinstance(claim.get("excerpt"), str) and claim["excerpt"].strip() != ""
