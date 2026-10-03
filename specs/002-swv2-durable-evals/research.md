# Research — 002-swv2-durable-evals

Shape: [`docs/agent-os/research-template.md`](../../docs/agent-os/research-template.md). Gates: [`PLAN_AUTHORING_GATES.md`](../../docs/agent-os/PLAN_AUTHORING_GATES.md), [`STACK_POSTURE.md`](../../docs/agent-os/STACK_POSTURE.md).

Locks honored to the letter: **A27** (Postgres via Supabase; uploads in Supabase Storage; LangGraph Postgres checkpointer; anonymous per-browser ownership; reusable pieces in `lab_shared` with declared consumers), **A28** (versioned migrations), baseline **D5** (one Railway service serves the built UI same-origin), spec **D1/D2/D4** (calibration bar, noise margin, Gemini judge).

Code facts (2026-10-03): `app/store.py` `InMemoryStore` + `UploadStore` (dicts); `lab_shared.jobs.JobRunner` in-memory; five agents hardcode `"openai:gpt-4o"`; `generate_graph.openai_generate_enabled()` selects `_run_generate_without_llm` when no key (the test seam); generate graph nodes `infer → materials → web → scored_loop → provenance`, revise graph `scored_revise`; graphs compiled without a checkpointer; UI built by hand and committed under `app/static/ui/` (24 files) and `web/out/`; no SWV2 staging footprint (`deploy/railway/staging/` has research-auditor only); uploads capped at 5 MiB.

---

## Block: UI client

- **Decision:** Unchanged Next.js (v0-designed) UI; adds the deletion date and the "stored in this browser only" notice on each conversation (FR-004a) and a conversation list for the owning browser.
- **Rationale:** Baseline lock; this delta adds small surfaces only.
- **Pattern source:** `apps/smart-writer-v2/web/`.
- **Alternatives considered:** Not reopened (baseline D5). A v0 regeneration pass for the new surfaces is allowed when the UI changes are larger than about 2 components (fidelity: letter on "v0").

## Block: UI host / deploy

- **Decision:** Same single Railway service (baseline D5). Change: the UI is **built inside the Nix image build** (`buildNpmPackage` over `web/` → static export copied into the image at `app/static/ui/`), and built assets are removed from git (FR-022).
- **Rationale:** Removes hand-built commits; the image is the only artifact (cattle).
- **Pattern source:** `flake.nix` `mkContainer`.
- **Alternatives considered:** **Vercel** for the UI (managed, STACK_POSTURE pref 1/3). Rejected because it reopens D5 (two hosts plus a BFF/secret custody question). Recorded as the migrate trigger if accounts arrive. **Dockerfile multi-stage** (mainstream): the flake already owns image builds, and two builders would drift.

## Block: API / application service

- **Decision:** Same FastAPI app. New typed layers:
  - `app/persistence/` — repositories behind the existing store interface; Postgres implementation plus an in-memory implementation used only for unit tests via dependency injection, never selected by key sniffing.
  - `app/ownership.py` — browser-key cookie.
  - `app/retention.py` — sweeper.
  - `app/models_config.py` — per-role model config and cost meter.
- **Rationale:** Keeps business logic out of entrypoints (I-A1); vendor access stays behind adapters (I-A4).
- **Pattern source:** baseline app layout.
- **Alternatives considered:** **Supabase client (PostgREST) from Python** (managed API, no SQL driver). Rejected: no multi-statement transactions, and the checkpointer needs a real Postgres connection anyway.

## Block: Jobs / orchestration

