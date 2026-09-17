"""Revise without a parent artifact is 409 (http-api.md errors)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.contract.grant_flow import (
    GRANT_PROMPT,
    create_conversation,
    post_followup_turn,
)


def test_revise_without_parent_returns_409(client: TestClient) -> None:
    """Unknown/missing parent for a revise-shaped turn → 409, no job."""
    conversation_id = create_conversation(client)
    response = post_followup_turn(
        client,
        conversation_id,
        GRANT_PROMPT,
        client_intent="auto",
        extra={"parent_artifact_id": "does-not-exist"},
    )
    assert response.status_code == 409, response.text
    payload = response.json()
    assert payload.get("type") != "job_accepted"
    assert "job_id" not in payload or payload.get("job_id") is None
