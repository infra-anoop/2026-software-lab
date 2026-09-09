# Mission: A22 — Supabase DDL apply CLI

You are a senior engineer in the 2026-software-lab monorepo. Close **A22 only**.

Cattle rule: **schema lives in git; apply is a scripted, testable control** — not a cheat-sheet that says “paste into the SQL editor.”

## Why this exists

P6 already committed idempotent DDL:

| File | Tables | Apps |
|------|--------|------|
| `db/supabase/runs_turns.sql` | `runs`, `turns` | both |
| `db/supabase/research_audits.sql` | `research_audits` | research-auditor CLI only |

Operators still apply by dashboard paste (`db/supabase/README.md`). That does not scale and is not CI-proven. A22 = a CLI that prints the ordered file set (`--dry-run`) and can apply against a Postgres URL (`--database-url`).

## Scope (do)

1. **CLI** under `scripts/` (e.g. `scripts/apply_supabase_ddl.py`), `uv run`-able, PEP8 + type hints.
   - `--app research-auditor|smart-writer` (required)
   - File sets:
     - `smart-writer` → `runs_turns.sql` only
     - `research-auditor` → `runs_turns.sql` then `research_audits.sql` (order matters)
   - `--dry-run` → print absolute or repo-relative paths in apply order; exit 0; **no** DB connection
   - `--database-url` → apply files in order (transaction per file or one transaction — document in `--help` only, not a long README)
   - Refuse unknown `--app`; refuse apply without `--database-url` unless dry-run
2. **Tests**
   - Unit: dry-run file order for both apps (no Postgres)
   - Apply: against **ephemeral Postgres** in CI (GitHub `services: postgres` **or** testcontainers). After apply, assert tables/columns exist that Python expects (at least `runs`, `turns`; for RA also `research_audits`). Prefer inspecting `information_schema` / simple SQL — do not require a live Supabase account.
3. **Wire optional check:** if cheap, add a CI step that runs **dry-run only** for both apps (no secrets). Full apply test can live in `scripts/test_*.py` run by pytest in verify or a small job — follow existing `scripts/test_validate_deploy_env.py` / `uv run pytest scripts/...` patterns.
4. **Minimal prose:** do not expand `db/supabase/README.md` into a tutorial. At most replace the paste steps with one line pointing at the CLI. Prefer executable help text over new markdown.

## Out of scope (do not)

- Infisical / A20–A21–A23–A26 secrets or Railway provision
- Changing Python `SupabaseRepo` / app insert shapes
- Migrations/ALTER for drifted live tables (scripts stay greenfield `IF NOT EXISTS` as today)
- Renaming tables or adding `app` discriminator columns
- Requiring Supabase for `/ready`
- Drive-by refactors, new product features, large docs

## Acceptance

- [ ] `uv run scripts/apply_supabase_ddl.py --app smart-writer --dry-run` lists only `runs_turns.sql`
- [ ] `uv run scripts/apply_supabase_ddl.py --app research-auditor --dry-run` lists `runs_turns.sql` then `research_audits.sql`
- [ ] Unit tests cover dry-run order
- [ ] Apply path proven against ephemeral Postgres (tables present)
- [ ] No live Supabase credentials required for CI
- [ ] Architect backlog A22 can be marked closed when you finish (update `notes/architect-backlog.md` closed row only for A22)

## Report back

Short summary: files touched, how apply is tested, any residual risk (e.g. greenfield-only DDL).