- **Decision (P1 lock — named LangGraph nodes, unchanged topology):** generate graph `infer → materials → web → scored_loop → provenance`; revise graph `scored_revise`. Both are compiled with **`AsyncPostgresSaver`** (`langgraph-checkpoint-postgres`), `thread_id = job_id`. `JobRunner` stays the in-process executor (single replica). A new durable `jobs` table holds job records. **On startup**, jobs left `queued` are re-enqueued; jobs left `running` are resumed with `ainvoke(None, {"configurable": {"thread_id": job_id}})`; a missing checkpoint or failed resume marks the job `failed` with reason `interrupted_retry`. Resume granularity is per node (an interrupted `scored_loop` restarts that node).
- **Rationale:** A27 letter; matches "never silently lost" (SW-D3) at the smallest topology change.
- **Pattern source:** `lab_shared.jobs.JobRunner` (kept as executor only, no longer the record of truth).
- **Alternatives considered:** **LangGraph Platform / LangGraph Server** (managed durable runs with built-in resume). Strongest SOTA fit, but adds a host and a vendor beyond A27. **Temporal / Inngest / Hatchet** (durable workflow engines). **Procrastinate / pgqueuer** (OSS Postgres-backed queues, no new service). Migrate trigger: more than one replica, or jobs longer than about 30 minutes; then Procrastinate first (same database).

## Block: Data store

- **Decision:** Dedicated Supabase project for SWV2 (backlog P6). Tables: `owners`, `conversations`, `messages`, `artifact_versions`, `run_states`, `uploads` (metadata; bytes in a private Storage bucket), `provenance_records`, `jobs`; checkpointer tables owned by `langgraph-checkpoint-postgres` in schema `langgraph`. Cascade: `conversations` → every owned row via `ON DELETE CASCADE`; Storage objects deleted by the sweeper before the row. Access: **psycopg 3 async pool** with hand-written SQL in repositories. **Migrations: dbmate** (SQL files with `-- migrate:up` / `-- migrate:down` under `apps/smart-writer-v2/db/migrations/`; `schema.sql` dump committed and diff-checked in CI).
- **Rationale:** The schema is small (8 tables); SQL-first migrations with explicit down blocks give the rollback path (FR-006). dbmate is a single binary in nixpkgs, language-agnostic, so V1/RA can adopt later without SQLAlchemy.
- **Pattern source:** `db/supabase/*.sql` (greenfield `IF NOT EXISTS`, retired by A28 for new schema).
- **Alternatives considered:** **Alembic + SQLAlchemy 2** (mainstream Python; adds an ORM stack we would not otherwise use). **Atlas** (declarative schema-as-code with migration linting; SOTA, but key features moved to the paid tier). **Supabase CLI migrations** (`supabase db push`; managed-native, but ties CI to the Supabase CLI and project linking). **Neon** (serverless Postgres with free instant branching, ideal for staging/preview DBs). Rejected because it splits from the A27 letter; noted as the staging alternative if Supabase project slots run out (see D5). **Postgres `bytea` for uploads** (simpler cascade). Rejected by the A27 letter (Supabase Storage).

## Block: Search / retrieval / LLM

- **Decision:** Per-role model ids from typed Settings (`SMART_WRITER_V2_MODEL_{WRITER,ASSESSOR,EXTRACTION,INFER}`), with defaults set from the bake-off. A **price table** in `lab_shared.model_config` feeds a per-job **cost meter** that sums PydanticAI `usage` per call and stops the job before a call that would cross the ceiling (D3, never above $3). The **judge and support checker** are Gemini models via PydanticAI's Google provider (`pydantic-ai-slim[google]`); they run only in eval CI and locally, never in the deployed app. Writer candidates exclude Gemini (D4).
- **Rationale:** Evidence-chosen models (SW-M1..M3); judge family separation (SW-E3).
- **Pattern source:** baseline agents.
- **Alternatives considered:** **OpenRouter** (one key, many families; good for bake-offs, but a broker in the spend path). **LiteLLM proxy** (OSS gateway with budgets; would give dollar budgets natively, at the cost of a service to run). Migrate trigger: more than 2 providers in production.

## Block: Evals

- **Decision:** **pydantic-evals** `Dataset` / `Case` over `apps/smart-writer-v2/evals/golden/*.yaml`, each tagged `tuning` or `heldout`. Custom evaluators:
  - `ProgramOfficerJudge` — per-dimension 1–5 scores with rationale; Gemini.
  - `SourceSupport` — per cited claim: supported or unsupported; Gemini.
  - `Latency`, `Cost`.

  Results are reported to Logfire, and the GitHub Actions job summary and artifacts. **Nightly on main:** the full set (incl. held-out) runs k=3 times to give per-dimension mean and noise band. Band = max(observed range across the 3 repeats, 0.25) per dimension and for the support rate, recomputed nightly. **Per PR:** the tuning subset (one case per scenario category, fixed list in `evals/subset.yaml`; rotation changes only at post-mortem) runs once and is compared with the latest nightly subset means. Any dimension or the support rate dropping more than its band blocks (FR-012/013a). The gate only reports until the noise band exists and calibration passes D1.
