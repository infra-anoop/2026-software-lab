"""Unit tests for scripts/db_bootstrap.py (no network, no database).

Spec 002 T109 / packet notes/packets/2026-10-03-lab-db-bootstrap.md. Real-Postgres
cases live in test_db_bootstrap_pg.py.
"""

from __future__ import annotations

import ast
import json
import logging
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import db_bootstrap as db
from secrets_sync.protocols import VaultRef

REPO = Path(__file__).resolve().parents[1]
DECLARATION = REPO / "deploy" / "db" / "smart-writer-v2.yml"
ENV_ROLES_SQL = REPO / "apps" / "smart-writer-v2" / "db" / "bootstrap" / "env_roles.sql"
PLACEHOLDER = "REPLACE_WITH_GENERATED_PASSWORD"

PROJECT = "2026-software-lab"
REF = "oguydvttuzbbiovvnxoj"
POOLER_HOST = "aws-0-us-east-1.pooler.supabase.com"
TOKEN = "sbp_unique_access_token_7Qx9a1b2c3d4"
PW_PROD = "0123456789abcdef" * 3
PW_STAGING = "fedcba9876543210" * 3
BAD_PW = "Zz-not-hex-but-48-chars-long-0123456789abcdefgh"

TOKEN_REF: VaultRef = {
    "project": PROJECT,
    "env": "production",
    "path": "/",
    "key": "SUPABASE_ACCESS_TOKEN",
}
PROD_PW_REF: VaultRef = {
    "project": PROJECT,
    "env": "production",
    "path": "/",
    "key": "SMART_WRITER_V2_DB_PASSWORD",
}
STAGING_PW_REF: VaultRef = {
    "project": PROJECT,
    "env": "production",
    "path": "/",
    "key": "SMART_WRITER_V2_STAGING_DB_PASSWORD",
}

ALL_SECRETS = (TOKEN, PW_PROD, PW_STAGING, BAD_PW)


def _tup(ref: VaultRef) -> tuple[str, str, str, str]:
    return (ref["project"], ref["env"], ref["path"], ref["key"])


# ── Fakes ─────────────────────────────────────────────────────────────────────


class MemoryVault:
    """Read-only in-memory vault (the automation never writes Infisical)."""

    def __init__(self) -> None:
        self.store: dict[tuple[str, str, str, str], str] = {}

    def get_secrets(self, refs: list[VaultRef]) -> dict[str, str]:
        return {r["key"]: self.store[_tup(r)] for r in refs if _tup(r) in self.store}


class Harness:
    """Wires EnsureDeps with spies. Fakes deliberately put secrets in their exceptions."""

    def __init__(
        self,
        *,
        token: str | None = TOKEN,
        password: str | None = PW_PROD,
        password_ref: VaultRef = PROD_PW_REF,
        login_ok: bool = False,
        fail_resolve: bool = False,
        fail_resolve_typed: bool = False,
        fail_run_sql: bool = False,
        fail_final_probe: bool = False,
    ) -> None:
        self.log: list[str] = []
        self.vault = MemoryVault()
        if token is not None:
            self.vault.store[_tup(TOKEN_REF)] = token
        if password is not None:
            self.vault.store[_tup(password_ref)] = password
        self.login_ok = login_ok
        self.fail_resolve = fail_resolve
        self.fail_resolve_typed = fail_resolve_typed
        self.fail_run_sql = fail_run_sql
        self.fail_final_probe = fail_final_probe
        self.runner_tokens: list[str] = []
        self.sql_runs: list[str] = []
        self.probe_calls: list[tuple[db.ConnParts, db.LoginPlan]] = []
        self._applied = False

    def make_runner(self, plan: db.LoginPlan, token: str) -> db.SqlRunner:
        self.runner_tokens.append(token)
        harness = self

        class Runner:
            def run(self, sql: str) -> None:
                harness.log.append("run_sql")
                harness.sql_runs.append(sql)
                if harness.fail_run_sql:
                    raise RuntimeError(f"HTTP 400 with token {token} for query: {sql}")
                harness._applied = True

        return Runner()

    def resolve_parts(self, plan: db.LoginPlan, token: str, password: str) -> db.ConnParts:
        self.log.append("resolve")
        if self.fail_resolve:
            raise RuntimeError(f"pooler lookup failed token={token} password={password}")
        if self.fail_resolve_typed:
            raise db.DbBootstrapError(
                "pooler host", f"HTTP 401 token={token} password={password}"
            )
        return db.ConnParts(
            host=POOLER_HOST,
            port=5432,
            user=f"{plan.login}.{REF}",
            dbname="postgres",
            password=password,
        )

    def probe(self, parts: db.ConnParts, plan: db.LoginPlan) -> None:
        self.log.append("probe")
        self.probe_calls.append((parts, plan))
        ok = (self._applied and not self.fail_final_probe) or (
            not self._applied and self.login_ok
        )
        if not ok:
            raise db.ProbeError(
                "probe",
                f"password authentication failed token={TOKEN} password={parts.password}",
            )

    @property
    def deps(self) -> db.EnsureDeps:
        return db.EnsureDeps(
            vault=self.vault,
            make_runner=self.make_runner,
            resolve_parts=self.resolve_parts,
            probe=self.probe,
        )


