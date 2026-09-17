"""Non-grant short-form smoke (catalog engine.nongrant_smoke / SC-005 structural).

Must enqueue and complete on the same engine without grant intent slots.
Do not treat this as the v2.0 success bar (F2). T35–T37 locked.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.contract.grant_flow import (
    AUTH,
    create_conversation,
    post_nongrant_turn,
    wait_job_success,
)

_WEB_SIGNALS = frozenset({"used", "none_declared", "disabled"})


def test_nongrant_prompt_completes_without_grant_slots(client: TestClient) -> None:
    """Explainer prompt → job_accepted + succeeded generate; not P5 clarify."""
    conversation_id = create_conversation(client)
    accepted = post_nongrant_turn(client, conversation_id)
    assert accepted.status_code in {200, 202}, accepted.text
    payload = accepted.json()
    assert payload.get("type") == "job_accepted", payload
    assert "job_id" in payload
    assert payload["job_id"]
    assert payload.get("mode") == "generate"
    assert "parent_artifact_id" in payload
    assert payload["parent_artifact_id"] is None
    job = wait_job_success(client, payload["job_id"])
    assert job["status"] == "succeeded"
    artifact = job["artifact"]
    assert "parent_artifact_id" in artifact
    assert artifact["parent_artifact_id"] is None
    assert artifact["producing_mode"] == "generate"
    body = artifact["body"]
    assert isinstance(body, str) and body.strip() != ""
    signal = artifact["web_signal"]
    assert signal in _WEB_SIGNALS
    assert signal == "none_declared"
    snapshot = client.get(f"/v1/conversations/{conversation_id}", headers=AUTH)
    body_snap = snapshot.json()
    assert "grant_beachhead" not in body_snap
    assert "run_state" not in body_snap
