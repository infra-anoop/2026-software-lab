# Architect backlog

Owned here. Other agents get a scoped prompt; they do not pick from this list unless asked.

Last review: Section 3 fully closed — all won’t-do / accept residual (A11, A12, A14, A9, A10, A4, A5). A5 ops: deleted zombie Railway project `capable-miracle`.

## Decisions locked (platform secrets)

| ID | Decision |
|---|---|
| **A20** | **Vault = Infisical Cloud** (not self-host). Schema = versioned name/ref map in git; values in Infisical. Pattern **2b** (sync into runtime env; apps do not call vault per request). |
| **A20 / A21** | **Adapters:** `VaultBackend` + `RuntimeTarget` — do not hardcode Infisical↔Railway. Railway first; Vercel (and Doppler-as-backend later) are new adapters, not a rewrite. Infisical native platform sync is optional sugar, not the core. |
| **A23** | **Manual `workflow_dispatch` only** for secrets install/rotate. **Not** post-`v*` ship. **Not** auto on first app push. Code CI (verify/ship/deploy) stays image/health-only. |
| **A23** | Auth to vault: **GitHub OIDC → Infisical** machine identity (prefer no long-lived Infisical token in GitHub). Fail-closed if names ∉ A20 schema. |
| **A23** | **Fail-safe if provision missing:** sync must refuse when target footprint (project/service/env) does not exist — do not create it in A23. Creation is **A26**. |
| **Lifecycle** | **Bootstrap** (A26 provision → A23 sync → A24 verify) ≠ **rotate** (A23 only) ≠ **code deploy** (`v*` image pin). Conscious choice to init deploy infra. |
| **A11** | **`/ready` = OpenAI only.** `*_AUDIT_SECRET` stays optional for ready; unset still 503s `/audit`. Green ready ≠ audits work. Revisit only if platform checks must mean “audit product live.” |
| **A12** | **Leave hybrid A.** Settings + catalogs for declared/gate knobs; leftover `getenv` in SW agents/prompts/retrieval, Logfire `main.py`, `lab_shared` Supabase client accepted. Boy-scout on touch; no dedicated migration epic. |
| **A14** | **Keep P6 schema knobs.** No `UNIQUE(run_id,step)`; `runs.status` CHECK stays `running`/`completed`/`failed`; greenfield `IF NOT EXISTS` only (recreate project if incompatible change). |
| **A9** | **Accept in-memory jobs.** `job_id` ephemeral (restart drops; not shared across replicas). Keep Railway replica count 1 for audit services. Multi-browser concurrency = process-local `JobRunner` (tune queue/concurrency/rate), not a shared queue. |
| **A10** | **Accept best-effort timeout.** `asyncio.wait_for` → job `timed_out`; in-flight OpenAI may still run. Prefer tuning timeout/iterations/concurrency over cancel plumbing. |
| **A4** | **Won’t-do / watch.** Keep dual start paths (flake `Cmd` + Railway YAML `start_command`; Railway wins). They match today; fix on drift. No CI equality assert, no single-source rewrite. |
| **A5** | **Tolerate residual as code; fix zombies in ops.** Pattern A image pin only. No git auto-deploy on lab services. Deleted leftover project `capable-miracle` / `Archived-research-auditor` (source of build-failure emails). Live project remains `2026-software-lab`. |

## Suggested execution order (remaining)

Work top-down. **Discuss** = lock a product/ops choice before coding. **Straight** = implement with the acceptance tests already on the row. Soft deps noted in Order notes.

| Order | ID | Mode | Order notes |
|---|---|---|---|
| — | *(none)* | — | Section 3 discusses complete. Next work is net-new, not this residual list. |

## Open — architect / operator

| ID | Item | Why it stays here | Status |
|---|---|---|---|
| — | *(none)* | Section 3 residuals accepted or closed. | — |

## Handed to other agents (not tracked as architect work)

| ID | Item |
|---|---|
| — | (none) |

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
| A20 | `deploy/secrets/schema.yaml` + `validate_secrets_schema.py` (Infisical Cloud refs; ⊆ Settings; hooked in verify-source). |
| A25 | `LOGFIRE_TOKEN` required in schema for every app×env; enforced by validator. |
| A22 | Supabase DDL apply CLI (`scripts/apply_supabase_ddl.py`); dry-run file order; apply one txn/file; verify-source dry-run + `pytest scripts/` + `services: postgres`; harness-only `pgcrypto`. Greenfield `IF NOT EXISTS` only. |
| A26 | Platform provision CLI (`scripts/provision_runtime.py`) + `provision-runtime.yml` (`workflow_dispatch` only). Idempotent Railway ensure project→env→service from deploy YAML; dry-run/apply mutually exclusive; mocked create+exists tests; no live Railway in CI. Empty service until deploy pins image. |
| A21 | `scripts/secrets_sync/` + `sync_runtime_secrets.py`: `VaultBackend` / `RuntimeTarget`; Infisical + Railway adapters; Vercel stub; dry-run names only; mocked GraphQL/HTTP tests (16). Fail closed on missing footprint. |
| A23 | `sync-runtime-secrets.yml` (`workflow_dispatch` only): dry-run → A21 CLI; apply → Railway token + Infisical OIDC (`infisical_oidc_login.py` → `INFISICAL_TOKEN`) or non-preferred `secrets.INFISICAL_TOKEN`; exit 2 on missing footprint. |
| A24 | `verify_runtime_bootstrap.py` + `verify-runtime-bootstrap.yml`: read-only footprint + required names (YAML ∪ schema); `variables` query names-only; exit 2 footprint miss; mocked tests. |
| A8 | Won’t-do (2-app lab): offline boot stays default image only. Cmd-check all apps + per-app ship + prod smoke cover the P2 failure mode. |
| A11 | Won’t-do: `/ready` stays OpenAI-only; `*_AUDIT_SECRET` optional for ready, required for successful `/audit`. First-run “secret not configured” is vault seed/sync, not a ready-probe change. |
| A12 | Won’t-do: leave Settings/getenv hybrid A; boy-scout on touch; no dedicated migration epic. |
| A14 | Won’t-do: keep P6 knobs — no UNIQUE(run_id,step); tight status CHECK; greenfield only (recreate if schema must change). |
| A9 | Won’t-do: accept in-memory `JobRunner`; job_id ephemeral; keep single replica for `/audit`; multi-browser = tune concurrency/queue, not Redis/DB. |
| A10 | Won’t-do: accept `timed_out` without deep in-flight LLM cancel; tune timeout/iterations/concurrency instead. |
| A5 | Won’t-do as code epic: Pattern A only; ops deleted zombie project `capable-miracle` (Archived-research-auditor build emails). Live = `2026-software-lab`. |
| A4 | Won’t-do / watch: dual start paths stay; match by discipline; no CI equality assert until drift actually hurts. |
