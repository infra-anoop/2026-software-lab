"""SC-004: web_research_enabled false → web_signal=disabled (T054)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.contract.grant_flow import (
    AUTH,
    GRANT_MATERIALS,
    GRANT_PROMPT,
    create_conversation,
    wait_job_success,
)

_DISABLE_WEB_PROMPT = GRANT_PROMPT + " Do not use web research."


def test_web_research_disabled_declares_disabled(client: TestClient) -> None:
    """User disables web → web_signal is disabled, not none_declared."""
    conversation_id = create_conversation(client)
    response = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers=AUTH,
        json={
            "text": _DISABLE_WEB_PROMPT,
            "client_intent": "auto",
            "citation_mode": None,
            "materials": GRANT_MATERIALS,
        },
    )
    assert response.status_code in {200, 202}, response.text
    accepted = response.json()
    assert accepted.get("type") == "job_accepted"
    job = wait_job_success(client, accepted["job_id"])
    signal = job["artifact"]["web_signal"]
    assert signal == "disabled"
    sources = job["artifact"]["sources"]
    assert all(row.get("bundle") != "web" for row in sources)
