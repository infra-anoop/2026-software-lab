"""Explicit regenerate is a fresh generate (http-api.md hook 2; T16 landmine)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.contract.grant_flow import (
    post_followup_turn,
    submit_grant_and_wait,
    wait_job_success,
)


def test_regenerate_is_generate_with_null_parent(client: TestClient) -> None:
    """client_intent=regenerate → mode=generate, new chain head, parent JSON null.

    Expected green until auto-follow-up is revise (T036). Then this must fail
    if regenerate is routed like auto.
    """
    conversation_id, _accepted, first = submit_grant_and_wait(client)
    first_id = first["artifact"]["artifact_id"]
    response = post_followup_turn(
        client,
        conversation_id,
        "Please write another complete draft.",
        client_intent="regenerate",
    )
    assert response.status_code in {200, 202}, response.text
    accepted = response.json()
    assert accepted.get("type") == "job_accepted"
    assert accepted["mode"] == "generate"
    assert "parent_artifact_id" in accepted
    assert accepted["parent_artifact_id"] is None
    job = wait_job_success(client, accepted["job_id"])
    assert job["mode"] == "generate"
    artifact = job["artifact"]
    assert artifact["producing_mode"] == "generate"
    assert "parent_artifact_id" in artifact
    assert artifact["parent_artifact_id"] is None
    assert artifact["artifact_id"] != first_id
