# Deployment Configuration

Railway deploy and post-deploy smoke read **per-app** YAML files keyed by application id (same ids as `apps/registry.yaml`).

## Layout

```
deploy/railway/
├── production/
│   ├── research-auditor.yml   # production service + GHCR image mapping
│   └── smart-writer.yml
├── staging/
│   └── research-auditor.yml   # manual / preview only (see below)
└── README.md
```

- **Path pattern:** `deploy/railway/<environment>/<app_id>.yml`
- **CI** (`.github/workflows/deploy.yml`, `smoke-test.yml`): `environment` is the folder name (`production` or `staging`).
- **Registry:** `deploy.railway.service_name` in `apps/registry.yaml` must match the Railway service name; `image.repository` must match how images are pushed from `ship-registry.yml` (typically `ghcr.io/<owner>/<oci.image_name>`).

## Staging / preview (asymmetric today)

**Staging is supported only for `research-auditor`.** There is no `deploy/railway/staging/smart-writer.yml` and no Railway staging target wired for smart-writer yet.

| App | Production | Staging |
|---|---|---|
| `research-auditor` | ✅ | ✅ (`research-auditor-staging`) |
| `smart-writer` | ✅ | ❌ not configured |

Manual `workflow_dispatch` with `environment=staging` and `app_id=smart-writer` will fail at config lookup with a clear error (`Missing config: deploy/railway/staging/smart-writer.yml`). Use `environment=production` for smart-writer until a preview Railway service exists.

Automated tag releases (`v*`) deploy **production only** for all apps with `deploy.enabled`. Future *preview* deployment is tracked separately (see comment block in `.github/workflows/ci-cd-pipeline.yml` and `notes/todo.md`).

Archived deploy history (old workflows, comparison notes) lives in `docs/archive/deploy/`.

## Flow

1. **Build:** `nix build .#container-<app_id>` (see `flake.nix`)
2. **Push:** GitHub Actions pushes `ghcr.io/<owner>/<oci.image_name>:<tag>`
3. **Deploy:** For each app with `deploy.enabled`, the pipeline loads `deploy/railway/production/<app_id>.yml` and triggers Railway.

## Production release (tag)

```bash
git tag v1.0.0
git push origin v1.0.0
```

Pushes images for every app with `ship.publish_container`, then deploys every app with `deploy.enabled`, then smoke-tests each.

## Manual deploy (one app)

```bash
gh workflow run deploy.yml \
  -f app_id=smart-writer \
  -f tag=v1.0.0 \
  -f environment=production
```

## Manual smoke

```bash
gh workflow run smoke-test.yml \
  -f app_id=research-auditor \
  -f environment=production
```

## Adding a new app

1. Add the app to `apps/registry.yaml` and run `uv run scripts/validate_app_registry.py --write-json`.
2. Add `deploy/railway/production/<app_id>.yml` (and Railway service + GHCR wiring).
3. Ensure `flake.nix` already builds `container-<app_id>` for that id.

Optional staging/preview: add `deploy/railway/staging/<app_id>.yml` only after the Railway preview service exists.
