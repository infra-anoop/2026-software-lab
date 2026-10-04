"""Real-Postgres tests for scripts/db_bootstrap.py (spec 002 T109).

Skipped unless ``LAB_TEST_PG_ADMIN_URL`` is set. That login must look like
Supabase's ``postgres``: ``NOSUPERUSER CREATEROLE``, ``CREATE`` on its database,
and ``CREATE`` on schema ``public`` (to create the stand-in ``public.runs``).
Host auth must check passwords (scram) so a rotated password is really rejected.
CI setup: ``.github/workflows/db-bootstrap-tests.yml``.

``PsycopgRunner`` stands in for the Management API runner (same SQL, same
non-superuser rights). Local Postgres has no pooler, so the tests resolve
connection parts from the admin URL with the plain login name; the Supabase
``<login>.<ref>`` form is unit-tested. The tests share one database and drop
every ``swv2_*`` role and schema around each test.
"""

from __future__ import annotations

import os
import secrets
import sys
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import db_bootstrap as db
from secrets_sync.protocols import VaultRef

ADMIN_URL = os.environ.get("LAB_TEST_PG_ADMIN_URL", "").strip()
pytestmark = pytest.mark.skipif(
    not ADMIN_URL, reason="LAB_TEST_PG_ADMIN_URL not set (real-Postgres tests)"
)

psycopg = pytest.importorskip("psycopg") if ADMIN_URL else None
if psycopg is not None:
    from psycopg import errors as pg_errors

REPO = Path(__file__).resolve().parents[1]
APP = "smart-writer-v2"
PROJECT = "2026-software-lab"
TOKEN = "sbp_pg_tests_dummy_token"
TOKEN_KEY = (PROJECT, "production", "/", "SUPABASE_ACCESS_TOKEN")
PW_KEY = {
    "production": (PROJECT, "production", "/", "SMART_WRITER_V2_DB_PASSWORD"),
    "staging": (PROJECT, "production", "/", "SMART_WRITER_V2_STAGING_DB_PASSWORD"),
}
SWV2_SCHEMAS = tuple(
    f"swv2_{e}{suffix}" for e in ("prod", "staging") for suffix in ("", "_langgraph", "_queue")
)


class MemoryVault:
    def __init__(self) -> None:
        self.store: dict[tuple[str, str, str, str], str] = {
            TOKEN_KEY: TOKEN,
            PW_KEY["production"]: secrets.token_hex(24),
            PW_KEY["staging"]: secrets.token_hex(24),
        }

    def get_secrets(self, refs: list[VaultRef]) -> dict[str, str]:
        out: dict[str, str] = {}
        for r in refs:
            t = (r["project"], r["env"], r["path"], r["key"])
            if t in self.store:
                out[r["key"]] = self.store[t]
        return out

    def password(self, environment: str) -> str:
        return self.store[PW_KEY[environment]]


def local_parts(plan: db.LoginPlan, password: str) -> db.ConnParts:
    p = urlsplit(ADMIN_URL)
    return db.ConnParts(
        host=p.hostname or "localhost",
        port=p.port or 5432,
        user=plan.login,
        dbname=unquote(p.path.lstrip("/")) or "postgres",
        password=password,
    )


class Counting:
    """PsycopgRunner wrapped with a call counter."""

    def __init__(self) -> None:
        self.sql_runs = 0
        self.tokens: list[str] = []

    def make_runner(self, plan: db.LoginPlan, token: str) -> db.SqlRunner:
        self.tokens.append(token)
        inner = db.PsycopgRunner(ADMIN_URL)
        counter = self

        class Runner:
            def run(self, sql: str) -> None:
                counter.sql_runs += 1
                inner.run(sql)

        return Runner()


def _deps(vault: MemoryVault, counting: Counting | None = None) -> db.EnsureDeps:
    c = counting or Counting()
    return db.EnsureDeps(
        vault=vault,
        make_runner=c.make_runner,
        resolve_parts=lambda plan, _token, password: local_parts(plan, password),
        probe=db.probe_login,
    )


