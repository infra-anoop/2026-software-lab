# A1 / A2 deploy runbook (Pattern A)

**Locked:** `main` + semver tags (`v*`) → **production**. Preview/staging is optional and manual later — not part of this proof.

**Goal:** Prove one (then both) production Railway service(s) run the **GHCR digest** CI shipped, not a Railpack/source build.

| ID | Closed when |
|---|---|
| **A2** | Railway service can **pull** private `ghcr.io/...` (registry credentials set; deploy does not die on image pull). |
| **A1** | Deploy job green **and** Railway UI shows digest pin + new deployment `ACTIVE`/`SUCCESS` + `GET /health` 200. |

Start with **one app** (`research-auditor` recommended — smaller surface). Repeat for `smart-writer`.

Repo HEAD at runbook authoring: see `git log -1 --oneline` on `main`.

---

## 0. Preflight — GitHub Actions secrets (deploy GraphQL)

Repo → **Settings → Secrets and variables → Actions**:

| Secret | Required | Role |
|---|---|---|
| `RAILWAY_WORKSPACE_TOKEN` (preferred) or `RAILWAY_TOKEN` | Yes | Deploy + smoke GraphQL |
| `GITHUB_TOKEN` | Automatic | Read/push GHCR in workflows |

If deploy fails immediately with “No Railway token found,” fix this before A2.

Check without guessing values:

```bash
nix develop --command gh secret list
```

---

## 1. Preflight — A2 (Railway pulls GHCR)

Private GHCR packages need **registry credentials on the Railway service**.  
`GITHUB_TOKEN` in Actions ≠ what Railway uses at runtime.

For each production service (`research-auditor`, later `smart-writer`):

1. GitHub → create a fine-scoped PAT (or classic) with **`read:packages`** (and SSO authorize if the org requires it).
2. Railway → project **`2026-software-lab`** → environment **`production`** → service → **Settings → Registry credentials** (or equivalent “private Docker registry” UI).
3. Register `ghcr.io` with username = GitHub user/org bot, password = that PAT.
4. Confirm the GHCR package exists and is **private** (do not flip public to skip A2).

Packages to expect (owner = `infra-anoop`):

- `ghcr.io/infra-anoop/research-auditor`
- `ghcr.io/infra-anoop/smart-writer`

**A2 fail signature:** GraphQL deploy “succeeds” or creates a deployment that then **CRASHED** / never pulls; Railway logs show auth/pull errors for `ghcr.io`.

---

## 2. Preflight — Railway service shape (not Railpack)

For the target service in Railway UI:

| Check | Expect |
|---|---|
| Source | **Image** / digest from GHCR after deploy — not “connected repo building with Railpack” as the live path |
| Service name | Matches YAML: `research-auditor` or `smart-writer` |
| Environment name | `production` (must match `deploy/railway/production/<app>.yml`) |
| Project name | `2026-software-lab` |
| Variables | At least `OPENAI_API_KEY` (for `/ready`). Optional: `*_AUDIT_SECRET`, Supabase, Logfire |
| `railway.toml` in git | Comment stub only — no `[build]` / Railpack |

YAML sources of truth:

- `deploy/railway/production/research-auditor.yml`
- `deploy/railway/production/smart-writer.yml`

---

## 3. Ensure a shippable image on GHCR

Pattern A production images come from the **tag pipeline** (or an equivalent ship of that commit).

### Preferred (full Pattern A)

From a clean `main` (today: include P5–P7 commit):

```bash
git fetch origin
git checkout main
git pull origin main
git log -1 --oneline   # note SHA

# Pick an unused semver patch (examples — use the next free tag)
git tag v0.5.0
git push origin v0.5.0
```

That should run `ci-cd-pipeline.yml`: verify → ship all publishable apps → deploy **production** → smoke `/health`.

Watch: GitHub → **Actions** → pipeline for that tag.

### Faster path (if you only need A1/A2 on one app)

If a recent image tag already exists on GHCR (`latest` or `sha-<short>`):

```bash
nix develop --command gh workflow run deploy.yml \
  -f app_id=research-auditor \
  -f tag=latest \
  -f environment=production
```

