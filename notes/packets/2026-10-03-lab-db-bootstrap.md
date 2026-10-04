# Work packet — lab database login bootstrap (ops tag)

## Meta

| Field | Value |
|-------|-------|
| Packet id | `2026-10-03-lab-db-bootstrap` |
| Status | implemented — green; ready for PR (orchestrator opens it) |
| Feature / spec | `specs/002-swv2-durable-evals/` (P0 ops: T013 done, T018 amended, T109–T112) |
| Branch | `packet/2026-10-03-lab-db-bootstrap` |
| Agent mode | **background** |
| Spawn | `docs/agent-os/SPAWN_WORKER.md` + `_WORKER_PROMPT.md` |

## Goal

Creating or checking an app's per-environment database login in the shared lab Supabase project becomes one ops tag push. CI reads the password the governor stored in Infisical and runs `apps/smart-writer-v2/db/bootstrap/env_roles.sql` through the Supabase Management API with it. It then proves the login works and is isolated. Nobody hand-assembles a connection string, and CI never writes to Infisical.

Governor decisions (2026-10-03):
- automate in the existing ops-tag pipeline instead of hand steps;
- the Management API with a project-scoped access token instead of an admin connection string;
- the governor stores the two passwords in Infisical, so the automation only reads (no writer identity, no GitHub environment, no `/generated` folder).

## Context to read first

