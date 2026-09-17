"""F3 / FR-006a: factual ranked low does not disable materials or web."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.contract.grant_flow import (
    AUTH,
    FACTUAL_LOW_PROMPT,
    GRANT_MATERIALS,
    create_conversation,
    wait_job_success,
)

_WEB_SIGNALS = frozenset({"used", "none_declared", "disabled"})

# T24 lock: T049 landmine (like T032). After ranking exists this file MUST fail
# if web_signal == "disabled". Do not pytest tone. F3 lock is != disabled (T27).


def test_factual_low_still_runs_materials_and_web(client: TestClient) -> None:
    """Generate with factual last still collects materials and does not disable web."""
    conversation_id = create_conversation(client)
    response = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers=AUTH,
        json={
            "text": FACTUAL_LOW_PROMPT,
            "client_intent": "auto",
            "citation_mode": None,
            "materials": GRANT_MATERIALS,
        },
    )
    assert response.status_code in {200, 202}, response.text
    accepted = response.json()
    assert accepted.get("type") == "job_accepted"
    job = wait_job_success(client, accepted["job_id"])
    artifact = job["artifact"]
    signal = artifact["web_signal"]
    assert signal in _WEB_SIGNALS
    assert signal != "disabled"
    claims = artifact["claims"]
    assert isinstance(claims, list)
    assert len(claims) >= 1, "materials path must still attach provenance when factual is low"
    sources = artifact["sources"]
    assert isinstance(sources, list)
    assert any(row.get("bundle") == "materials" for row in sources), sources
