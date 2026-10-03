# Data model — 002 delta

Baseline entities ([`../smart-writer-v2/data-model.md`](../smart-writer-v2/data-model.md)) become durable. Every table is schema-qualified (`{env_schema}.` = `public` in production, `staging` under D5-A).

| Table | Key columns | Notes |
|-------|-------------|-------|
| `owners` | `id uuid pk`, `token_sha256 bytea unique`, `created_at` | One per browser cookie |
| `conversations` | `id uuid pk`, `owner_id fk → owners ON DELETE CASCADE`, `created_at`, `updated_at`, `last_used_at timestamptz not null` | `expires_at` = `last_used_at + 30 days` (computed, returned by API) |
| `messages` | `id`, `conversation_id fk ON DELETE CASCADE`, `role`, `text`, `created_at` | |
| `run_states` | `conversation_id pk/fk ON DELETE CASCADE`, `state jsonb` | InternalRunState (never exposed, baseline FR-017) |
| `artifact_versions` | `id`, `conversation_id fk ON DELETE CASCADE`, `version int`, `body jsonb`, `created_at` | Every version kept |
| `provenance_records` | `id`, `artifact_id fk ON DELETE CASCADE`, `claim`, `source_ref`, `status` | Baseline grounding records |
| `uploads` | `content_ref pk`, `conversation_id fk ON DELETE CASCADE`, `storage_path`, `mime`, `byte_len`, `created_at` | Bytes in Storage bucket at `storage_path` |
| `jobs` | `id uuid pk`, `conversation_id fk ON DELETE CASCADE`, `kind generate|revise`, `status queued|running|succeeded|failed|timed_out`, `error`, `fail_reason`, `cost_usd numeric`, timestamps | `thread_id = id` for the checkpointer |
| `langgraph.*` | owned by `langgraph-checkpoint-postgres` | Rows for a job deleted by the sweeper when the conversation is purged (explicit delete by `thread_id`; not FK-linked) |

**Use (FR-004):** `retention.touch(conversation_id)` sets `last_used_at = now()` on: GET conversation, POST message, POST upload, job enqueue, job completion. Listing conversations does **not** touch (opening does).

**Sweep:** every hour, `conversations where last_used_at < now() - 30 days` → delete Storage objects for their uploads → delete checkpoint rows by job `thread_id` → delete conversation (cascade). Idempotent; logs counts to Logfire.

**Job recovery (startup):** `queued` → re-enqueue; `running` → resume from checkpoint; resume failure or no checkpoint → `failed`, `fail_reason = interrupted_retry`.
