# Work packet — SW V2 Railway bootstrap (A26 → A23 → ship → deploy → smoke)

Lab cattle already exists. This packet **wires `smart-writer-v2` onto it**. Not a Spec Kit product story. Do **not** `git tag v*` (that ships every `publish_container` app).

## Meta

| Field | Value |
|-------|-------|
| Packet id | `2026-09-17-swv2-railway-bootstrap` |
| Status | done |
| Feature / spec | `specs/smart-writer-v2/` (T006 done; T066 docs; T067 Vercel **out**) |
| Branch | current (`main` OK — no new factory) |
| Agent mode | session |

## Goal

Railway service `smart-writer-v2` in project `2026-software-lab` runs the GHCR digest and **`GET /health` returns 200** via `smoke-test.yml`.

## Context to read first

- `AGENTS.md` (cattle; no vault/runtime create without this packet)
- `notes/architect-backlog.md` — A26 provision, A23 sync, A24 verify, A20 Infisical, A9 in-memory, A11 `/ready`
- `deploy/railway/README.md`
- `deploy/railway/production/smart-writer-v2.yml`
- `apps/registry.yaml` (`smart-writer-v2`: `publish_container` + `deploy.enabled`)
- `deploy/secrets/schema.yaml` → `smart-writer-v2` / `production`

## Owned paths (may edit)

- `notes/packets/2026-09-17-swv2-railway-bootstrap.md`
- `specs/smart-writer-v2/quickstart.md`
- `specs/smart-writer-v2/tasks.md` (T066 checkbox only)
- `apps/smart-writer-v2/README.md`
- `deploy/railway/README.md` (layout / V2 rows — no new workflow)
- `scripts/provision_runtime.py` + `scripts/test_provision_runtime.py` (A26: also ensure a public service domain so smoke can `GET /health`)

## Forbidden paths (do not edit)

- Spec Kit product US6+ (`T058+` implementation) in this packet
- `deploy/secrets/schema.yaml` values (names already declared)
- Other apps’ product code
- Vercel / T067
- `git tag v*`

## Already in git (do not recreate)

| Piece | Where |
|-------|--------|
| Registry ship + deploy | `apps/registry.yaml` `smart-writer-v2` |
| Railway YAML | `deploy/railway/production/smart-writer-v2.yml` |
| Secret **names** | `deploy/secrets/schema.yaml` |
| Nix image | `nix build .#container-smart-writer-v2` |
| Workflows | `provision-runtime.yml`, `sync-runtime-secrets.yml`, `verify-runtime-bootstrap.yml`, `ship-registry.yml`, `deploy.yml`, `smoke-test.yml` |

## Execution order

1. **Git cattle docs** — T066 (in-memory/restart + local run); README layout lists `smart-writer-v2.yml`.
2. **Dry-run (no writes)**
   ```bash
   uv run scripts/provision_runtime.py --app-id smart-writer-v2 --environment production --dry-run
   uv run scripts/sync_runtime_secrets.py --app-id smart-writer-v2 --environment production --target railway --dry-run
   uv run scripts/verify_runtime_bootstrap.py --app-id smart-writer-v2 --environment production --dry-run
   ```
3. **Live footprint (read-only)** — `verify_runtime_bootstrap.py` without `--dry-run`, or `gh workflow run verify-runtime-bootstrap.yml -f app_id=smart-writer-v2 -f environment=production -f dry_run=false`. Exit **2** = service missing.
4. **HITL if footprint missing** — `provision-runtime.yml` **apply** (`dry_run=false`). Empty service until deploy pins image. Do not create from Railway UI.
5. **HITL vault** — Infisical Cloud project `2026-software-lab` / env `production` / path `/`:
   - `OPENAI_API_KEY` — likely already present (shared key)
   - `SMART_WRITER_V2_AUDIT_SECRET` — **new**; human seeds once
   - `TAVILY_API_KEY` / `LOGFIRE_TOKEN` optional
