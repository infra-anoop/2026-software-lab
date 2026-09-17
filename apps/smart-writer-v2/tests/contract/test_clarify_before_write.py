"""Grant turn with empty Whom/Ask → clarify, no job (http-api.md hook 6; P5)."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from tests.contract.grant_flow import create_conversation, post_empty_whom_ask_turn

# Internal slot/axis labels (FR-021). Word tokens as named in T039.
_SLOT_LABEL_RE = re.compile(r"(?i)\b(whom|ask|axis)\b")


def test_empty_whom_ask_is_clarify_without_job(client: TestClient) -> None:
    """Missing Whom/Ask → type=clarify, no job_id, NL text without slot labels."""
    conversation_id = create_conversation(client)
    response = post_empty_whom_ask_turn(client, conversation_id)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get("type") == "clarify"
    assert "job_id" not in payload
    assistant = payload["assistant_message"]
    text = assistant["text"]
    assert isinstance(text, str) and text.strip() != ""
    assert _SLOT_LABEL_RE.search(text) is None, text
