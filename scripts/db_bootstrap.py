#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "httpx>=0.27",
#   "psycopg[binary]>=3.2",
#   "pyyaml>=6",
# ]
# ///
"""Ensure an app's per-environment database login in the shared lab Supabase project.

``ensure --app-id <id> --environment <env>`` reads ``deploy/db/<id>.yml``, then
the Supabase access token and the environment's password from Infisical
(read-only). It probes the login; if the probe passes it does nothing. Otherwise
it runs the app's bootstrap SQL through the Supabase Management API and probes
again.

Supabase Management API (OpenAPI ``https://api.supabase.com/api/v1-json``):
``GET /v1/projects/{ref}/config/database/pooler`` (entries with
``database_type`` and ``db_host``) and ``POST /v1/projects/{ref}/database/query``
with body ``{"query": ...}`` (beta).

Never prints or logs the token or passwords; errors name the step only.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol

import httpx
from secrets_sync.protocols import VaultBackend, VaultRef

REPO_ROOT = Path(__file__).resolve().parents[1]
SUPABASE_API = "https://api.supabase.com"
SQL_ENVS = frozenset({"prod", "staging"})
PASSWORD_RE = re.compile(r"[0-9a-f]{48}")


class DbBootstrapError(Exception):
    """Fail-closed error. ``step`` names where it failed; never carries a value."""

    def __init__(self, step: str, detail: str = "") -> None:
        self.step = step
        super().__init__(f"{step}: {detail}" if detail else step)


class ProbeError(DbBootstrapError):
    """The login cannot connect, or does not have exactly the expected access."""


@dataclass(frozen=True)
class LoginPlan:
    """Names and non-secret parts only (from ``deploy/db/<app>.yml``); safe to print."""

    app_id: str
    environment: str
    sql_env: str
    login: str
    schemas: tuple[str, ...]
    other_schemas: tuple[str, ...]
    project_ref: str
    token_ref: VaultRef
    password_ref: VaultRef
    bootstrap_sql: str
    port: int
    dbname: str

    @property
    def app_schema(self) -> str:
        return self.schemas[0]


@dataclass(frozen=True)
class ConnParts:
    """psycopg keyword parameters for the login. ``password`` is kept out of repr."""

    host: str
    port: int
    user: str
    dbname: str
    password: str = field(repr=False)


class SqlRunner(Protocol):
    def run(self, sql: str) -> None:
        """Run ``sql`` with admin rights; raise ``DbBootstrapError`` on failure."""


class ManagementApiRunner:
    """Runs SQL through ``POST /v1/projects/{ref}/database/query``."""

    def __init__(
        self,
        *,
        project_ref: str,
        token: str,
        client: httpx.Client | None = None,
        base_url: str = SUPABASE_API,
    ) -> None:
        raise NotImplementedError("ManagementApiRunner: T111")

    def run(self, sql: str) -> None:
        raise NotImplementedError("ManagementApiRunner.run: T111")


class PsycopgRunner:
    """Runs SQL on a direct admin connection (pg tests: non-superuser CREATEROLE admin)."""

    def __init__(self, admin_url: str) -> None:
        raise NotImplementedError("PsycopgRunner: T111")

    def run(self, sql: str) -> None:
        raise NotImplementedError("PsycopgRunner.run: T111")


@dataclass(frozen=True)
class EnsureResult:
    action: Literal["noop", "applied"]
    login: str


def load_plan(app_id: str, environment: str, *, repo_root: Path = REPO_ROOT) -> LoginPlan:
    raise NotImplementedError("load_plan: T111")


def render_sql(template: str, *, env: str, password: str) -> str:
    raise NotImplementedError("render_sql: T111")


def fetch_pooler_host(
    project_ref: str,
    token: str,
    *,
    client: httpx.Client | None = None,
    base_url: str = SUPABASE_API,
) -> str:
    raise NotImplementedError("fetch_pooler_host: T111")


def connection_parts(plan: LoginPlan, *, host: str, password: str) -> ConnParts:
    raise NotImplementedError("connection_parts: T111")


def probe_login(parts: ConnParts, plan: LoginPlan) -> None:
    raise NotImplementedError("probe_login: T111")


def management_api_runner(plan: LoginPlan, token: str) -> SqlRunner:
    raise NotImplementedError("management_api_runner: T111")


def pooler_connection_parts(plan: LoginPlan, token: str, password: str) -> ConnParts:
    raise NotImplementedError("pooler_connection_parts: T111")


@dataclass(frozen=True)
class EnsureDeps:
    """Injection points (tests swap any of them; defaults are the live ones)."""

    vault: VaultBackend
    make_runner: Callable[[LoginPlan, str], SqlRunner] = management_api_runner
    resolve_parts: Callable[[LoginPlan, str, str], ConnParts] = pooler_connection_parts
    probe: Callable[[ConnParts, LoginPlan], None] = probe_login


def ensure(
    app_id: str,
    environment: str,
    deps: EnsureDeps,
    *,
    repo_root: Path = REPO_ROOT,
) -> EnsureResult:
    raise NotImplementedError("ensure: T111")


def main(argv: Sequence[str] | None = None, *, deps: EnsureDeps | None = None) -> int:
    raise NotImplementedError("main: T111")


if __name__ == "__main__":
    raise SystemExit(main())
