# Smart Writer V2 — environment bootstrap

`env_roles.sql` creates one database login and three schemas per environment inside the shared lab Supabase project `2026-software-lab` (backlog A31; spec 002 data-model § Environments). It never touches `public` (V1 / Research Auditor tables) or the other environment.

| Env | Login | Schemas |
|-----|-------|---------|
| production | `swv2_prod` | `swv2_prod`, `swv2_prod_langgraph`, `swv2_prod_queue` |
| staging | `swv2_staging` | `swv2_staging`, `swv2_staging_langgraph`, `swv2_staging_queue` |

The schemas are owned by the role that runs the script (`postgres` in the SQL editor); the login gets `USAGE` + `CREATE` on them and owns every object it creates. It cannot create or drop schemas, and cannot read `public` tables or the other environment.

## Run (automated — governor decision 2026-10-03)

Nobody runs this file by hand. The ops tag `db/smart-writer-v2/<environment>` (packet `notes/packets/2026-10-03-lab-db-bootstrap.md`; spec 002 T109–T112) does it:

1. It reads `SUPABASE_ACCESS_TOKEN` and the environment's password from Infisical (read-only CI login). The passwords are `SMART_WRITER_V2_DB_PASSWORD` and `SMART_WRITER_V2_STAGING_DB_PASSWORD`, seeded by the governor.
2. It sends this file to the Supabase Management API with the two `EDIT` values filled in.
3. It logs in as the new login and proves isolation.

Re-running is a no-op when the login already works. Rotation: change the password in Infisical, then re-push the tag. There is no stored connection-string secret; the app connects from the non-secret parts in `deploy/db/smart-writer-v2.yml` plus the password.

Break-glass only: paste the file into the Supabase SQL editor with the two `EDIT` values set to the environment and its Infisical password, and close the query without saving.

## Tests

`tests/pg/test_migrations.py` (spec 002 T036) applies this file to an ephemeral Postgres for both environments by substituting the two `EDIT` values, then proves isolation.
