"""Optional Tavily search. No key → empty list (plan P2)."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import get_tavily_api_key


async def tavily_search(query: str, *, max_results: int = 5) -> list[dict[str, Any]]:
    """POST Tavily search. Empty query or missing key → []."""
    key = get_tavily_api_key()
    q = query.strip()
    if not key or not q:
        return []
    payload = {
        "api_key": key,
        "query": q,
        "max_results": max(1, min(max_results, 10)),
        "include_answer": False,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post("https://api.tavily.com/search", json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError:
        return []
    results = data.get("results") or []
    if not isinstance(results, list):
        return []
    return [item for item in results if isinstance(item, dict)]
