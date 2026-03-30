# Deployment Configuration

Railway deploy and post-deploy smoke read **per-app** YAML files keyed by application id (same ids as `apps/registry.yaml`).

## Layout

```
deploy/railway/
├── production/
│   ├── research-auditor.yml   # production service + GHCR image mapping
│   └── smart-writer.yml
├── staging/
│   └── research-auditor.yml   # optional; manual / preview workflows
└── README.md
```

- **Path pattern:** `deploy/railway/<environment>/<app_id>.yml`
- **CI** (`.github/workflows/deploy.yml`, `smoke-test.yml`): `environment` is the folder name (`production` or `staging`).
- **Registry:** `deploy.railway.service_name` in `apps/registry.yaml` must match the Railway service name; `image.repository` must match how images are pushed from `ship-registry.yml` (typically `ghcr.io/<owner>/<oci.image_name>`).

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
