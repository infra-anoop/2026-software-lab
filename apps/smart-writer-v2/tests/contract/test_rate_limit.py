"""B5-class spend caps: sliding-window 429 vs queue-full 503 (http-api.md).

T062 — rate limiter + Settings. Queue-full path raises QueueFullError → 503.
Limiter is messages-scoped (create/GET exempt); all POST .../messages share the window.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.entrypoints import http as http_mod
from app.entrypoints.http import app
from tests.contract.grant_flow import (
    AUTH,
    EMPTY_WHOM_ASK_PROMPT,
    GRANT_PROMPT,
    SECRET,
    create_conversation,
)


def test_post_message_429_when_rate_limited_clarify(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All POST .../messages share the limiter — including clarify (T41)."""
    monkeypatch.setenv("SMART_WRITER_V2_AUDIT_SECRET", SECRET)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    monkeypatch.setenv("SMART_WRITER_V2_AUDIT_RATE_LIMIT_PER_MIN", "1")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    get_settings.cache_clear()

    with TestClient(app) as client:
        conversation_id = create_conversation(client)
        body = {"text": EMPTY_WHOM_ASK_PROMPT, "client_intent": "auto"}
        first = client.post(
            f"/v1/conversations/{conversation_id}/messages",
            headers=AUTH,
            json=body,
        )
        assert first.status_code == 200, first.text
        assert first.json().get("type") == "clarify"
        second = client.post(
            f"/v1/conversations/{conversation_id}/messages",
            headers=AUTH,
            json=body,
        )
        assert second.status_code == 429, second.text
    get_settings.cache_clear()


def test_post_message_429_when_rate_limited_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enqueue/spend path must share the same messages bucket (T41 twin)."""
    monkeypatch.setenv("SMART_WRITER_V2_AUDIT_SECRET", SECRET)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    monkeypatch.setenv("SMART_WRITER_V2_AUDIT_RATE_LIMIT_PER_MIN", "1")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    get_settings.cache_clear()

    async def noop(_payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "humor_enabled": False,
            "artifact": {
                "artifact_id": "art-test",
                "parent_artifact_id": None,
                "producing_mode": "generate",
                "body": "stub",
                "citation_mode": "panel",
                "sources": [],
                "claims": [],
                "materials_bundle_ids": [],
                "web_bundle_ids": [],
                "web_signal": "none_declared",
            },
        }

    with (
        patch.object(http_mod, "_execute_job", side_effect=noop),
        TestClient(app) as client,
    ):
        conversation_id = create_conversation(client)
        body = {"text": GRANT_PROMPT, "client_intent": "auto"}
        first = client.post(
            f"/v1/conversations/{conversation_id}/messages",
            headers=AUTH,
            json=body,
        )
        assert first.status_code in {200, 202}, first.text
        assert first.json().get("type") == "job_accepted"
        second = client.post(
            f"/v1/conversations/{conversation_id}/messages",
            headers=AUTH,
            json={
                "text": "Tighten the ask to adult literacy outcomes.",
                "client_intent": "auto",
            },
        )
        assert second.status_code == 429, second.text
    get_settings.cache_clear()


def test_post_message_503_when_queue_full(monkeypatch: pytest.MonkeyPatch) -> None:
    """QueueFullError → 503 (contract); must not be remapped to rate-limit 429 (T44)."""
    monkeypatch.setenv("SMART_WRITER_V2_AUDIT_SECRET", SECRET)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setattr(http_mod, "DEFAULT_JOB_QUEUE_MAX", 1)
    get_settings.cache_clear()

    async def slow(_payload: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(30)
        return {}

    with (
        patch.object(http_mod, "_execute_job", side_effect=slow),
        TestClient(app) as client,
    ):
        conversation_id = create_conversation(client)
        first = client.post(
            f"/v1/conversations/{conversation_id}/messages",
            headers=AUTH,
            json={"text": GRANT_PROMPT, "client_intent": "auto"},
        )
        assert first.status_code in {200, 202}, first.text
        assert first.json().get("type") == "job_accepted"
        second = client.post(
            f"/v1/conversations/{conversation_id}/messages",
            headers=AUTH,
            json={
                "text": "Tighten the ask to adult literacy outcomes.",
                "client_intent": "auto",
            },
        )
        assert second.status_code in {200, 202}, second.text
        assert second.json().get("type") == "job_accepted"
        third = client.post(
            f"/v1/conversations/{conversation_id}/messages",
            headers=AUTH,
            json={
                "text": "One more revise while the queue is full.",
                "client_intent": "auto",
            },
        )
        # Anti-V1/RA: queue overloaded is 503 here, not 429.
        assert third.status_code == 503, third.text
    get_settings.cache_clear()
