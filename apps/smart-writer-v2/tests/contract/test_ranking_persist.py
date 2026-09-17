"""T25: persist ranking on InternalRunState; omit from GET conversation (T2)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.store import STORE
from tests.contract.grant_flow import (
    AUTH,
    GRANT_MATERIALS,
    RANKING_CLOSED_PROMPT,
    create_conversation,
    wait_job_success,
)


def test_http_stores_ranking_and_snapshot_omits_it(client: TestClient) -> None:
    conversation_id = create_conversation(client)
    response = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers=AUTH,
        json={
            "text": RANKING_CLOSED_PROMPT,
            "client_intent": "auto",
            "citation_mode": None,
            "materials": GRANT_MATERIALS,
        },
    )
    assert response.status_code in {200, 202}, response.text
    accepted = response.json()
    assert accepted.get("type") == "job_accepted"
    wait_job_success(client, accepted["job_id"])
    state = STORE.get_run_state(conversation_id)
    assert state is not None
    assert {"warm", "persuasive", "urgent"} <= set(state.property_ranking)
    snapshot = client.get(
        f"/v1/conversations/{conversation_id}",
        headers=AUTH,
    )
    assert snapshot.status_code == 200, snapshot.text
    body = snapshot.json()
    assert "property_ranking" not in body
    assert "run_state" not in body