def _raising_deps() -> db.EnsureDeps:
    def boom(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("dry-run must not touch the vault, the API or the database")

    class Boom:
        get_secrets = staticmethod(boom)

    return db.EnsureDeps(vault=Boom(), make_runner=boom, resolve_parts=boom, probe=boom)


def _assert_error_chain_scrubbed(exc: BaseException) -> None:
    """The error and everything chained to it (what a traceback would print) hold no value."""
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        text = f"{cur!s} {cur!r} {cur.args!r}"
        for secret in ALL_SECRETS:
            assert secret not in text, f"secret value in {type(cur).__name__} of the error chain"
        cur = cur.__cause__ or cur.__context__


def _assert_no_secrets(text: str, *, allow_mask_lines: bool = False) -> None:
    for line in text.splitlines():
        if allow_mask_lines and line.startswith("::add-mask::"):
            continue
        for secret in ALL_SECRETS:
            assert secret not in line, f"secret value leaked in output line: {line[:40]!r}…"


# ── Declaration / plan (names and non-secret parts only) ─────────────────────


def test_declaration_file_exists_and_holds_no_values() -> None:
    assert DECLARATION.is_file(), "deploy/db/smart-writer-v2.yml missing"
    text = DECLARATION.read_text(encoding="utf-8")
    assert "://" not in text
    assert "@" not in text
    assert re.search(r"[0-9a-f]{32,}", text) is None
    raw = yaml.safe_load(text)
    assert isinstance(raw, dict)
    assert raw.get("supabase_project_ref") == REF
    assert raw.get("access_token_vault_ref") == dict(TOKEN_REF)
    assert raw.get("bootstrap_sql") == "apps/smart-writer-v2/db/bootstrap/env_roles.sql"


def test_load_plan_production() -> None:
    plan = db.load_plan("smart-writer-v2", "production", repo_root=REPO)
    assert plan.app_id == "smart-writer-v2"
    assert plan.environment == "production"
    assert plan.sql_env == "prod"
    assert plan.login == "swv2_prod"
    assert plan.schemas == ("swv2_prod", "swv2_prod_langgraph", "swv2_prod_queue")
    assert plan.app_schema == "swv2_prod"
    assert plan.other_schemas == (
        "swv2_staging",
        "swv2_staging_langgraph",
        "swv2_staging_queue",
    )
    assert plan.project_ref == REF
    assert dict(plan.token_ref) == dict(TOKEN_REF)
    assert dict(plan.password_ref) == dict(PROD_PW_REF)
    assert plan.bootstrap_sql == "apps/smart-writer-v2/db/bootstrap/env_roles.sql"
    assert plan.port == 5432
    assert plan.dbname == "postgres"


def test_load_plan_staging() -> None:
    plan = db.load_plan("smart-writer-v2", "staging", repo_root=REPO)
    assert plan.sql_env == "staging"
    assert plan.login == "swv2_staging"
    assert plan.schemas[0] == "swv2_staging"
    assert plan.other_schemas[0] == "swv2_prod"
    assert dict(plan.password_ref) == dict(STAGING_PW_REF)
    assert plan.port == 5432
    assert plan.dbname == "postgres"


def test_load_plan_without_declaration_fails() -> None:
    with pytest.raises(db.DbBootstrapError, match="deploy/db"):
        db.load_plan("research-auditor", "production", repo_root=REPO)


def test_load_plan_rejects_undeclared_environment(tmp_path: Path) -> None:
    assert DECLARATION.is_file(), "deploy/db/smart-writer-v2.yml missing"
    (tmp_path / "deploy" / "db").mkdir(parents=True)
    src = yaml.safe_load(DECLARATION.read_text(encoding="utf-8"))
    src["environments"] = {k: v for k, v in src["environments"].items() if k == "production"}
    (tmp_path / "deploy" / "db" / "smart-writer-v2.yml").write_text(
        yaml.safe_dump(src), encoding="utf-8"
    )
    with pytest.raises(db.DbBootstrapError, match="staging"):
        db.load_plan("smart-writer-v2", "staging", repo_root=tmp_path)


# ── SQL render ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("env", ["prod", "staging"])
def test_render_sql_replaces_only_the_two_edit_assignments(env: str) -> None:
    template = ENV_ROLES_SQL.read_text(encoding="utf-8")
    out = db.render_sql(template, env=env, password=PW_PROD)
    before = template.splitlines()
    after = out.splitlines()
    assert len(before) == len(after)
    changed = [(b, a) for b, a in zip(before, after, strict=True) if b != a]
    assert len(changed) == 2, changed
    env_line = next(a for _, a in changed if re.search(r"\benv\s+text\s*:=", a))
    pw_line = next(a for _, a in changed if re.search(r"\bpw\s+text\s*:=", a))
    assert re.search(rf"\benv\s+text\s*:=\s*'{env}'\s*;", env_line)
    assert re.search(rf"\bpw\s+text\s*:=\s*'{PW_PROD}'\s*;", pw_line)
    assert PLACEHOLDER not in pw_line
    # The guard `IF pw = 'REPLACE_WITH_GENERATED_PASSWORD'` stays; the assignment does not.
    assert template.count(PLACEHOLDER) == 2
    assert out.count(PLACEHOLDER) == 1


@pytest.mark.parametrize(
    "env",
    ["production", "PROD", "", "prod'; DROP ROLE postgres; --", "staging "],
)
def test_render_sql_rejects_bad_env(env: str) -> None:
    template = ENV_ROLES_SQL.read_text(encoding="utf-8")
    with pytest.raises((ValueError, db.DbBootstrapError)):
        db.render_sql(template, env=env, password=PW_PROD)


@pytest.mark.parametrize(
    "password",
    [
        PLACEHOLDER,
        PW_PROD[:-1],
        PW_PROD + "0",
        "g" * 48,
        "0123456789abcdef0123456789abcdef0123456789abcde'",
        BAD_PW,
        "",
    ],
)
def test_render_sql_rejects_bad_password(password: str) -> None:
    template = ENV_ROLES_SQL.read_text(encoding="utf-8")
    with pytest.raises((ValueError, db.DbBootstrapError)) as ei:
        db.render_sql(template, env="prod", password=password)
    if password:
        assert password not in str(ei.value)


def test_render_sql_refuses_template_without_pw_assignment() -> None:
    template = ENV_ROLES_SQL.read_text(encoding="utf-8")
    broken = "\n".join(
        line for line in template.splitlines() if not re.search(r"\bpw\s+text\s*:=", line)
    )
    with pytest.raises((ValueError, db.DbBootstrapError)):
        db.render_sql(broken, env="prod", password=PW_PROD)


def test_render_sql_refuses_template_without_env_assignment() -> None:
    template = ENV_ROLES_SQL.read_text(encoding="utf-8")
    broken = "\n".join(
        line for line in template.splitlines() if not re.search(r"\benv\s+text\s*:=", line)
    )
    with pytest.raises((ValueError, db.DbBootstrapError)):
        db.render_sql(broken, env="prod", password=PW_PROD)


# ── Connection parts ──────────────────────────────────────────────────────────


def test_connection_parts_session_pooler() -> None:
    plan = db.load_plan("smart-writer-v2", "production", repo_root=REPO)
    parts = db.connection_parts(plan, host=POOLER_HOST, password=PW_PROD)
    assert parts.host == POOLER_HOST
    assert parts.port == 5432
    assert parts.user == f"swv2_prod.{REF}"
    assert parts.dbname == "postgres"
    assert parts.password == PW_PROD
    assert PW_PROD not in repr(parts) and PW_PROD not in str(parts)


def test_connection_parts_staging_user() -> None:
    plan = db.load_plan("smart-writer-v2", "staging", repo_root=REPO)
    parts = db.connection_parts(plan, host=POOLER_HOST, password=PW_STAGING)
    assert parts.user == f"swv2_staging.{REF}"


# ── Supabase Management API (fake transport) ──────────────────────────────────

# Endpoints from Supabase's published OpenAPI (https://api.supabase.com/api/v1-json),
# confirmed 2026-10-04: v1-get-pooler-config and v1-run-a-query (beta, 201 on success).
API_BASE = "https://api.supabase.test"
POOLER_PATH = f"/v1/projects/{REF}/config/database/pooler"
QUERY_PATH = f"/v1/projects/{REF}/database/query"
QUERY_BODY_KEYS = frozenset({"query", "parameters", "read_only"})


def _pooler_entry(database_type: str, host: str, *, port: int = 6543) -> dict[str, Any]:
    return {
        "identifier": REF,
        "database_type": database_type,
        "is_using_scram_auth": True,
        "db_user": f"postgres.{REF}",
        "db_host": host,
        "db_port": port,
        "db_name": "postgres",
        "connection_string": f"postgresql://postgres.{REF}:[YOUR-PASSWORD]@{host}:{port}/postgres",
        "connectionString": f"postgresql://postgres.{REF}:[YOUR-PASSWORD]@{host}:{port}/postgres",
        "default_pool_size": 15,
        "max_client_conn": 200,
        "pool_mode": "transaction",
    }


class FakeSupabase:
    def __init__(
        self,
        *,
        pooler: list[dict[str, Any]] | None = None,
        pooler_status: int = 200,
        query_status: int = 201,
    ) -> None:
        self.pooler = (
            pooler
            if pooler is not None
            else [
                _pooler_entry("READ_REPLICA", "replica.pooler.supabase.com"),
                _pooler_entry("PRIMARY", POOLER_HOST),
            ]
        )
        self.pooler_status = pooler_status
        self.query_status = query_status
        self.requests: list[tuple[str, str]] = []
        self.queries: list[dict[str, Any]] = []
        self.unknown: list[str] = []

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self._handle))

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append((request.method, request.url.path))
        if request.headers.get("Authorization") != f"Bearer {TOKEN}":
            return httpx.Response(401, json={"message": "Unauthorized"})
        if request.method == "GET" and request.url.path == POOLER_PATH:
            if self.pooler_status != 200:
                # Sentinel: an error body that echoes the credential must not be relayed.
                return httpx.Response(
                    self.pooler_status,
                    json={"message": f"rejected {request.headers.get('Authorization')}"},
                )
            return httpx.Response(200, json=self.pooler)
        if request.method == "POST" and request.url.path == QUERY_PATH:
            body = json.loads(request.content)
            self.queries.append(body)
            if self.query_status >= 300:
                # Supabase echoes the failing statement; the client must not.
                return httpx.Response(
                    self.query_status,
                    json={"message": f"ERROR: 42501: failed near: {body.get('query')}"},
                )
            return httpx.Response(self.query_status, json=[])
        self.unknown.append(f"{request.method} {request.url.path}")
        return httpx.Response(404, json={"message": "unknown endpoint (fake)"})


