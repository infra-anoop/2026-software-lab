"""Web enabled + empty Tavily/noop → web_signal=none_declared (hook 5)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.contract.grant_flow import submit_grant_and_wait

_WEB_SIGNALS = frozenset({"used", "none_declared", "disabled"})


def test_web_enabled_empty_search_declares_none(client: TestClient) -> None:
    """TAVILY unset (noop) with default web_research_enabled → none_declared, not disabled."""
    _conversation_id, _accepted, job = submit_grant_and_wait(client)
    signal = job["artifact"]["web_signal"]
    assert signal in _WEB_SIGNALS
    assert signal == "none_declared"
    assert signal != "disabled"
