"""Successful revise job (http-api.md hook 1; catalog revise.continuity_default)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.contract.grant_flow import (
    post_followup_turn,
    submit_grant_and_wait,
    wait_job_success,
)


def test_feedback_after_generate_is_revise_with_parent(client: TestClient) -> None:
    """Prior artifact + feedback → mode=revise and parent_artifact_id set."""
    conversation_id, _accepted, first = submit_grant_and_wait(client)
    parent_id = first["artifact"]["artifact_id"]
    response = post_followup_turn(
        client,
        conversation_id,
        "Make the ask more specific to adult literacy outcomes.",
        client_intent="auto",
    )
    assert response.status_code in {200, 202}, response.text
    accepted = response.json()
    assert accepted.get("type") == "job_accepted"
    assert accepted["mode"] == "revise"
    assert "parent_artifact_id" in accepted
    assert accepted["parent_artifact_id"] == parent_id
    job = wait_job_success(client, accepted["job_id"])
    assert job["mode"] == "revise"
    artifact = job["artifact"]
    assert artifact["producing_mode"] == "revise"
    assert artifact["parent_artifact_id"] == parent_id