def _admin() -> psycopg.Connection:
    return psycopg.connect(ADMIN_URL, autocommit=True)


def _connect(parts: db.ConnParts) -> psycopg.Connection:
    return psycopg.connect(
        host=parts.host,
        port=parts.port,
        user=parts.user,
        password=parts.password,
        dbname=parts.dbname,
        autocommit=True,
    )


def _reset() -> None:
    with _admin() as conn:
        conn.execute("DROP TABLE IF EXISTS public.runs")
        for s in SWV2_SCHEMAS:
            conn.execute(f'DROP SCHEMA IF EXISTS "{s}" CASCADE')
        conn.execute("DROP ROLE IF EXISTS swv2_prod")
        conn.execute("DROP ROLE IF EXISTS swv2_staging")
        conn.execute("CREATE TABLE public.runs (id int)")


@pytest.fixture(autouse=True)
def clean_db() -> Iterator[None]:
    _reset()
    yield
    _reset()


def _plan(environment: str) -> db.LoginPlan:
    return db.load_plan(APP, environment, repo_root=REPO)


def _parts(vault: MemoryVault, environment: str) -> db.ConnParts:
    return local_parts(_plan(environment), vault.password(environment))


# ── Fixture fidelity ──────────────────────────────────────────────────────────


def test_admin_is_non_superuser_createrole_like_supabase() -> None:
    with _admin() as conn:
        row = conn.execute(
            "SELECT rolsuper, rolcreaterole FROM pg_roles WHERE rolname = current_user"
        ).fetchone()
    assert row == (False, True)


# ── ensure: prod, then staging, then no-op ────────────────────────────────────


def test_ensure_prod_then_staging_then_rerun_is_noop(capsys: pytest.CaptureFixture[str]) -> None:
    vault = MemoryVault()
    first = Counting()

    assert db.ensure(APP, "production", _deps(vault, first), repo_root=REPO).action == "applied"
    assert db.ensure(APP, "staging", _deps(vault, first), repo_root=REPO).action == "applied"
    assert first.sql_runs == 2
    assert first.tokens == [TOKEN, TOKEN]

    with _connect(_parts(vault, "staging")) as stg:
        assert stg.execute("SELECT current_user").fetchone() == ("swv2_staging",)
        stg.execute("CREATE TABLE swv2_staging.secret_rows (id int)")
    with _connect(_parts(vault, "production")) as prod:
        assert prod.execute("SELECT current_user").fetchone() == ("swv2_prod",)
        sp = prod.execute("SHOW search_path").fetchone()[0]
        assert sp.replace('"', "").split(",")[0].strip() == "swv2_prod"
        prod.execute("CREATE TABLE prod_rows (id int)")  # lands in swv2_prod via search_path
        assert prod.execute(
            "SELECT schemaname FROM pg_tables WHERE tablename = 'prod_rows'"
        ).fetchone() == ("swv2_prod",)
        with pytest.raises(pg_errors.InsufficientPrivilege):
            prod.execute("SELECT * FROM swv2_staging.secret_rows")
        with pytest.raises(pg_errors.InsufficientPrivilege):
            prod.execute("SELECT * FROM public.runs")
        with pytest.raises(pg_errors.InsufficientPrivilege):
            prod.execute("CREATE TABLE public.sneaky (id int)")
        prod.execute("DROP TABLE prod_rows")

    again = Counting()
    assert db.ensure(APP, "production", _deps(vault, again), repo_root=REPO).action == "noop"
    assert db.ensure(APP, "staging", _deps(vault, again), repo_root=REPO).action == "noop"
    assert again.sql_runs == 0

    cap = capsys.readouterr()
    for secret in (vault.password("production"), vault.password("staging"), TOKEN):
        assert secret not in cap.out and secret not in cap.err