- **Rationale:** PydanticAI-native, so it shares models and agents with the app (the engine-learning goal); results land in Logfire, already in the stack.
- **Pattern source:** none.
- **Alternatives considered:** **Braintrust**, **LangSmith** (managed eval platforms with datasets, experiment diffs, and human review UIs). Best-in-class review UX, but add vendors and secrets. **promptfoo** (OSS, CI-first, YAML), **Inspect AI** (OSS, rigorous; UK AISI), **DeepEval** (OSS pytest-style). pydantic-evals is chosen for stack coherence; Braintrust is the migrate trigger if governor review of drafts needs a UI beyond markdown sheets.

## Block: Secrets / preview gate

- **Decision:** Preview audit secret unchanged (baseline). **Ownership** = a server-issued random 256-bit token in an **HttpOnly, Secure, SameSite=Lax cookie** `swv2_owner`, set on first visit; the database stores only its SHA-256. New runtime secret names (schema + Settings): `SMART_WRITER_V2_DATABASE_URL`, `SMART_WRITER_V2_SUPABASE_URL`, `SMART_WRITER_V2_SUPABASE_SECRET_KEY`. **CI-only** secret names: `GEMINI_API_KEY` and `OPENAI_API_KEY` (eval runs; spend, so governor-only gate category), declared in the secrets schema for a GitHub Actions target.
- **Rationale:** An HttpOnly cookie keeps the ownership token away from page scripts. Same-origin (D5) makes cookies simple.
- **Pattern source:** baseline audit-secret pattern.
- **Alternatives considered:** **Supabase Anonymous Sign-ins** (managed, SOTA: anonymous JWT that later links to a real account, plus RLS). Attractive for the future accounts direction; rejected now because the browser never talks to Supabase directly, so RLS adds nothing yet. **Migrate trigger:** the accounts sprint. **localStorage key in a header**: readable by any script on the page.

## Block: Topology & runtime custody

- **Decision:**
  - Runtimes per environment: one Railway service `smart-writer-v2` (FastAPI + static UI) plus one Supabase project (Postgres + Storage).
  - **Environments**: production (exists) and staging (**new footprint**; database form is spec decision D5).
  - UI → API: same-origin fetch; the cookie is sent automatically; the preview secret stays as in baseline.
  - Custody: database URL and Storage key are held by the service only (never in the browser); eval provider keys live only in GitHub Actions secrets.
  - Cattle: `deploy/railway/staging/smart-writer-v2.yml`, `deploy/secrets/schema.yaml`, migrations in git, and the CI migration job.
- **Rationale:** Smallest change that meets FR-006 (staging before production).
- **Alternatives considered:** see D5 options in `plan.md`.

## Other forks

- **Test seam removal:** delete `openai_generate_enabled` / `_run_generate_without_llm`. Agents are built by role factories from config; tests use PydanticAI `Agent.override(model=TestModel() | FunctionModel(...))` plus `ALLOW_MODEL_REQUESTS = False`. A `graph-node-coverage` test asserts every node name appears in the LangGraph stream for generate and revise. Alternative: VCR-style recorded HTTP (`pytest-recording`), which is more realistic but brittle across model versions; kept for a single nightly smoke only.
- **Retention sweeper:** in-process hourly asyncio task (single replica); idempotent; deletes Storage objects, then the conversation row (cascade). Alternatives: **pg_cron** (managed in Supabase) cannot delete Storage objects safely; **GitHub Actions scheduled job** needs database credentials in CI.
- **Per-PR eval spend ledger:** the eval job sums costs from prior eval check runs on the same PR (checks API) and refuses beyond $2 (spend, so a governor-only gate). Skips when the app-tree hash is unchanged since the last eval run on the PR.