def test_fetch_pooler_host_picks_primary() -> None:
    fake = FakeSupabase()
    with fake.client() as client:
        host = db.fetch_pooler_host(REF, TOKEN, client=client, base_url=API_BASE)
    assert host == POOLER_HOST
    assert fake.requests == [("GET", POOLER_PATH)]


@pytest.mark.parametrize(
    "pooler",
    [[], [_pooler_entry("READ_REPLICA", "replica.pooler.supabase.com")]],
    ids=["empty", "replica-only"],
)
def test_fetch_pooler_host_without_primary_fails_closed(pooler: list[dict[str, Any]]) -> None:
    fake = FakeSupabase(pooler=pooler)
    with fake.client() as client, pytest.raises(db.DbBootstrapError) as ei:
        db.fetch_pooler_host(REF, TOKEN, client=client, base_url=API_BASE)
    assert "pooler" in ei.value.step.lower()
    assert TOKEN not in str(ei.value)


@pytest.mark.parametrize("status", [401, 403, 500])
def test_fetch_pooler_host_http_error_names_step_not_token(status: int) -> None:
    fake = FakeSupabase(pooler_status=status)
    with fake.client() as client, pytest.raises(db.DbBootstrapError) as ei:
        db.fetch_pooler_host(REF, TOKEN, client=client, base_url=API_BASE)
    assert "pooler" in ei.value.step.lower()
    assert str(status) in str(ei.value)
    assert "rejected" not in str(ei.value)  # the response body is not echoed
    _assert_error_chain_scrubbed(ei.value)


