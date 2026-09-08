"""Contract: committed SQL matches SupabaseRepo + save_to_supabase keys (no live DB)."""

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_RUNS_TURNS_SQL = _REPO_ROOT / "db" / "supabase" / "runs_turns.sql"
_RESEARCH_AUDITS_SQL = _REPO_ROOT / "db" / "supabase" / "research_audits.sql"

# Keys Python writes — modules/lab_shared/src/lab_shared/db/supabase_repo.py
_RUNS_INSERT_KEYS = ("topic", "status", "created_at")
_RUNS_UPDATE_KEYS = ("status", "completed_at", "final_output", "error", "trace_id")
_TURNS_INSERT_KEYS = (
    "run_id",
    "step",
    "agent",
    "input",
    "output",
    "ok",
    "error",
    "created_at",
)

# Keys Python writes — apps/research-auditor/app/main.py → save_to_supabase
_RESEARCH_AUDITS_INSERT_KEYS = (
    "title",
    "findings",
    "verdict",
    "critique",
    "iterations",
)


def test_runs_turns_sql_exists_and_matches_repo_columns() -> None:
    assert _RUNS_TURNS_SQL.is_file(), f"missing {_RUNS_TURNS_SQL}"
    sql = _RUNS_TURNS_SQL.read_text(encoding="utf-8").lower()

    assert "create table if not exists public.runs" in sql
    assert "create table if not exists public.turns" in sql
    assert "gen_random_uuid()" in sql
    assert "on delete cascade" in sql
    assert "check (status in ('running', 'completed', 'failed'))" in sql

    for col in (*_RUNS_INSERT_KEYS, *_RUNS_UPDATE_KEYS, "id"):
        assert col in sql, f"runs column missing from SQL: {col}"

    for col in (*_TURNS_INSERT_KEYS, "id"):
        assert col in sql, f"turns column missing from SQL: {col}"


def test_research_audits_sql_exists_and_matches_save_keys() -> None:
    assert _RESEARCH_AUDITS_SQL.is_file(), f"missing {_RESEARCH_AUDITS_SQL}"
    sql = _RESEARCH_AUDITS_SQL.read_text(encoding="utf-8").lower()

    assert "create table if not exists public.research_audits" in sql
    assert "gen_random_uuid()" in sql
    assert "created_at" in sql  # operator convenience; Python may omit

    for col in (*_RESEARCH_AUDITS_INSERT_KEYS, "id"):
        assert col in sql, f"research_audits column missing from SQL: {col}"
