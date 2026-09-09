"""Shared Railway GraphQL HTTP client (A21 / A26 / A24).

One place for backboard URL, bearer auth, and error redaction.
Domain logic (ensure vs upsert vs verify) stays in callers.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

RAILWAY_API_URL = "https://backboard.railway.com/graphql/v2"


class RailwayGraphqlError(RuntimeError):
    """Transport or GraphQL failure; message must never include tokens or secret values."""


def select_railway_token(environ: Mapping[str, str]) -> str | None:
    """Prefer RAILWAY_WORKSPACE_TOKEN, else RAILWAY_TOKEN (deploy/provision/sync)."""
    for key in ("RAILWAY_WORKSPACE_TOKEN", "RAILWAY_TOKEN"):
        raw = environ.get(key, "")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return None


class RailwayGraphqlClient:
    """POST GraphQL to Railway backboard; never logs the token."""

    def __init__(
        self,
        token: str,
        *,
        api_url: str = RAILWAY_API_URL,
        client: httpx.Client | None = None,
        timeout: float = 60.0,
    ) -> None:
        if not token.strip():
            raise ValueError("Railway token is empty")
        self._token = token.strip()
        self._api_url = api_url
        self._client = client
        self._timeout = timeout

    def execute(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return the full GraphQL JSON object ``{data, errors?}``.

        Raises ``RailwayGraphqlError`` on HTTP/GraphQL failures (messages only).
        """
        payload: dict[str, Any] = {"query": query}
        if variables is not None:
            payload["variables"] = variables

        own = self._client is None
        client = self._client or httpx.Client(timeout=self._timeout)
        try:
            try:
                resp = client.post(
                    self._api_url,
                    headers={
                        "Authorization": f"Bearer {self._token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            except httpx.HTTPError as e:
                raise RailwayGraphqlError(f"Railway HTTP error: {e}") from e

            if resp.status_code >= 400:
                raise RailwayGraphqlError(f"Railway HTTP {resp.status_code}")

            try:
                body = resp.json()
            except ValueError as e:
                raise RailwayGraphqlError("Railway response was not JSON") from e
            if not isinstance(body, dict):
                raise RailwayGraphqlError("Railway response JSON must be an object")

            errors = body.get("errors")
            if errors:
                msgs: list[str] = []
                if isinstance(errors, list):
                    for err in errors:
                        if isinstance(err, dict) and isinstance(err.get("message"), str):
                            msgs.append(err["message"])
                raise RailwayGraphqlError(
                    "Railway GraphQL errors: "
                    + ("; ".join(msgs) if msgs else str(errors))
                )
            return body
        finally:
            if own:
                client.close()

    def execute_data(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> Any:
        """Return the ``data`` field from a successful GraphQL response."""
        body = self.execute(query, variables)
        return body.get("data")
