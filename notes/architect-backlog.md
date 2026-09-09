# Architect backlog

Owned here. Other agents get a scoped prompt; they do not pick from this list unless asked.

Last review: Docs-min correction — reclaim automated (A18/A19); prose trimmed (A7/A15). Next discuss: A20 vault product.

## Suggested execution order (remaining)

Work top-down. **Discuss** = lock a product/ops choice before coding. **Straight** = implement with the acceptance tests already on the row. Soft deps noted in Order notes.

| Order | ID | Mode | Order notes |
|---|---|---|---|
| 1 | A20 | Discuss | **Which vault product?** (Doppler / Infisical / 1Password Connect / AWS SM). Schema shape after that choice |
| 2 | A25 | Straight | After A20: Logfire paths + manual→vault doc (no Logfire create-API required) |
| 3 | A22 | Straight | Supabase DDL CLI; unblocks repeatable persistence setup |
| 4 | A21 | Straight | Railway var upsert library (mocked); needs A20 name lists |
| 5 | A23 | Discuss | **When** sync runs (dispatch only vs post-ship); vault OIDC in GitHub |
| 6 | A24 | Straight | Read-only bootstrap verifier (mocked GraphQL) |
| 7 | A8 | Straight | Optional: offline boot more than default image — low urgency |
| 8 | A12 | Discuss | **Migrate all getenv now vs leave hybrid A?** Scope can sprawl |
| 9 | A11 | Discuss | **Should `/ready` require audit secret?** Changes operator meaning of ready |
| 10 | A14 | Discuss | UNIQUE(run_id,step)? loosen status CHECK? ALTER story for drift |
| 11 | A10 | Discuss | How hard to cancel in-flight OpenAI on timeout (cost vs complexity) |
| 12 | A9 | Discuss | Accept single-instance jobs vs real queue (Redis/DB) — architecture |
| 13 | A4 | Watch | Only act on drift; YAML≈CMD today |
| 14 | A5 | Discuss / watch | Tolerate git-connect risk vs spend to disable Railpack — policy |

## Open — architect / operator

| ID | Item | Why it stays here | Status |
|---|---|---|---|
| A4 | YAML start_command vs image CMD | P1 still sends YAML to Railway (Railway wins). YAML now matches flake CMD. Divergence is a prod footgun. | Residual — watch |
| A8 | CI offline boot is default image only | `verify-source` docker `--network none` /health is `nix build .#container` (first ship app). `validate-container` checks Cmd for all apps, not a live boot. | Open, low |
| A5 | Git-connect / Railpack residual | Dashboard can still source-build. toml comments are not a control. CI overwrite is. | Residual — watch |
| A9 | In-memory jobs | Job ids 404 after restart and across Railway replicas. Accepted P3 leftover until a real queue. | Residual — watch |
| A10 | Timeout vs in-flight OpenAI | Job `timed_out` may not cancel an already-running LLM call; tokens can still burn. | Residual — watch |
| A11 | `/ready` vs `/audit` secrets | `/ready` only requires `OPENAI_API_KEY`. `*_AUDIT_SECRET` is YAML **optional**; unset still 503s `/audit`. Green `/ready` ≠ audits work. | Residual — watch |
| A12 | Settings vs leftover getenv | Catalog helpers are on Settings. Call sites still getenv: SW `llm_settings` / prompts / orchestrator / retrieval; both `main.py` Logfire; `lab_shared` Supabase client. Hybrid A — migrate later. | Residual — watch |
| A14 | Supabase schema product knobs | P6: no `UNIQUE(run_id,step)`; closed `status` CHECK; greenfield `IF NOT EXISTS`. Live RA/SW persistence proven manually; knobs still product decisions. | Residual — watch |
| A20 | Canonical secret path schema | Stop sprinkling values without a map. Add versioned schema (e.g. `deploy/secrets/schema.yaml`) of vault paths per `app_id` × env × name (`OPENAI_API_KEY`, `*_AUDIT_SECRET`, `SUPABASE_*`, `LOGFIRE_TOKEN`, shared GHCR pull). Names must ⊆ Settings / Railway YAML catalogs. **Tests:** unit test every registry `deploy.enabled` app has required paths; unknown names fail. No live vault. | Open |
| A21 | Railway variable upsert library | Deploy-time sync (pattern 2b), not runtime vault calls in the app. Library/CLI: given `app_id`, environment, and `{name: value}` from a vault adapter interface, upsert Railway service variables via API/GraphQL. **Tests:** httpx/GraphQL mocks — set/update/noop; never log values. Dry-run prints names only. Depends on A20 for name lists; can stub values in tests. | Open |
| A22 | Supabase DDL apply CLI | Replace dashboard paste for `db/supabase/*.sql`. CLI: `--app research-auditor\|smart-writer` chooses file set (SW: `runs_turns` only; RA: + `research_audits`); `--dry-run` prints ordered files; `--database-url` applies. **Tests:** dry-run file order; apply against ephemeral Postgres in CI (or testcontainers) asserts tables/columns exist. No Supabase account required for CI. | Open |
| A23 | Optional deploy job: sync secrets | Wire A21 into Actions (manual `workflow_dispatch` or post-ship). Job reads vault via OIDC/adapter (stub OK for first slice), syncs one `app_id` + `environment`. **Tests:** workflow job defined; entrypoint `--dry-run` in CI without real Railway/vault. Fail closed if names not in A20 schema. | Open |
| A24 | New-app bootstrap verifier | API check that a registry app is operable: Railway project/service/environment exist; required env *names* from deploy YAML present on the service (values redacted). **Tests:** mocked GraphQL fixtures for pass/fail; real run optional/manual. Does not create resources (read-only verify). | Open |
| A25 | Logfire token path in vault schema | Logfire provisioning APIs are thin; don’t block on full IaC. Extend A20 with `LOGFIRE_TOKEN` path; short doc: create token in UI once → vault → A21 sync. **Tests:** schema contains path for both apps; doc section exists. Spike note if a create-token API appears later. | Open, low |

