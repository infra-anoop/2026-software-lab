# Data model — 002 delta

Baseline entities ([`../smart-writer-v2/data-model.md`](../smart-writer-v2/data-model.md)) become durable.

## Environments (D5 locked: schemas inside the SWV2 Supabase project)

| Env | App schema | Checkpoint schema | Queue schema | DB login | Upload bucket |
|-----|-----------|-------------------|--------------|----------|---------------|
| production | `swv2_prod` | `swv2_prod_langgraph` | `swv2_prod_queue` | `swv2_prod` | `uploads-prod` |
| staging | `swv2_staging` | `swv2_staging_langgraph` | `swv2_staging_queue` | `swv2_staging` | `uploads-staging` |

Each login owns its own three schemas — `USAGE`, `CREATE` and DML on its own three schemas only, nothing elsewhere — and has `search_path` set to them at the role level. The checkpointer and queue connect with that login, so their tables are created in the env's own schemas; each pool sets its own schema first in `search_path` (app pool → app schema, checkpointer → checkpoint schema, queue → queue schema) so setup DDL lands in the right one. Migrations are schema-qualified: they are written once with an `{{app_schema}}` token that `app/migrate.py` renders per environment (from the connected login) before dbmate runs. A CI lint rejects unqualified DDL, and an isolation test proves the staging login cannot read `swv2_prod*`. Production migrations run only after the same migration succeeded on staging (governor-only "irreversible" gate).

## Tables (in the env app schema)

| Table | Key columns | Notes |
|-------|-------------|-------|
| `owners` | `id uuid pk`, `token_sha256 bytea unique`, `created_at` | One per browser cookie |
| `conversations` | `id uuid pk`, `owner_id fk → owners ON DELETE CASCADE`, `created_at`, `updated_at`, `last_used_at timestamptz not null`, `deleting_at timestamptz null` | `expires_at` = `last_used_at + 30 days` (computed, returned by API) |
| `messages` | `id`, `conversation_id fk ON DELETE CASCADE`, `role`, `text`, `created_at` | |
| `run_states` | `conversation_id pk/fk ON DELETE CASCADE`, `state jsonb` | InternalRunState (never exposed, baseline FR-017) |
| `artifact_versions` | `id`, `conversation_id fk ON DELETE CASCADE`, `job_id uuid unique null`, `version int`, `body jsonb`, `created_at` | `job_id` unique → idempotent publication (a repeated final node cannot create a second version) |
| `provenance_records` | `id`, `artifact_id fk ON DELETE CASCADE`, `claim`, `source_ref`, `source_sha256`, `source_text`, `status` | Captured source text makes support checks reproducible |
| `uploads` | `content_ref pk`, `conversation_id fk ON DELETE CASCADE`, `storage_path`, `sha256`, `mime`, `byte_len`, `created_at` | Bytes in the env bucket |
| `jobs` | `id uuid pk`, `conversation_id fk ON DELETE CASCADE`, `kind generate\|revise`, `status queued\|running\|succeeded\|failed`, `attempt int`, `fail_reason`, `cost_reserved_usd`, `cost_actual_usd`, timestamps | Product-facing job record; the queue job carries `job_id`; `thread_id = id` for the checkpointer |
| `storage_deletions` | `storage_path pk`, `enqueued_at`, `attempts`, `last_error` | Outbox: Storage objects pending delete (retried until gone) |

## Use (FR-004)

`retention.touch(conversation_id)` runs `UPDATE … SET last_used_at = now() WHERE id = $1 AND deleting_at IS NULL RETURNING id` on: GET conversation, POST message, POST upload, job enqueue, job completion. If no row is returned, the conversation is being deleted, and the request gets **404** (job completion: the job ends `failed`, `fail_reason = conversation_deleted`, nothing published). Listing does not touch.

## Sweep protocol (review P1 — no delete-while-in-use)

Hourly, for each candidate:

1. **Claim, in one transaction:** `SELECT … FOR UPDATE SKIP LOCKED` the conversation row `WHERE last_used_at < now() - 30d AND deleting_at IS NULL AND NOT EXISTS (jobs queued|running)`, then `SET deleting_at = now()`. Touches serialize on the same row lock, so a concurrent touch either lands first (the row no longer qualifies) or sees `deleting_at` and gets 404.
2. **Delete, in one transaction:** insert every upload `storage_path` into `storage_deletions`; delete checkpoint rows for the conversation's job `thread_id`s; delete the conversation (cascade).
3. **Outbox:** delete each Storage object, removing the outbox row on success; retry with backoff on failure. A missing object counts as success.

Crash safety: a crash between steps 1 and 2 leaves `deleting_at` set; the next sweep resumes step 2 for rows with `deleting_at` older than 10 minutes. Tests cover touch-vs-claim and job-completion-vs-claim races with two connections.

## Job execution (review P2 — Procrastinate locked)

- **Enqueue** (HTTP): in one transaction, insert `jobs` row (`queued`, `attempt 0`, reservation check) and the Procrastinate job (`queueing_lock = job_id`, so a job cannot be enqueued twice).
- **Worker** (in-process Procrastinate async worker, started in FastAPI lifespan, concurrency 1): marks `running`, `attempt += 1`, and invokes the graph with `thread_id = job_id`. On the first attempt it starts fresh; on subsequent attempts it resumes from the last checkpoint (`ainvoke(None, config)`).
- **Stalled jobs:** worker heartbeats; on startup and every minute, stalled jobs (no heartbeat for > 2 minutes) are retried. This covers a crash mid-run.
- **Retry policy:** max 2 attempts. After that the job is `failed` with `fail_reason = interrupted_retry`, and the user sees "retry".
- **Repeated node after resume:** the node from the last checkpoint re-runs. Model calls inside it repeat, and their cost is charged again against the same job's reservation (FR-017 holds across attempts). Publication is idempotent via `artifact_versions.job_id unique` (`ON CONFLICT DO NOTHING`).