def test_management_api_runner_posts_query() -> None:
    fake = FakeSupabase()
    sql = "SELECT 1; -- unique-sql-marker"
    with fake.client() as client:
        db.ManagementApiRunner(
            project_ref=REF, token=TOKEN, client=client, base_url=API_BASE
        ).run(sql)
    assert fake.requests == [("POST", QUERY_PATH)]
    body = fake.queries[0]
    assert body["query"] == sql
    assert set(body) <= QUERY_BODY_KEYS
    assert body.get("read_only") is not True
    assert fake.unknown == []


@pytest.mark.parametrize("status", [400, 401, 403, 500])
def test_management_api_runner_non_2xx_fails_loudly_without_values(status: int) -> None:
    fake = FakeSupabase(query_status=status)
    template = ENV_ROLES_SQL.read_text(encoding="utf-8")
    sql = template.replace(f"'{PLACEHOLDER}';", f"'{PW_PROD}';", 1)
    assert PW_PROD in sql
    with fake.client() as client, pytest.raises(db.DbBootstrapError) as ei:
        db.ManagementApiRunner(
            project_ref=REF, token=TOKEN, client=client, base_url=API_BASE
        ).run(sql)
    msg = str(ei.value)
    assert ei.value.step
    assert str(status) in msg
    assert "failed near" not in msg  # the response body is not echoed
    _assert_error_chain_scrubbed(ei.value)


