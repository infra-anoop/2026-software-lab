"""D2 outer spend caps: write jobs + clarify turns per conversation → 429.

T063 — fail closed when conversation hits max write jobs (default 3) or max
clarify turns (default 10). Status aligns with http-api.md ``429 | Rate limit``
(spend / rate family); distinct detail from sliding-window B5 limiter.

Inner max 8 (``get_max_inner_assessor_turns``) is Settings-only until the D8
scored loop (T078+) enforces it in the generate/revise graph — see unit test
``test_max_inner_assessor_turns_default``.
"""

from __future__ import annotations

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

_NOOP_ARTIFACT = {
    "artifact_id": "art-cap",
    "parent_artifact_id": None,
    "producing_mode": "generate",
    "body": "stub",
    "citation_mode": "panel",
    "sources": [],
    "claims": [],
    "materials_bundle_ids": [],
    "web_bundle_ids": [],
    "web_signal": "none_declared",
}


async def _noop_execute(_payload: dict[str, Any]) -> dict[str, Any]:
    return {"humor_enabled": False, "artifact": _NOOP_ARTIFACT}


def _cap_env(monkeypatch: pytest.MonkeyPatch, **overrides: str) -> None:
    monkeypatch.setenv("SMART_WRITER_V2_AUDIT_SECRET", SECRET)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    # Avoid B5 sliding-window 429 colliding with conversation caps.
    monkeypatch.setenv("SMART_WRITER_V2_AUDIT_RATE_LIMIT_PER_MIN", "1000")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    for key, value in overrides.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()


def test_post_message_429_when_write_job_cap_hit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fourth write job on one conversation fails closed with 429 (D2 default 3)."""
    _cap_env(monkeypatch)

    with (
        patch.object(http_mod, "_execute_job", side_effect=_noop_execute),
        TestClient(app) as client,
    ):
        conversation_id = create_conversation(client)
        for i in range(3):
            response = client.post(
                f"/v1/conversations/{conversation_id}/messages",
                headers=AUTH,
                json={
                    "text": GRANT_PROMPT if i == 0 else f"Revise pass {i}: tighten ask.",
                    "client_intent": "auto",
                },
            )
            assert response.status_code in {200, 202}, response.text
            assert response.json().get("type") == "job_accepted"
        blocked = client.post(
            f"/v1/conversations/{conversation_id}/messages",
            headers=AUTH,
            json={
                "text": "One more revise after the write-job cap.",
                "client_intent": "auto",
            },
        )
        assert blocked.status_code == 429, blocked.text
        assert "write job" in blocked.json().get("detail", "").lower()
    get_settings.cache_clear()


def test_post_message_429_when_clarify_turn_cap_hit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Clarify turns beyond max fail closed with 429 (env override 2 for speed)."""
    _cap_env(
        monkeypatch,
        SMART_WRITER_V2_MAX_CLARIFY_TURNS_PER_CONVERSATION="2",
    )

    with TestClient(app) as client:
        conversation_id = create_conversation(client)
        body = {"text": EMPTY_WHOM_ASK_PROMPT, "client_intent": "auto"}
        for _ in range(2):
            response = client.post(
                f"/v1/conversations/{conversation_id}/messages",
                headers=AUTH,
                json=body,
            )
            assert response.status_code == 200, response.text
            assert response.json().get("type") == "clarify"
        blocked = client.post(
            f"/v1/conversations/{conversation_id}/messages",
            headers=AUTH,
            json=body,
        )
        assert blocked.status_code == 429, blocked.text
        assert "clarify" in blocked.json().get("detail", "").lower()
    get_settings.cache_clear()
