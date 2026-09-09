"""Tests for scripts/railway_graphql.py (mocked HTTP; no live Railway)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
import pytest

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import railway_graphql as rgql  # noqa: E402


def test_select_token_prefers_workspace() -> None:
    assert (
        rgql.select_railway_token(
            {"RAILWAY_WORKSPACE_TOKEN": "ws", "RAILWAY_TOKEN": "other"}
        )
        == "ws"
    )


def test_select_token_falls_back() -> None:
    assert rgql.select_railway_token({"RAILWAY_TOKEN": "t"}) == "t"


def test_select_token_missing() -> None:
    assert rgql.select_railway_token({}) is None


def test_client_rejects_empty_token() -> None:
    with pytest.raises(ValueError, match="empty"):
        rgql.RailwayGraphqlClient("  ")


def test_execute_returns_body_and_execute_data() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer tok"
        payload = json.loads(request.content.decode())
        assert payload["query"] == "{ ping }"
        return httpx.Response(200, json={"data": {"ping": True}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    gql = rgql.RailwayGraphqlClient("tok", client=client)
    body = gql.execute("{ ping }")
    assert body == {"data": {"ping": True}}
    assert gql.execute_data("{ ping }") == {"ping": True}
    client.close()


def test_execute_raises_on_graphql_errors_without_dumping_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"errors": [{"message": "nope", "extensions": {"secret": "leak"}}]},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    gql = rgql.RailwayGraphqlClient("tok", client=client)
    with pytest.raises(rgql.RailwayGraphqlError, match="nope") as ei:
        gql.execute("{ x }")
    assert "leak" not in str(ei.value)
    client.close()


def test_execute_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="bad gateway")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    gql = rgql.RailwayGraphqlClient("tok", client=client)
    with pytest.raises(rgql.RailwayGraphqlError, match="502"):
        gql.execute("{ x }")
    client.close()