def test_ensure_through_fake_management_api() -> None:
    fake = FakeSupabase()
    h = Harness(password=PW_PROD)
    client = fake.client()

    def make_runner(plan: db.LoginPlan, token: str) -> db.SqlRunner:
        h.runner_tokens.append(token)
        return db.ManagementApiRunner(
            project_ref=plan.project_ref, token=token, client=client, base_url=API_BASE
        )

    def resolve_parts(plan: db.LoginPlan, token: str, password: str) -> db.ConnParts:
        host = db.fetch_pooler_host(plan.project_ref, token, client=client, base_url=API_BASE)
        return db.connection_parts(plan, host=host, password=password)

    probes: list[db.ConnParts] = []

    def probe(parts: db.ConnParts, plan: db.LoginPlan) -> None:
        probes.append(parts)
        if not fake.queries:
            raise db.ProbeError("probe", "login missing")

    deps = db.EnsureDeps(
        vault=h.vault, make_runner=make_runner, resolve_parts=resolve_parts, probe=probe
    )
    try:
        res = db.ensure("smart-writer-v2", "production", deps, repo_root=REPO)
    finally:
        client.close()
    assert res.action == "applied"
    assert h.runner_tokens == [TOKEN]
    assert len(fake.queries) == 1
    assert re.search(rf"\bpw\s+text\s*:=\s*'{PW_PROD}'", fake.queries[0]["query"])
    assert re.search(r"\benv\s+text\s*:=\s*'prod'", fake.queries[0]["query"])
    assert [(p.host, p.port, p.user, p.dbname) for p in probes] == [
        (POOLER_HOST, 5432, f"swv2_prod.{REF}", "postgres")
    ] * 2
    assert fake.unknown == []


# ── ensure(): the idempotent decision ─────────────────────────────────────────


def test_ensure_noop_when_probe_passes_with_vault_password() -> None:
    h = Harness(login_ok=True)
    res = db.ensure("smart-writer-v2", "production", h.deps, repo_root=REPO)
    assert res.action == "noop"
    assert res.login == "swv2_prod"
    assert h.log == ["resolve", "probe"]
    assert h.sql_runs == []
    parts, plan = h.probe_calls[0]
    assert parts.password == PW_PROD
    assert parts.user == f"swv2_prod.{REF}"
    assert plan.login == "swv2_prod"


def test_ensure_applies_sql_when_probe_fails_then_probes_again() -> None:
    h = Harness(login_ok=False)
    res = db.ensure("smart-writer-v2", "production", h.deps, repo_root=REPO)
    assert res.action == "applied"
    assert h.log == ["resolve", "probe", "run_sql", "probe"]
    assert h.runner_tokens == [TOKEN]
    sql = h.sql_runs[0]
    assert re.search(r"\benv\s+text\s*:=\s*'prod'", sql)
    assert re.search(rf"\bpw\s+text\s*:=\s*'{PW_PROD}'", sql)
    assert h.probe_calls[-1][0].password == PW_PROD


