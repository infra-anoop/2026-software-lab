# T* review — database-login bootstrap

## Verdict

**reject**

The suite is honestly red and has strong coverage of password validation, SQL rendering, Management API failures, idempotency, rotation, and isolation over-grants. It still permits two material violations: a `db/**` run may require Railway credentials before reaching the database step, and `probe_login` may omit the required current-user and own-schema write checks. Fix B1 and B2 before implementing against these tests.

## Findings

| ID | Severity | Tag | Locus | Finding | Suggested resolution |
|----|----------|-----|-------|---------|----------------------|
| B1 | Blocker | product | `scripts/test_ops_runtime_tag.py::test_ops_runtime_db_kind_runs_only_the_database_step`; `.github/workflows/ops-runtime.yml` | The test calls the run “only the database step” but does not inspect **Select Railway token**. That step is currently unconditional and fails when Railway credentials are absent, so a green implementation could still make `db/smart-writer-v2/staging` depend on Railway despite the accepted no-footprint/db-only behavior. | Assert that a `db` tag skips Railway-token selection as well as provision/sync/verify, while still running checkout, tooling, Infisical auth, and database ensure. |
| B2 | Blocker | product | `scripts/test_db_bootstrap_pg.py` probe cases | The tests do not fail if `probe_login` omits `current_user` validation or omits create/drop in the app schema. `test_probe_leaves_no_tables_behind` checks cleanup only, and the manual `prod_rows` operation is outside the probe. A lazy probe can satisfy every over-grant test while never proving the connected identity or own-schema write capability. | Add a wrong-plan/wrong-user negative case and a case that revokes `CREATE` (or `USAGE`) on the expected app schema and requires `ProbeError`. Keep the test capability-based; do not require a particular temporary-table SQL spelling. |
| B3 | Debate | process | `scripts/test_db_bootstrap.py::Harness`; CLI leakage matrix | The harness says collaborators put secrets in exceptions, but only the SQL-runner failure does. Resolve/pooler and final-probe fake failures carry no token/password, so blindly echoing those collaborator exceptions is not rejected by the CLI matrix. The real-PG authentication case helps, but does not cover every wrapper path. | Put sentinel secrets into resolve and probe exception details and assert the wrapped error, stdout, stderr, and logs scrub them. This changes test SNR, not product behavior. |
| B4 | Debate | process | `scripts/test_db_bootstrap.py::test_no_infisical_write_code` | The no-write check is a substring heuristic: it can reject harmless prose containing `upsert` while allowing a write through another helper/import. The read-only fake is useful but does not prove the live construction path uses only `VaultBackend.get_secrets`. | Replace or supplement the scan with a test of live dependency construction using a read-only backend spy and a narrow import/AST assertion against known writer APIs. Cloud identity scope remains an ops verification, not an auto-test claim. |
| B5 | Nit | process | Management API, red-state, and Postgres cases | **Strength:** the fake matches the published array-shaped pooler response and query endpoint, accepts `201`, selects `PRIMARY`, keeps `read_only` from becoming true, and proves non-2xx bodies containing rendered SQL are not echoed. The real-PG suite also exercises rotation and surviving over-grants with a non-superuser `CREATEROLE` admin. | Retain these cases. |
| B6 | Nit | process | `scripts/test_ops_runtime_tag.py` helper-level tests | Tests for private helper names `has_db_declaration` and `validate_db_app_environment` over-specify decomposition beyond the letter. The CLI and workflow behavior already provide the meaningful contract. This is not blocking, but it makes equivalent implementations unnecessarily fail. | Prefer behavior-level parse/dry-run tests; keep helper tests only if these names are intentionally a supported script API. |

## Test-encoded choices not stated by the letter

