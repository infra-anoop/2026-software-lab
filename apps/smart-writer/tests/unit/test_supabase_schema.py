"""Contract: committed SQL matches SupabaseRepo insert/update keys (no live DB)."""

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_RUNS_TURNS_SQL = _REPO_ROOT / "db" / "supabase" / "runs_turns.sql"

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
