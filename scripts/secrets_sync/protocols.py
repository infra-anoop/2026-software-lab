"""Protocols for vault read and runtime variable upsert (A21)."""

from __future__ import annotations

from typing import Mapping, Protocol, TypedDict


class VaultRef(TypedDict):
    """Infisical-oriented ref shape from deploy/secrets/schema.yaml (data, not imports)."""

    project: str
    env: str
    path: str
    key: str


class VaultBackend(Protocol):
    """Fetch secret values by vault refs. Never log return values."""

    def get_secrets(self, refs: list[VaultRef]) -> dict[str, str]:
        """Return mapping vault key → value for refs that exist.

        Missing optional keys may be omitted; required handling is the caller's job.
        """


class RuntimeTarget(Protocol):
    """Upsert env vars onto a runtime (Railway now; Vercel later)."""

    @property
    def label(self) -> str:
        """Human label for dry-run (no secrets)."""

    def resolve_footprint(self) -> None:
        """Fail closed if project/service/environment do not exist (A23/A26 contract)."""

    def upsert_variables(self, variables: Mapping[str, str]) -> UpsertResult:
        """Write variables; never log values. replace=False semantics (merge/upsert)."""


class UpsertResult(TypedDict):
    """Names touched only — never values."""

    upserted: list[str]
    noop: list[str]
