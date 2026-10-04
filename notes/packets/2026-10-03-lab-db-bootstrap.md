# Work packet — lab database login bootstrap (ops tag)

## Meta

| Field | Value |
|-------|-------|
| Packet id | `2026-10-03-lab-db-bootstrap` |
| Status | ready |
| Feature / spec | `specs/002-swv2-durable-evals/` (P0 ops: T013 done, T018 amended, T109–T112) |
| Branch | `packet/2026-10-03-lab-db-bootstrap` |
| Agent mode | **background** |
| Spawn | `docs/agent-os/SPAWN_WORKER.md` + `_WORKER_PROMPT.md` |

## Goal

Creating or checking an app's per-environment database login in the shared lab Supabase project becomes one ops tag push. CI generates the password, runs `apps/smart-writer-v2/db/bootstrap/env_roles.sql`, builds the connection string, stores it in Infisical, and proves the login works and is isolated. No human hand-assembles a connection string.

Governor decision (2026-10-03): automate in the existing ops-tag pipeline instead of the six hand steps (copy SQL, edit, run, compose URL, store).

## Context to read first

- `AGENTS.md`, `docs/agent-os/SPAWN_WORKER.md`
- `notes/architect-backlog.md` A20/A21 (Infisical OIDC), A23/A24/A26 (ops tags), **A30** (vault naming), **A31** (shared Supabase project)
- `.github/workflows/ops-runtime.yml`, `scripts/ops_runtime_tag.py` (+ its tests), `scripts/infisical_oidc_login.py`, `scripts/secrets_sync/vault_infisical.py`, `scripts/secrets_sync/protocols.py`
- `apps/smart-writer-v2/db/bootstrap/env_roles.sql` + `README.md` (verified on Postgres 17 as a non-superuser CREATEROLE role, like Supabase's `postgres`)
- `specs/002-swv2-durable-evals/data-model.md` § Environments, `tasks.md` T013/T018/T109–T112

## Design (letter)

1. **Declaration** `deploy/db/smart-writer-v2.yml` (names only, no values):
   - `admin_vault_ref`: `{project: 2026-software-lab, env: production, path: /, key: SUPABASE_DB_ADMIN_URL}`. This is the session-pooler admin URL of project `2026-software-lab`, stored once by the governor and shared by every app (A30: plain name).
   - `bootstrap_sql: apps/smart-writer-v2/db/bootstrap/env_roles.sql`
   - per environment: `production → login swv2_prod, output vault_ref {env: production, path: /generated, key: SMART_WRITER_V2_DATABASE_URL}`, and `staging → login swv2_staging, output {env: production, path: /generated, key: SMART_WRITER_V2_STAGING_DATABASE_URL}`.
   - Generated credentials live under folder `/generated`, so the CI identity's write access can be limited to that folder.
2. **Tag kind `db/<app_id>/<environment>`** in `scripts/ops_runtime_tag.py`: parse, create and push like `sync`/`bootstrap`; valid only when `deploy/db/<app_id>.yml` exists. **`bootstrap/<app>/<env>`** runs the db step after provision and before sync, only when that file exists.
3. **`scripts/db_bootstrap.py ensure --app-id <id> --environment <env>`** (PEP 723 inline deps like the sibling scripts; psycopg 3 + httpx):
   - Read the admin URL and the existing output value from Infisical.
   - **Idempotent:** if the output value exists and the probe (step 6) passes with it, do nothing and exit 0.
   - Otherwise generate a password with `secrets.token_hex(24)` and render the SQL. Replace only the two `EDIT` assignments, after validating `env ∈ {prod, staging}` and the password with a 48-hex-character regex. Run it on the admin connection.
   - Compose the URL from the admin URL by replacing the user with `<login>.<project-ref>` (the ref is the suffix of the admin user `postgres.<ref>`) and the password; keep host, port 5432 and database.
   - Write it to Infisical: create the secret if missing, else update it. Create folder `/generated` if missing.
   - Probe as the new login: `current_user`; the `search_path` starts with the app schema; create and drop a temp table in the app schema; `SELECT` on the other environment's app schema raises `InsufficientPrivilege`; `SELECT` on `public.runs` raises `InsufficientPrivilege` when that table exists.
   - **Never print or log** the password, URLs or the admin URL. Use `::add-mask::` under GitHub Actions and never write them to `GITHUB_ENV`/`GITHUB_OUTPUT`. Errors name the step, never the value.
4. **Infisical write** support next to the reader in `scripts/secrets_sync/` (same auth: `INFISICAL_TOKEN` from OIDC). Confirm the API paths and bodies against Infisical's current docs; if you cannot reach them, stop and say so instead of guessing.
5. **Workflow** `ops-runtime.yml`: add `db/**` to the tag triggers and a "Database login (ensure)" step for `kind == db`, and for `kind == bootstrap` when `deploy/db/<app>.yml` exists. It runs before sync, with the existing OIDC token.

## Tests first (red before impl; T* review between)

- `scripts/test_db_bootstrap.py` (unit, no network):
  - URL composition, including rejecting an admin URL that is not `postgres.<ref>@…:5432`;
  - SQL render validation (bad env or non-hex password refused; the placeholder can never be emitted);
  - the idempotent no-op decision;
  - the write is create-or-update (fake `httpx.MockTransport`);
  - no secret value appears in captured stdout/stderr/logs on success or on each failure path.
- `scripts/test_ops_runtime_tag.py` (extend): the `db/<app>/<env>` parse/create, and rejection when `deploy/db/<app>.yml` is absent.
- `scripts/test_db_bootstrap_pg.py` (real Postgres, marked; skipped without `LAB_TEST_PG_ADMIN_URL`):
  - a non-superuser CREATEROLE admin like Supabase's;
  - ensure for prod, then staging; a re-run is a no-op;
  - the deleted-output case regenerates and rotates (old password rejected);
  - the probe catches a deliberately over-granted login.
  - CI: new workflow `.github/workflows/db-bootstrap-tests.yml` with a `postgres:17` service creating that admin role; runs on PRs touching the owned paths.

After the red tests are committed, write `notes/packets/2026-10-03-lab-db-bootstrap-test-review-t.md`, push, and **stop** with handoff "red; T* requested". The orchestrator spawns the reviewer and resumes you.

## Owned paths (may edit)

- `scripts/db_bootstrap.py`, `scripts/test_db_bootstrap.py`, `scripts/test_db_bootstrap_pg.py`
- `scripts/ops_runtime_tag.py`, `scripts/test_ops_runtime_tag.py`
- `scripts/secrets_sync/**` (add writer only; reader behaviour unchanged)
- `.github/workflows/ops-runtime.yml`, `.github/workflows/db-bootstrap-tests.yml` (new)
- `deploy/db/**` (new)
- `apps/smart-writer-v2/db/bootstrap/**` (README run section → "push the ops tag"; SQL only if a test proves a defect)
- `notes/packets/2026-10-03-lab-db-bootstrap*`, `specs/002-swv2-durable-evals/tasks.md` (tick T109–T112 only)

## Forbidden paths

- `deploy/secrets/schema.yaml` and its validator (factory slice A owns it during Wave 1; spec 002 T014 adds the runtime mapping later)
- `scripts/factory/**`, `bus/**`, other apps, rule/process paths (constitution, `AGENTS.md`, `.cursor/rules/`, `docs/agent-os/`)

## Parallelism

| Field | Value |
|-------|-------|
| `[P]` tasks in this packet | no (one worker) |
| Disjoint from other in-flight packets? | yes (factory P0 owns `scripts/factory/**`, `factory.toml`, `bus/**`, `factory-gates.yml`, and only an `--ignore` line in `verify-source.yml`; this packet does not touch `verify-source.yml`) |

## Definition of Done

- [ ] Red tests committed first; T* review triaged in the review packet before implement
- [ ] `uv run --script` / `uv run pytest scripts/test_db_bootstrap.py scripts/test_ops_runtime_tag.py` green; pg tests green locally (`nix shell nixpkgs#postgresql_17`) and in the new workflow
- [ ] `uv run ruff check scripts/` clean
- [ ] Dry run documented: `scripts/db_bootstrap.py ensure --dry-run` prints planned names only (login, schemas, output key), no values
- [ ] PR opened with summary; no live tag pushed (the orchestrator pushes the first live tag after the governor's one-time steps)

## Out of scope

- Pushing a live `db/**` or `bootstrap/**` tag
- Explicit rotation command (rotation today = delete the output secret, then re-run)
- Runtime mapping into Railway (spec 002 T014/T020)
- Changing any `public` table or the `smart-writer-prod` / `research-auditor-prod` projects

## Governor locks required

| Lock | Value or `blocked until human` |
|------|--------------------------------|
| Automate DB login bootstrap via ops tag | locked 2026-10-03 (governor: "automate") |
| `SUPABASE_DB_ADMIN_URL` stored in Infisical | `blocked until human` (needed for the live run only, not for this packet's DoD) |
| CI identity can write Infisical folder `/generated` | `blocked until human` (live run only) |

## Fidelity (constitution §I — required)

| Lock | fidelity | How this packet honors it |
|------|----------|---------------------------|
| A31 shared project, own schemas/login, never `public` | letter | Runs the committed `env_roles.sql` unchanged; the probe proves isolation |
| A30 naming | letter | Plain `SUPABASE_DB_ADMIN_URL` (shared); app+env prefix for the outputs |
| A20/A21 OIDC, no GitHub repo secrets | letter | Reuses the `ops-runtime.yml` OIDC token; adds no repo secrets |
| Cattle (A23/A26) | letter | Declaration in git; tag-triggered; idempotent |

## Stop / escalate if

- The Infisical write API cannot be confirmed
- Any test needs a live Supabase or Infisical call
- DoD needs paths outside Owned paths

## Handoff notes (agent fills at end)

- What changed:
- Tests run:
- Open questions for human:
