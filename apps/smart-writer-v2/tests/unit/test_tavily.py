"""Tavily noop when key unset."""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.retrieval.tavily import tavily_search


@pytest.mark.asyncio
async def test_tavily_empty_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    get_settings.cache_clear()
    hits = await tavily_search("Ford Foundation literacy")
    assert hits == []
    get_settings.cache_clear()