def test_ensure_staging_uses_staging_password_and_env() -> None:
    h = Harness(password=PW_STAGING, password_ref=STAGING_PW_REF)
    res = db.ensure("smart-writer-v2", "staging", h.deps, repo_root=REPO)
    assert res.action == "applied"
    assert res.login == "swv2_staging"
    assert re.search(r"\benv\s+text\s*:=\s*'staging'", h.sql_runs[0])
    assert re.search(rf"\bpw\s+text\s*:=\s*'{PW_STAGING}'", h.sql_runs[0])
    assert h.probe_calls[0][0].user == f"swv2_staging.{REF}"


def test_ensure_final_probe_failure_is_an_error() -> None:
    h = Harness(fail_final_probe=True)
    with pytest.raises(db.DbBootstrapError) as ei:
        db.ensure("smart-writer-v2", "production", h.deps, repo_root=REPO)
    assert "probe" in ei.value.step
    assert h.log == ["resolve", "probe", "run_sql", "probe"]
    _assert_error_chain_scrubbed(ei.value)


@pytest.mark.parametrize(
    "password",
    [BAD_PW, PW_PROD[:-1], PW_PROD + "a", "g" * 48, PLACEHOLDER, ""],
    ids=["non-hex", "47", "49", "g48", "placeholder", "empty"],
)
def test_ensure_invalid_vault_password_fails_before_anything_runs(password: str) -> None:
    h = Harness(password=password)
    with pytest.raises(db.DbBootstrapError) as ei:
        db.ensure("smart-writer-v2", "production", h.deps, repo_root=REPO)
    assert h.log == []
    assert h.runner_tokens == []
    assert "SMART_WRITER_V2_DB_PASSWORD" in str(ei.value)
    if password:
        assert password not in str(ei.value)


def test_ensure_missing_vault_password_fails_before_anything_runs() -> None:
    h = Harness(password=None)
    with pytest.raises(db.DbBootstrapError) as ei:
        db.ensure("smart-writer-v2", "production", h.deps, repo_root=REPO)
    assert h.log == []
    assert "SMART_WRITER_V2_DB_PASSWORD" in str(ei.value)


def test_ensure_missing_access_token_fails_before_anything_runs() -> None:
    h = Harness(token=None)
    with pytest.raises(db.DbBootstrapError) as ei:
        db.ensure("smart-writer-v2", "production", h.deps, repo_root=REPO)
    assert h.log == []
    assert "SUPABASE_ACCESS_TOKEN" in str(ei.value)


@pytest.mark.parametrize("typed", [False, True], ids=["raw-exception", "bootstrap-error"])
def test_ensure_pooler_lookup_failure_runs_no_sql(typed: bool) -> None:
    h = Harness(fail_resolve=not typed, fail_resolve_typed=typed)
    with pytest.raises(db.DbBootstrapError) as ei:
        db.ensure("smart-writer-v2", "production", h.deps, repo_root=REPO)
    assert "pooler" in ei.value.step
    assert h.sql_runs == []
    _assert_error_chain_scrubbed(ei.value)


def test_ensure_sql_failure_names_step_not_values() -> None:
    h = Harness(fail_run_sql=True)
    with pytest.raises(db.DbBootstrapError) as ei:
        db.ensure("smart-writer-v2", "production", h.deps, repo_root=REPO)
    assert ei.value.step
    _assert_error_chain_scrubbed(ei.value)
    assert h.log == ["resolve", "probe", "run_sql"]


# ── CLI: no secret value ever reaches stdout / stderr / logs / GITHUB_* ───────

_SCENARIOS: dict[str, tuple[Callable[[], Harness], int]] = {
    "noop": (lambda: Harness(login_ok=True), 0),
    "applied": (lambda: Harness(), 0),
    "bad_password": (lambda: Harness(password=BAD_PW), 1),
    "missing_password": (lambda: Harness(password=None), 1),
    "missing_token": (lambda: Harness(token=None), 1),
    "pooler_fails": (lambda: Harness(fail_resolve=True), 1),
    "pooler_fails_typed": (lambda: Harness(fail_resolve_typed=True), 1),
    "sql_fails": (lambda: Harness(fail_run_sql=True), 1),
    "final_probe_fails": (lambda: Harness(fail_final_probe=True), 1),
}


