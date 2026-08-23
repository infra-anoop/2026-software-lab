# Architect backlog

Owned here. Other agents get a scoped prompt; they do not pick from this list unless asked.

Last review: P4-F1 accepted (2026-08-23). Validator failures print to stderr and exit 1; named config helpers share the Settings snapshot with `/ready`. First live Railway run is still unproven.

## Open — architect / operator

| ID | Item | Why it stays here | Status |
|---|---|---|---|
| A1 | First live deploy proof | Needs GitHub + Railway tokens this workspace does not have. Confirm UI shows `ghcr.io/…@sha256:…`, new deployment id, `ACTIVE`/`SUCCESS`. | Open |
| A2 | Railway GHCR pull credentials | Private packages: PAT `read:packages` on the service. GraphQL success ≠ container pull. | Open (ops gate on A1) |
| A3 | Smoke GraphQL host `.app` vs `.com` | Deploy moved to `backboard.railway.com`; smoke still `.app`. Hygiene, not P1. | Open |
| A4 | YAML start_command vs image CMD | P1 still sends YAML to Railway (Railway wins). YAML now matches flake CMD. Divergence is a prod footgun. | Residual — watch |
| A8 | CI offline boot is default image only | `verify-source` docker `--network none` /health is `nix build .#container` (first ship app). `validate-container` checks Cmd for all apps, not a live boot. | Open, low |
| A5 | Git-connect / Railpack residual | Dashboard can still source-build. toml comments are not a control. CI overwrite is. | Residual — watch |
| A6 | Deploy workflow hygiene | Unpinned `yq` (`releases/latest`); `cancel-in-progress: true` on deploy can abort a prod ship. | Open, low |
| A7 | README vs workflow mutation names | README still says only `serviceInstanceUpdate`; workflow also probes `serviceUpdate`, `startCommand` / `start_command`. | Open, low |
| A9 | In-memory jobs | Job ids 404 after restart and across Railway replicas. Accepted P3 leftover until a real queue. | Residual — watch |
| A10 | Timeout vs in-flight OpenAI | Job `timed_out` may not cancel an already-running LLM call; tokens can still burn. | Residual — watch |
| A11 | `/ready` vs `/audit` secrets | `/ready` only requires `OPENAI_API_KEY`. `*_AUDIT_SECRET` is YAML **optional**; unset still 503s `/audit`. Green `/ready` ≠ audits work. | Residual — watch |
| A12 | Settings vs leftover getenv | Catalog helpers are on Settings. Call sites still getenv: SW `llm_settings` / prompts / orchestrator / retrieval; both `main.py` Logfire; both `db/client.py` Supabase. Hybrid A — migrate later. | Residual — watch |

## Handed to other agents (not tracked as architect work)

| ID | Item |
|---|---|
| P7 | HTTP **result-field** lock vs live OpenAPI/mapper (e.g. stop_* / persist_* / RA research model attrs). Auth/cap/429/GET /jobs 401 are done (P3+B5). Mock `run_workflow`. No live LLM. |

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
