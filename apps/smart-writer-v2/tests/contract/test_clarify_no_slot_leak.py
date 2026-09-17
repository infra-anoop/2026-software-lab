"""Default clarify JSON omits missing_hints (FR-021)."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.contract.grant_flow import create_conversation, post_empty_whom_ask_turn


def _json_keys(value: Any) -> set[str]:
    """Collect object keys from a JSON-like value (nested)."""
    keys: set[str] = set()
    if isinstance(value, dict):
        keys.update(value.keys())
        for child in value.values():
            keys.update(_json_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_json_keys(child))
    return keys


def test_clarify_payload_omits_missing_hints(client: TestClient) -> None:
    """Clarify response must not include missing_hints anywhere in the JSON."""
    conversation_id = create_conversation(client)
    response = post_empty_whom_ask_turn(client, conversation_id)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get("type") == "clarify"
    assert "missing_hints" not in _json_keys(payload)