@pytest.fixture
def gha_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    env_file = tmp_path / "github_env"
    out_file = tmp_path / "github_output"
    env_file.write_text("", encoding="utf-8")
    out_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("GITHUB_ENV", str(env_file))
    monkeypatch.setenv("GITHUB_OUTPUT", str(out_file))
    return env_file, out_file


@pytest.mark.parametrize("scenario", sorted(_SCENARIOS))
def test_cli_never_prints_or_logs_secret_values(
    scenario: str,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    gha_files: tuple[Path, Path],
) -> None:
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    caplog.set_level(logging.DEBUG)
    make, want_code = _SCENARIOS[scenario]
    h = make()
    code = db.main(
        ["ensure", "--app-id", "smart-writer-v2", "--environment", "production"],
        deps=h.deps,
    )
    assert code == want_code
    cap = capsys.readouterr()
    _assert_no_secrets(cap.out)
    _assert_no_secrets(cap.err)
    _assert_no_secrets(caplog.text)
    assert "::add-mask::" not in cap.out
    for f in gha_files:
        assert f.read_text(encoding="utf-8") == ""
    if want_code == 1:
        assert cap.err.strip(), "failure must name the failing step on stderr"


@pytest.mark.parametrize("scenario", sorted(_SCENARIOS))
def test_cli_under_actions_masks_and_only_mask_lines_carry_values(
    scenario: str,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    gha_files: tuple[Path, Path],
) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    caplog.set_level(logging.DEBUG)
    make, want_code = _SCENARIOS[scenario]
    h = make()
    code = db.main(
        ["ensure", "--app-id", "smart-writer-v2", "--environment", "production"],
        deps=h.deps,
    )
    assert code == want_code
    cap = capsys.readouterr()
    _assert_no_secrets(cap.out, allow_mask_lines=True)
    _assert_no_secrets(cap.err)
    _assert_no_secrets(caplog.text)
    for f in gha_files:
        assert f.read_text(encoding="utf-8") == ""
    masks = {
        line[len("::add-mask::") :]
        for line in cap.out.splitlines()
        if line.startswith("::add-mask::")
    }
    if scenario != "missing_token":
        assert TOKEN in masks
        stored_pw = h.vault.store.get(_tup(PROD_PW_REF))
        if stored_pw:
            assert stored_pw in masks


