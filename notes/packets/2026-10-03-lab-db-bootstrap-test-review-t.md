# Review packet — lab database login bootstrap: T* test review

## Meta

| Field | Value |
|-------|-------|
| Packet id | `2026-10-03-lab-db-bootstrap-test-review-t` |
| Status | ready |
| Gate | T* (spec 002 T110, on the T109 red tests) |
| Brief | `docs/agent-os/TEST_REVIEW_PROMPT.md` |
| Feature dir | `specs/002-swv2-durable-evals/` |
| Commit | `packet/2026-10-03-lab-db-bootstrap` @ `63a600c` (red tests + interface stubs) |
| Agent mode | spawned-reviewer, family ≠ author (author: Claude) |

## Context to read first

- `docs/agent-os/SPAWN_REVIEWER.md`, `docs/agent-os/TEST_REVIEW_PROMPT.md`
- `notes/packets/2026-10-03-lab-db-bootstrap.md` — the work packet. Its **Design (letter)** section (Management API + scoped token, governor-seeded passwords, read-only CI; revision `84812a4`) is the contract these tests must encode. Its Handoff notes are the worker's claims (**not evidence**; verify each yourself)
- `specs/002-swv2-durable-evals/PLAN_DELTA.md` § Database credentials; `tasks.md` P0 connection-secret delta note, T018, T109–T112; `data-model.md` § Environments
- `notes/architect-backlog.md` A20/A21, A23/A24/A26, **A30**, **A31**
- `apps/smart-writer-v2/db/bootstrap/env_roles.sql` (+ `README.md`) — the SQL the step runs unchanged
- Supabase Management API OpenAPI: `https://api.supabase.com/api/v1-json` — operations `v1-get-pooler-config` (`GET /v1/projects/{ref}/config/database/pooler`) and `v1-run-a-query` (`POST /v1/projects/{ref}/database/query`, beta)
- Finding IDs: if `specs/002-swv2-durable-evals/TEST_REVIEW.md` does not exist, start at **T1**; if it does, add a section for this slice and continue from the highest existing T id

## Artifacts under review

- Diff: `git diff origin/main...origin/packet/2026-10-03-lab-db-bootstrap -- scripts/ .github/`
- Tests:
  - `scripts/test_db_bootstrap.py` — unit, no network: declaration/plan, SQL render, connection parts, Management API calls against a fake transport (pooler host, query runner, non-2xx), the `ensure` decision (no-op / applied / each failure step, invalid or missing vault password before anything runs), CLI never leaks values (8 scenarios, locally and under Actions), dry-run, no Infisical write code
  - `scripts/test_db_bootstrap_pg.py` — real Postgres 17 with a non-superuser `CREATEROLE` admin; skipped without `LAB_TEST_PG_ADMIN_URL`
  - `scripts/test_ops_runtime_tag.py` — new `db/<app>/<env>` cases at the end of the file, plus `ops-runtime.yml` step-condition checks
  - `.github/workflows/db-bootstrap-tests.yml` — new CI job (`postgres:17` service + Supabase-like admin role)
