"""Grant turn with empty slots → clarify, no job, no artifact (http-api.md hook 6; P5)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.contract.grant_flow import (
    assert_clarify_no_artifact,
    create_conversation,
    post_empty_whom_ask_turn,
    post_whom_ask_filled_why_empty_turn,
)


def test_empty_whom_ask_is_clarify_without_job(client: TestClient) -> None:
    """Missing Whom/Ask → type=clarify, no job, no ArtifactVersion (T9/T10)."""
    conversation_id = create_conversation(client)
    response = post_empty_whom_ask_turn(client, conversation_id)
    assert_clarify_no_artifact(client, conversation_id, response)


def test_whom_ask_filled_why_empty_is_clarify_without_job(client: TestClient) -> None:
    """Who+Whom+Ask filled but Why/Evidence empty still clarifies (T11)."""
    conversation_id = create_conversation(client)
    response = post_whom_ask_filled_why_empty_turn(client, conversation_id)
    assert_clarify_no_artifact(client, conversation_id, response)
