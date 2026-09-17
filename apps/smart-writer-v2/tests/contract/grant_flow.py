"""Shared HTTP helpers for grant contract tests.

These helpers call the public contract only. They do not stub the LangGraph
or Tavily. Until POST .../messages exists (T043 clarify / T028 enqueue),
turns should fail (red).
"""

from __future__ import annotations

import re
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

# US4 / T046: closed ids plus invented labels that must not leak (R8).
RANKING_CLOSED_PROMPT = (
    GRANT_PROMPT
    + " Keep it warm, persuasive, and urgent. Also make it emotional and visionary."
)

# US4 / T024+T047: factual present and not first; retrieval must stay on.
FACTUAL_LOW_PROMPT = (
    GRANT_PROMPT
    + " Prefer a warm, persuasive tone rather than dry and factual. Rank factual last."
)

# Who + some evidence; Whom (funder) and Ask (amount/request) absent — P5 / hook 6.
EMPTY_WHOM_ASK_PROMPT = (
    "We're Literacy Partners, a NYC adult literacy nonprofit. "
    "Please help us with a draft. Our 2024 program report shows 400 adults "
    "gained at least one grade level."
)

# Who + Whom + Ask filled; Why-funder and Evidence absent (T11 — not a funder+$amount-only gate).
WHOM_ASK_FILLED_WHY_EMPTY_PROMPT = (
    "Literacy Partners (our org) is asking the Ford Foundation for $50,000 "
    "for adult literacy in NYC."
)

# US6 / T058: non-grant short-form — must not require Axis A grant slots (SC-005 smoke).
NONGRANT_PROMPT = (
    "Write a two-page explainer on backyard composting for apartment dwellers. "
    "This is a blog post, not a grant or donation ask."
)

# FR-021 / T9: structured labels only. English "ask" / "whom" in questions is allowed.
_STRUCTURED_LABEL_RE = re.compile(
    r"(?i)(\baxis\b|\baxis_[ab]\b|\bintent_slots\b|\bwhy_funder\b|"
    r"\bmissing_hints\b|\bwhom:)"
)


def create_conversation(client: TestClient) -> str:
    """POST /v1/conversations and return conversation_id."""
    response = client.post("/v1/conversations", headers=AUTH)
    assert response.status_code == 200, response.text
    conversation_id = response.json()["conversation_id"]
    assert isinstance(conversation_id, str) and conversation_id
    return conversation_id


def _post_turn(client: TestClient, conversation_id: str, text: str) -> Any:
    """POST /messages with client_intent=auto and no citation override."""
    return client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers=AUTH,
        json={
            "text": text,
            "client_intent": "auto",
            "citation_mode": None,
            "materials": [],
        },
    )


def post_empty_whom_ask_turn(client: TestClient, conversation_id: str) -> Any:
    """POST a grant-ish turn with Whom and Ask empty (P5 must-clarify fixture)."""
    return _post_turn(client, conversation_id, EMPTY_WHOM_ASK_PROMPT)


def post_whom_ask_filled_why_empty_turn(client: TestClient, conversation_id: str) -> Any:
    """POST Who+Whom+Ask filled, Why/Evidence empty (T11)."""
    return _post_turn(client, conversation_id, WHOM_ASK_FILLED_WHY_EMPTY_PROMPT)


def assert_clarify_no_artifact(
    client: TestClient,
    conversation_id: str,
    response: Any,
) -> dict[str, Any]:
    """Clarify payload + GET snapshot has no ArtifactVersion (T9/T10/T15)."""
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get("type") == "clarify"
    assert payload.get("job_id") is None
    assistant = payload["assistant_message"]
    assert "message_id" in assistant
    text = assistant["text"]
    assert isinstance(text, str) and text.strip() != ""
    assert _STRUCTURED_LABEL_RE.search(text) is None, text
    snapshot_response = client.get(
        f"/v1/conversations/{conversation_id}",
        headers=AUTH,
    )
    assert snapshot_response.status_code == 200, snapshot_response.text
    snapshot = snapshot_response.json()
    assert "last_artifact_id" in snapshot
    assert snapshot["last_artifact_id"] is None
    for key in ("artifact", "latest_artifact"):
        value = snapshot.get(key)
        assert value in (None, {}), snapshot
    return payload


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


def post_followup_turn(
    client: TestClient,
    conversation_id: str,
    text: str,
    *,
    client_intent: str = "auto",
    extra: dict[str, Any] | None = None,
) -> Any:
    """POST a later turn (feedback / regenerate / extra contract fields)."""
    payload: dict[str, Any] = {
        "text": text,
        "client_intent": client_intent,
        "citation_mode": None,
        "materials": [],
    }
    if extra:
        payload.update(extra)
    return client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers=AUTH,
        json=payload,
    )


def wait_job_success(client: TestClient, job_id: str, timeout_sec: float = 8.0) -> dict[str, Any]:
    """Poll GET /v1/jobs/{job_id} until succeeded or timeout.

    8s is enough while the route 404s (scaffold-red). After T028, raise this or
    inject a deterministic executor — do not stub the graph to the assertion JSON.
    """
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
