# Research — 002-swv2-durable-evals

Shape: [`docs/agent-os/research-template.md`](../../docs/agent-os/research-template.md). Gates: [`PLAN_AUTHORING_GATES.md`](../../docs/agent-os/PLAN_AUTHORING_GATES.md), [`STACK_POSTURE.md`](../../docs/agent-os/STACK_POSTURE.md).

Locks honored to the letter: **A27** (Postgres via Supabase; uploads in Supabase Storage; LangGraph Postgres checkpointer; anonymous per-browser ownership; reusable pieces in `lab_shared` with declared consumers), **A28** (versioned migrations), baseline **D5** (one Railway service serves the built UI same-origin), spec **D1/D2/D4** (calibration bar, noise margin, judge family — D4 re-locked 2026-10-03: OpenAI judge + support checker, Anthropic writer; see § Amendment 2026-10-03).

Code facts (2026-10-03): `app/store.py` `InMemoryStore` + `UploadStore` (dicts); `lab_shared.jobs.JobRunner` in-memory; five agents hardcode `"openai:gpt-4o"`; `generate_graph.openai_generate_enabled()` selects `_run_generate_without_llm` when no key or a fake key (the test seam), and the same key sniffing appears in `revise_graph.openai_revise_enabled()` (canned `write_turn_canned` writer) and `assessor.openai_assess_enabled()` (`assess_draft_heuristic` fallback); generate graph nodes `infer → materials → web → scored_loop → provenance`, revise graph `scored_revise`; graphs compiled without a checkpointer; UI built by hand and committed under `app/static/ui/` (24 files) and `web/out/`; no SWV2 staging footprint (`deploy/railway/staging/` has research-auditor only); uploads capped at 5 MiB.

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

- **Decision (P1 lock — named LangGraph nodes, unchanged topology):** generate graph `infer → materials → web → scored_loop → provenance`; revise graph `scored_revise`. Both are compiled with **`AsyncPostgresSaver`** (`langgraph-checkpoint-postgres`), `thread_id = job_id`. **Execution (locked 2026-10-03, review P2): Procrastinate**, an OSS Postgres-backed task queue. It runs as an in-process async worker in the same service and database, and supplies atomic claims, heartbeats, stalled-job retry, and enqueue-once locks. Resumed attempts call `ainvoke(None, {"configurable": {"thread_id": job_id}})`. After 2 attempts the job is `failed`, `interrupted_retry`. Resume granularity is per node (an interrupted `scored_loop` restarts that node). Protocol: data-model § Job execution.
- **Rationale:** A27 letter; matches "never silently lost" (SW-D3) at the smallest topology change.
- **Pattern source:** `lab_shared.jobs.JobRunner` (retired for SWV2; V1/RA keep it).
- **Alternatives considered:** **LangGraph Platform / LangGraph Server** (managed durable runs with built-in resume). Strongest SOTA fit, but adds a host and a vendor beyond A27. **Temporal / Inngest / Hatchet** (durable workflow engines). **pgqueuer** (OSS Postgres queue; leaner, fewer built-ins for stalled jobs). **JobRunner plus hand-built leases** in the `jobs` table (rejected: we would reimplement claim, heartbeat, and stalled recovery). Migrate trigger to Temporal/LangGraph Platform: multi-step human-in-the-loop waits or jobs longer than about 30 minutes.

## Block: Data store

- **Decision:** Dedicated Supabase project for SWV2 (backlog P6). Tables: `owners`, `conversations`, `messages`, `artifact_versions`, `run_states`, `uploads` (metadata; bytes in a private Storage bucket), `provenance_records`, `jobs`, `storage_deletions` (Storage outbox); checkpointer and queue tables in per-environment schemas under per-environment logins (D5 locked; data-model § Environments). Cascade: `conversations` → every owned row via `ON DELETE CASCADE`; Storage objects deleted through the outbox after the row (data-model § Sweep protocol). Access: **psycopg 3 async pool** with hand-written SQL in repositories. **Migrations: dbmate** (SQL files with `-- migrate:up` / `-- migrate:down` under `apps/smart-writer-v2/db/migrations/`; `schema.sql` dump committed and diff-checked in CI).
- **Rationale:** The schema is small (9 tables); SQL-first migrations with explicit down blocks give the rollback path (FR-006). dbmate is a single binary in nixpkgs, language-agnostic, so V1/RA can adopt it in a subsequent sprint without SQLAlchemy.
- **Pattern source:** `db/supabase/*.sql` (greenfield `IF NOT EXISTS`, retired by A28 for new schema).
- **Alternatives considered:** **Alembic + SQLAlchemy 2** (mainstream Python; adds an ORM stack we would not otherwise use). **Atlas** (declarative schema-as-code with migration linting; SOTA, but key features moved to the paid tier). **Supabase CLI migrations** (`supabase db push`; managed-native, but ties CI to the Supabase CLI and project linking). **Neon** (serverless Postgres with free instant branching, ideal for staging/preview DBs). Rejected because it splits from the A27 letter; noted as the staging alternative if Supabase project slots run out (see D5). **Postgres `bytea` for uploads** (simpler cascade). Rejected by the A27 letter (Supabase Storage).

