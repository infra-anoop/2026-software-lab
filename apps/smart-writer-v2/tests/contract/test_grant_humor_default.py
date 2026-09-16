"""Grant default humor_enabled is false (catalog grant.default_humor_low structural)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.contract.grant_flow import submit_grant_and_wait


def test_grant_default_humor_off_after_generate(client: TestClient) -> None:
    """Grant generate without user enabling humor → job snapshot humor_enabled is false."""
    _conversation_id, _accepted, job = submit_grant_and_wait(client)
    assert job["status"] == "succeeded"
    assert "humor_enabled" in job
    assert job["humor_enabled"] is False
