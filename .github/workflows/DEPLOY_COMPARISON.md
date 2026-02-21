# Deploy Workflow Comparison

## Context

**Railway CLI limitation**: The Railway CLI does **not** provide a way to update a service's source image. Deploying a pre-built Docker image from GHCR requires the Railway GraphQL API ([Railway confirmation](https://station.railway.com/questions/change-ghcr-image-tag-from-railway-cli-11ee5faa)). `railway redeploy` only restarts the existing deployment—it does not pull a new image.

Therefore, a **pure Railway CLI** approach is not possible for your flow (Nix build → ship to GHCR → deploy to Railway).

## Options

| Approach | API usage | Complexity | "No config in Railway" |
|----------|-----------|------------|------------------------|
| **Original (deploy_api_backup.uml)** | Full: service lookup, image update, status polling | High: yq, jq, 3 GraphQL calls, 225 lines | ✅ Yes |
| **Streamlined (deploy.yml)** | Minimal: service lookup, image update; health-check wait | Lower: same config loading, 2 GraphQL calls, ~120 lines | ✅ Yes |

## What changed in the streamlined version

1. **Replaced GraphQL status polling** → **RAILWAY_URL/health polling**
   - Simpler: plain `curl` instead of jq + GraphQL status loop
   - Stronger signal: app is actually serving, not just "Railway says SUCCESS"
   - New requirement: `RAILWAY_URL` secret (already used by smoke-test)

2. **Consolidated steps**
   - Merged "Set params" and "Load config" into one step
   - Removed redundant outputs

3. **Same goals preserved**
   - No hardcoding (config from `deploy/railway/production.yml`)
   - No configuration in Railway (image + start_command passed each deploy)
   - Trigger only after ship-registry (unchanged in ci-cd-pipeline)
   - Manual deploy via `workflow_dispatch`
   - Positive signal: health-check polling until 200 OK (instead of GraphQL status)

3. **New requirement**: `RAILWAY_URL` secret (you already have it for smoke-test)

## If you want pure CLI

You would need to change the architecture:

- **Option A**: Configure the service in Railway with Docker image `ghcr.io/owner/repo:latest` and start command (one-time setup). Ship pushes to `:latest`. Use `railway redeploy` + health-check wait. **Trade-off**: image and start_command live in Railway.

- **Option B**: Switch to `railway up` (deploy source, not pre-built image). Railway would build from Dockerfile/Railpack. **Trade-off**: different build path (no Nix image).
