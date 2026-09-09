"""Vault backends: dict stub for tests + Infisical Cloud HTTP (A21)."""

from __future__ import annotations

from typing import Mapping

import httpx

from .protocols import VaultRef


class DictVaultBackend:
    """In-memory vault keyed by (project, env, path, key). For tests / dry fixtures."""

    def __init__(self, store: Mapping[tuple[str, str, str, str], str]) -> None:
        self._store = dict(store)

    def get_secrets(self, refs: list[VaultRef]) -> dict[str, str]:
        out: dict[str, str] = {}
        for ref in refs:
            tup = (ref["project"], ref["env"], ref["path"], ref["key"])
            if tup in self._store:
                out[ref["key"]] = self._store[tup]
        return out


class InfisicalCloudBackend:
    """Fetch secrets from Infisical Cloud REST API.

    Auth: ``INFISICAL_TOKEN`` bearer (machine identity / service token).
    Live OIDC wiring is A23; this backend is callable when a token is present.
    """

    def __init__(
        self,
        *,
        token: str,
        base_url: str = "https://app.infisical.com/api",
        client: httpx.Client | None = None,
    ) -> None:
        if not token.strip():
            raise ValueError("Infisical token is empty")
        self._token = token
        self._base = base_url.rstrip("/")
        self._client = client

    def get_secrets(self, refs: list[VaultRef]) -> dict[str, str]:
        # Group by project/env/path to minimize round-trips.
        groups: dict[tuple[str, str, str], list[VaultRef]] = {}
        for ref in refs:
            groups.setdefault((ref["project"], ref["env"], ref["path"]), []).append(ref)

        out: dict[str, str] = {}
        own_client = self._client is None
        client = self._client or httpx.Client(timeout=30.0)
        try:
            for (project, env, path), group in groups.items():
                payload = self._list_secrets(client, project=project, env=env, path=path)
                wanted = {r["key"] for r in group}
                for key, value in payload.items():
                    if key in wanted:
                        out[key] = value
        finally:
            if own_client:
                client.close()
        return out

    def _list_secrets(
        self,
        client: httpx.Client,
        *,
        project: str,
        env: str,
        path: str,
    ) -> dict[str, str]:
        # Infisical API v3 raw secrets list (projectSlug + environment).
        url = f"{self._base}/v3/secrets/raw"
        params = {
            "workspaceSlug": project,
            "environment": env,
            "secretPath": path,
            "include_imports": "false",
        }
        resp = client.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {self._token}"},
        )
        if resp.status_code >= 400:
            raise RuntimeError(
                f"Infisical list secrets failed HTTP {resp.status_code} "
                f"for project={project!r} env={env!r} (body redacted)"
            )
        data = resp.json()
        secrets = data.get("secrets")
        if not isinstance(secrets, list):
            # Some responses nest under data
            nested = data.get("data")
            if isinstance(nested, dict):
                secrets = nested.get("secrets")
        if not isinstance(secrets, list):
            return {}
        out: dict[str, str] = {}
        for item in secrets:
            if not isinstance(item, dict):
                continue
            key = item.get("secretKey") or item.get("key")
            val = item.get("secretValue") or item.get("value")
            if isinstance(key, str) and isinstance(val, str):
                out[key] = val
        return out
