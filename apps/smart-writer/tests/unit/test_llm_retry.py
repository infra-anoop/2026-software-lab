"""Tests for transient LLM retry helper (no network)."""

from unittest.mock import AsyncMock, patch

import pytest
from pydantic_ai.exceptions import ModelHTTPError

from app.llm.retry import (
    get_workflow_run_id,
    reset_workflow_run_id,
    set_workflow_run_id,
    with_transient_llm_retry,
)


@pytest.mark.asyncio
async def test_retry_succeeds_after_transient_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_LLM_RETRY_MAX_ATTEMPTS", "4")
    monkeypatch.setenv("SMART_WRITER_LLM_RETRY_BASE_SEC", "0.01")
    monkeypatch.setenv("SMART_WRITER_LLM_RETRY_MAX_SEC", "0.05")

    calls = 0

    async def factory() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ModelHTTPError(429, "openai:test")
        return "ok"

    with patch("app.llm.retry.asyncio.sleep", new_callable=AsyncMock):
        out = await with_transient_llm_retry(factory, phase="test_phase")

    assert out == "ok"
    assert calls == 3


@pytest.mark.asyncio
async def test_retry_stops_on_non_transient(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_LLM_RETRY_MAX_ATTEMPTS", "5")

    async def factory() -> str:
        raise ModelHTTPError(400, "openai:test")

    with patch("app.llm.retry.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(ModelHTTPError) as ei:
            await with_transient_llm_retry(factory, phase="test")
    assert ei.value.status_code == 400


def test_workflow_run_id_context() -> None:
    assert get_workflow_run_id() is None
    tok = set_workflow_run_id("run-abc")
    assert get_workflow_run_id() == "run-abc"
    reset_workflow_run_id(tok)
    assert get_workflow_run_id() is None
