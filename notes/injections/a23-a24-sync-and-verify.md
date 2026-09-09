# Mission: A23 + A24 — Secrets sync workflow + read-only bootstrap verify

You are a senior engineer in the 2026-software-lab monorepo. Close **A23 and A24 only**.

**TDD:** write failing tests first, then implement. Prefer mocked HTTP/GraphQL; no live Infisical or Railway required for CI green.

Cattle rule: **platform bootstrap ≠ code CI.** Secrets sync and verify are conscious `workflow_dispatch` (or local CLI) controls — never hooked to push/PR/`v*` ship.

## Why this exists

| ID | Gap |
|---|---|
| **A21** (done) | Library + CLI `scripts/sync_runtime_secrets.py` + `scripts/secrets_sync/` — vault → Railway upsert, dry-run names only, `FootprintMissingError` if project/service/env absent |
| **A26** (done) | Creates footprint; does not sync secrets |
| **A23** | Wire **Actions** (and thin CLI polish if needed) so operators can **install/rotate** secrets via dispatch; OIDC to Infisical; fail-closed on schema / missing footprint |
| **A24** | **Read-only** check: footprint exists + required env *names* present on the service (values never printed) |

Lifecycle (locked):

```text
A26 provision → A23 sync → A24 verify
     ≠
v* ship → digest pin → smoke
```

## Do not reopen (product locks)

1. **A23 trigger:** `workflow_dispatch` only. Not post-ship, not first-push, not `ci-cd-pipeline` tag path.
2. **A23 auth to vault:** prefer **GitHub OIDC → Infisical** machine identity (`id-token: write`). Avoid long-lived `INFISICAL_TOKEN` in GitHub secrets if OIDC works; if OIDC needs a one-line stub/doc for “wire identity id later,” dry-run path must still CI-green without live Infisical.
3. **A23 footprint:** on apply, if Railway project/service/env missing → **fail closed** (reuse A21 `FootprintMissingError` / exit code). Do **not** create resources (that is A26).
4. **A23 names:** only secrets listed in `deploy/secrets/schema.yaml` for that `app_id`×`environment`. Unknown names fail closed (A20/A21 already enforce).
5. **A24:** **verify only** — never create, never upsert secrets, never deploy images.
6. **Target v1:** Railway. Do not implement Vercel sync/verify beyond refusing or NotImplemented.
7. **Minimal prose:** workflow header comments + `--help` only. No cheat-sheet chapters.

## What already exists (reuse — do not rewrite)

| Artifact | Use |
|---|---|
| `deploy/secrets/schema.yaml` | A20 name/ref map |
| `scripts/secrets_sync/` + `scripts/sync_runtime_secrets.py` | A21 sync library/CLI (`--dry-run` \| `--apply`, `--app-id`, `--environment`, `--target railway`) |
| `scripts/test_sync_runtime_secrets.py` | Contract examples for mocks |
| `scripts/provision_runtime.py` + `provision-runtime.yml` | A26 pattern for dispatch inputs / token selection |
| `deploy/railway/<env>/<app_id>.yml` | `railway.*` names + `env.required` / `env.optional` |
| `verify-source.yml` | Already runs `pytest scripts/` with httpx/pyyaml/psycopg |

**Prefer calling A21 CLI from the workflow** over duplicating upsert GraphQL. Extend A21 only if OIDC token handoff or exit codes need a small, tested change.

## Scope — A23 (do)

1. **Workflow** e.g. `.github/workflows/sync-runtime-secrets.yml`:
   - `workflow_dispatch` inputs: `app_id` (string), `environment` choice `[production, staging]` default `production`, `dry_run` boolean default `false` (same shape as `provision-runtime.yml`)
   - Dry-run job path: `uv run scripts/sync_runtime_secrets.py … --dry-run` (no Railway/Infisical secrets required)
   - Apply path: Railway token selection **same as deploy/provision** (`RAILWAY_WORKSPACE_TOKEN` preferred else `RAILWAY_TOKEN`); Infisical via **OIDC** (Infisical GitHub Action or documented machine-identity flow). If full OIDC cannot be completed without an org-specific identity id, implement:
     - dry-run + workflow structure + permissions `id-token: write`
     - apply step that uses OIDC **or** clearly fails closed with “configure Infisical machine identity id” — **and** unit/integration tests that mock vault so CI does not need live Infisical
   - **Never** add this workflow to `v*` ship / `ci-cd-pipeline` deploy jobs
2. **Tests:**
   - Workflow file exists and is dispatch-only (assert via YAML parse or smoke grep in a small test — keep light)
   - CLI dry-run still green for both apps (may already pass)
   - Apply path: mocked footprint-missing → non-zero exit; mocked success → names-only reporting (no values in stdout)
3. **Backlog:** move **A23** to Closed when done.

### Soft OIDC note

Identity id / project slug may be repo Variables (non-secret) once the human creates the Infisical machine identity. Do not invent a second vault product. Do not store Infisical long-lived tokens if OIDC is viable; a temporary `INFISICAL_TOKEN` fallback is acceptable **only** if documented in `--help`/workflow comments as non-preferred and tests do not require it.

## Scope — A24 (do)

1. **CLI** e.g. `scripts/verify_runtime_bootstrap.py` (name flexible), `uv run`-able, PEP8 + type hints:
   - `--app-id` (required), `--environment` (default `production`)
   - Exactly one mode if you mirror siblings: prefer **always read-only** (no `--apply`). Optional `--dry-run` that only prints planned checks from YAML/schema without Railway — fine.
   - **Checks (Railway):**
     1. Footprint exists (project + service + environment names from deploy YAML) — fail if missing
     2. Required env **names** present on the service for that environment — use deploy YAML `env.required` and/or A20 schema entries with `required: true` (union is OK; document in `--help`). **Print names only; never values.**
   - Auth: same Railway token env vars as deploy; refuse without token when talking to Railway
2. **Tests:** mocked GraphQL fixtures for pass / missing footprint / missing required name; no live Railway
3. **Optional workflow:** `workflow_dispatch` verify-only job **or** a `verify` boolean/mode on a shared bootstrap workflow — keep A23 sync and A24 verify **conceptually separate** (different blast radius). A dedicated `verify-runtime-bootstrap.yml` is preferred.
4. **Backlog:** move **A24** to Closed when done.

## Out of scope (do not)

- A26 provision creates, A22 DDL, image deploy, start_command, domains, Railpack
- Rewriting A21 adapters into an Infisical↔Railway monolith
- Vercel implement (stub/refuse only)
- Changing app Settings / `/ready` semantics (A11)
- Large README / cheat-sheet updates
- Auto-sync on secret change inside Infisical native Railway sync (optional sugar — not this mission)

## Acceptance

### A23
- [ ] `sync-runtime-secrets` (or equiv.) workflow: `workflow_dispatch` only; inputs `app_id`, `environment`, `dry_run`
- [ ] Dry-run path runs without vault/Railway secrets in CI
- [ ] Apply path fail-closed on missing footprint (tested with mocks)
- [ ] No hook into `v*` ship pipeline
- [ ] Secret **values** never appear in logs/stdout from our code
- [ ] A23 closed in `notes/architect-backlog.md`

### A24
- [ ] Verify CLI: footprint + required **names** (values redacted)
- [ ] Mocked tests: pass / missing footprint / missing name
- [ ] Does not create or upsert
- [ ] A24 closed in backlog

## Report back

Short summary: files touched, how OIDC was handled (live wiring vs stub), exit codes for footprint miss, residuals (e.g. Infisical identity id still needs human setup once).