## Block: Search / retrieval / LLM

- **Decision:** Per-role model ids from typed Settings (`SMART_WRITER_V2_MODEL_{WRITER,ASSESSOR,EXTRACTION,INFER}`), with defaults set from the bake-off. Role → agent: writer = `agents/writer.py`; assessor = `agents/assessor.py`; infer = `agents/infer.py`; extraction = `agents/infer_state.py` + `agents/provenance.py`. The spec's judge role (judge + support checker) is configured in eval settings (`SMART_WRITER_V2_MODEL_JUDGE`, `SMART_WRITER_V2_MODEL_SUPPORT`), since it never runs in the deployed app. A **price table** in `lab_shared.model_config` feeds a per-job **pre-call reservation**: worst-case cost from counted input tokens and the role's provider-enforced `max_output_tokens`, reconciled with actual usage after each call. Unknown prices fail closed (D3; never above $3; plan § Spend ceiling). The **judge and support checker** are OpenAI models via PydanticAI's OpenAI provider (already a runtime dependency); they run only in eval CI and locally, never in the deployed app. The **writer** is an Anthropic model via PydanticAI's Anthropic provider (`pydantic-ai-slim[anthropic]`, runtime); `models_config` refuses an OpenAI writer id, and writer candidates exclude OpenAI (D4). Families of the assessor, infer, and extraction roles: D9. Interim models before the bake-off: writer D8, judge + support D10.
- **Rationale:** Evidence-chosen models (SW-M1..M3); judge family separation (SW-E3).
- **Pattern source:** baseline agents.
- **Alternatives considered:** **OpenRouter** (one key, many families; good for bake-offs, but a broker in the spend path). **LiteLLM proxy** (OSS gateway with budgets; would give dollar budgets natively, at the cost of a service to run). Migrate trigger: more than 2 providers in production.

## Block: Evals

- **Decision:** **pydantic-evals** `Dataset` / `Case` over `apps/smart-writer-v2/evals/golden/*.yaml`, each tagged `tuning` or `heldout`. Custom evaluators:
  - `ProgramOfficerJudge` — per-dimension 1–5 scores with rationale; OpenAI (D4; model D10).
  - `SourceSupport` — per cited claim: supported or unsupported; OpenAI (D4; model D10).
  - `Latency`, `Cost`.

  Results are reported to Logfire, and the GitHub Actions job summary and artifacts. **Per PR (paired, locked 2026-10-03):** main and PR heads both run the tuning subset in one job. Band = p95 of |Δ| over ≥ 10 no-change pairs (floors 0.25 / 0.05). Any dimension or the support rate dropping more than its band blocks. The gate is report-only until ≤ 1 false alarm in the last 10 no-change pairs and D1 is met. **Nightly:** one no-change pair plus the full tuning set (monitoring + latency). **Held-out:** sealed until the post-mortem. Details: contracts/evals.
- **Rationale:** PydanticAI-native, so it shares models and agents with the app (the engine-learning goal); results land in Logfire, already in the stack.
- **Pattern source:** none.
- **Alternatives considered:** **Braintrust**, **LangSmith** (managed eval platforms with datasets, experiment diffs, and human review UIs). Best-in-class review UX, but add vendors and secrets. **promptfoo** (OSS, CI-first, YAML), **Inspect AI** (OSS, rigorous; UK AISI), **DeepEval** (OSS pytest-style). pydantic-evals is chosen for stack coherence; Braintrust is the migrate trigger if governor review of drafts needs a UI beyond markdown sheets.

## Block: Secrets / preview gate

- **Decision:** Preview audit secret unchanged (baseline). **Ownership** = a server-issued random 256-bit token in an **HttpOnly, Secure, SameSite=Lax cookie** `swv2_owner`, set on first visit; the database stores only its SHA-256. New runtime secret names (schema + Settings): `SMART_WRITER_V2_DATABASE_URL`, `SMART_WRITER_V2_SUPABASE_URL`, `SMART_WRITER_V2_SUPABASE_SECRET_KEY`, and `ANTHROPIC_API_KEY` (writer, D4; production + staging). **CI** secret names: `ANTHROPIC_API_KEY` (eval drafts) and `OPENAI_API_KEY` (judge + support checker) (eval runs; spend, so governor-only gate category), declared in the secrets schema for a GitHub Actions target.
- **Rationale:** An HttpOnly cookie keeps the ownership token away from page scripts. Same-origin (D5) makes cookies simple.
- **Pattern source:** baseline audit-secret pattern.
- **Alternatives considered:** **Supabase Anonymous Sign-ins** (managed, SOTA: anonymous JWT that can be linked to a real account, plus RLS). Attractive for the accounts direction (out of scope this version, SW-X1); rejected now because the browser never talks to Supabase directly, so RLS adds nothing yet. **Migrate trigger:** the accounts sprint. **localStorage key in a header**: readable by any script on the page.