1. **DB tag runs only database work:** accept as the necessary meaning of the dedicated tag, subject to B1; Railway credential selection must also be skipped.
2. **DB validation uses only the DB declaration/environment:** accept. It enables staging before a secrets-schema row or Railway footprint exists and remains fail-closed on the declaration.
3. **`db_bootstrap=true|false` output and output-only conditions:** accept. This is a reasonable workflow contract; the evaluator usefully rejects unsupported expressions.
4. **Helper names and declaration shape:** accept `environments` and the declaration keys; B6 applies to private helper names.
5. **Read → validate → resolve → probe → SQL → probe; `noop|applied`:** accept. It directly supports no-call validation and idempotency.
6. **Errors may name keys but not values/body/collaborator text:** accept as the security-preserving interpretation; B3 asks for complete negative coverage.
7. **Actions masking, no mask lines locally, no `GITHUB_ENV`/`GITHUB_OUTPUT` values:** accept. Mask commands are the only permitted value-bearing stdout lines under Actions.
8. **Local PG uses plain login names and `PsycopgRunner`:** accept. Pooler-qualified users are separately unit-tested, and the same SQL runs with the intended admin privilege shape.
9. **Missing/wrong login becomes `ProbeError`:** accept. `ensure` needs that classification to distinguish “apply” from an unhandled client exception, and final probe failure still fails closed.

## Contract coverage

| Contract area | Evidence | Result |
|---------------|----------|--------|
| Declaration, A30 names, A31 project/schema boundaries | plan/declaration tests plus SQL and PG isolation tests | Covered; declaration intentionally red |
| 48-hex validation before API/database activity | render and ensure invalid/missing-password matrix | Covered |
| Pooler `PRIMARY`, API paths/auth, query non-2xx | `FakeSupabase` transport tests | Covered |
| Never expose values | API and CLI matrices | Partial — B3 |
| Idempotent no-op and rotation | harness no-op plus real-PG rotation | Covered |
| Probe identity, search path, own-schema write, cross-env/public isolation | PG probe tests | Partial — B2 |
| Dedicated DB-tag workflow and bootstrap ordering | ops-tag/workflow tests | Partial — B1 |
| Infisical read-only | fake protocol and source scan | Partial — B4 |
| No GitHub environment or database-step secrets/vars | workflow shape test | Covered |

## Adversarial positions

**Tests can go green while a lock fails.** An implementation can omit `current_user` and own-schema create/drop from `probe_login`, retain all tested search-path and over-grant checks, and pass. Separately, workflow conditions can make provision/sync/verify skip for `kind=db` while leaving Railway token selection unconditional; the tag then fails before database ensure when Railway credentials are absent. The suite would be right only if Railway credentials were guaranteed for every DB-only run and identity/write capability were proven elsewhere, neither of which the packet states.

**Tests over-constrain implementation.** The helper-name tests require two private functions even though declaration validation can cleanly live inside parse/build/CLI code. `EnsureResult` and the larger injected interface are frozen by the packet, so those are accepted; the extra ops helper decomposition is not needed to preserve governor-visible behavior. The suite would be right anyway if these helper names are deliberately treated as a stable script API.

## Commands run

- `uv run --with pytest --with pyyaml --with httpx --with 'psycopg[binary]' pytest scripts/test_db_bootstrap.py scripts/test_ops_runtime_tag.py -q` — unavailable in the bare shell (`uv: command not found`).
- Same command under `nix develop -c` — **88 failed, 27 passed**; no collection errors. Failures were the expected stubs, absent declaration/workflow changes, parser rejection, missing helper attributes, and assertions.
- Postgres 17 throwaway cluster via `nix shell nixpkgs#postgresql_17`, `lab_admin NOSUPERUSER CREATEROLE`, database/schema `CREATE`, and `LAB_TEST_PG_ADMIN_URL` — **10 failed, 1 passed**. Every failure reached a `NotImplementedError` call site; the admin-fidelity test passed.
- PG test without `LAB_TEST_PG_ADMIN_URL` and with imported dependencies — **11 skipped**. One preliminary dependency-adjustment run omitted `httpx` and failed collection; rerun with the packet dependencies collected cleanly.
- `nix develop -c uvx ruff check scripts/db_bootstrap.py scripts/test_db_bootstrap.py scripts/test_db_bootstrap_pg.py` — **passed**.

## Required edits before implementation

- Add the Railway-token skip assertion for `kind=db`.
- Add wrong-current-user and missing-own-schema-write probe negatives.
- Add secret-bearing resolve and probe collaborator failures to the CLI leakage matrix.
- Replace or strengthen the no-Infisical-write substring scan.

## Triage

