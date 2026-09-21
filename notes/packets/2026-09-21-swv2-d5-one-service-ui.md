# Work packet — SW V2 D5 re-lock: one-service UI + V1-style secret (T069)

Governor re-locked **D5** (2026-09-21): keep v0 UI design; **one** Railway service; **V1-style** preview secret (not BFF / not `smart-writer-v2-ui`).

## Meta

| Field | Value |
|-------|-------|
| Packet id | `2026-09-21-swv2-d5-one-service-ui` |
| Status | **done** |
| Feature / spec | `specs/smart-writer-v2/` |
| Branch | merged via PR #3 → `main` (`b0beb5b`) |
| Agent mode | **background** |
| Spawn | `docs/agent-os/SPAWN_WORKER.md` + `_WORKER_PROMPT.md` |
| Note | Prod proof 2026-09-21: ship #9 + deploy #5; UI + 401 gate on worker URL. |

## Goal

Ship the existing v0 Next UI from **`smart-writer-v2`** same-origin with FastAPI, using a **typed preview secret** like V1; remove the second-UI / BFF-as-gate path.

## Context to read first

- `AGENTS.md`
- `specs/smart-writer-v2/spec.md` — **D5** (re-locked), **D6** note
- `specs/smart-writer-v2/plan.md` — Topology & P1
- `specs/smart-writer-v2/PLAN_DELTA.md` — §G.1 gate
- `specs/smart-writer-v2/tasks.md` — **T069**
- V1 pattern: `apps/smart-writer/app/entrypoints/http.py` (`AUDIT_FORM_HTML` + `sessionStorage` + `X-Audit-Secret`)
- Current UI: `apps/smart-writer-v2/web/`

## Owned paths (may edit)

- `apps/smart-writer-v2/app/` (static mount / SPA fallback; image build if needed)
- `apps/smart-writer-v2/web/` (remove BFF dependency; secret field; same-origin `/v1` calls)
- `apps/smart-writer-v2/README.md`
- `apps/smart-writer-v2/web/README.md`
- `deploy/railway/README.md` (mark `-ui` superseded)
- `deploy/railway/production/smart-writer-v2-ui.yml` (delete or clearly deprecate)
- `specs/smart-writer-v2/tasks.md` (T069 checkbox only when proven)
- `notes/packets/2026-09-21-swv2-d5-one-service-ui.md`

## Forbidden paths (do not edit)

- Inventing a new preview-secret **value**
- Re-introducing BFF custody as the spend gate
- Creating/pushing `ghcr.io/.../smart-writer-v2-ui` as the product host
- Unrelated Phase 10 tasks (T064, T073+) unless blocking T069

## Parallelism

| Field | Value |
|-------|-------|
| `[P]` tasks in this packet | no |
| Disjoint from other in-flight packets? | n/a |

## Definition of Done

- [x] Next build assets served by FastAPI on `/` (or documented path); `/v1` still works
- [x] UI has V1-style preview-secret field; mutating calls send `X-Audit-Secret`; **no** reliance on server-held secret in Next for custody
- [x] `web/app/api/proxy/...` removed or unused; README says same-origin + V1-style gate
- [x] `smart-writer-v2-ui` cattle removed or marked do-not-ship; `deploy/railway/README.md` updated
- [x] Nix/Docker image path builds UI into worker image (or documented CI step); one-app deploy still `smart-writer-v2`
- [x] Local: `npm run build` + serve path documented; pytest green for app
- [x] T069 checkbox updated only when public URL on **worker** service shows UI + gated API — **2026-09-21** ship #9 / deploy #5; `GET /` HTML; `/v1` → 401 without/wrong secret
- [x] Handoff notes any human ops (rebuild Codespace N/A; may need ship/deploy)

## Out of scope

- Real user login / OAuth
- Re-opening D8/D2/D3
- `p*` ops-tag platform work (separate decision)
- Broadening Codespace `actions: write`

## Governor locks required

| Lock | Value |
|------|--------|
| D5 | **re-locked** — one service + V1-style secret + v0 design kept |
| D6 | Seed already done; sync to **one** service |
| FINISH_BAR | Implement unblocked: yes |
| PLAN_DELTA | §G.1 D5 amend recorded |

## Fidelity (constitution §I)

| Lock | fidelity | How this packet honors it |
|------|----------|---------------------------|
| D5 | letter | One Railway service; V1-style secret field; v0 UI kept; no BFF-as-gate substitute |
| D6 | letter | Secret name in Infisical → one Railway service env |

## Stop / escalate if

- Next App Router cannot be served as static/SPA without losing required Settings/chat behavior — pose A/B (lighter SSR vs multi-process one service) to human; do not silently restore BFF custody
- Image build cannot include Node build in Nix cattle — escalate with plain options

## Handoff notes (agent fills at end)

- **Branch:** `packet/2026-09-21-swv2-d5-one-service-ui` @ `9a32891` (from `origin/main` @ `507d587`)
- **What changed:**
  - Next `output: "export"`; `npm run build:fastapi` → `app/static/ui/` (committed for Nix cattle)
  - FastAPI serves UI at `/` + static assets; `/v1` + `/health` unchanged
  - Settings: V1-style preview secret → `sessionStorage` → `X-Audit-Secret` on same-origin `/v1`
  - Removed `web/app/api/proxy` (BFF custody)
  - Deleted `deploy/railway/production/smart-writer-v2-ui.yml`; READMEs + Dockerfile marked do-not-ship
- **Tests / commands:**
  - `nix-shell -p nodejs_22 --run 'cd apps/smart-writer-v2/web && npm ci && npm run build:fastapi'`
  - `cd apps/smart-writer-v2 && nix develop -c bash -c 'uv sync --locked && uv run ruff check app/ tests/ && uv run pytest -q'` → **58 passed**
- **T069 checkbox:** **unchecked** — local proven; public worker URL not redeployed from this session
- **Human ops (ship/deploy):** Codespace may lack `actions: write` / `workflow_dispatch`. From a machine with `gh` auth:
  1. Merge/push this branch (or cherry-pick) to `main`
  2. `gh workflow run ship-registry.yml -f app_id=smart-writer-v2 -f nix_attr=container-smart-writer-v2 -f image_name=smart-writer-v2`
  3. `gh workflow run deploy.yml -f app_id=smart-writer-v2 -f tag=latest -f environment=production`
  4. Open `https://smart-writer-v2-production.up.railway.app/` → Settings secret → confirm gated `/v1`
  5. Then check T069 in `tasks.md`
- **Fidelity:** letter D5/D6; no BFF substitute; flake.nix untouched — UI baked via committed `app/static/ui` (documented rebuild path)