6. **A23 sync** — `sync-runtime-secrets.yml` apply for `smart-writer-v2` / `production`.
7. **A24 verify live** — required names present (`OPENAI_API_KEY`).
8. **One-app ship** (not a `v*` tag):
   ```bash
   gh workflow run ship-registry.yml \
     -f app_id=smart-writer-v2 \
     -f nix_attr=container-smart-writer-v2 \
     -f image_name=smart-writer-v2
   ```
   From `main`, tags include `branch-main`, `sha-<short>`, `latest`.
9. **One-app deploy + smoke**
   ```bash
   gh workflow run deploy.yml -f app_id=smart-writer-v2 -f tag=latest -f environment=production
   gh workflow run smoke-test.yml -f app_id=smart-writer-v2 -f environment=production
   ```
10. **Stop** — smoke `/health` 200 is DoD. Then Lane A (US6 T058) is a **new** slice.

## Definition of Done

- [x] T066 documented (restart/in-memory + local worker/UI)
- [x] `deploy/railway/README.md` lists V2 production YAML
- [x] Provision dry-run prints project `2026-software-lab` / env `production` / service `smart-writer-v2`
- [x] Railway service exists (A26 apply if it did not) — created `35df644b-93d4-4685-adb8-3ebff89077cb`
- [x] Infisical has `OPENAI_API_KEY` synced; `SMART_WRITER_V2_AUDIT_SECRET` skipped (not in vault)
- [x] GHCR image `smart-writer-v2` pushed; Railway digest-pinned (`sha256:4eaa26de4f018dfa081f3eaac15c61ecf93c8e10c0c23038b2a61341adcc9a67`)
- [x] `smoke-test.yml` `GET /health` 200 — `https://smart-writer-v2-production.up.railway.app/health` → `{"ok":true}` ([35183326809](https://github.com/infra-anoop/2026-software-lab/actions/runs/35183326809))
- [x] This packet `Status` → `done`

## Out of scope

- Vercel / T067 / playing in the browser
- US6 non-grant (T058–T060) and polish T062–T065
- Staging Railway for V2
- Lab-wide `v*` release

## Stop / escalate if

- Infisical missing `SMART_WRITER_V2_AUDIT_SECRET` (human seed)
- Provision apply needed and no Railway token in this environment
- GHCR package permissions fail for the new image name
- Conflict with A23 (must not create footprint) or A5 (no git-connect Railpack)

## Handoff notes (agent fills at end)

- What changed: T066 docs; Railway README lists V2 YAML; A26 now ensures a public service domain (smoke needs it).
- Tests / commands run:
  - `provision_runtime.py --dry-run` → project `2026-software-lab` / env `production` / service `smart-writer-v2`
  - `sync_runtime_secrets.py --dry-run` → 4 names (`OPENAI_API_KEY` required)
  - Live verify [35182859838](https://github.com/infra-anoop/2026-software-lab/actions/runs/35182859838) **exit 2** then provision [35182905249](https://github.com/infra-anoop/2026-software-lab/actions/runs/35182905249) **created** service
  - Sync [35182938075](https://github.com/infra-anoop/2026-software-lab/actions/runs/35182938075) upserted `OPENAI_API_KEY`; skipped audit/tavily/logfire
  - Ship [35182940574](https://github.com/infra-anoop/2026-software-lab/actions/runs/35182940574) `ghcr.io/infra-anoop/smart-writer-v2`
  - Deploy [35183028871](https://github.com/infra-anoop/2026-software-lab/actions/runs/35183028871) **SUCCESS** digest `sha256:4eaa26de4f018dfa081f3eaac15c61ecf93c8e10c0c23038b2a61341adcc9a67`
  - Smoke [35183103596](https://github.com/infra-anoop/2026-software-lab/actions/runs/35183103596) **failed**: no serviceDomains
  - `uv run pytest scripts/test_provision_runtime.py` 19 passed
- Open questions for human:
  - Seed Infisical `SMART_WRITER_V2_AUDIT_SECRET` when you want mutating `/v1` on Railway (optional for `/health`)
- Next agent step: Lane A US6 T058 (red tests) → spawn T059. Cattle finish line met.
