"""Successful revise job (http-api.md hook 1; T18 chain-head fields)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.contract.grant_flow import (
    AUTH,
    post_followup_turn,
    submit_grant_and_wait,
    wait_job_success,
)


def test_feedback_after_generate_is_revise_with_parent(client: TestClient) -> None:
    """Prior artifact + feedback → revise, new id, last_artifact_id moves."""
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
    assert artifact["artifact_id"] != parent_id
    body = artifact["body"]
    assert isinstance(body, str) and body.strip() != ""
    snapshot = client.get(f"/v1/conversations/{conversation_id}", headers=AUTH)
    assert snapshot.status_code == 200, snapshot.text
    snap = snapshot.json()
    assert "last_artifact_id" in snap
    assert snap["last_artifact_id"] == artifact["artifact_id"]
