# Codespaces: agent tags (ship / sync / bootstrap)

**Audience:** agents in this Codespace. Prefer **git push of annotated tags** — no `workflow_dispatch`, no PAT, no Codespace `actions:write`.

## Preference order

| Rank | Path | When |
|------|------|------|
| **1** | **Tag + helper** (`scripts/ops_runtime_tag.py`) | **Preferred for agents.** Ordinary git push auth is enough. |
| **2** | Actions UI `workflow_dispatch` on the leaf workflows | Human break-glass |
| **3** | Session PAT (`actions:write`) or local `--apply` with Infisical + Railway tokens | Non-preferred |

**Do not** rely on Codespace `actions:write` or a staged `.devcontainer` permission bump. That path was removed on purpose.

## Tags (strict)

```text
ship/<app_id>/<environment>       # verify → GHCR → Railway pin → smoke
sync/<app_id>/<environment>       # A23 rotate only (no image pin)
bootstrap/<app_id>/<environment>  # A26 → A23 → A24 (no image pin)
```

`environment` ∈ `{production, staging}`; `app_id` must be `deploy.enabled` in `apps/registry.yaml` and present in `deploy/secrets/schema.yaml` for that env. `ship` also requires `ship.publish_container` and `deploy/railway/<env>/<app_id>.yml`.

```bash
# Always under nix develop (uv + git live there)

# One-app publish + deploy (same sequence as v*, one app)
nix develop -c uv run scripts/ops_runtime_tag.py ship \
  --app-id smart-writer-v2 --environment production --dry-run

nix develop -c uv run scripts/ops_runtime_tag.py ship \
  --app-id smart-writer-v2 --environment production --push

# Secrets rotate
nix develop -c uv run scripts/ops_runtime_tag.py sync \
  --app-id smart-writer-v2 --environment production --push

# First-time Railway footprint + secrets
nix develop -c uv run scripts/ops_runtime_tag.py bootstrap \
  --app-id smart-writer-v2 --environment production --push
```

Re-run `ship` / `sync` / `bootstrap` for the same app×env with `--force` (replaces the git tag).

Watch:

- [Ship one app](https://github.com/infra-anoop/2026-software-lab/actions/workflows/ship-one.yml) — `gh run list --workflow=ship-one.yml`
- [Ops runtime](https://github.com/infra-anoop/2026-software-lab/actions/workflows/ops-runtime.yml) — `gh run list --workflow=ops-runtime.yml`

Lifecycle: **`ship/…` or `v*` = code deploy** (image pin). `v*` still ships every `publish_container` app. Ops tags (`sync` / `bootstrap`) never pin images. Sync refuses a missing Railway footprint (A23 fail-safe; provision is A26 / `bootstrap/…`).

## Break-glass UI

- [Ship container](https://github.com/infra-anoop/2026-software-lab/actions/workflows/ship-registry.yml)
- [Deploy to Railway](https://github.com/infra-anoop/2026-software-lab/actions/workflows/deploy.yml)
- [Smoke](https://github.com/infra-anoop/2026-software-lab/actions/workflows/smoke-test.yml)
- [Sync runtime secrets](https://github.com/infra-anoop/2026-software-lab/actions/workflows/sync-runtime-secrets.yml)
- [Provision runtime](https://github.com/infra-anoop/2026-software-lab/actions/workflows/provision-runtime.yml)
- [Verify runtime bootstrap](https://github.com/infra-anoop/2026-software-lab/actions/workflows/verify-runtime-bootstrap.yml)

## Why default Codespace token cannot dispatch

Default Codespace `GITHUB_TOKEN` (`ghu_*`) can git push tags but **cannot** `workflow_dispatch` (`HTTP 403`). That is why tags are the agent happy path — not a PAT or `actions:write` grant.

## After a successful ship

1. Confirm a new green run on `ship-one.yml`.
2. Open the Railway public URL → `/health` 200 (smoke already did this).
3. Never log secret values.

## After a successful sync / bootstrap

1. Confirm a new green run on `ops-runtime.yml` (or the break-glass workflow).
2. Names-only check: `uv run scripts/verify_runtime_bootstrap.py --app-id … --environment …` (or live verify already ran on bootstrap tags).
3. Mutating probe for SWV2: `POST /v1/conversations` without header — **503** means audit secret still missing on Railway; after sync+redeploy expect **401** without/wrong `X-Audit-Secret`.
4. Never log secret values.

## Anti-patterns

- `gh workflow run` / `workflow_dispatch` as the agent path for ship, deploy, provision, or sync.
- Folding sync into `v*` / `ship-one.yml` / `deploy.yml`.
- Installing `gh` when `nix develop` already has it.
- Treating old green Actions runs as post-seed sync.
- Local `--apply` without vault + Railway tokens when an ops tag would work.
- Re-adding Codespace `actions:write` as the happy path.
