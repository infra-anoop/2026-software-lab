# Deployment Configuration

Railway deploy and post-deploy smoke read **per-app** YAML files keyed by application id (same ids as `apps/registry.yaml`).

## What production runs

**The GHCR image digest is the production identity.** Tags (`v1.2.3`, `latest`, `sha-<git>`) exist so humans and CI can *find* an image. Railway is told to run `ghcr.io/<owner>/<name>@sha256:<digest>`, not a floating tag.

`.github/workflows/deploy.yml` does the mapping:

1. Read `deploy/railway/<environment>/<app_id>.yml`
2. Resolve `image.registry` / `image.repository` + the workflow `tag` input to a GHCR tag
3. Ask GHCR for that tag's **content digest** (`docker buildx imagetools inspect`)
4. Call Railway GraphQL `serviceInstanceUpdate` with `source.image` = digest pin and `runtime.start_command`
5. Call `serviceInstanceDeploy` and wait until **that new** deployment is `ACTIVE`/`SUCCESS` (or `FAILED`/`CRASHED`/`ERROR`)

`workflow_dispatch` on `deploy.yml` is the same path as the tag pipeline (app + tag + environment).

### Tag → digest (local)

```bash
# After docker login ghcr.io
docker buildx imagetools inspect ghcr.io/<owner>/<oci.image_name>:v1.0.0
# Digest: sha256:...
```

That `sha256:…` is what Railway should show as the service image after a successful deploy.

## GitHub secrets (required)

| Secret | Where | Purpose |
|---|---|---|
| `RAILWAY_WORKSPACE_TOKEN` (preferred) or `RAILWAY_TOKEN` | GitHub Actions | GraphQL: resolve IDs, set image + start command, deploy, poll status |
| `GITHUB_TOKEN` | Automatic in Actions | Read GHCR manifests (workflow `packages: read`). Also used by `ship-registry.yml` to **push**. |

Railway must **pull** the private GHCR image at runtime. That credential is **not** `GITHUB_TOKEN` (job-scoped). Store a GitHub PAT (`read:packages`) in the Railway service **Registry Credentials**. Keep GHCR packages private — do not flip them public to skip this.

GraphQL endpoint used by deploy: `https://backboard.railway.com/graphql/v2` (Railway's API gateway). Smoke still uses the older `.app` host; that is out of scope for this change.

## railway.toml is not a builder

`apps/*/railway.toml` is a **comment stub only**. It must not contain `[build]` / `builder = "RAILPACK"`.

Nix + GHCR is the only production factory. Railway is a runtime. If a service is git-connected, Railway can still Railpack-build from the repo — that is a **misconfiguration**. Production services must be image-sourced; CI overwrites the image to the digest on every deploy.

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

1. **Build:** `nix build .#container-<app_id>` (see `flake.nix`). Runtime deps are baked into the image at build; start is uvicorn only (no `uv sync` at boot).
2. **Push:** GitHub Actions pushes `ghcr.io/<owner>/<oci.image_name>:<tag>` (and `sha-<git>`, `latest`)
3. **Deploy:** For each app with `deploy.enabled`, the pipeline loads `deploy/railway/production/<app_id>.yml`, pins the tag's **digest** on the Railway service, applies `runtime.start_command`, deploys, and waits.

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

Same GraphQL path as the tag pipeline: digest pin → start command → deploy → wait.

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
4. Do **not** add a Railpack `[build]` to `apps/<id>/railway.toml`.

Optional staging/preview: add `deploy/railway/staging/<app_id>.yml` only after the Railway preview service exists.

## Runtime env (names in git, values in Railway)

Secrets are **not** stored in GitHub Actions or in this repo. GitHub deploy secrets are Railway tokens. Application secrets (`OPENAI_API_KEY`, optional Supabase/Logfire/Tavily) are pasted into each Railway **service Variables** UI.

`deploy/railway/<environment>/<app_id>.yml` lists **names** only:

- `env.required` — must be set for `GET /ready` to return 200. Today: `OPENAI_API_KEY`.
- `env.optional` — operator-facing knobs operators often set in Railway (observability, persistence, model id, audit HTTP secret). Code defaults apply if unset. This list is a subset of each app’s Settings catalog; the full name list is `apps/<id>/.env.example`.

`PORT` is injected by Railway; do not put it on the checklist.

### `/health` vs `/ready`

| Probe | Meaning | Secret check | CI |
| --- | --- | --- | --- |
| `GET /health` | Process is up | No | Nix offline smoke and GitHub smoke stay on `/health` (runners typically lack `OPENAI_API_KEY`) |
| `GET /ready` | Config present | `OPENAI_API_KEY` non-empty. **Does not** instantiate an OpenAI client, **does not** call api.openai.com, **does not** run the graph | Use on Railway after variables are injected |

`POST /audit` still returns 503 if the key is missing (independent of `/ready`).

### Preview gate (`POST /audit` / `GET /jobs`)

This is **not** a user login. Anyone with the shared secret can enqueue jobs and read outputs (drafts/verdicts). The HTML form stores the value in `sessionStorage` and sends it from JavaScript — convenience, not confidentiality against someone who loaded the page.

| | Research Auditor | Smart Writer |
|---|---|---|
| Header | `X-Audit-Secret` | `X-Audit-Secret` |
| Env (Railway Variables UI, never git) | `RESEARCH_AUDITOR_AUDIT_SECRET` | `SMART_WRITER_AUDIT_SECRET` |
| Unset / blank | POST `/audit` and GET `/jobs` → **503** | same |
| Wrong / missing header | **401** | same |
| HTTP `max_iterations` | server cap **8** (422 if client sends 99) | same; do not raise |
| POST `/audit` rate limit | 5/min per process (env override) | same |

`GET /`, `/health`, `/ready`, `/docs` stay unauthenticated. CLI is **not** the public cost control (Research Auditor CLI hardcodes 8; Smart Writer `--max-iterations` is flag-driven).

Set the secret in the Railway service Variables UI. Listing the name under `env.optional` does not inject a value.

```bash
# Enqueue (202 + job_id). Poll GET /jobs/{id} with the same header.
curl -sS -X POST "$RAILWAY_URL/audit" \
  -H "Content-Type: application/json" \
  -H "X-Audit-Secret: $AUDIT_SECRET" \
  -d '{"raw_input":"One sentence to audit.","max_iterations":1}'

curl -sS "$RAILWAY_URL/jobs/JOB_ID" \
  -H "X-Audit-Secret: $AUDIT_SECRET"
```

There is no 1Password/Vault integration. Env vars on the Railway service remain the injection mechanism. CI (`scripts/validate_deploy_env.py`) fails if a `deploy.enabled` app has an empty `env.required` or if YAML names are not in that app’s Settings catalog.