## Handed to other agents (not tracked as architect work)

| ID | Item |
|---|---|
| *(none)* | Designer queue clear. Pick open A-items independently; A21→A23 and A20→A25 are soft sequences, not hard blockers to start. |

## Closed

| ID | Item |
|---|---|
| P1 | Railway runs GHCR digest, not a second builder. Fail-closed if image cannot be set. |
| P1-F1 | Distinct GraphQL probes: `serviceInstanceUpdate`/`serviceUpdate`, input type then mutation arg type (skip duplicate), `startCommand`/`start_command`. Fail-closed if `source` or start field missing. |
| P2 | Python deps installed at Nix image build (`uv sync --frozen --no-dev` → `/app/.venv`). Production image has no uv. CMD is uvicorn only. Offline `/health` proven for both apps; CI boots the default image with `--network none`. |
| P3 | `POST /audit` → 202 + `job_id`; `GET /jobs/{id}` snapshot only; in-process worker calls `run_workflow`. CLI unchanged. Auth + HTTP iteration cap 8 landed with this slice. |
| B5 | Gate in both apps (P3): `X-Audit-Secret`, HTTP cap 8, in-memory POST rate limit. Close-the-gaps: 422 on `max_iterations: 99`, 429 tests, RA 401 wrong secret + GET /jobs 401; docs call it a preview gate. `*_AUDIT_SECRET` stays YAML optional (`/ready` stays OpenAI-only). |
| P4-B8 | Typed Settings + `REQUIRED_ENV_NAMES`/`ALL_ENV_NAMES`; Railway YAML `env.required`/`optional`; `GET /ready` presence-only for `OPENAI_API_KEY`; `/health` unchanged; RA `RESEARCH_AUDITOR_MODEL`; validator hooked in `verify-source`. |
| P4-F1 | Validator `_err` → stderr + exit 1 (unit-tested). Named config helpers (`get_audit_secret`, timeouts, concurrency, rate limit, SW LLM retry/concurrency) read `get_settings()` via `_settings_str`. `os` gone from both `config.py`. |
| P7 | HTTP contract suites lock live OpenAPI + mapper fields (SW `stop_reason`/persist_*; RA title←`source_material_title`, findings←`executive_summary`). Fake `run_workflow` uses orchestrator names. No production code change. |
| P6 | Idempotent DDL at `db/supabase/` (`runs`/`turns` + RA `research_audits`); README apply steps + one-project-per-app; contract tests in both apps; `writer_runs` folklore fixed. Python unchanged. |
| P5 | `modules/lab_shared` (`jobs` + `db`); hard-cut app imports; uv path dep; `flake.nix` `mkAppTree` + container `/app` → `apps/<id>` symlink; registry `watch_paths`. |
| A16 | Durability commit: P5–P7 (+ SQL schema) pushed to `origin/main`. |
| A17 | Removed empty `apps/*/app/db/` leftover dirs after P5 hard-cut. |
| A1 | Pattern A `v0.5.0`: both apps digest-pinned, deployment SUCCESS, `/health`+`/ready` 200. |
| A2 | Railway GHCR pull proven (private packages; SUCCESS boots). |
| A15 | RA `REVIEW.md` stub: superseded; contracts are `main.py` / `http.py` (no annotated archaeology). |
| A7 | Deploy README points at `deploy.yml` for GraphQL pin/fail-closed; probe name list not duplicated in prose. |
| A19 | Disk guidance not in cheat-sheet; reclaim is automated (verify-source + Codespace postStart). |
| A18 | `scripts/disk_hygiene.py` dry-run/apply; `--apply` allowed in CI; wired to verify-source + postStart. |
| A13 | RA HTTP `test_audit_429_when_rate_limited` (sliding-window; distinct from queue-full). |
| A3 | Smoke GraphQL host `backboard.railway.com` (aligned with deploy). |
| A6 | Pin `yq` v4.53.6 in deploy + smoke; deploy `cancel-in-progress: false`. |
