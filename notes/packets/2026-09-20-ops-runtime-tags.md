# Packet: 2026-09-20-ops-runtime-tags

## Meta

| Field | Value |
|-------|-------|
| Packet id | `2026-09-20-ops-runtime-tags` |
| Status | done |
| Feature / spec | Lab cattle (A23/A26) — not a product feature |
| Branch | `main` OK |
| Agent mode | **background** |
| Spawn | `docs/agent-os/SPAWN_WORKER.md` + `_WORKER_PROMPT.md` |

## Goal

Agents (and humans) can trigger Infisical→Railway **sync** and full **bootstrap** from a Codespace via **git push of annotated ops tags**, without `workflow_dispatch`, PAT, or Codespace `actions:write`. Keep secrets-rotate ≠ code-deploy (`v*`).

## Design (authoritative — implement this)

### Lifecycle (unchanged intent)

| Intent | Mechanism | Must not |
|--------|-----------|----------|
| Code ship / image pin | `v*` + existing ship/deploy | Run A23 sync |
| Secrets rotate | ops tag `sync/…` **or** UI `workflow_dispatch` | Pin images |
| First-time footprint | ops tag `bootstrap/…` **or** UI dispatch chain | Auto on ordinary branch push |

### Tag shapes (strict)

```text
sync/<app_id>/<environment>
bootstrap/<app_id>/<environment>
```

Examples: `sync/smart-writer-v2/production`, `bootstrap/smart-writer-v2/production`.

- `environment` ∈ `{production, staging}` only.
- `app_id` must be in `apps/registry.yaml` with `deploy.enabled` (same gate as today’s provision/sync CLIs).
- No extra path segments. Fail closed in workflow + helper.

### Workflow: `.github/workflows/ops-runtime.yml`

```yaml
on:
  push:
    tags:
      - 'sync/**'
      - 'bootstrap/**'
```

- **Not** on `v*`, branch push, or PR.
- Parse `github.ref_name` → `kind`, `app_id`, `environment`; invalid → fail job with clear message.
- **`sync`:** same guts as `sync-runtime-secrets.yml` apply (Railway token select + Infisical OIDC + `uv run scripts/sync_runtime_secrets.py --apply`). Prefer factoring shared steps via composite or duplicated steps matching current yml (duplication OK if clearer; no behavior drift).
- **`bootstrap`:** sequential apply: `provision_runtime.py --apply` → sync apply → `verify_runtime_bootstrap.py` (live, not dry-run). Stop on first failure.
- Permissions: `contents: read`, `id-token: write` (OIDC).
- Keep existing `sync-runtime-secrets.yml`, `provision-runtime.yml`, `verify-runtime-bootstrap.yml` **`workflow_dispatch` as break-glass** — do not delete; comment that preferred agent path is ops tags.

### Helper: `scripts/ops_runtime_tag.py` (uv script / runnable under nix)

```bash
nix develop -c uv run scripts/ops_runtime_tag.py sync \
  --app-id smart-writer-v2 --environment production --push

nix develop -c uv run scripts/ops_runtime_tag.py bootstrap \
  --app-id smart-writer-v2 --environment production --push
```

Behavior:

1. Validate `app_id` / `environment` (registry + secrets schema presence for that app×env).
2. Build tag name; refuse if remote tag exists unless `--force` (then delete remote+local tag first).
3. Create **annotated** tag on current `HEAD` with a short message (`ops sync …` / `ops bootstrap …`).
4. With `--push`: `git push origin refs/tags/<tag>` (needs ordinary push auth — Codespace already has this).
5. Print: tag, commit SHA, expected Actions filter URL (and `gh run list` hint if `gh` works).
6. `--dry-run`: print tag + validations only; no tag create/push.
7. Never require `INFISICAL_TOKEN` / `RAILWAY_*` / PAT with `actions:write`.

Tests: unit tests for parse/validate/tag naming (no live push); extend `scripts/test_*.py` style.

### Docs

1. `deploy/railway/README.md` — short **Ops tags** section: when to use sync vs bootstrap vs `v*`; helper command; break-glass UI dispatch.
2. `notes/codespace-a23-dispatch.md` — rewrite preference order:
   1. **ops tag + helper** (preferred for agents)
   2. Actions UI `workflow_dispatch` (human break-glass)
   3. Session PAT / local `--apply` (non-preferred)
   - Explicitly: **do not** rely on Codespace `actions:write` / staged `.devcontainer` permission bump.

### Backlog amend (required)

In `notes/architect-backlog.md` **Decisions locked** + Closed rows for A23/A26/Lifecycle:

- Conscious trigger for A23/A26/A24 ops = **`workflow_dispatch` OR ops tag push** (`sync/**`, `bootstrap/**`).
- Still **not** on `v*` / ordinary branch push / PR.
- A23 fail-safe (no create in sync) unchanged; OIDC auth unchanged.
- Lifecycle sentence: Bootstrap = A26→A23→A24 via `bootstrap/…` tag (or UI); rotate = `sync/…` (or UI); code deploy = `v*`.