Only do this if you know `latest` is the digest you intend to prove. Prefer an explicit `v*` or `sha-…` tag when in doubt.

Manual ship of one app (if no image yet and you do not want a full release tag yet):

```bash
nix develop --command gh workflow run ship-registry.yml \
  -f app_id=research-auditor
# then deploy with the tag ship printed (branch-main or sha-…)
```

---

## 4. Deploy acceptance (A1)

### From the Actions job log

Confirm the deploy step:

1. Resolved `ghcr.io/infra-anoop/<image>@sha256:…`
2. Applied `start_command` from YAML (uvicorn under `/app/.venv/...`)
3. Waited on **that** deployment id until `ACTIVE` / `SUCCESS`
4. Job conclusion: success

### From Railway UI (required — GraphQL alone is not A1)

| Check | Pass |
|---|---|
| Service image | `ghcr.io/…@sha256:…` (digest), not an anonymous Railpack build |
| Deployment | New id created by this run; status success/active |
| Runtime logs | uvicorn listening; no `uv sync` at boot; no pull auth loop |

### From the public URL

Smoke workflow uses Railway domains GraphQL (host quirk A3 is hygiene only).

```bash
# After smoke or from Railway networking panel:
curl -sS -o /dev/null -w '%{http_code}\n' "$RAILWAY_URL/health"    # expect 200
curl -sS "$RAILWAY_URL/ready"                                       # 200 if OPENAI_API_KEY set; 503 if not
```

**A1 minimum:** `/health` 200 + UI digest + successful deployment.

**A1 strong:** `/ready` 200 as well.

**Not required for A1 close:** `POST /audit` (needs `*_AUDIT_SECRET` — related to A11). Optional bonus after A1:

```bash
curl -sS -X POST "$RAILWAY_URL/audit" \
  -H "Content-Type: application/json" \
  -H "X-Audit-Secret: $AUDIT_SECRET" \
  -d '{"raw_input":"One short sentence.","max_iterations":1}'
```

---

## 5. Persistence (optional, not A1 gate)

If you set `SUPABASE_URL` + `SUPABASE_SECRET_KEY` on the service, apply DDL first (P6):

1. Supabase SQL editor → run `db/supabase/runs_turns.sql`
2. For research-auditor also `db/supabase/research_audits.sql`
3. Prefer **one Supabase project per app** (see `db/supabase/README.md`)

Skip until after container proof if secrets are not ready.

---

## 6. Failure triage (quick)

| Symptom | Likely | Action |
|---|---|---|
| Actions: no Railway token | GitHub secret missing | §0 |
| Missing `deploy/railway/production/<app>.yml` | Wrong `app_id` / env | Check inputs |
| Deploy green, Railway still old image | UI looking at wrong service/env | Confirm project/service/environment names |
| Deployment CRASHED / pull denied | **A2** | Registry credentials on service |
| Boot loops `uv sync` / build | Railpack/git source still winning | Disconnect source build; redeploy image pin (P1/A5) |
| `/health` 200, `/ready` 503 | Missing `OPENAI_API_KEY` | Set Variables; not an image failure |
| `/ready` 200, `/audit` 503 | Missing audit secret | Expected (A11); set optional secret to exercise audit |
| Smoke can’t find domain | Domain not attached / GraphQL host A3 | Attach Railway domain; A3 is follow-up |

---

## 7. Close-out checklist (report back to architect)

Copy and fill:

```text
App: research-auditor | smart-writer
Git SHA / tag proven: …
GHCR digest on Railway: ghcr.io/…@sha256:…
Deployment id + status: …
A2 registry creds: yes/no (and whether pull errors seen)
GET /health: …
GET /ready: …
POST /audit exercised: yes/no
Supabase DDL applied: yes/no
Blockers fixed during run: …
```

Close **A2** when pull works. Close **A1** when UI digest + active deployment + `/health` are proven for that app. Repeat for the second app when ready.

---

## 8. Out of scope for this runbook

- Preview/staging deploys (Pattern A keeps them manual/later)
- Renaming staging → preview in YAML
- A3 smoke `.app` vs `.com` host cleanup
- A9 durable jobs / A10 cancel-in-flight LLM
- Making `*_AUDIT_SECRET` required for `/ready` (A11)
