# Codespaces: A23 sync / A26 bootstrap (ops tags preferred)

**Audience:** agents in this Codespace. Prefer **git push of annotated ops tags** — no `workflow_dispatch`, no PAT, no Codespace `actions:write`.

## Preference order

| Rank | Path | When |
|------|------|------|
| **1** | **Ops tag + helper** (`scripts/ops_runtime_tag.py` → `ops-runtime.yml`) | **Preferred for agents.** Ordinary git push auth is enough. |
| **2** | Actions UI `workflow_dispatch` on `sync-runtime-secrets.yml` / `provision-runtime.yml` / `verify-runtime-bootstrap.yml` | Human break-glass |
| **3** | Session PAT (`actions:write`) or local `--apply` with Infisical + Railway tokens | Non-preferred |

**Do not** rely on Codespace `actions:write` or a staged `.devcontainer` permission bump. That path was removed on purpose.

## Ops tags (strict)

```text
sync/<app_id>/<environment>       # A23 rotate only
bootstrap/<app_id>/<environment>  # A26 → A23 → A24
```

`environment` ∈ `{production, staging}`; `app_id` must be `deploy.enabled` in `apps/registry.yaml` and present in `deploy/secrets/schema.yaml` for that env.

```bash
# Always under nix develop (uv + git live there)
nix develop -c uv run scripts/ops_runtime_tag.py sync \
  --app-id smart-writer-v2 --environment production --dry-run

nix develop -c uv run scripts/ops_runtime_tag.py sync \
  --app-id smart-writer-v2 --environment production --push

nix develop -c uv run scripts/ops_runtime_tag.py bootstrap \
  --app-id smart-writer-v2 --environment production --push
```

Watch: [Ops runtime](https://github.com/infra-anoop/2026-software-lab/actions/workflows/ops-runtime.yml) or `gh run list --workflow=ops-runtime.yml`.

Lifecycle reminder: **`v*` = code deploy** (image pin). Ops tags never pin images. Sync refuses a missing Railway footprint (A23 fail-safe; provision is A26 / `bootstrap/…`).

## Break-glass UI

- [Sync runtime secrets](https://github.com/infra-anoop/2026-software-lab/actions/workflows/sync-runtime-secrets.yml)
- [Provision runtime](https://github.com/infra-anoop/2026-software-lab/actions/workflows/provision-runtime.yml)
- [Verify runtime bootstrap](https://github.com/infra-anoop/2026-software-lab/actions/workflows/verify-runtime-bootstrap.yml)

## Why default Codespace token cannot dispatch

Default Codespace `GITHUB_TOKEN` (`ghu_*`) can git push tags but **cannot** `workflow_dispatch` (`HTTP 403`). That is why ops tags are the agent happy path — not a PAT or `actions:write` grant.

## After a successful sync / bootstrap

1. Confirm a new green run on `ops-runtime.yml` (or the break-glass workflow).
2. Names-only check: `uv run scripts/verify_runtime_bootstrap.py --app-id … --environment …` (or live verify already ran on bootstrap tags).
3. Mutating probe for SWV2: `POST /v1/conversations` without header — **503** means audit secret still missing on Railway; after sync+redeploy expect **401** without/wrong `X-Audit-Secret`.
4. Never log secret values.

## Anti-patterns

- Folding sync into `v*` / `deploy.yml`.
- Installing `gh` when `nix develop` already has it.
- Treating old green Actions runs as post-seed sync.
- Local `--apply` without vault + Railway tokens when an ops tag would work.
- Re-adding Codespace `actions:write` as the happy path.
