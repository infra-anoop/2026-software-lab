# Research-Auditor App — Structural Review

> **Status (2026-09):** Several findings below are **historical**. Read this section before acting on B1–R8.

## Current status (overrides below where noted)

| ID | Original claim | Status now |
|---|---|---|
| **B1 / R1** | CLI skips `run_workflow` / never writes `runs`/`turns` | **Fixed.** `app/main.py` calls `run_workflow()`; CLI writes `runs`/`turns` via `RunRepo`, then `save_to_supabase` → `research_audits`. |
| **B2 / R2** | Duplicate Supabase clients | **Mostly fixed.** Shared `lab_shared.db.client.get_supabase_client()`; orchestrator uses `SupabaseRepo`/`NullRepo`; CLI still inserts `research_audits` separately (intentional summary table). |
| **HTTP / R8** | HTTP is health-only | **Fixed.** `POST /audit` (202 jobs), `GET /jobs/{id}`, `/ready`, form UI, audit secret gate. |
| **B6 / R7** | Agents `sys.exit` on missing key at import | **Fixed.** Key enforced at CLI/`/ready`/`/audit`; agents importable without exit. |
| **Persistence split** | Form vs CLI | **By design:** HTTP → `runs`/`turns` only; CLI also writes `research_audits`. See `db/supabase/README.md`. |

Remaining items below may still be useful hygiene (requirements.txt, naming, scripts) but are **not** the old “CLI has no run/turn persistence” bug.

---

## 1. Organization score: 6.5 / 10 (original review)

### What works well
Clear split: `app/` (agents, db → now `lab_shared`, orchestrator, entrypoints), `tests/` (unit vs integration), scripts for one-off/legacy.
Protocol-based persistence (`RunRepo`) with `NullRepo` and `SupabaseRepo`.
Pydantic models in `app/agents/models.py` define agent outputs in one place.
Single entrypoints: CLI = `app.main`, HTTP = `app.entrypoints.http`.

### What held the score back (at time of writing)
Two persistence paths and CLI wiring inconsistency — **see status table**; HTTP was health-only — **fixed**.
Stale or misleading references (`requirements.txt` vs `pyproject.toml`, naming).
So structure was reasonable; several wiring issues have since been closed.

## 2. Bugs and issues (original; annotated)

**B1. CLI skips run/turn persistence** — ~~open~~ **FIXED** (see status).

**B2. Duplicate Supabase usage** — shared client now; `research_audits` remains CLI summary write.

**B3. Stale comment in HTTP entrypoint** — verify/`http.py` header; fix if still wrong.

**B4. Unit test imports the wrong “app”** — package vs graph naming; low priority.

**B5. requirements.txt vs pyproject.toml** — prefer uv + `pyproject.toml`; treat requirements as legacy if still present.

**B6. Harsh agent import-time behavior** — ~~open~~ **FIXED** (see status).

## 3. Recommended improvements (original; annotated)

**R1.** Unify CLI with `run_workflow` — **done**.

**R2.** Single Supabase story — shared client done; optional: move `research_audits` into repo layer later.

**R3–R7, R9–R10.** Naming, `__init__.py`, requirements, pyproject name, scripts, typing — backlog/hygiene if still open.

**R8.** Clarify deployment contract — **superseded**: document jobs API + `/ready` + audit secret (see `docs/ARCHITECTURE.md` / deploy README), not “health-only.”

## Summary

Original score reflected inconsistent persistence and a health-only HTTP surface. **CLI `run_workflow` + HTTP audit jobs are in place.** Treat this file as an annotated archive plus the status table at the top — do not re-open B1 as if the CLI still skipped `runs`/`turns`.