## Block: Topology & runtime custody

- **Decision:**
  - Runtimes per environment: one Railway service `smart-writer-v2` (FastAPI + static UI) plus one Supabase project (Postgres + Storage).
  - **Environments**: production (exists) and staging (**new footprint**; D5 locked: per-env schemas in the SWV2 project).
  - UI → API: same-origin fetch; the cookie is sent automatically; the preview secret stays as in baseline.
  - Custody: database URL, Storage key, and provider keys (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) are held by the service only (never in the browser); eval runs read both provider keys from Infisical at job time via GitHub OIDC (`vars.INFISICAL_MACHINE_IDENTITY_ID`, `scripts/infisical_oidc_login.py`), the lab's existing CI path (backlog A20/A21) — no GitHub repository secrets (the judge's OpenAI use is eval-only).
  - Cattle: `deploy/railway/staging/smart-writer-v2.yml`, `deploy/secrets/schema.yaml`, migrations in git, and the CI migration job.
- **Rationale:** Smallest change that meets FR-006 (staging before production).
- **Alternatives considered:** separate staging Supabase project; Neon branch (both in plan § Staging database).

## Other forks

- **Test seam removal:** delete `openai_generate_enabled` / `_run_generate_without_llm`. Agents are built by role factories from config; tests use PydanticAI `Agent.override(model=TestModel() | FunctionModel(...))` plus `ALLOW_MODEL_REQUESTS = False`. A `graph-node-coverage` test asserts every node name appears in the LangGraph stream for generate and revise. Alternative: VCR-style recorded HTTP (`pytest-recording`), which is more realistic but brittle across model versions; kept for a single nightly smoke only.
- **Retention sweeper:** in-process hourly asyncio task (single replica); idempotent; claims the row, deletes it (cascade) while enqueuing its Storage objects in the outbox, then drains the outbox (data-model § Sweep protocol). Alternatives: **pg_cron** (managed in Supabase) cannot delete Storage objects safely; **GitHub Actions scheduled job** needs database credentials in CI.
- **UI disclosure test (FR-004a):** vitest + Testing Library component test in `web/` (row deletion date, footer notice). Alternative: Playwright end-to-end against the built image (stronger, but needs a browser in CI for one assertion).
- **Per-PR eval spend ledger:** the eval job sums costs from prior eval check runs on the same PR (checks API) and refuses beyond $2 (spend, so a governor-only gate). Skips when the app-tree hash is unchanged since the last eval run on the PR.

## Amendment 2026-10-03 — D4 re-lock (§G.1; record → [`PLAN_DELTA.md`](./PLAN_DELTA.md))

- **Overturned decision:** "judge and support checker are Gemini via `pydantic-ai-slim[google]`, eval CI only; writer candidates exclude Gemini."
- **New decision (governor lock, letter):** judge + support checker are **OpenAI**; the writer is **Anthropic**; bake-off writer candidates exclude OpenAI. The shape lock "judge is a different model family from the writer" is unchanged.
- **Consequences:** Anthropic joins the production and staging runtime (the writer runs in the deployed graph), not only eval CI as Gemini did; `ANTHROPIC_API_KEY` replaces `GEMINI_API_KEY` in the vault, schema, Settings, manifests, and workflow secrets; `OPENAI_API_KEY` stays (runtime roles D9 leaves on OpenAI + eval judge); the Google provider extra is dropped and the Anthropic extra added at runtime. Production now talks to 2 providers, which is at — not past — the OpenRouter/LiteLLM migrate trigger ("more than 2 providers in production").
- **Interpretation recorded:** "the writer moves to Anthropic" is read at letter fidelity as an Anthropic-only writer (the bake-off compares Anthropic models for the writer role). Adding a third family to the writer bake-off would be a new governor decision (new key).
- **Alternatives considered:** **Gemini judge, OpenAI writer** (the superseded lock — kept no Anthropic runtime dependency, but added a third vendor account for eval only); **Anthropic judge, OpenAI writer** (swaps the roles; keeps production single-provider; not chosen by the governor); **OpenRouter** as one broker key for both families (managed, simplifies custody; still a broker in the spend path — migrate trigger above).
