"""Generate job success shape (http-api.md hook 2; F7 panel when sources exist)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.contract.grant_flow import submit_grant_and_wait


def test_generate_job_mode_and_complete_body(client: TestClient) -> None:
    """Fresh generate: mode=generate, parent_artifact_id null, nonempty body."""
    _conversation_id, accepted, job = submit_grant_and_wait(client)
    assert accepted["mode"] == "generate"
    assert "parent_artifact_id" in accepted
    assert accepted["parent_artifact_id"] is None
    assert job["status"] == "succeeded"
    assert job["mode"] == "generate"
    artifact = job["artifact"]
    assert "parent_artifact_id" in artifact
    assert artifact["parent_artifact_id"] is None
    assert artifact["producing_mode"] == "generate"
    body = artifact["body"]
    assert isinstance(body, str) and body.strip() != ""
    sources = artifact.get("sources") or []
    if sources:
        assert artifact["citation_mode"] == "panel"