- `AGENTS.md`, `docs/agent-os/SPAWN_WORKER.md`
- `notes/architect-backlog.md` A20/A21 (Infisical OIDC), A23/A24/A26 (ops tags), **A30** (vault naming), **A31** (shared Supabase project)
- `.github/workflows/ops-runtime.yml`, `scripts/ops_runtime_tag.py` (+ its tests), `scripts/infisical_oidc_login.py`, `scripts/secrets_sync/vault_infisical.py`, `scripts/secrets_sync/protocols.py`
- `apps/smart-writer-v2/db/bootstrap/env_roles.sql` + `README.md` (verified on Postgres 17 as a non-superuser CREATEROLE role, like Supabase's `postgres`)
- `specs/002-swv2-durable-evals/data-model.md` § Environments, `tasks.md` T013/T018/T109–T112

## Design (letter)

1. **Declaration** `deploy/db/smart-writer-v2.yml` (names and non-secret parts only):
   - `supabase_project_ref: oguydvttuzbbiovvnxoj` (project `2026-software-lab`).
   - `access_token_vault_ref: {project: 2026-software-lab, env: production, path: /, key: SUPABASE_ACCESS_TOKEN}`. This is a Supabase personal access token scoped to that project only, with Database Read-Write and Connection Pooling Read; the governor stored it 2026-10-03.
   - `bootstrap_sql: apps/smart-writer-v2/db/bootstrap/env_roles.sql`
   - Per environment: `production → login swv2_prod, password_vault_ref {env: production, path: /, key: SMART_WRITER_V2_DB_PASSWORD}`, and `staging → login swv2_staging, password_vault_ref {…, key: SMART_WRITER_V2_STAGING_DB_PASSWORD}`. The governor seeds both with `openssl rand -hex 24`.
   - Connection parts: port `5432` (session pooler), database `postgres`, user `<login>.<project_ref>`. The host is read from the pooler-config API at run time and is not declared.
2. **Tag kind `db/<app_id>/<environment>`** in `scripts/ops_runtime_tag.py`: parse, create and push like `sync`/`bootstrap`; valid only when `deploy/db/<app_id>.yml` exists. **`bootstrap/<app>/<env>`** runs the db step after provision and before sync, only when that file exists.
3. **`scripts/db_bootstrap.py ensure --app-id <id> --environment <env>`** (PEP 723 inline deps like the sibling scripts; httpx + psycopg 3):
   - Read the access token and the env password from Infisical with the existing **read-only** OIDC token. Validate the password against a 48-hex-character regex and fail closed otherwise.
   - Get the session-pooler host: `GET https://api.supabase.com/v1/projects/{ref}/config/database/pooler` → `db_host` (the entry with `database_type: PRIMARY`).
   - **Idempotent:** probe (below) as `<login>.<ref>` with the vault password. If it passes, do nothing and exit 0.
   - Otherwise render the SQL, replacing only the two `EDIT` assignments after validating `env ∈ {prod, staging}` and the password. Run it with `POST https://api.supabase.com/v1/projects/{ref}/database/query` `{"query": …}`. This is a beta endpoint: any non-2xx fails loudly with the step name. Then probe again; a failure is an error.
   - Behind a `SqlRunner` protocol: `ManagementApiRunner` (production) and `PsycopgRunner` (the pg tests, which run the same SQL as a non-superuser CREATEROLE admin).
   - Probe as the login, connecting with psycopg keyword parameters (host, port, user, password, dbname; no URL, no escaping):
     - `current_user`;
     - the `search_path` starts with the app schema;
     - create and drop a temp table in the app schema;
     - `SELECT` on the other environment's app schema (when it exists) and on `public.runs` (when it exists) raises `InsufficientPrivilege`.
   - Rotation: the governor edits the Infisical value and re-pushes the tag. The probe fails with the old password, so the script re-runs the SQL, which sets the new one.
   - **Never print or log** the token or the passwords. Use `::add-mask::` under GitHub Actions and never write them to `GITHUB_ENV`/`GITHUB_OUTPUT`. Errors name the step, never the value.
4. **No Infisical write code.** Reuse `scripts/secrets_sync/vault_infisical.py` for reads, unchanged.
5. **Workflow** `ops-runtime.yml`: add `db/**` to the tag triggers and a "Database login (ensure)" step for `kind == db`, and for `kind == bootstrap` when `deploy/db/<app>.yml` exists. It runs before sync, with the existing OIDC token. No new GitHub environment or variables.
6. **App side (connection from parts), out of scope here:** spec 002's Settings compose the connection from the declared parts plus `SMART_WRITER_V2_DB_PASSWORD` (T014/T016 follow the rename recorded in `tasks.md`).

## Tests first (red before impl; T* review between)

- `scripts/test_db_bootstrap.py` (unit, no network):
  - connection-parts composition (`<login>.<ref>`, port 5432, host from a fake pooler response; a missing PRIMARY entry fails closed);
  - SQL render validation (bad env or non-hex password refused; the placeholder can never be emitted);
  - the idempotent no-op decision;
  - Management API calls (fake `httpx.MockTransport`): the right paths and bearer header; non-2xx fails with the step name; the token never appears in errors;
  - an invalid vault password (not 48-hex, or missing) fails closed before any SQL runs;
  - no secret value appears in captured stdout/stderr/logs on success or on each failure path.
- `scripts/test_ops_runtime_tag.py` (extend): the `db/<app>/<env>` parse/create, and rejection when `deploy/db/<app>.yml` is absent.
- `scripts/test_db_bootstrap_pg.py` (real Postgres, marked; skipped without `LAB_TEST_PG_ADMIN_URL`):
  - a non-superuser CREATEROLE admin like Supabase's;
  - ensure for prod, then staging; a re-run is a no-op;
  - rotation: a changed vault password makes the probe fail, the re-run sets it, and the old password is rejected;
  - the probe catches a deliberately over-granted login.
  - CI: new workflow `.github/workflows/db-bootstrap-tests.yml` with a `postgres:17` service creating that admin role; runs on PRs touching the owned paths.

After the red tests are committed, write `notes/packets/2026-10-03-lab-db-bootstrap-test-review-t.md`, push, and **stop** with handoff "red; T* requested". The orchestrator spawns the reviewer and resumes you.

## Owned paths (may edit)

- `scripts/db_bootstrap.py`, `scripts/test_db_bootstrap.py`, `scripts/test_db_bootstrap_pg.py`
- `scripts/ops_runtime_tag.py`, `scripts/test_ops_runtime_tag.py`
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

- [x] Red tests committed first; T* review triaged in the review packet before implement (accepted in round 3)
- [x] `uv run --script` / `uv run pytest scripts/test_db_bootstrap.py scripts/test_ops_runtime_tag.py` green; pg tests green locally (`nix shell nixpkgs#postgresql_17`) and in the new workflow (local green; the workflow runs on the PR)
- [ ] `uv run ruff check scripts/` clean (packet files clean; scripts-wide still has pre-existing findings in files outside this packet, see Round 0 notes)
- [x] Dry run documented (Handoff notes): `scripts/db_bootstrap.py ensure --dry-run` prints planned names only (login, schemas, output key), no values
- [ ] PR opened with summary; no live tag pushed (the orchestrator pushes the first live tag after the governor's one-time steps)

## Out of scope

- Pushing a live `db/**` or `bootstrap/**` tag
- Writing to Infisical (governor decision: read-only automation)
- Runtime mapping into Railway (spec 002 T014/T020)
- Changing any `public` table or the `smart-writer-prod` / `research-auditor-prod` projects

## Governor locks required

| Lock | Value or `blocked until human` |
|------|--------------------------------|
| Automate DB login bootstrap via ops tag | locked 2026-10-03 (governor: "automate") |
| Management API + scoped token `SUPABASE_ACCESS_TOKEN` | locked 2026-10-03; token stored by the governor |
| Passwords seeded by the governor; automation read-only | locked 2026-10-03; `SMART_WRITER_V2_DB_PASSWORD` / `SMART_WRITER_V2_STAGING_DB_PASSWORD` stored by the governor before the live run (not needed for DoD) |

## Fidelity (constitution §I — required)

| Lock | fidelity | How this packet honors it |
|------|----------|---------------------------|
| A31 shared project, own schemas/login, never `public` | letter | Runs the committed `env_roles.sql` unchanged; the probe proves isolation |
| A30 naming | letter | Plain `SUPABASE_ACCESS_TOKEN` (lab-shared); app and app+env prefixes for the passwords |
| A20/A21 OIDC, no GitHub repo secrets | letter | Reuses the `ops-runtime.yml` OIDC token; adds no repo secrets |
| Cattle (A23/A26) | letter | Declaration in git; tag-triggered; idempotent |

## Stop / escalate if

- The Supabase Management API paths cannot be confirmed from Supabase's docs
- Any test needs a live Supabase or Infisical call
- DoD needs paths outside Owned paths

## Handoff notes (agent fills at end)

**Status: T111 implemented; green; ready for PR** (2026-10-04). Merged `origin/review/lab-db-bootstrap-t-r3` (`--no-ff`; T* accepted, R3-1 to R3-3 confirmations); `origin/main` had not moved. T109–T111 ticked in `tasks.md`. No PR opened and no `db/*` or ops tag pushed (orchestrator: PR, merge on green, T112 live tags). No test was changed in this phase.

- What changed:
  - `scripts/db_bootstrap.py`: `ensure` reads the token and the environment password through the existing `InfisicalCloudBackend` (read-only, `INFISICAL_TOKEN` from the OIDC step), validates the 48-hex password, gets the `PRIMARY` `db_host` from the pooler-config API, probes as `<login>.<ref>` on 5432 / `postgres`, and only if that fails renders `env_roles.sql` (the two `EDIT` lines only, marked `-- set by scripts/db_bootstrap.py`) and posts it to the query endpoint, then probes again. The probe proves `current_user`, the `search_path` head, create/insert/select/drop in the app schema, no `CREATE` on `public`, no read on `public.runs`, and no access to the other environment's schemas or their tables. Write checks run in a transaction that is always rolled back. Every collaborator failure is re-raised `from None` with the step name and a value-scrubbed detail (raw exceptions: type name only). Management API errors carry only the HTTP status. `::add-mask::` is emitted only when `main` runs under `GITHUB_ACTIONS=true`.
  - `deploy/db/smart-writer-v2.yml`: the non-secret declaration (project ref, token ref, SQL path, port 5432, `postgres`, and per environment `sql_env`, `login`, `password_vault_ref`).
  - `scripts/ops_runtime_tag.py`: `db/<app>/<env>` kind (parse, `db` subcommand, dry-run, create/push) valid only when `deploy/db/<app>.yml` declares the environment (no registry or secrets-schema check); `parse` emits `db_bootstrap=true|false` for bootstrap tags. File mode set executable (ruff `EXE001`; it already had a shebang).
  - `.github/workflows/ops-runtime.yml`: `db/**` trigger; **Database login (ensure)** after Provision and before Sync, when `kind == 'db'` or `db_bootstrap == 'true'`, with only `INFISICAL_TOKEN` from the existing OIDC step; Select Railway token and Sync skip `db` tags.
- Tests run (Postgres 17.11 throwaway cluster, `lab_admin NOSUPERUSER CREATEROLE`, `CREATE` on the database, `CREATE ON SCHEMA public WITH GRANT OPTION`, scram host auth):
  - unit (`test_db_bootstrap.py` + `test_ops_runtime_tag.py`): 119 passed
  - real Postgres: 16 passed (three reruns stable); 16 skipped without `LAB_TEST_PG_ADMIN_URL`
  - `db-bootstrap-tests.yml` file set with Postgres: 151 passed; under `GITHUB_ACTIONS=true`: unit + pg 93 passed
  - `pytest scripts/ --ignore=scripts/factory` (as `verify-source.yml`): 209 passed, 18 skipped
  - `uvx ruff check` on `db_bootstrap.py`, both test files and `ops_runtime_tag.py`: clean
- Dry run (`uv run scripts/db_bootstrap.py ensure --app-id smart-writer-v2 --environment staging --dry-run`, no token needed): prints `login: swv2_staging`, the three schemas, `pooler user: swv2_staging.oguydvttuzbbiovvnxoj`, the project ref, `port: 5432  dbname: postgres`, `password key (read): SMART_WRITER_V2_STAGING_DB_PASSWORD [2026-software-lab/production/]`, `access token key (read): SUPABASE_ACCESS_TOKEN`, and the SQL path; no values.
- For the live run (T112):
  - Push with `nix develop -c uv run scripts/ops_runtime_tag.py db --app-id smart-writer-v2 --environment staging --push` (then `production`). No workflow inputs, no new GitHub environment, secrets or variables: the run uses the existing `vars.INFISICAL_MACHINE_IDENTITY_ID` OIDC identity. It needs read on Infisical project `2026-software-lab`, env `production`, path `/` (the same scope sync already reads) for `SUPABASE_ACCESS_TOKEN`, `SMART_WRITER_V2_STAGING_DB_PASSWORD` and `SMART_WRITER_V2_DB_PASSWORD`.
  - Expected log lines (Database login step), first run: `db_bootstrap: swv2_staging: probe failed; applying apps/smart-writer-v2/db/bootstrap/env_roles.sql`, `db_bootstrap: swv2_staging: bootstrap SQL applied`, `db_bootstrap: swv2_staging: probe passed after apply`, `ok: swv2_staging applied`. Re-push: `db_bootstrap: swv2_staging: probe passed; nothing to do`, `ok: swv2_staging noop`. Failures print `db_bootstrap error: <step>: <detail>` on stderr (steps: `declaration`, `vault read`, `password check`, `pooler host`, `probe`, `render sql`, `database query`, `probe after apply`).
  - A `database query` failure shows only the HTTP status (the body echoes the SQL with the password); read the failing statement in the Supabase logs. `probe after apply` lists the failed checks by name (for example `can create objects in public` if `PUBLIC` still has `CREATE` on `public`; the SQL itself also refuses that case).
  - Unverifiable offline, confirmed by the first live run: that the query endpoint runs as `postgres` (R3-3), and that the pooler-config `PRIMARY` `db_host` accepts session connections on 5432 as `swv2_<env>.<ref>`.
- Deviations from the packet: none in behavior. `render_sql` also replaces the trailing `-- EDIT` comment on the two assignment lines (required by the accepted test that both lines change, including `env = 'staging'`, which matches the template default). The DoD item "`ruff check scripts/` clean" holds for the packet's files only (pre-existing findings elsewhere).

### Round 2 triage

**Status: round 2 triaged; red; T* round-3 confirmation requested** (2026-10-04). Merged `origin/review/lab-db-bootstrap-t-r2` (`--no-ff`); triage recorded in `TEST_REVIEW_DB_BOOTSTRAP.md` § Triage (orchestrator, round 2); review packet has a Round 3 section. Still no implementation logic; no tag pushed; no PR.

- R2-1 (A31): new real-Postgres negative, a login granted `CREATE` on `public` fails `probe_login` and `ensure` fails closed. The pg admin now needs `CREATE ON SCHEMA public WITH GRANT OPTION` (CI workflow and fidelity test updated).
- R2-2: chain-scrub helper checks the rendered traceback and only unsuppressed context, so `raise … from None` is accepted; helper pinned by a self-test.
- Runs: unit 90 failed / 29 passed; Postgres 15 failed / 1 passed (16 skipped without the URL); scripts-wide 90 / 119 / 18 with all failures in this packet's tests; ruff clean.

### Round 1 triage

**Status: round 1 triaged; red; T* re-review requested** (2026-10-04). Merged `origin/main` and `origin/review/lab-db-bootstrap-t`; triage recorded in `specs/002-swv2-durable-evals/TEST_REVIEW_DB_BOOTSTRAP.md` § Triage (decided by: orchestrator 2026-10-04; B1–B4 and B6 accepted, B5 kept). Review packet updated with a Round 2 section. Still no implementation logic in `scripts/db_bootstrap.py`; no tag pushed; no PR.

- Test changes: Railway-token skip for `db` tags (B1); probe negatives for the other environment's login, a lookalike decoy identity, and `REVOKE CREATE` / `REVOKE USAGE` on the app schema (B2); secret-bearing resolve/pooler/probe failures with whole-error-chain scrubbing and a 9th CLI leakage scenario (B3); AST writer-API check plus live-wiring test with a read-only `InfisicalCloudBackend` spy (B4); helper-name tests replaced by `parse` / `--dry-run` behavior (B6).
- Runs: unit 90 failed / 28 passed; real Postgres 17.11 14 failed / 1 passed (15 skipped without the URL); ruff clean on the packet files; `pytest scripts/ --ignore=scripts/factory` 90 failed / 118 passed / 17 skipped, all failures in this packet's tests. Details in the Triage section's post-triage runs.
- New test-encoded choices for T* (listed in the review packet's Round 2): raw resolve exceptions wrapped as a `pooler` step; no secret anywhere in the error's cause/context chain; `main` builds `InfisicalCloudBackend(token=$INFISICAL_TOKEN)` at call time with live collaborator defaults.

### Round 0 (red tests, phase 1)

**Status: red; T* requested** (phase 1 = T109 red tests + T110 review packet `notes/packets/2026-10-03-lab-db-bootstrap-test-review-t.md`). Written against design revision `84812a4` (Management API, governor-seeded passwords, read-only CI). No implementation logic; no Infisical write code; no tag pushed.

- What changed:
  - Red tests: `scripts/test_db_bootstrap.py` (72), `scripts/test_db_bootstrap_pg.py` (11, real Postgres), 21 new cases in `scripts/test_ops_runtime_tag.py`; CI job `.github/workflows/db-bootstrap-tests.yml` (`postgres:17` + `lab_admin` NOSUPERUSER CREATEROLE).
  - Interface stub `scripts/db_bootstrap.py` (every function raises `NotImplementedError`): `LoginPlan`, `ConnParts`, `SqlRunner`, `ManagementApiRunner`, `PsycopgRunner`, `EnsureDeps`, `EnsureResult`, `DbBootstrapError`/`ProbeError`, `load_plan`, `render_sql`, `fetch_pooler_host`, `connection_parts`, `probe_login`, `ensure`, `main`.
  - Supabase Management API confirmed from Supabase's published OpenAPI (`https://api.supabase.com/api/v1-json`, 2026-10-04): `GET /v1/projects/{ref}/config/database/pooler` → array of `{database_type: PRIMARY|READ_REPLICA, db_host, db_port, pool_mode, …}`; `POST /v1/projects/{ref}/database/query` body `{query, parameters?, read_only?}`, `201` on success, marked Beta. Both bearer-authenticated.
  - Test-encoded choices the letter does not state (for T* to judge):
    1. A `db/<app>/<env>` tag runs only the database step (no provision / sync / verify), because `db/smart-writer-v2/staging` must work while staging has no secrets-schema entry or Railway footprint.
    2. `db` tag validation needs only `deploy/db/<app>.yml` with that environment declared; no secrets-schema or registry check.
    3. `ops_runtime_tag.py parse --github-output` emits `db_bootstrap=true|false` for bootstrap tags; the workflow's `if:` conditions use only `steps.tag.outputs.*` (the test evaluates them). The database step references no `secrets.*` / `vars.*` and the job gets no `environment:`.
    4. New names: `ort.has_db_declaration`, `ort.validate_db_app_environment`; declaration YAML keys `supabase_project_ref`, `access_token_vault_ref`, `bootstrap_sql` (letter) and `environments` (test-chosen; per-environment key names left to the implementation, read through `load_plan`).
    5. Order: read token + password → validate password → pooler host → probe → (SQL → probe). An invalid or missing password, or a missing token, stops before any call (the spy log stays empty). `EnsureResult.action` is `noop` or `applied`.
    6. Errors may name the vault key (`SMART_WRITER_V2_DB_PASSWORD`, `SUPABASE_ACCESS_TOKEN`) but never a value. Collaborator exception text is never echoed (the fakes put secrets in it). A Management API error carries the HTTP status but not the response body (Supabase echoes the failing SQL, which contains the password).
    7. Outside Actions no `::add-mask::` line appears; under Actions only `::add-mask::` lines may carry values, and the token and the password read from the vault must be masked (even a password that then fails validation).
    8. The pg tests run the same SQL through `PsycopgRunner` as the non-superuser admin, and resolve connection parts from the admin URL with the plain login name (local Postgres has no pooler); `<login>.<ref>` is unit-tested only. The pg admin also needs `CREATE` on schema `public` (to create the stand-in `public.runs`).
    9. A probe against a login that does not exist, or with a wrong password, must raise `ProbeError` (not a raw psycopg error), so `ensure` treats it as "apply".
- Tests run (local, Postgres 17.11 via `nix shell nixpkgs#postgresql_17`, `scram-sha-256` host auth, `lab_admin` NOSUPERUSER CREATEROLE):
  - `scripts/test_db_bootstrap.py`: 70 failed, 2 passed (workflow shape; no Infisical write code)
  - `scripts/test_db_bootstrap_pg.py`: 10 failed, 1 passed (admin fidelity); 11 skipped without `LAB_TEST_PG_ADMIN_URL`
  - `scripts/test_ops_runtime_tag.py`: 18 failed (new), 25 passed (22 existing + 3 new)
  - Failure kinds (98): `NotImplementedError` 78, assertions 12, missing `ort` attribute 3, today's parser rejecting the `db` kind (`OpsTagError`) 3, argparse rejecting the `db` subcommand 2. No collection errors. `pytest scripts/`: no other test regressed.
  - Checked by hand (psql as `lab_admin`) that `env_roles.sql` runs for both environments and that the pg fixture's cleanup works as the non-superuser admin with over-grants and login-owned tables present.
- Open questions for human: none blocking. Notes for the orchestrator:
  - The branch moved to the revised design while phase 1 ran; tests written against the first design were discarded (kept only on a local branch, never pushed).
  - DoD "`uv run ruff check scripts/` clean" cannot hold as written: ruff 0.16 defaults report 77 findings in existing scripts outside this packet. The new workflow runs ruff on this packet's new files only (clean); `test_ops_runtime_tag.py` keeps one existing `RUF100`.
  - `verify-source.yml` runs `pytest scripts/`, so these red tests turn it red on any PR from this branch until T111 lands. No PR opened in phase 1.
  - Live-run note (not a test): the pooler-config entry also carries `db_port` and `pool_mode`, which may describe the transaction pooler (6543). Per the letter, only `db_host` is used; the port is the declared session port 5432. T112's first live probe confirms that host + 5432 works.
