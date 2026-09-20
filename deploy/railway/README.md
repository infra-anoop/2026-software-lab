# Deployment Configuration

Railway deploy and post-deploy smoke read **per-app** YAML files keyed by application id (same ids as `apps/registry.yaml`).

## What production runs

**The GHCR image digest is the production identity.** Tags (`v1.2.3`, `latest`, `sha-<git>`) exist so humans and CI can *find* an image. Railway is told to run `ghcr.io/<owner>/<name>@sha256:<digest>`, not a floating tag.

`.github/workflows/deploy.yml` does the mapping:

1. Read `deploy/railway/<environment>/<app_id>.yml`
2. Resolve `image.registry` / `image.repository` + the workflow `tag` input to a GHCR tag
3. Ask GHCR for that tag's **content digest** (`docker buildx imagetools inspect`)
4. Pin digest + start command on Railway via GraphQL, then `serviceInstanceDeploy` and wait until that deployment is terminal — fail-closed if the live schema cannot accept the pin (probe details live only in `deploy.yml`)

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

GraphQL endpoint used by **deploy and smoke**: `https://backboard.railway.com/graphql/v2` (Railway's API gateway).

## railway.toml is not a builder

`apps/*/railway.toml` is a **comment stub only**. It must not contain `[build]` / `builder = "RAILPACK"`.

Nix + GHCR is the only production factory. Railway is a runtime. If a service is git-connected, Railway can still Railpack-build from the repo — that is a **misconfiguration**. Production services must be image-sourced; CI overwrites the image to the digest on every deploy.

## Layout

```
deploy/railway/
├── production/
│   ├── research-auditor.yml   # production service + GHCR image mapping
│   ├── smart-writer.yml
│   ├── smart-writer-v2.yml      # FastAPI worker (Nix / registry ship)
│   └── smart-writer-v2-ui.yml   # Next UI+BFF (Docker first-ship; not registry)
├── staging/
│   └── research-auditor.yml   # manual / preview only (see below)
└── README.md
```

- **Path pattern:** `deploy/railway/<environment>/<app_id>.yml`
- **CI** (`.github/workflows/deploy.yml`, `smoke-test.yml`): `environment` is the folder name (`production` or `staging`).
- **Registry:** `deploy.railway.service_name` in `apps/registry.yaml` must match the Railway service name; `image.repository` must match how images are pushed from `ship-registry.yml` (typically `ghcr.io/<owner>/<oci.image_name>`).

## Staging / preview (asymmetric today)

**Staging is supported only for `research-auditor`.** There is no `deploy/railway/staging/smart-writer.yml` or `smart-writer-v2.yml`, and no Railway staging target wired for those apps yet.

| App | Production | Staging |
|---|---|---|
| `research-auditor` | ✅ | ✅ (`research-auditor-staging`) |
| `smart-writer` | ✅ | ❌ not configured |
| `smart-writer-v2` | ✅ YAML in git; **service bootstrap** is `notes/packets/2026-09-17-swv2-railway-bootstrap.md` | ❌ not configured |
| `smart-writer-v2-ui` | ✅ YAML in git (Docker UI; **not** `apps/registry.yaml`) — first-ship steps below | ❌ not configured |

Manual `workflow_dispatch` with `environment=staging` and `app_id=smart-writer` or `smart-writer-v2` will fail at config lookup with a clear error (`Missing config: deploy/railway/staging/<app_id>.yml`). Use `environment=production` until a preview Railway service exists.

**One-app ship:** do not `git tag v*` to publish V2 alone — a `v*` tag ships every `publish_container` app. Use `workflow_dispatch` on `ship-registry.yml` / `deploy.yml` / `smoke-test.yml` with `app_id=smart-writer-v2` (see the bootstrap packet).

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

## Ops tags (secrets sync / bootstrap — not code deploy)

Conscious Infisical→Railway ops use **annotated tags**, not `v*`. Preferred agent path from a Codespace (ordinary git push; no PAT / no `actions:write`):

| Intent | Tag | Workflow |
|--------|-----|----------|
| Secrets rotate (A23) | `sync/<app_id>/<environment>` | `ops-runtime.yml` → sync apply |
| First-time footprint (A26→A23→A24) | `bootstrap/<app_id>/<environment>` | provision → sync → verify (live) |
| Code ship / image pin | `v*` | existing ship/deploy — **never** runs A23 sync |

```bash
nix develop -c uv run scripts/ops_runtime_tag.py sync \
  --app-id smart-writer-v2 --environment production --dry-run

nix develop -c uv run scripts/ops_runtime_tag.py sync \
  --app-id smart-writer-v2 --environment production --push

nix develop -c uv run scripts/ops_runtime_tag.py bootstrap \
  --app-id smart-writer-v2 --environment production --push
```

Break-glass: Actions UI `workflow_dispatch` on `sync-runtime-secrets.yml`, `provision-runtime.yml`, `verify-runtime-bootstrap.yml`. Playbook: `notes/codespace-a23-dispatch.md`.

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
2. Add `deploy/railway/production/<app_id>.yml` (and Railway service + **public service domain** + GHCR wiring). `provision-runtime.yml` apply is idempotent: project → env → service → `serviceDomainCreate` if smoke would see empty domains.
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

| | Research Auditor | Smart Writer (V1) | Smart Writer V2 |
|---|---|---|---|
| Header | `X-Audit-Secret` | `X-Audit-Secret` | `X-Audit-Secret` |
| Env (Railway Variables / Infisical, never git) | `RESEARCH_AUDITOR_AUDIT_SECRET` | `SMART_WRITER_AUDIT_SECRET` | `SMART_WRITER_V2_AUDIT_SECRET` |
| Unset / blank | POST `/audit` and GET `/jobs` → **503** | same | mutating `/v1/*` and jobs → **503** |
| Wrong / missing header | **401** | **401** | **401** |
| Browser | HTML + `sessionStorage` | HTML + `sessionStorage` | Railway Next BFF (`smart-writer-v2-ui`) holds the secret (no `NEXT_PUBLIC_*`) |

`GET /`, `/health`, `/ready`, `/docs` stay unauthenticated. CLI is **not** the public cost control (Research Auditor CLI hardcodes 8; Smart Writer `--max-iterations` is flag-driven).

Set the secret via Infisical (preferred: `sync/<app>/<env>` ops tag / `ops-runtime.yml`; break-glass: A23 `sync-runtime-secrets.yml`) or the Railway service Variables UI. Listing the name under `env.optional` does not inject a value.

```bash
# Enqueue (202 + job_id). Poll GET /jobs/{id} with the same header.
curl -sS -X POST "$RAILWAY_URL/audit" \
  -H "Content-Type: application/json" \
  -H "X-Audit-Secret: $AUDIT_SECRET" \
  -d '{"raw_input":"One sentence to audit.","max_iterations":1}'

curl -sS "$RAILWAY_URL/jobs/JOB_ID" \
  -H "X-Audit-Secret: $AUDIT_SECRET"
```

Application secrets live in Infisical Cloud (schema in `deploy/secrets/schema.yaml`); A23 syncs names into Railway env. GitHub Actions holds Railway tokens, not app keys. CI (`scripts/validate_deploy_env.py`) fails if a `deploy.enabled` app has an empty `env.required` or if YAML names are not in that app’s Settings catalog.

## Smart Writer V2 UI (`smart-writer-v2-ui`) — Docker first-ship

**Lock (D5):** two Railway services in project `2026-software-lab` — worker `smart-writer-v2` + UI `smart-writer-v2-ui`. Design is in-repo Next; production host is Railway (not Vercel, not Codespaces).

**Why not registry/Nix:** the lab ship matrix (`ship-registry.yml` / `container-*`) is Python/Nix today. Expanding it for Node is a separate platform epic. T069 ships **Docker-only** cattle: `apps/smart-writer-v2/web/Dockerfile` + `deploy/railway/production/smart-writer-v2-ui.yml`. `deploy.yml` can pin any YAML `app_id`; `provision_runtime.py` / ops tags / A23 sync **require** a registry `deploy.enabled` id — they do **not** cover `smart-writer-v2-ui` yet.

### Env names (UI service Variables)

| Name | Kind | Notes |
|------|------|--------|
| `SMART_WRITER_V2_AUDIT_SECRET` | secret | Same Infisical value as the worker. Server-only BFF. Never `NEXT_PUBLIC_*`. |
| `SMART_WRITER_V2_WORKER_URL` | plain config | Public worker URL, e.g. `https://smart-writer-v2-production.up.railway.app` (no trailing slash). |

### Human first-ship (exact)

1. **Create service** in Railway project `2026-software-lab` / environment `production`: name **`smart-writer-v2-ui`**. Attach a **public service domain**. Add GHCR **Registry Credentials** (`read:packages`) on that service (same as worker).
2. **Variables** on `smart-writer-v2-ui`:
   - `SMART_WRITER_V2_AUDIT_SECRET` — copy from Infisical key `SMART_WRITER_V2_AUDIT_SECRET` (or from worker Variables).
   - `SMART_WRITER_V2_WORKER_URL` — `https://smart-writer-v2-production.up.railway.app`
3. **Build + push** image (local or CI runner with Docker + `docker login ghcr.io`):

```bash
cd apps/smart-writer-v2/web
docker build -t ghcr.io/<owner>/smart-writer-v2-ui:latest .
docker push ghcr.io/<owner>/smart-writer-v2-ui:latest
# optional: also tag sha-<git>
```

4. **Pin + deploy** (digest path — same as other apps):

```bash
gh workflow run deploy.yml \
  -f app_id=smart-writer-v2-ui \
  -f tag=latest \
  -f environment=production
```

5. **Verify:** open the Railway public UI URL (chat loads). Browser must never see the audit secret (DevTools → Network: only same-origin `/api/proxy/...`). Worker `GET /health` alone is insufficient for the UI finish bar.

Do **not** use Codespaces as the production product URL. Do **not** provision a Vercel project for this ship.

