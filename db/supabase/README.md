# Supabase schema (P6)

Versioned DDL for tables the Python apps already write. **Schema lives in git.**
Secrets stay in Railway / local `.env` — never commit them.

| File | Tables | Used by |
|------|--------|---------|
| `runs_turns.sql` | `public.runs`, `public.turns` | smart-writer + research-auditor (`SupabaseRepo`) |
| `research_audits.sql` | `public.research_audits` | research-auditor CLI (`save_to_supabase`) only |

Python source of truth (do not invent columns beyond these):

- `modules/lab_shared/src/lab_shared/db/supabase_repo.py` (shared `SupabaseRepo`)
- `apps/research-auditor/app/main.py` → `save_to_supabase`

## How to apply (operator step)

1. Open your Supabase project → **SQL Editor**.
2. Paste and run `runs_turns.sql` (both apps need these tables).
3. For research-auditor, also paste and run `research_audits.sql`.
4. Scripts are **idempotent** (`CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS`). Re-running does not drop data.
5. **Greenfield assumption:** if a table already exists with different columns, these scripts will **not** alter it. Fix drift manually or recreate in a fresh project.

## Environment

| Variable | Role |
|----------|------|
| `SUPABASE_URL` | Project URL |
| `SUPABASE_SECRET_KEY` | Service-role / secret key for **server-side** inserts |

Both are **optional**. If unset:

- `get_supabase_client()` returns `None`
- Orchestrator uses `NullRepo` (no `runs`/`turns` writes)
- Research Auditor `save_to_supabase` is a no-op
- Apps still run (CLI / HTTP)

`GET /ready` stays **OpenAI-only** — it does **not** require Supabase. Do not change that.

## One Supabase project per app (recommended)

Both apps use the **same table names** `runs` and `turns`. If both point at one Supabase project, traces share those tables (mixed `agent` / `topic` values).

**Recommended:** one Supabase project per app.

**Alternative:** accept a shared trace store. Do **not** rename tables in Python without a deliberate product change. An `app` discriminator column is out of scope for P6 (would require updating both `SupabaseRepo` classes and tests).

## Table notes

- **PK:** `uuid` with `DEFAULT gen_random_uuid()` (Supabase default; no `uuid-ossp` needed).
- **JSON:** `jsonb` (`final_output`, `input`/`output`, `findings`, `critique`).
- **Timestamps:** `timestamptz` (Python sends ISO strings; Postgres coerces).
- **`runs.status`:** `CHECK (status IN ('running', 'completed', 'failed'))`.
- **`turns.run_id`:** FK → `runs.id` with **`ON DELETE CASCADE`** (deleting a run removes its turns).
- **`research_audits`:** **unlinked** from `runs` — Python does not write a FK. Extra `created_at DEFAULT now()` is for operators (Python omit is fine).
- **RLS:** tables are for the **service role**. Enable RLS later if you expose them to anon/browser clients; not configured here.

## Layout why (Option A)

Shared DDL at monorepo root avoids per-app SQL drift. App-specific `research_audits` stays in its own file beside the shared script.
