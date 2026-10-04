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

import argparse
import contextvars
import os
import re
import secrets
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

import httpx
import yaml
from secrets_sync import vault_infisical
from secrets_sync.protocols import VaultBackend, VaultRef

REPO_ROOT = Path(__file__).resolve().parents[1]
SUPABASE_API = "https://api.supabase.com"
SQL_ENVS = frozenset({"prod", "staging"})
PASSWORD_RE = re.compile(r"[0-9a-f]{48}")
ENVIRONMENTS = ("production", "staging")
# Mirrors env_roles.sql: login, login_langgraph, login_queue.
SCHEMA_SUFFIXES = ("", "_langgraph", "_queue")
HTTP_TIMEOUT = 60.0

_APP_ID_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
_IDENT_RE = re.compile(r"[a-z_][a-z0-9_]*")
_ENV_LINE_RE = re.compile(r"^(?P<indent>[ \t]*)env\s+text\s*:=\s*'[^'\n]*'\s*;[^\n]*$", re.MULTILINE)
_PW_LINE_RE = re.compile(r"^(?P<indent>[ \t]*)pw\s+text\s*:=\s*'[^'\n]*'\s*;[^\n]*$", re.MULTILINE)
_RENDERED_MARK = "-- set by scripts/db_bootstrap.py"

_MASK_FOR_ACTIONS: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "db_bootstrap_mask_for_actions", default=False
)


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


def _scrub(text: str, values: Sequence[str]) -> str:
    for v in values:
        if v:
            text = text.replace(v, "***")
    return text


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
        self._ref = project_ref
        self._token = token
        self._client = client
        self._base = base_url.rstrip("/")

    def run(self, sql: str) -> None:
        url = f"{self._base}/v1/projects/{self._ref}/database/query"
        headers = {"Authorization": f"Bearer {self._token}"}
        status = _send("database query", self._client, "POST", url, headers, {"query": sql}).status_code
        if not 200 <= status < 300:
            # The response body echoes the failing SQL (which holds the password).
            raise DbBootstrapError("database query", f"Management API returned HTTP {status}")


class PsycopgRunner:
    """Runs SQL on a direct admin connection (pg tests: non-superuser CREATEROLE admin)."""

    def __init__(self, admin_url: str) -> None:
        self._url = admin_url

    def run(self, sql: str) -> None:
        import psycopg

        try:
            with psycopg.connect(self._url, autocommit=True) as conn:
                conn.execute(sql.encode("utf-8"))
        except psycopg.Error as e:
            sqlstate = getattr(e, "sqlstate", None) or "-"
            raise DbBootstrapError(
                "database query", f"{type(e).__name__} (SQLSTATE {sqlstate})"
            ) from None


def _send(
    step: str,
    client: httpx.Client | None,
    method: str,
    url: str,
    headers: dict[str, str],
    json_body: dict[str, Any] | None = None,
) -> httpx.Response:
    own = client is None
    c = client or httpx.Client(timeout=HTTP_TIMEOUT)
    try:
        resp = c.request(method, url, headers=headers, json=json_body)
        resp.read()
        return resp
    except httpx.HTTPError as e:
        raise DbBootstrapError(step, f"request failed ({type(e).__name__})") from None
    finally:
        if own:
            c.close()


@dataclass(frozen=True)
class EnsureResult:
    action: Literal["noop", "applied"]
    login: str


def _vault_ref(raw: Any, where: str) -> VaultRef:
    keys = ("project", "env", "path", "key")
    if not isinstance(raw, dict) or not all(isinstance(raw.get(k), str) and raw[k] for k in keys):
        raise DbBootstrapError("declaration", f"{where} needs project, env, path and key")
    return {k: raw[k] for k in keys}  # type: ignore[return-value]


def _schemas(login: str) -> tuple[str, ...]:
    return tuple(f"{login}{suffix}" for suffix in SCHEMA_SUFFIXES)


