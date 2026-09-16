"""Shared HTTP helpers for US1 grant-generate contract tests.

These helpers call the public contract only. They do not stub the LangGraph
or Tavily. Until T028 exists, POST .../messages should fail (red).
"""

from __future__ import annotations

import time
from typing import Any

from fastapi.testclient import TestClient

SECRET = "test-preview-secret"
AUTH = {"X-Audit-Secret": SECRET}

# Free-form prompt that fills Who / Whom / Ask / Why-funder / Evidence so these
# tests are not the P5 clarify fixture (T039).
GRANT_PROMPT = (
    "Literacy Partners (our org) is asking the Ford Foundation for $50,000 for "
    "adult literacy in NYC. Ford's education strategy names adult literacy as a "
    "priority. Our 2024 program report shows 400 adults gained at least one "
    "grade level."
)

GRANT_MATERIALS = [
    {"uri": "https://example.org/ford-education-criteria", "label": "Ford education criteria"},
]


def create_conversation(client: TestClient) -> str:
    """POST /v1/conversations and return conversation_id."""
    response = client.post("/v1/conversations", headers=AUTH)
    assert response.status_code == 200, response.text
    conversation_id = response.json()["conversation_id"]
    assert isinstance(conversation_id, str) and conversation_id
    return conversation_id


def post_grant_turn(client: TestClient, conversation_id: str) -> Any:
    """POST a filled grant turn (client_intent=auto)."""
    return client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers=AUTH,
        json={
            "text": GRANT_PROMPT,
            "client_intent": "auto",
            "citation_mode": None,
            "materials": GRANT_MATERIALS,
        },
    )


def wait_job_success(client: TestClient, job_id: str, timeout_sec: float = 8.0) -> dict[str, Any]:
    """Poll GET /v1/jobs/{job_id} until succeeded or timeout."""
    deadline = time.monotonic() + timeout_sec
    last_text = ""
    while time.monotonic() < deadline:
        response = client.get(f"/v1/jobs/{job_id}", headers=AUTH)
        last_text = response.text
        if response.status_code == 200:
            body = response.json()
            status = body.get("status")
            if status == "succeeded":
                return body
            if status in {"failed", "timed_out"}:
                raise AssertionError(f"job ended {status}: {body}")
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} did not succeed in time: {last_text}")


def submit_grant_and_wait(client: TestClient) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Create conversation, enqueue generate, wait for success snapshot."""
    conversation_id = create_conversation(client)
    accepted = post_grant_turn(client, conversation_id)
    assert accepted.status_code in {200, 202}, accepted.text
    payload = accepted.json()
    assert payload.get("type") == "job_accepted"
    job_id = payload["job_id"]
    job = wait_job_success(client, job_id)
    return conversation_id, payload, job