**Decided by:** orchestrator, 2026-10-04. B1 and B2 are tagged product but only enforce the packet's already-locked letter (db-only tag; probe checks `current_user` and own-schema create/drop), so no new governor decision is needed. B3/B4 are process Debates, agent-adjudicated. All findings accepted; tests amended on `packet/2026-10-03-lab-db-bootstrap`; implementation still stubbed.

| ID | Disposition | Decided by | Resolution (where in the tests) |
|----|-------------|------------|---------------------------------|
| B1 | accept | orchestrator 2026-10-04 | `test_ops_runtime_db_kind_runs_only_the_database_step`: for `kind=db`, Checkout, Install uv, Parse and validate, Infisical auth and Database login (ensure) run; **Select Railway token**, Provision, Sync and Verify do not. `test_ops_runtime_sync_kind_skips_database_step` also requires Select Railway token to still run for `sync`. |
| B2 | accept | orchestrator 2026-10-04 | `test_db_bootstrap_pg.py`: `test_probe_fails_for_the_other_environments_login` (staging login vs prod plan); `test_probe_fails_for_a_lookalike_identity` (decoy login with the prod `search_path`, write on the prod schemas and no other access, so only an identity check catches it; the test proves the decoy really can write there); `test_probe_fails_when_login_cannot_write_own_app_schema[CREATE\|USAGE]` (plain `REVOKE` on the app schema). Capability-based: no SQL spelling is asserted. |
| B3 | accept | orchestrator 2026-10-04 | Harness resolve failures carry the token and password in a raw `RuntimeError` and in a typed `DbBootstrapError`; probe failures carry them in `ProbeError` text; the pooler fake's error body echoes the bearer header. New `_assert_error_chain_scrubbed` checks the raised error **and its `__cause__`/`__context__` chain** (what a traceback prints) on the pooler, SQL, final-probe and Management API paths. CLI leakage matrix gains `pooler_fails_typed` (9 scenarios × local/Actions). |
| B4 | accept | orchestrator 2026-10-04 | Prose `upsert` substring check dropped. `test_no_infisical_write_code` is an AST/import check against known writer APIs (`upsert_variables`, `RuntimeTarget`, `secrets_sync.target_*`, …). New `test_live_main_builds_read_only_vault_and_ensure_only_reads_it`: `main` without injected deps must build the existing `InfisicalCloudBackend` (spied) from `INFISICAL_TOKEN`, keep the live collaborator defaults, and the real `ensure` may access nothing on that vault but `get_secrets`. |
| B5 | keep | orchestrator 2026-10-04 | Management API, red-state and Postgres cases retained unchanged. |
| B6 | accept | orchestrator 2026-10-04 | Tests of `ort.has_db_declaration` / `ort.validate_db_app_environment` removed. Behavior covered by `parse`/`db --dry-run` CLI tests (declaration required; staging parses without a secrets-schema row) plus a contrast that `sync --dry-run` for staging still fails closed. |

### Post-triage runs (worker, 2026-10-04, `nix shell nixpkgs#uv nixpkgs#python312` / `nixpkgs#postgresql_17`)

- Unit (`test_db_bootstrap.py` + `test_ops_runtime_tag.py`): **90 failed, 28 passed**, no collection errors. Kinds: `NotImplementedError` 72, assertions 13, `OpsTagError` 3, argparse `SystemExit` 2.
- Real Postgres 17.11 (`lab_admin NOSUPERUSER CREATEROLE`, `CREATE` on the database and `public`, scram host auth): **14 failed, 1 passed** (admin fidelity); every failure is `NotImplementedError`. Without `LAB_TEST_PG_ADMIN_URL`: **15 skipped**.
- New fixture SQL checked by hand with psql as `lab_admin`: the decoy can connect, sees the prod `search_path`, creates and drops a table in `swv2_prod`, and is denied on `public.runs` and `swv2_staging`. `REVOKE CREATE` blocks `CREATE TABLE swv2_prod.t`; `REVOKE USAGE` still allows that `CREATE TABLE` but blocks lookup/drop. Reset drops every `swv2_*` role and schema.
- `uvx ruff check` on the three packet files: clean. `pytest scripts/ --ignore=scripts/factory` (as `verify-source.yml`): only this packet's red tests fail.
