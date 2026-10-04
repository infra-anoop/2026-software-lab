# Ops packet — SWV2 P0 footprint (spec 002 T017–T021, T109–T112)

## Meta

| Field | Value |
|-------|-------|
| Packet id | `2026-10-04-swv2-p0-staging-footprint` |
| Status | in_progress (governor steps done; T112 done 2026-10-04; agent step T020 pending) |
| Feature / spec | `specs/002-swv2-durable-evals/` (P0 ops) |
| Branch | per step (`orch/*`, `packet/*`); live runs are ops tags |
| Agent mode | session (governor walkthrough) + background (ops worker for T020) |

## Goal

Smart Writer V2 has everything it needs outside the repo: storage, database logins, provider key, staging service, and the production-migration approval gate.

## Steps (plain language)

1. **Storage and keys in the shared Supabase project `2026-software-lab`** (T018, backlog A31). Two private buckets. The app's own Supabase secret key. A project-scoped access token for automation. Two database passwords.
2. **Anthropic key** (T019) in Infisical. CI reads Infisical through the existing GitHub OIDC login; there are no GitHub repository secrets.
3. **Database logins** (T109–T112). The `db/smart-writer-v2/<env>` ops tag creates `swv2_prod` / `swv2_staging` through the Supabase Management API using the stored passwords, then proves isolation. Packet `notes/packets/2026-10-03-lab-db-bootstrap.md`.
4. **Staging service + secret sync** (T020). Ops tags `bootstrap/smart-writer-v2/staging`, then `sync/…/staging` and `sync/…/production`.
5. **Production-migration gate** (T021). GitHub environment `swv2-production-migrate`, which the governor approves.

## Fidelity (constitution §I — required)

| Lock | fidelity | How honored |
|------|----------|-------------|
| A31 shared Supabase project, own schemas/login/bucket | letter | Buckets `swv2-uploads-{prod,staging}`; logins via the committed `env_roles.sql` |
| A30 vault naming | letter | Plain lab-shared names (`ANTHROPIC_API_KEY`, `SUPABASE_ACCESS_TOKEN`); app and app+env prefixes otherwise |
| A20/A21 Infisical via OIDC, no repo secrets | letter | No GitHub secrets added |
| Read-only CI on Infisical (governor 2026-10-03) | letter | Governor seeded the passwords; the automation never writes the vault |

## Log (names only — never values)

| When (UTC-7) | Task | What | Verified how |
|--------------|------|------|--------------|
| 2026-10-03 21:50 | T018 | Buckets `swv2-uploads-prod`, `swv2-uploads-staging` created in project `2026-software-lab` (ref `oguydvttuzbbiovvnxoj`) | Orchestrator listed buckets via the Storage API: both present, `public=false` |
| 2026-10-03 21:50 | T018 | Infisical `production` `/`: `SMART_WRITER_V2_SUPABASE_URL`, `SMART_WRITER_V2_SUPABASE_SECRET_KEY` (own `smart-writer-v2` key) | Governor confirmed; first CI read verifies |
| 2026-10-03 22:40 | T018 | Infisical `production` `/`: `SUPABASE_ACCESS_TOKEN` (scoped to project `2026-software-lab`, Database Read-Write + Connection Pooling Read) | Governor confirmed; first `db/` tag run verifies |
| 2026-10-03 23:00 | T018 | Infisical `production` `/`: `SMART_WRITER_V2_DB_PASSWORD`, `SMART_WRITER_V2_STAGING_DB_PASSWORD` (`openssl rand -hex 24`) | Governor confirmed; the `db/` run validates the 48-hex format before any SQL |
| 2026-10-03 23:06 | T019 | Infisical `production` `/`: `ANTHROPIC_API_KEY` (workspace `2026-software-lab`, prepaid credits, auto-reload off) | Governor confirmed |
| 2026-10-03 23:04 | T019 | GitHub variable `INFISICAL_MACHINE_IDENTITY_ID` exists | Run 35539381829 (Sync runtime secrets, 2026-09-20) logged "Using Infisical OIDC (machine identity)" |
| 2026-10-03 23:16 | T021 | GitHub environment `swv2-production-migrate`: required reviewer `infra-anoop`, prevent-self-review off, admin bypass off, deployment rule tag `ship/smart-writer-v2/production` | Orchestrator read it back via the REST environments API |
| 2026-10-04 11:40 | T112 | First `db/smart-writer-v2/staging` run (37225335757) failed at Infisical OIDC login (HTTP 403): the machine identity's OIDC Subject trusted only `refs/heads/main`; this was the first tag-triggered `ops-runtime.yml` run (earlier secret syncs were `workflow_dispatch` on `main`). Nothing reached the database | Run log: Infisical auth step failed; ensure step skipped |
| 2026-10-04 12:22 | T112 | Governor set the Infisical machine identity's OIDC Subject to `repo:infra-anoop/2026-software-lab:ref:refs/{heads/main,tags/sync/*,tags/bootstrap/*,tags/db/*}` (audiences/claims unchanged). Unblocks every ops-tag family, not only `db/` | Governor confirmed; next tag run logged in via OIDC |
| 2026-10-04 12:24 | T112 | `db/smart-writer-v2/staging` (run 37228069765): probe failed → `env_roles.sql` applied via Management API → probe passed; `ok: swv2_staging applied` | Run log |
| 2026-10-04 12:26 | T112 | `db/smart-writer-v2/production` (run 37233353978): `ok: swv2_prod applied` after probe passed | Run log |
| 2026-10-04 12:27 | T112 | Staging re-push (run 37233389998): `probe passed; nothing to do`, `ok: swv2_staging noop` — idempotent | Run log |

## Open items

- **T020** staging service + sync: ops worker, after T007/T014/T015 land.
- **Gate coverage (for T052):** the lab-wide `v*` release (`ship-registry.yml`) also deploys registry apps. T052 must make sure a `v*` release carrying unapplied SWV2 migrations either waits on `swv2-production-migrate` or skips SWV2. Today only `ship-one.yml` is planned to use the gate.
- Terminal scrollback: the governor was advised to clear the terminal where the passwords were generated.
