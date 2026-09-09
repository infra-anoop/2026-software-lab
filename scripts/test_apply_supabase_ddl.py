"""Tests for scripts/apply_supabase_ddl.py.

Dry-run / file-order tests need no Postgres.
Apply tests run only when DATABASE_URL is set (skip otherwise).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import apply_supabase_ddl as ddl  # noqa: E402

_HAS_DATABASE_URL = bool(os.environ.get("DATABASE_URL", "").strip())


def test_ddl_rel_paths_smart_writer() -> None:
    assert ddl.ddl_rel_paths("smart-writer") == ("db/supabase/runs_turns.sql",)


def test_ddl_rel_paths_research_auditor_order() -> None:
    assert ddl.ddl_rel_paths("research-auditor") == (
        "db/supabase/runs_turns.sql",
        "db/supabase/research_audits.sql",
    )


def test_ddl_rel_paths_unknown_app() -> None:
    with pytest.raises(ValueError, match="unknown --app"):
        ddl.ddl_rel_paths("not-an-app")


def test_dry_run_smart_writer(capsys: pytest.CaptureFixture[str]) -> None:
    code = ddl.main(["--app", "smart-writer", "--dry-run"])
    assert code == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["db/supabase/runs_turns.sql"]


def test_dry_run_research_auditor(capsys: pytest.CaptureFixture[str]) -> None:
    code = ddl.main(["--app", "research-auditor", "--dry-run"])
    assert code == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert out == [
        "db/supabase/runs_turns.sql",
        "db/supabase/research_audits.sql",
    ]


def test_dry_run_wins_over_database_url(capsys: pytest.CaptureFixture[str]) -> None:
    code = ddl.main(
        [
            "--app",
            "smart-writer",
            "--dry-run",
            "--database-url",
            "postgresql://should-not-connect/db",
        ]
    )
    assert code == 0
    assert capsys.readouterr().out.strip() == "db/supabase/runs_turns.sql"


def test_apply_without_url_refuses(capsys: pytest.CaptureFixture[str]) -> None:
    code = ddl.main(["--app", "smart-writer"])
    assert code == 1
    err = capsys.readouterr().err
    assert "database-url" in err.lower() or "dry-run" in err.lower()


def test_ddl_files_exist_on_disk() -> None:
    for app in sorted(ddl.KNOWN_APPS):
        paths = ddl.ddl_abs_paths(app)
        assert paths
        for path in paths:
            assert path.is_file()


def _table_columns(conn: object, table: str) -> set[str]:
    row = conn.execute(  # type: ignore[attr-defined]
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (table,),
    ).fetchall()
    return {r[0] for r in row}


@pytest.mark.skipif(not _HAS_DATABASE_URL, reason="DATABASE_URL not set")
def test_apply_smart_writer_creates_runs_turns() -> None:
    import psycopg

    url = os.environ["DATABASE_URL"]
    with psycopg.connect(url) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        conn.commit()

    assert ddl.main(["--app", "smart-writer", "--database-url", url]) == 0

    with psycopg.connect(url) as conn:
        runs_cols = _table_columns(conn, "runs")
        turns_cols = _table_columns(conn, "turns")
        assert {
            "id",
            "topic",
            "status",
            "created_at",
            "completed_at",
            "final_output",
            "error",
            "trace_id",
        } <= runs_cols
        assert {
            "id",
            "run_id",
            "step",
            "agent",
            "input",
            "output",
            "ok",
            "error",
            "created_at",
        } <= turns_cols


@pytest.mark.skipif(not _HAS_DATABASE_URL, reason="DATABASE_URL not set")
def test_apply_research_auditor_creates_research_audits() -> None:
    import psycopg

    url = os.environ["DATABASE_URL"]
    with psycopg.connect(url) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        conn.commit()

    assert ddl.main(["--app", "research-auditor", "--database-url", url]) == 0

    with psycopg.connect(url) as conn:
        assert {
            "id",
            "topic",
            "status",
            "created_at",
            "completed_at",
            "final_output",
            "error",
            "trace_id",
        } <= _table_columns(conn, "runs")
        assert {
            "id",
            "run_id",
            "step",
            "agent",
            "input",
            "output",
            "ok",
            "error",
            "created_at",
        } <= _table_columns(conn, "turns")
        assert {
            "id",
            "title",
            "findings",
            "verdict",
            "critique",
            "iterations",
            "created_at",
        } <= _table_columns(conn, "research_audits")