def test_probe_leaves_no_tables_behind() -> None:
    vault = MemoryVault()
    db.ensure(APP, "production", _deps(vault), repo_root=REPO)
    with _admin() as conn:
        n = conn.execute(
            "SELECT count(*) FROM pg_tables WHERE schemaname = ANY(%s)",
            (list(SWV2_SCHEMAS),),
        ).fetchone()[0]
    assert n == 0


# ── rotation: the governor changes the vault value and re-pushes the tag ──────


def test_changed_vault_password_rotates_and_old_password_is_rejected() -> None:
    vault = MemoryVault()
    db.ensure(APP, "production", _deps(vault), repo_root=REPO)
    old = _parts(vault, "production")

    vault.store[PW_KEY["production"]] = secrets.token_hex(24)
    with pytest.raises(db.ProbeError):
        db.probe_login(_parts(vault, "production"), _plan("production"))

    c = Counting()
    assert db.ensure(APP, "production", _deps(vault, c), repo_root=REPO).action == "applied"
    assert c.sql_runs == 1

    with pytest.raises(psycopg.OperationalError):
        _connect(old).close()
    with _connect(_parts(vault, "production")) as conn:
        assert conn.execute("SELECT current_user").fetchone() == ("swv2_prod",)


# ── the probe ─────────────────────────────────────────────────────────────────


def _both() -> MemoryVault:
    vault = MemoryVault()
    db.ensure(APP, "production", _deps(vault), repo_root=REPO)
    db.ensure(APP, "staging", _deps(vault), repo_root=REPO)
    return vault


def test_probe_passes_for_correct_logins() -> None:
    vault = _both()
    db.probe_login(_parts(vault, "production"), _plan("production"))
    db.probe_login(_parts(vault, "staging"), _plan("staging"))


def test_probe_fails_as_probe_error_when_login_does_not_exist() -> None:
    vault = MemoryVault()
    with pytest.raises(db.ProbeError) as ei:
        db.probe_login(_parts(vault, "production"), _plan("production"))
    assert vault.password("production") not in str(ei.value)


def test_probe_catches_read_access_to_other_environment() -> None:
    vault = _both()
    with _admin() as conn:
        conn.execute("CREATE TABLE swv2_staging.leak (id int)")
        conn.execute("GRANT USAGE ON SCHEMA swv2_staging TO swv2_prod")
        conn.execute("GRANT SELECT ON swv2_staging.leak TO swv2_prod")
    with pytest.raises(db.ProbeError) as ei:
        db.probe_login(_parts(vault, "production"), _plan("production"))
    assert vault.password("production") not in str(ei.value)


def test_probe_catches_usage_on_other_environment_schema() -> None:
    vault = _both()
    with _admin() as conn:
        conn.execute("GRANT USAGE ON SCHEMA swv2_prod TO swv2_staging")
    with pytest.raises(db.ProbeError):
        db.probe_login(_parts(vault, "staging"), _plan("staging"))


def test_probe_catches_read_access_to_public_runs() -> None:
    vault = _both()
    with _admin() as conn:
        conn.execute("GRANT SELECT ON public.runs TO swv2_prod")
    with pytest.raises(db.ProbeError):
        db.probe_login(_parts(vault, "production"), _plan("production"))


def test_probe_catches_wrong_search_path() -> None:
    vault = _both()
    with _admin() as conn:
        conn.execute("ALTER ROLE swv2_prod SET search_path = public, swv2_prod")
    with pytest.raises(db.ProbeError):
        db.probe_login(_parts(vault, "production"), _plan("production"))


def test_ensure_fails_closed_when_over_grant_survives_bootstrap() -> None:
    vault = _both()
    with _admin() as conn:
        conn.execute("GRANT SELECT ON public.runs TO swv2_prod")
    with pytest.raises(db.DbBootstrapError) as ei:
        db.ensure(APP, "production", _deps(vault), repo_root=REPO)
    assert "probe" in ei.value.step