def load_plan(app_id: str, environment: str, *, repo_root: Path = REPO_ROOT) -> LoginPlan:
    if not _APP_ID_RE.fullmatch(app_id):
        raise DbBootstrapError("declaration", f"invalid app id {app_id!r}")
    rel = f"deploy/db/{app_id}.yml"
    path = repo_root / rel
    if not path.is_file():
        raise DbBootstrapError("declaration", f"missing {rel}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise DbBootstrapError("declaration", f"{rel} must be a mapping")

    ref = raw.get("supabase_project_ref")
    sql_path = raw.get("bootstrap_sql")
    envs = raw.get("environments")
    if not isinstance(ref, str) or not re.fullmatch(r"[a-z0-9]+", ref):
        raise DbBootstrapError("declaration", f"{rel}: supabase_project_ref missing or invalid")
    if not isinstance(sql_path, str) or sql_path.startswith("/") or ".." in Path(sql_path).parts:
        raise DbBootstrapError("declaration", f"{rel}: bootstrap_sql must be a repo-relative path")
    if not isinstance(envs, dict):
        raise DbBootstrapError("declaration", f"{rel}: environments missing")
    if environment not in envs:
        raise DbBootstrapError(
            "declaration", f"environment {environment!r} not declared in {rel}"
        )

    def env_body(name: str) -> tuple[str, str, VaultRef]:
        body = envs[name]
        if not isinstance(body, dict):
            raise DbBootstrapError("declaration", f"{rel}: environments.{name} must be a mapping")
        sql_env, login = body.get("sql_env"), body.get("login")
        if sql_env not in SQL_ENVS:
            raise DbBootstrapError(
                "declaration", f"{rel}: environments.{name}.sql_env must be prod or staging"
            )
        if not isinstance(login, str) or not _IDENT_RE.fullmatch(login):
            raise DbBootstrapError("declaration", f"{rel}: environments.{name}.login invalid")
        pw_ref = _vault_ref(body.get("password_vault_ref"), f"environments.{name}.password_vault_ref")
        return sql_env, login, pw_ref

    sql_env, login, password_ref = env_body(environment)
    other_schemas: list[str] = []
    for other in envs:
        if other != environment:
            other_schemas.extend(_schemas(env_body(other)[1]))

    return LoginPlan(
        app_id=app_id,
        environment=environment,
        sql_env=sql_env,
        login=login,
        schemas=_schemas(login),
        other_schemas=tuple(other_schemas),
        project_ref=ref,
        token_ref=_vault_ref(raw.get("access_token_vault_ref"), "access_token_vault_ref"),
        password_ref=password_ref,
        bootstrap_sql=sql_path,
        port=int(raw.get("port", 5432)),
        dbname=str(raw.get("dbname", "postgres")),
    )


def render_sql(template: str, *, env: str, password: str) -> str:
    if env not in SQL_ENVS:
        raise DbBootstrapError("render sql", "env must be prod or staging")
    if not PASSWORD_RE.fullmatch(password):
        raise DbBootstrapError("render sql", "password must be 48 lowercase hex characters")
    if len(_ENV_LINE_RE.findall(template)) != 1 or len(_PW_LINE_RE.findall(template)) != 1:
        raise DbBootstrapError(
            "render sql", "template must hold exactly one env and one pw assignment"
        )
    out = _ENV_LINE_RE.sub(
        lambda m: f"{m.group('indent')}env text := '{env}';  {_RENDERED_MARK}", template
    )
    return _PW_LINE_RE.sub(
        lambda m: f"{m.group('indent')}pw  text := '{password}';  {_RENDERED_MARK}", out
    )


def fetch_pooler_host(
    project_ref: str,
    token: str,
    *,
    client: httpx.Client | None = None,
    base_url: str = SUPABASE_API,
) -> str:
    step = "pooler host"
    url = f"{base_url.rstrip('/')}/v1/projects/{project_ref}/config/database/pooler"
    resp = _send(step, client, "GET", url, {"Authorization": f"Bearer {token}"})
    if resp.status_code != 200:
        raise DbBootstrapError(step, f"Management API returned HTTP {resp.status_code}")
    try:
        entries = resp.json()
    except ValueError:
        raise DbBootstrapError(step, "response is not JSON") from None
    if isinstance(entries, dict):
        entries = [entries]
    if isinstance(entries, list):
        for entry in entries:
            if (
                isinstance(entry, dict)
                and entry.get("database_type") == "PRIMARY"
                and isinstance(entry.get("db_host"), str)
                and entry["db_host"].strip()
            ):
                return entry["db_host"].strip()
    raise DbBootstrapError(step, "no PRIMARY entry with db_host")


def connection_parts(plan: LoginPlan, *, host: str, password: str) -> ConnParts:
    return ConnParts(
        host=host,
        port=plan.port,
        user=f"{plan.login}.{plan.project_ref}",
        dbname=plan.dbname,
        password=password,
    )


def probe_login(parts: ConnParts, plan: LoginPlan) -> None:
    """Log in as the login and prove its identity and exact access; raise ``ProbeError``.

    Write checks run inside a transaction that is always rolled back.
    """
    import psycopg
    from psycopg import errors as pg_errors
    from psycopg import sql as pg_sql

    try:
        conn = psycopg.connect(
            host=parts.host,
            port=parts.port,
            user=parts.user,
            password=parts.password,
            dbname=parts.dbname,
            connect_timeout=15,
            autocommit=True,
        )
    except psycopg.Error as e:
        raise ProbeError("probe", f"cannot log in as {parts.user} ({type(e).__name__})") from None

    problems: list[str] = []
    try:
        with conn:
            row = conn.execute("SELECT current_user").fetchone()
            user = row[0] if row else None
            if user != plan.login:
                raise ProbeError("probe", f"connected as {user!r}, expected {plan.login!r}")

            row = conn.execute("SHOW search_path").fetchone()
            first = str(row[0] if row else "").split(",")[0].strip().strip('"')
            if first != plan.app_schema:
                problems.append(f"search_path does not start with {plan.app_schema}")

            def denied(statement: pg_sql.Composable | str) -> bool:
                try:
                    with conn.transaction():
                        conn.execute(statement)
                except pg_errors.InsufficientPrivilege:
                    return True
                return False

            probe_table = f"db_bootstrap_probe_{secrets.token_hex(4)}"
            own = pg_sql.Identifier(plan.app_schema, probe_table)
            in_public = pg_sql.Identifier("public", probe_table)
            with conn.transaction(force_rollback=True):
                try:
                    with conn.transaction():
                        conn.execute(pg_sql.SQL("CREATE TABLE {} (id int)").format(own))
                        conn.execute(pg_sql.SQL("INSERT INTO {} VALUES (1)").format(own))
                        conn.execute(pg_sql.SQL("SELECT id FROM {}").format(own)).fetchall()
                        conn.execute(pg_sql.SQL("DROP TABLE {}").format(own))
                except pg_errors.InsufficientPrivilege:
                    problems.append(f"cannot create, use and drop a table in {plan.app_schema}")

                if not denied(pg_sql.SQL("CREATE TABLE {} (id int)").format(in_public)):
                    problems.append("can create objects in public")

                runs = conn.execute(
                    "SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relname = 'runs'"
                ).fetchone()
                if runs and not denied("SELECT 1 FROM public.runs LIMIT 0"):
                    problems.append("can read public.runs")

            if plan.other_schemas:
                others = list(plan.other_schemas)
                for name, usage, create in conn.execute(
                    "SELECT nspname, has_schema_privilege(oid, 'USAGE'), "
                    "has_schema_privilege(oid, 'CREATE') "
                    "FROM pg_namespace WHERE nspname = ANY(%s) ORDER BY nspname",
                    (others,),
                ).fetchall():
                    if usage or create:
                        problems.append(f"has access to schema {name}")
                for schema, table in conn.execute(
                    "SELECT n.nspname, c.relname FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = ANY(%s) AND c.relkind IN ('r', 'v', 'm', 'p', 'f') "
                    "AND has_table_privilege(c.oid, 'SELECT') ORDER BY 1, 2",
                    (others,),
                ).fetchall():
                    problems.append(f"can read {schema}.{table}")
    except ProbeError:
        raise
    except psycopg.Error as e:
        raise ProbeError("probe", f"unexpected {type(e).__name__}") from None

    if problems:
        raise ProbeError("probe", "; ".join(problems))


def management_api_runner(plan: LoginPlan, token: str) -> SqlRunner:
    return ManagementApiRunner(project_ref=plan.project_ref, token=token)


def pooler_connection_parts(plan: LoginPlan, token: str, password: str) -> ConnParts:
    host = fetch_pooler_host(plan.project_ref, token)
    return connection_parts(plan, host=host, password=password)


@dataclass(frozen=True)
class EnsureDeps:
    """Injection points (tests swap any of them; defaults are the live ones)."""

    vault: VaultBackend
    make_runner: Callable[[LoginPlan, str], SqlRunner] = management_api_runner
    resolve_parts: Callable[[LoginPlan, str, str], ConnParts] = pooler_connection_parts
    probe: Callable[[ConnParts, LoginPlan], None] = probe_login


def _mask(value: str) -> None:
    if value and _MASK_FOR_ACTIONS.get():
        print(f"::add-mask::{value}", flush=True)


def _say(message: str) -> None:
    print(f"db_bootstrap: {message}", flush=True)


def _rewrap(step: str, err: BaseException, values: Sequence[str]) -> DbBootstrapError:
    """A value-free error for a collaborator failure (its own text is only kept, scrubbed,
    when it is one of ours)."""
    cls = ProbeError if isinstance(err, ProbeError) else DbBootstrapError
    if isinstance(err, DbBootstrapError):
        detail = _scrub(str(err).removeprefix(f"{err.step}: "), values)
        return cls(step, detail)
    return cls(step, type(err).__name__)


def ensure(
    app_id: str,
    environment: str,
    deps: EnsureDeps,
    *,
    repo_root: Path = REPO_ROOT,
) -> EnsureResult:
    plan = load_plan(app_id, environment, repo_root=repo_root)
    token_key, pw_key = plan.token_ref["key"], plan.password_ref["key"]

    try:
        values = deps.vault.get_secrets([plan.token_ref, plan.password_ref])
    except Exception as e:  # noqa: BLE001 — collaborator text is never echoed
        raise DbBootstrapError("vault read", type(e).__name__) from None
    token = values.get(token_key) or ""
    password = values.get(pw_key) or ""
    _mask(token)
    _mask(password)
    secret_values = (token, password)

    if not token:
        raise DbBootstrapError("vault read", f"{token_key} is missing or empty")
    if not password:
        raise DbBootstrapError("vault read", f"{pw_key} is missing or empty")
    if not PASSWORD_RE.fullmatch(password):
        raise DbBootstrapError(
            "password check", f"{pw_key} must be 48 lowercase hex characters (openssl rand -hex 24)"
        )

    try:
        parts = deps.resolve_parts(plan, token, password)
    except Exception as e:  # noqa: BLE001
        step = e.step if isinstance(e, DbBootstrapError) else "pooler host"
        raise _rewrap(step, e, secret_values) from None

    try:
        deps.probe(parts, plan)
    except ProbeError:
        _say(f"{plan.login}: probe failed; applying {plan.bootstrap_sql}")
    except Exception as e:  # noqa: BLE001
        raise _rewrap("probe", e, secret_values) from None
    else:
        _say(f"{plan.login}: probe passed; nothing to do")
        return EnsureResult(action="noop", login=plan.login)

    sql_file = repo_root / plan.bootstrap_sql
    if not sql_file.is_file():
        raise DbBootstrapError("render sql", f"missing {plan.bootstrap_sql}")
    sql = render_sql(sql_file.read_text(encoding="utf-8"), env=plan.sql_env, password=password)

    try:
        deps.make_runner(plan, token).run(sql)
    except Exception as e:  # noqa: BLE001
        step = e.step if isinstance(e, DbBootstrapError) else "database query"
        raise _rewrap(step, e, secret_values) from None
    _say(f"{plan.login}: bootstrap SQL applied")

    try:
        deps.probe(parts, plan)
    except Exception as e:  # noqa: BLE001
        raise _rewrap("probe after apply", e, secret_values) from None
    _say(f"{plan.login}: probe passed after apply")
    return EnsureResult(action="applied", login=plan.login)


def _print_plan(plan: LoginPlan) -> None:
    print(f"dry-run: {plan.app_id}/{plan.environment} (no vault, API or database calls)")
    print(f"login: {plan.login}")
    print(f"schemas: {', '.join(plan.schemas)}")
    print(f"pooler user: {plan.login}.{plan.project_ref}")
    print(f"supabase project ref: {plan.project_ref}")
    print(f"port: {plan.port}  dbname: {plan.dbname}  host: session pooler (read at run time)")
    print(f"password key (read): {plan.password_ref['key']} "
          f"[{plan.password_ref['project']}/{plan.password_ref['env']}{plan.password_ref['path']}]")
    print(f"access token key (read): {plan.token_ref['key']}")
    print(f"bootstrap sql: {plan.bootstrap_sql} (env = {plan.sql_env})")


def _live_deps() -> EnsureDeps:
    infisical_token = os.environ.get("INFISICAL_TOKEN", "").strip()
    if not infisical_token:
        raise DbBootstrapError("vault read", "INFISICAL_TOKEN is not set (ops-runtime OIDC step)")
    return EnsureDeps(vault=vault_infisical.InfisicalCloudBackend(token=infisical_token))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    e = sub.add_parser("ensure", help="Create or check the login for app × environment")
    e.add_argument("--app-id", required=True, help="app id with deploy/db/<app_id>.yml")
    e.add_argument("--environment", required=True, choices=ENVIRONMENTS)
    e.add_argument("--dry-run", action="store_true", help="Print planned names only")
    return p


def main(argv: Sequence[str] | None = None, *, deps: EnsureDeps | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        if args.dry_run:
            _print_plan(load_plan(args.app_id, args.environment))
            return 0
        live = deps if deps is not None else _live_deps()
        mask_token = _MASK_FOR_ACTIONS.set(os.environ.get("GITHUB_ACTIONS") == "true")
        try:
            result = ensure(args.app_id, args.environment, live)
        finally:
            _MASK_FOR_ACTIONS.reset(mask_token)
    except DbBootstrapError as err:
        print(f"db_bootstrap error: {err}", file=sys.stderr)
        return 1
    except Exception as err:  # noqa: BLE001 — never print collaborator text or a traceback
        print(f"db_bootstrap error: unexpected {type(err).__name__}", file=sys.stderr)
        return 1
    print(f"ok: {result.login} {result.action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
