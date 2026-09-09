# Mission: A26 — Platform provision (runtime footprint)

You are a senior engineer in the 2026-software-lab monorepo. Close **A26 only**.

Cattle rule: **creating deploy infrastructure is a conscious, dispatch-only control** — not tied to code CI (`verify` / `v*` ship / image pin). Secrets sync (A23) and image deploy stay separate.

## Independence (read this)

| Depends on A26? | A26 depends on? |
|---|---|
| Live A23 / A24 (refuse or verify footprint) | **Nothing hard.** Not A20, A21, A22, or Infisical. |

You may run **in parallel with A21**. Do **not** implement vault upsert, Infisical, or secrets schema work. If you need a Railway GraphQL HTTP helper, keep it **local to this slice** (e.g. under `scripts/` or a small `deploy/` helper). Do not invent a shared “platform SDK” or merge with A21’s future `RuntimeTarget` — architect will reconcile overlap later.

## Why this exists

Today Railway project/service/environment are assumed to already exist. `deploy.yml` **resolves** names from `deploy/railway/<environment>/<app_id>.yml` and fails if missing. Operators create footprint in the Railway UI by hand.

A26 = scripted **ensure** of that footprint so bootstrap is repeatable and A23 can fail-closed when it is absent.

Locked lifecycle:

```text
A26 provision → A23 secrets sync → A24 verify
     ≠
v* ship → digest pin → smoke
```

## Product locks (do not reopen)

1. **Trigger:** manual only (`workflow_dispatch` and/or local CLI). **Not** on push, PR, first app commit, or `v*` tag.
2. **Target v1:** **Railway** only. Shape code so a later Vercel provisioner can be a second backend (interface or clear module boundary) — stub/NotImplemented is fine; do not build Vercel create in this slice.
3. **Semantics:** **ensure / idempotent** — if project, service, and environment already exist (match YAML names), succeed as no-op (or print “exists”). If missing, create what is missing. Do **not** delete or rename existing resources.
4. **Names from git:** read `deploy/railway/<environment>/<app_id>.yml` → `railway.project_name`, `railway.service_name`, `railway.environment_name`. Registry `deploy.enabled` / `app_id` select which YAML. Do not hardcode service names in the workflow beyond inputs.
5. **Auth:** use existing GitHub pattern — `RAILWAY_WORKSPACE_TOKEN` (preferred) or `RAILWAY_TOKEN` (same as deploy/smoke). Document in `--help` / workflow comments only — no long README.
6. **API host:** `https://backboard.railway.com/graphql/v2` (aligned with deploy/smoke).
7. **Out of A26:** setting GHCR image, start command, variables/secrets, domain, Railpack disconnect, Supabase, Infisical.

## Scope (do)

1. **CLI** (preferred entrypoint), e.g. `scripts/provision_runtime.py` (name flexible), `uv run`-able, PEP8 + type hints:
   - `--app-id` (required) — must be a registry `deploy.enabled` app
   - `--environment` (default `production`) — folder under `deploy/railway/`
   - `--dry-run` — print planned ensure steps (project/service/env names from YAML); **no** Railway calls; exit 0
   - `--apply` — perform ensure via GraphQL (needs token in env)
   - Refuse unknown app / missing YAML; refuse `--apply` without token
2. **Idempotent ensure logic** (mocked in unit tests):
   - Resolve project by name → create if absent
   - Resolve/create environment by name under project
   - Resolve/create service by name under project
   - Print ids/names at end (no secrets). Never log tokens.
3. **GitHub workflow** (e.g. `.github/workflows/provision-runtime.yml`):
   - `workflow_dispatch` inputs: `app_id`, `environment` (choice or string; default production)
   - Checkout → run CLI `--apply` (or dry-run input if you add one)
   - Same token selection pattern as `deploy.yml`
   - **Do not** hook into `ci-cd-pipeline.yml` tag/ship path
4. **Tests** (no live Railway required for CI):
   - Dry-run: known app×env prints expected names from fixture or repo YAML
   - Ensure logic: httpx/GraphQL **mocks** — create path, already-exists path, missing-token refuse
   - Fail closed on unknown `app_id`
5. **Minimal prose:** workflow header comment + CLI `--help` only. Do not add cheat-sheet chapters.
6. **Backlog:** when done, move **A26 only** to Closed in `notes/architect-backlog.md`.

### Soft API note

Railway GraphQL create mutation names drift (same class of problem as deploy’s `serviceInstanceUpdate` / `serviceUpdate` probes). Prefer: probe or try documented create mutations; **fail closed** with a clear error if create is impossible. Do not require live Railway in CI — mocks define the contract you implement.

## Out of scope (do not)

- A20/A21/A23/A24 (schema, vault upsert, secrets sync, verify-only beyond what provision returns)
- Image deploy, start_command pin, smoke
- Auto-provision on registry change or first push
- Vercel/Doppler implementation (boundary only)
- Rewriting `deploy.yml` resolve logic (you may **read** it for patterns)
- Large docs, drive-by refactors, app business logic

## Acceptance

- [ ] `uv run scripts/<provision>.py --app-id research-auditor --environment production --dry-run` exits 0 and shows project/service/env from YAML
- [ ] `--apply` refused without Railway token
- [ ] Unit tests: dry-run + mocked ensure (create + idempotent exist) + unknown app fails
- [ ] `workflow_dispatch` workflow exists and is **not** triggered by `v*` ship
- [ ] No live Railway calls required for CI green
- [ ] A26 closed in architect backlog only

## Report back

Short summary: files touched, ensure semantics, which GraphQL mutations you used (or probe strategy), residuals (e.g. empty service with no image until deploy).
