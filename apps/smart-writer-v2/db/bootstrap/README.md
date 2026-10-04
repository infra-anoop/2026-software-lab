# Smart Writer V2 — environment bootstrap

`env_roles.sql` creates one database login and three schemas per environment inside the shared lab Supabase project `2026-software-lab` (backlog A31; spec 002 data-model § Environments). It never touches `public` (V1 / Research Auditor tables) or the other environment.

| Env | Login | Schemas |
|-----|-------|---------|
| production | `swv2_prod` | `swv2_prod`, `swv2_prod_langgraph`, `swv2_prod_queue` |
| staging | `swv2_staging` | `swv2_staging`, `swv2_staging_langgraph`, `swv2_staging_queue` |

The schemas are owned by the role that runs the script (`postgres` in the SQL editor); the login gets `USAGE` + `CREATE` on them and owns every object it creates. It cannot create or drop schemas, and cannot read `public` tables or the other environment.

## Run (governor, once per environment)

1. `openssl rand -hex 24` → a 48-character password (hex: no URL escaping needed).
2. Supabase → project `2026-software-lab` → **SQL Editor** → new query → paste `env_roles.sql`.
3. Edit the two `EDIT` lines (`env`, `pw`), run. Expect `NOTICE: ok: login swv2_<env> …`.
4. Close the query without saving it (it contains the password).
5. Save the connection string in Infisical (project `2026-software-lab`, env `production`, path `/`):
   - production → `SMART_WRITER_V2_DATABASE_URL`
   - staging → `SMART_WRITER_V2_STAGING_DATABASE_URL`

   Form (Supabase **Connect** → **Session pooler**, port 5432; the user is `<login>.<project-ref>`):

   ```text
   postgresql://swv2_prod.oguydvttuzbbiovvnxoj:<password>@<pooler-host>:5432/postgres
   ```

Re-running with a new password rotates it (update the Infisical value afterwards).

## Tests

`tests/pg/test_migrations.py` (spec 002 T036) applies this file to an ephemeral Postgres for both environments by substituting the two `EDIT` values, then proves isolation.