### Devcontainer

- **Remove** the staged `customizations.codespaces.repositories` `actions: write` block from `.devcontainer/devcontainer.json` (restore to no Codespace Actions write request). Do not leave it as an accidental path.

## Context to read first

- `notes/architect-backlog.md` (A20–A26, Lifecycle)
- `.github/workflows/{sync-runtime-secrets,provision-runtime,verify-runtime-bootstrap}.yml`
- `scripts/{sync_runtime_secrets,provision_runtime,verify_runtime_bootstrap,infisical_oidc_login}.py`
- `notes/codespace-a23-dispatch.md`
- `deploy/railway/README.md`
- `apps/registry.yaml` + `deploy/secrets/schema.yaml`

## Owned paths (may edit)

- `.github/workflows/ops-runtime.yml` (**new**)
- `.github/workflows/sync-runtime-secrets.yml` (comment only: prefer ops tags)
- `.github/workflows/provision-runtime.yml` (comment only)
- `.github/workflows/verify-runtime-bootstrap.yml` (comment only)
- `scripts/ops_runtime_tag.py` + `scripts/test_ops_runtime_tag.py` (and tiny shared parse helper if needed)
- `notes/architect-backlog.md`
- `notes/codespace-a23-dispatch.md`
- `deploy/railway/README.md`
- `.devcontainer/devcontainer.json` (remove actions:write block)
- `notes/packets/2026-09-20-ops-runtime-tags.md` (handoff)

## Forbidden paths (do not edit)

- Folding sync into `deploy.yml` / `v*` ship matrix
- Product apps (`apps/smart-writer-v2/` etc.) except if a one-line README pointer is clearly needed — prefer railway README only
- Committing `.tools/`, secrets, or PAT docs as the happy path
- Expanding Codespace token permissions

## Parallelism

| Field | Value |
|-------|-------|
| `[P]` | yes vs product UI packet (disjoint paths) |
| Disjoint from other in-flight? | yes (`web/` vs this) |

## Definition of Done

- [x] `ops-runtime.yml` exists; tag push triggers sync or bootstrap as designed
- [x] Helper validates + tags + optional push; `--dry-run` safe; tests green
- [x] Backlog A23/A26/Lifecycle wording amended
- [x] Docs + codespace playbook prefer ops tags
- [x] `.devcontainer` actions:write block removed
- [x] Existing workflow_dispatch workflows retained as break-glass
- [x] `uv run pytest scripts/test_ops_runtime_tag.py` (and any touched script tests) green
- [x] Commit(s); handoff with example dry-run output

## Out of scope

- OpenTofu / `infra/*` apply pipeline (future; same pattern later)
- Deleting historical ops tags automatically in GH (document discipline only)
- Changing Infisical OIDC or Railway token secrets layout
- Live push of a real `sync/…` tag in CI (do not burn prod from the packet unless human asks)

## Governor locks required

| Lock | Value |
|------|--------|
| Human | Prefer ops-tag path (option 2); keep lifecycle ≠ deploy; no PAT / no actions:write as happy path |
| A23 fail-safe | Sync still refuses missing footprint |

## Stop / escalate if

- Tempted to trigger sync on every deploy / `v*`
- Tag grammar would need free-form inputs beyond app_id/environment — escalate rather than invent

## Handoff notes (agent fills at end)

- What changed:
  - New `.github/workflows/ops-runtime.yml` (`push` tags `sync/**` | `bootstrap/**` only).
  - `scripts/ops_runtime_tag.py` + `scripts/test_ops_runtime_tag.py` (17 passed with `uv run --with pytest --with 'pyyaml>=6'`).
  - A23/A26/A24/Lifecycle backlog rows: conscious trigger = ops tag **or** workflow_dispatch break-glass.
  - `notes/codespace-a23-dispatch.md` + `deploy/railway/README.md` prefer ops tags; dispatch workflows comment updated.
  - Staged Codespace `actions:write` removed (not the happy path).
  - Hung worker interrupted; orchestrator finished handoff + commit.
- Example dry-run:
  ```text
  $ nix develop -c uv run --with pyyaml scripts/ops_runtime_tag.py sync \
      --app-id smart-writer-v2 --environment production --dry-run
  dry-run: would create annotated tag sync/smart-writer-v2/production on <HEAD>
  kind=sync app_id=smart-writer-v2 environment=production
  actions: https://github.com/infra-anoop/2026-software-lab/actions/workflows/ops-runtime.yml?query=branch%3Async/smart-writer-v2/production
  ```
- Open questions for human: none — first live `--push` is optional when you want to dogfood rotate.
