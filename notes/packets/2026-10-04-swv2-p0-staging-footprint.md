# Ops packet — SWV2 P0 footprint (spec 002 T017–T021, T109–T112)

## Meta

| Field | Value |
|-------|-------|
| Packet id | `2026-10-04-swv2-p0-staging-footprint` |
| Status | in_progress (governor steps done; agent steps T020, T112 pending) |
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

## Open items

- **T112** live database-login run: after the lab-db-bootstrap packet merges.
- **T020** staging service + sync: ops worker, after T007/T014/T015 land.
- **Gate coverage (for T052):** the lab-wide `v*` release (`ship-registry.yml`) also deploys registry apps. T052 must make sure a `v*` release carrying unapplied SWV2 migrations either waits on `swv2-production-migrate` or skips SWV2. Today only `ship-one.yml` is planned to use the gate.
- Terminal scrollback: the governor was advised to clear the terminal where the passwords were generated.
