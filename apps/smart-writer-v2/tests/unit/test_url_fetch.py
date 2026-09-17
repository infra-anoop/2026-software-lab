"""SSRF-oriented URL fetch rejects loopback."""

from __future__ import annotations

import pytest

from app.retrieval.url_fetch import (
    FetchBudget,
    fetch_url_text,
    resolved_hosts_are_public,
)


def test_loopback_host_not_public() -> None:
    assert resolved_hosts_are_public("127.0.0.1") is False
    assert resolved_hosts_are_public("localhost") is False


@pytest.mark.asyncio
async def test_fetch_localhost_returns_none() -> None:
    got = await fetch_url_text("http://127.0.0.1/", budget=FetchBudget(allow_http=True, timeout_sec=2.0))
    assert got is None
