"""Non-grant short-form smoke (catalog engine.nongrant_smoke / SC-005 structural).

Must enqueue and complete on the same engine without grant intent slots.
Do not treat this as the v2.0 success bar (F2).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.contract.grant_flow import (
    NONGRANT_PROMPT,
    create_conversation,
    post_followup_turn,
    wait_job_success,
)


def test_nongrant_prompt_completes_without_grant_slots(client: TestClient) -> None:
    """Blog/explainer prompt → job_accepted + succeeded generate; not P5 clarify."""
    conversation_id = create_conversation(client)
    accepted = post_followup_turn(client, conversation_id, NONGRANT_PROMPT)
    assert accepted.status_code in {200, 202}, accepted.text
    payload = accepted.json()
    assert payload.get("type") == "job_accepted", payload
    assert payload.get("job_id")
    assert payload.get("mode") == "generate"
    job = wait_job_success(client, payload["job_id"])
    assert job["status"] == "succeeded"
    artifact = job["artifact"]
    assert artifact["producing_mode"] == "generate"
    body = artifact["body"]
    assert isinstance(body, str) and body.strip() != ""
