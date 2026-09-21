# Work packet — SW V2 D5 re-lock: one-service UI + V1-style secret (T069)

Governor re-locked **D5** (2026-09-21): keep v0 UI design; **one** Railway service; **V1-style** preview secret (not BFF / not `smart-writer-v2-ui`).

## Meta

| Field | Value |
|-------|-------|
| Packet id | `2026-09-21-swv2-d5-one-service-ui` |
| Status | ready |
| Feature / spec | `specs/smart-writer-v2/` |
| Branch | `packet/2026-09-21-swv2-d5-one-service-ui` (or current `main` if human prefers) |
| Agent mode | **background** |
| Spawn | `docs/agent-os/SPAWN_WORKER.md` + `_WORKER_PROMPT.md` |

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

- [ ] Next build assets served by FastAPI on `/` (or documented path); `/v1` still works
- [ ] UI has V1-style preview-secret field; mutating calls send `X-Audit-Secret`; **no** reliance on server-held secret in Next for custody
- [ ] `web/app/api/proxy/...` removed or unused; README says same-origin + V1-style gate
- [ ] `smart-writer-v2-ui` cattle removed or marked do-not-ship; `deploy/railway/README.md` updated
- [ ] Nix/Docker image path builds UI into worker image (or documented CI step); one-app deploy still `smart-writer-v2`
- [ ] Local: `npm run build` + serve path documented; pytest green for app
- [ ] T069 checkbox updated only when public URL on **worker** service shows UI + gated API
- [ ] Handoff notes any human ops (rebuild Codespace N/A; may need ship/deploy)

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

- …