def test_cli_dry_run_prints_names_only(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("INFISICAL_TOKEN", raising=False)
    code = db.main(
        ["ensure", "--app-id", "smart-writer-v2", "--environment", "production", "--dry-run"],
        deps=_raising_deps(),
    )
    assert code == 0
    out = capsys.readouterr().out
    for name in (
        "swv2_prod",
        "swv2_prod_langgraph",
        "swv2_prod_queue",
        "SMART_WRITER_V2_DB_PASSWORD",
        "SUPABASE_ACCESS_TOKEN",
        REF,
        "5432",
    ):
        assert name in out
    assert "://" not in out


def test_cli_dry_run_needs_no_token(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("INFISICAL_TOKEN", raising=False)
    code = db.main(
        ["ensure", "--app-id", "smart-writer-v2", "--environment", "staging", "--dry-run"]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "swv2_staging" in out
    assert "SMART_WRITER_V2_STAGING_DB_PASSWORD" in out


def test_cli_live_without_infisical_token_fails_closed(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("INFISICAL_TOKEN", raising=False)
    code = db.main(["ensure", "--app-id", "smart-writer-v2", "--environment", "production"])
    assert code == 1
    assert "INFISICAL_TOKEN" in capsys.readouterr().err


def test_cli_unknown_app_fails(capsys: pytest.CaptureFixture[str]) -> None:
    code = db.main(
        ["ensure", "--app-id", "research-auditor", "--environment", "production", "--dry-run"],
        deps=_raising_deps(),
    )
    assert code == 1
    assert "deploy/db" in capsys.readouterr().err


def test_cli_rejects_unknown_environment() -> None:
    with pytest.raises(SystemExit) as ei:
        db.main(
            ["ensure", "--app-id", "smart-writer-v2", "--environment", "prod", "--dry-run"],
            deps=_raising_deps(),
        )
    assert ei.value.code == 2


_WRITER_APIS = frozenset(
    {
        "upsert_variables",
        "upsert_secret",
        "create_secret",
        "update_secret",
        "delete_secret",
        "RuntimeTarget",
    }
)
_WRITER_IMPORT_MODULES = frozenset(
    {
        "secrets_sync.target_railway",
        "secrets_sync.target_vercel",
    }
)


def test_no_infisical_write_code() -> None:
    """Narrow AST/import check against known writer APIs (not a prose substring scan)."""
    path = REPO / "scripts" / "db_bootstrap.py"
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in _WRITER_APIS:
            hits.append(node.attr)
        elif isinstance(node, ast.Name) and node.id in _WRITER_APIS:
            hits.append(node.id)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod in _WRITER_IMPORT_MODULES:
                hits.append(mod)
            hits.extend(alias.name for alias in node.names if alias.name in _WRITER_APIS)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in _WRITER_IMPORT_MODULES or alias.name in _WRITER_APIS:
                    hits.append(alias.name)
    assert hits == [], f"db_bootstrap.py uses writer APIs: {hits}"
    assert not re.search(r"\.(post|patch|put)\([^)]*infisical", src, flags=re.IGNORECASE)
    assert not (REPO / "scripts" / "secrets_sync" / "vault_infisical_writer.py").exists()


def test_live_main_builds_read_only_vault_and_ensure_only_reads_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live wiring (no injected deps): the vault ``main`` builds is the existing Infisical
    reader, and the real ``ensure`` touches nothing on it but ``get_secrets``."""
    oidc = "oidc-dummy-not-a-secret-value"
    backing = Harness(login_ok=True)
    inits: list[dict[str, Any]] = []
    accessed: list[str] = []

    class ReadOnlyBackendSpy:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            inits.append(dict(kwargs, _args=args))

        def __getattribute__(self, name: str) -> Any:
            if not name.startswith("_"):
                accessed.append(name)
            if name == "get_secrets":
                return backing.vault.get_secrets
            return object.__getattribute__(self, name)

    import secrets_sync.vault_infisical as vault_mod

    monkeypatch.setattr(vault_mod, "InfisicalCloudBackend", ReadOnlyBackendSpy)
    if hasattr(db, "InfisicalCloudBackend"):
        monkeypatch.setattr(db, "InfisicalCloudBackend", ReadOnlyBackendSpy)
    monkeypatch.setenv("INFISICAL_TOKEN", oidc)

    real_ensure = db.ensure
    built: list[db.EnsureDeps] = []

    def ensure_with_offline_collaborators(
        app_id: str, environment: str, deps: db.EnsureDeps, *, repo_root: Path = REPO
    ) -> db.EnsureResult:
        built.append(deps)
        offline = db.EnsureDeps(
            vault=deps.vault,
            make_runner=backing.make_runner,
            resolve_parts=backing.resolve_parts,
            probe=backing.probe,
        )
        return real_ensure(app_id, environment, offline, repo_root=repo_root)

    monkeypatch.setattr(db, "ensure", ensure_with_offline_collaborators)
    code = db.main(["ensure", "--app-id", "smart-writer-v2", "--environment", "production"])

    assert code == 0
    assert len(built) == 1
    assert isinstance(built[0].vault, ReadOnlyBackendSpy)
    assert len(inits) == 1 and inits[0].get("token") == oidc
    assert built[0].make_runner is db.management_api_runner
    assert built[0].resolve_parts is db.pooler_connection_parts
    assert built[0].probe is db.probe_login
    assert accessed and set(accessed) == {"get_secrets"}
    assert backing.log == ["resolve", "probe"]


def test_db_bootstrap_tests_workflow_runs_pg_tests_against_supabase_like_admin() -> None:
    wf = REPO / ".github" / "workflows" / "db-bootstrap-tests.yml"
    data = yaml.safe_load(wf.read_text(encoding="utf-8"))
    triggers = data.get("on", data.get(True))
    paths = triggers["pull_request"]["paths"]
    for owned in (
        "scripts/db_bootstrap.py",
        "scripts/test_db_bootstrap_pg.py",
        "scripts/ops_runtime_tag.py",
        "deploy/db/**",
        "apps/smart-writer-v2/db/bootstrap/**",
        ".github/workflows/ops-runtime.yml",
    ):
        assert owned in paths
    job = data["jobs"]["test"]
    assert job["services"]["postgres"]["image"] == "postgres:17"
    assert job["env"]["LAB_TEST_PG_ADMIN_URL"]
    text = wf.read_text(encoding="utf-8")
    assert "NOSUPERUSER CREATEROLE" in text
    assert "scripts/test_db_bootstrap_pg.py" in text