- Frozen interfaces (stubs raise `NotImplementedError`) in `scripts/db_bootstrap.py`: `LoginPlan`, `ConnParts` (password kept out of `repr`), `SqlRunner`, `ManagementApiRunner`, `PsycopgRunner`, `EnsureDeps` (`vault`, `make_runner(plan, token)`, `resolve_parts(plan, token, password)`, `probe(parts, plan)`), `EnsureResult` (`noop` | `applied`), `DbBootstrapError` / `ProbeError` (with `.step`), `load_plan`, `render_sql`, `fetch_pooler_host`, `connection_parts`, `probe_login`, `ensure`, `main(argv, *, deps)`
- Commands (run them; record results). Use `nix develop -c …`; never `pip install`.
  - Unit: `uv run --with pytest --with 'psycopg[binary]>=3.2' --with 'pyyaml>=6' --with 'httpx>=0.27' pytest -q scripts/test_db_bootstrap.py scripts/test_ops_runtime_tag.py` — expect 88 failed / 27 passed (failures are `NotImplementedError`, missing `ort` attributes, today's parser or argparse rejecting `db`, or assertions; no collection errors)
  - Real Postgres: `nix shell nixpkgs#postgresql_17`, `initdb` a throwaway cluster under `/tmp` with `--auth-host=scram-sha-256`, then as the superuser: `CREATE ROLE lab_admin LOGIN NOSUPERUSER CREATEROLE PASSWORD '…'; GRANT CREATE ON DATABASE <db> TO lab_admin;` and in that database `GRANT CREATE ON SCHEMA public TO lab_admin;`. Export `LAB_TEST_PG_ADMIN_URL=postgresql://lab_admin:…@127.0.0.1:<port>/<db>` and run `pytest -q scripts/test_db_bootstrap_pg.py` — expect 10 failed / 1 passed; without the variable, 11 skipped
  - `uvx ruff check` on the three files listed in the new workflow's Ruff step

## Review questions (in addition to the brief)

1. Do the tests encode the packet's **Design (letter)** as written, or something weaker or different? In particular: Infisical read-only (token + env password), password validated against the 48-hex regex before anything runs; pooler host = `db_host` of the `PRIMARY` entry, missing entry fails closed; idempotent no-op when the probe passes with the vault password; only the two `EDIT` assignments replaced after env + password validation; the query endpoint's non-2xx fails loudly with the step name; probe again after the SQL and fail on error; the probe's checks (current user, `search_path` first entry, temp table in the app schema, `InsufficientPrivilege` on the other environment and on `public.runs`); connection by psycopg keyword parameters; never print/log the token or passwords, `::add-mask::` under Actions, nothing written to `GITHUB_ENV`/`GITHUB_OUTPUT`. Would a lazy implementation pass?
2. Judge each **test-encoded choice the letter does not state** (listed in the work packet's Handoff notes): accept, or finding. The ones most likely to matter: a `db/…` tag runs only the database step (no provision/sync/verify); the `db` tag does not require a secrets-schema entry for that environment; `parse` emits `db_bootstrap=true|false` and the workflow's `if:` conditions may use only step outputs; errors name the vault **key** (e.g. `SMART_WRITER_V2_DB_PASSWORD`) but never a value; collaborator exception text is never echoed (the fakes put secrets in it); the Management API error message carries the HTTP status but not the response body.
3. Is the Supabase fake faithful to the published OpenAPI (`SupavisorConfigResponse` entries, `V1RunQueryBody` keys `query` / `parameters` / `read_only`, `201` on success)? Is `read_only` correctly kept off for the bootstrap query?
4. Is the real-Postgres fixture a fair stand-in for running the SQL through the Management API as Supabase's `postgres` (non-superuser `CREATEROLE`, `CREATE` on the database and on `public`)? Do the over-grant cases (read on the other environment, `USAGE` on its schema, `SELECT` on `public.runs`, wrong `search_path`) and the rotation case really fail a correct-looking but weak probe?
5. Fidelity (§I): A31 (committed SQL unchanged, never `public`), A30 naming (`SUPABASE_ACCESS_TOKEN` plain; app / app+env prefixes for passwords), A20/A21 OIDC with no new repo secrets or variables, cattle (declaration in git, tag-triggered, idempotent), no Infisical writes.

## Owned paths (may edit) — on a new branch `review/lab-db-bootstrap-t` from `origin/packet/2026-10-03-lab-db-bootstrap`

- `specs/002-swv2-durable-evals/TEST_REVIEW.md` (new, or a new section if it exists; T* findings Blocker/Debate/Later/Nit with product/process tags, ≥ 1 Debate, ≥ 1 strength)

## Forbidden paths

- Everything else (no test or implementation fixes; report them as findings)

## Definition of Done

- [ ] `TEST_REVIEW.md` committed on `review/lab-db-bootstrap-t` and pushed
- [ ] Commands above run, results recorded in `TEST_REVIEW.md`
- [ ] Stop — the orchestrator triages; the governor adjudicates product-tagged Debates

## Fidelity (constitution §I)

| Lock | letter \| intent | Notes |
|------|------------------|-------|
| Reviewer family ≠ author family (author: Claude) | letter | |
| Reviewer isolation | letter | inputs are git artifacts only; no chat transcripts |
| No live Supabase / Infisical calls | letter | fakes and a local Postgres only |
