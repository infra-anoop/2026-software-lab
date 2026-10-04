# Implementation Plan: Smart Writer V2 — durable state + measured quality (delta)

**Branch**: `002-swv2-durable-evals` (work orders → one branch + PR each) | **Date**: 2026-10-03 | **Spec**: [`spec.md`](./spec.md) (Approved)

**Input**: spec, [`intent.yaml`](./intent.yaml), [`research.md`](./research.md), baseline plan [`../smart-writer-v2/plan.md`](../smart-writer-v2/plan.md), backlog A27–A29, factory plan [`../001-factory-v2/plan.md`](../001-factory-v2/plan.md) (gates this work runs under).

**Lab rule (constitution §E):** Architecture + Phased delivery; human approval after P* triage before tasks.

**Approval:** Architecture + Phased delivery approved by the governor 2026-10-03, after P* triage.

**Amendment (§G.1, 2026-10-03):** D4 re-locked after approval — OpenAI judges and checks source support; the writer is Anthropic. Amended in place (not a re-plan): Summary, External systems, Secret custody, Phased delivery P0/P1a/P2b, Technical Context, Constitution Check, Complexity Tracking. Reconcile record and open D8–D10: [`PLAN_DELTA.md`](./PLAN_DELTA.md).

## Summary

Make every piece of user work durable (Postgres + Storage in a dedicated Supabase project, versioned migrations proven on staging, resumable jobs via the LangGraph Postgres checkpointer, anonymous cookie ownership with 30-day visible retention). Make quality measurable: an OpenAI program-officer judge plus an OpenAI source-support checker in pydantic-evals, scoring drafts from an Anthropic writer (D4), gated per PR by a paired main-vs-PR comparison against a noise band from no-change pairs, calibrated to the governor. Remove the test seam, so tests run the shipped graph with models substituted at the boundary. Models come from per-role config with a per-job cost meter, and the UI is built in the image.

## Architecture *(mandatory — first-class)*

### System building blocks

- **UI / clients**: existing Next.js UI (static export, same-origin). Adds a conversation list, a deletion date, and the browser-only notice.
- **API / application services**: existing FastAPI app. New modules:
  - `app/persistence/` (repositories: `ConversationRepo`, `ArtifactRepo`, `RunStateRepo`, `UploadRepo`, `JobRepo`; Postgres implementations; in-memory test implementations injected only by tests).
  - `app/storage_adapter.py` (Supabase Storage via httpx).
  - `app/ownership.py` (cookie issue and verify).
  - `app/retention.py` (sweeper + `last_used_at` touch).
  - `app/models_config.py` (role → model id from Settings).
  - `app/spend.py` (pre-call reservation + reconciliation against the ceiling; see Spend below).
- **Orchestration / jobs**: **P1 lock: the same named LangGraph nodes** (`infer → materials → web → scored_loop → provenance`; `scored_revise`), compiled with `AsyncPostgresSaver`. **Execution: Procrastinate** (Postgres-backed queue, in-process async worker in the FastAPI lifespan, same database). It provides atomic claims, heartbeats, stalled-job retry, and enqueue-once locks. The `jobs` table is the product-facing record; resumed attempts continue from the last checkpoint; publication is idempotent (data-model § Job execution). `lab_shared.jobs.JobRunner` is retired for SWV2 only (V1/RA keep it).
- **Data stores**: Supabase Postgres with three schemas per environment (app, checkpoints, queue) under a per-environment database login, and a private Storage bucket per environment (data-model § Environments).
- **External systems**: **Anthropic** (writer, D4; plus any role D9 moves off OpenAI) at runtime and in eval CI (drafts are generated through the shipped graph); **OpenAI** at runtime for roles D9 leaves on OpenAI, and in eval CI for the judge and support checker (D4); Tavily (unchanged); Logfire (traces + eval results); Supabase; Railway.
- **Role → family map (D4 + D9)**: writer (`agents/writer.py`, authors every word of the scored draft in `scored_loop` and `scored_revise`) = **Anthropic**, enforced in `models_config` (an OpenAI writer id is refused). Judge + support checker (eval only) = **OpenAI**. Assessor (`agents/assessor.py`, scores each inner turn and feeds revision guidance to the writer), infer (`agents/infer.py`), extraction (`agents/infer_state.py` + `agents/provenance.py`, claim → source mapping after the draft is final) = family per **D9** (open). Interim models: writer per **D8**, judge + support per **D10** (both open); the P3 bake-off replaces them.

**Shared (`modules/lab_shared`, designed for reuse; each module declares consumers `[smart-writer-v2]` now, intended next `[smart-writer, research-auditor]` — I-A5):**
- `lab_shared.db.pool` — psycopg pool from typed settings, health check (new module inside the existing `lab_shared/db/` package; not imported by its `__init__`, so V1/RA stay psycopg-free).
- `lab_shared.checkpoint` — `AsyncPostgresSaver` setup and teardown.
- `lab_shared.model_config` — price table + `CostMeter`.
- `lab_shared.evals` — paired comparison, no-change noise band, per-dimension gate decision, report-only state, spend ledger.

App-specific (schema, repositories, golden set, judge rubric) stays in the app.

### Boundaries & responsibilities

| Block | Owns | Does not own |
|-------|------|--------------|
| `entrypoints/http.py` | Routing, cookie/secret checks, mapping to services | SQL, model calls, retention policy |
| `persistence/*` | SQL + transactions per aggregate; cascade semantics | Business rules (caps, retention timing) |
| `storage_adapter` | Upload bytes put/get/delete | Ownership checks |
| `ownership` | Token issue, hash, lookup; `owner_id` for requests | Retention |
| `retention` | `touch(conversation)` on every use; hourly sweep per data-model § Sweep protocol (claim row, delete rows + enqueue Storage outbox, drain outbox) | Which routes count as use (declared in `entrypoints` per FR-004 list) |
| `orchestrator/*` | Graphs, nodes, checkpointer config | Job records (JobRepo) |
| `spend` + `lab_shared.model_config` | Cost accounting per job; stop before exceeding the ceiling | Choosing models |
| `evals/` (app) | Golden set, subset list, judge and support evaluators, calibration sheets | Gate math (`lab_shared.evals`) |
| CI `swv2-evals.yml` | Per-PR paired subset run, nightly no-change pair + full tuning set ×1, ledger, job summary, check run | Merging decisions beyond its check |

### Topology & runtime custody

- **Runtimes / hosts**: per environment, one Railway service `smart-writer-v2` serving FastAPI and the static UI (baseline D5) plus one Supabase database (form per **D5**). Environments: production (exists) and **staging (new)**.
- **How UI calls API**: same-origin `fetch`; the `swv2_owner` HttpOnly cookie is sent automatically; preview audit secret unchanged.
- **Secret custody**: the service (production and staging) holds `SMART_WRITER_V2_DATABASE_URL`, `SMART_WRITER_V2_SUPABASE_URL`, `SMART_WRITER_V2_SUPABASE_SECRET_KEY`, and the provider keys `ANTHROPIC_API_KEY` (writer, D4) and `OPENAI_API_KEY` (roles D9 leaves on OpenAI). The browser holds only the opaque owner cookie (HttpOnly) and the preview secret (baseline). GitHub Actions holds `ANTHROPIC_API_KEY` (eval drafts come from the Anthropic writer), `OPENAI_API_KEY` (judge + support checker), and `SMART_WRITER_V2_STAGING_DATABASE_URL` (migration proof), plus `TAVILY_API_KEY` (nightly cases honor `web_research`) and `LOGFIRE_TOKEN` (eval results go to Logfire).
- **Production migrations**: run at service start (`python -m app.migrate up`, dbmate in the image) under the production login, so the production database URL never leaves the service. A production ship refuses unless staging has already applied the same migration version, and a ship carrying new migrations waits on governor approval (the "irreversible" gate).
- **Cattle manifests**: `deploy/railway/{production,staging}/smart-writer-v2.yml`, `deploy/secrets/schema.yaml`, `apps/smart-writer-v2/db/migrations/`, `flake.nix` (UI build), `.github/workflows/swv2-evals.yml`, and the migration job in the PR pipeline.

### Staging database *(spec D5 — **locked 2026-10-03: option A**, with per-env checkpoint and queue schemas and per-env logins per review P6)*

The production SWV2 project uses one Supabase free-tier slot. Supabase allows two active free projects per organization, and V1 and Research Auditor already share one.

| Option | What changes | Cost | Ops steps (governor) | Risk |
|--------|--------------|------|----------------------|------|
| **A. Staging schemas inside the SWV2 project** — **locked** | `swv2_staging{,_langgraph,_queue}` vs `swv2_prod{,_langgraph,_queue}`; one database login per env with grants only on its schemas; buckets `uploads-staging` / `uploads-prod`; migrations run on staging first | Free | Create one SWV2 project; add the staging Railway service | A bad migration that touches shared objects (extensions, roles) could affect prod; mitigated because migrations are schema-qualified and CI lints for non-schema-qualified DDL |
| **B. Separate staging Supabase project** | Full isolation | Needs a Pro org (~$25/mo) unless a free slot is freed | Create two projects | None material |
| **C. Neon branch for staging** (Postgres only; Storage stays Supabase) | Free instant branches per PR | Free tier | Neon account + key | Staging DB differs from the prod vendor (not A27 letter: needs a fidelity waive) |

CI proves migrations against the ephemeral Postgres service first, then against staging. A production migration runs only after the same migration succeeded on staging (a governor-only "irreversible" gate). An isolation test proves the staging login cannot read production schemas.

### Spend ceiling *(review P5 — pre-call guarantee)*

Before every model call, `spend` **reserves** the worst-case cost: `price(model).input × counted_input_tokens × 1.1` plus `price(model).output × max_output_tokens`. Here `max_output_tokens` is set per role in model settings and enforced by the provider, and tool and retry calls each reserve separately. The call is refused if `actual_so_far + reservation > ceiling`. After the call, actual usage replaces the reservation. An unknown model or missing price fails closed (job `failed`, `fail_reason = spend_unpriced`). Reservations persist on the `jobs` row, so resumed attempts keep the running total. This keeps the "never above $3" letter.

### Data & persistence

- [`data-model.md`](./data-model.md): tables, cascade, `last_used_at`, jobs, checkpoint linkage.
- Durable: all conversation-owned rows and uploads; jobs and checkpoints (deleted with the conversation). Ephemeral: rate limiter (in-process, baseline). Eval artifacts are synthetic, outside retention (FR-004), kept in GitHub artifacts (90 days) and Logfire. Bake-off records and calibration results are committed under `specs/002-swv2-durable-evals/evidence/`.

### APIs & contracts

- HTTP delta: [`contracts/http-api-delta.md`](./contracts/http-api-delta.md) (cookie, list conversations, `expires_at` fields, job recovery states).
- Evals and gate: [`contracts/evals.md`](./contracts/evals.md) (golden case schema, subset, judge output schema, gate decision, ledger).
- Baseline contracts stay in force: `specs/smart-writer-v2/contracts/`.

### UI surfaces

- Conversation list (owner's only), showing a deletion date per row and a persistent footer notice: "Stored in this browser only. Clearing browser data loses access. Deleted 30 days after last use."
- The job view shows `failed: interrupted — retry` after a restart (SW-D3).

### Major risks / non-goals

- **Judge/proxy validity**: mitigated by the held-out slice + blinded review (FR-007/013b); positioning note in spec.
- **Checkpoint granularity**: `scored_loop` is one node (up to 8 inner turns), so an interrupted loop restarts that node. Acceptable for "last completed step"; splitting the loop into nodes is a post-mortem candidate.
- **Eval cost creep**: ledger + app-tree hash skip; paired runs double per-PR model calls, so the subset is sized to ≤ ~$1.50 per paired run. The D8 writer price sets how many cases fit; if the T079 dry-run cannot cover every tuning category within that size, the orchestrator escalates (no silent shrink of FR-011 coverage).
- **Unmeasured first writer switch (D4 re-lock)**: the P1a ship moves production drafts from `openai:gpt-4o` to the D8 Anthropic model before the eval harness exists (P2b), so FR-016's full eval run cannot accompany that one change; the P2b baseline is recorded on the Anthropic writer, and FR-016 applies to every model change from the eval workflow's first merge (T084). Disclosed to the governor in the D8 question.
- **Cookie on Railway domain**: `Secure` + `SameSite=Lax` on the service domain; `localhost` dev uses non-Secure via Settings.
- Non-goals: accounts, export, multi-replica, splitting `scored_loop`.

## Phased delivery *(mandatory — Wave 2 lanes, cap 3 shared with factory P2)*

| Phase | Lane | Goal | Architecture pieces | Exit criteria (failable) |
|-------|------|------|---------------------|--------------------------|
| **P0 — ops** `[HITL]` | Ops | Footprints exist | SWV2 Supabase project; staging per D5; Railway staging service via `ops_runtime_tag.py bootstrap`; `ANTHROPIC_API_KEY` in the vault, synced to production + staging; GitHub Actions secrets | Secrets schema validates; staging `/health` 200; migration job can reach the staging DB; production and staging Railway services hold `ANTHROPIC_API_KEY` |
| **P1a — Models + tests** (first) | Models+tests | Truthful tests, config models, spend stop, Anthropic writer | Role factories, `models_config` (writer family check), `spend`, seam removal, `Agent.override` fixtures, node coverage; D8/D9 locked before defaults ship | SC-008 (zero seams, all nodes executed, baseline rows green); SC-009 (engineered overspend stops); no hardcoded model ids; writer default is the D8 Anthropic model and an OpenAI writer id is refused |
| **P1b — Durability: storage** (parallel with P1a; disjoint paths) | Durability | Data survives and is isolated | dbmate migrations, repositories, Storage adapter, ownership cookie, retention + disclosure | SC-001, SC-002, SC-003, SC-012, SC-014 against a real Postgres in CI + staging |
| **P1c — Ship** (parallel) | Ship | UI built in the image (latency measurement rides the P2b nightly run, which owns the harness) | `flake.nix` buildNpmPackage; remove committed assets | FR-022 check (no built assets in git); image serves the UI in the offline boot smoke |
| **P2a — Durability: jobs** (after P1a merges) | Durability | Jobs never silently lost | Procrastinate worker, checkpointer wiring, `jobs` table, stalled-job retry, idempotent publication | SC-004 (kill mid-pipeline → resumed or failed with reason) |
| **P2b — Evals** (after P1a merges) | Evals | Measured quality gate | Golden set `[HITL review]`, OpenAI judge + support evaluators (interim models D10), calibration `[HITL]`, nightly paired no-change + tuning monitor, paired per-PR gate + ledger, sealed held-out runner | SC-005, SC-006, SC-007, SC-013; gate blocking only after D1 met |
| **P3 — Bake-off** (Wave 3) | Evals | Evidence-chosen models | Bake-off runner, bundle comparison, judge-by-agreement ranking | SC-011; governor locks bake-off and D3 ceiling |

**MVP definition**: after a redeploy, a browser's conversations, versions, and uploads are still there and nobody else's are visible; an interrupted job resumes or fails visibly; every app PR shows per-dimension and support scores vs main, and a seeded single-dimension regression is blocked once calibrated.

## Technical Context

**Language/Version**: Python 3.12; TypeScript (Next.js static export) for UI

**Primary Dependencies**: FastAPI, PydanticAI (`pydantic-ai-slim[openai,anthropic]`; the judge reuses the runtime OpenAI provider, so the eval group adds no provider extra), LangGraph 1.0 + `langgraph-checkpoint-postgres`, Procrastinate, psycopg 3 (`psycopg[binary,pool]`), pydantic-evals, Logfire, httpx; dbmate (Nix)

**Storage**: Supabase Postgres + Supabase Storage (A27)

**Testing**: pytest; unit tests with in-memory repositories (injected); integration tests against ephemeral Postgres (CI service) for repositories, migrations, cascade, recovery; `Agent.override` + `TestModel`/`FunctionModel` for all model calls; node-coverage test; evals are separate (not pytest)

**Target Platform**: Railway (one service per env), Supabase, GitHub Actions

**Project Type**: monorepo app `apps/smart-writer-v2` + `modules/lab_shared`

**Performance Goals**: p95 draft time measured against 10 min (not gated)

**Constraints**: $3 hard per draft; ~$1–2 per PR eval; single replica; changed-lines architecture lints (factory)

**Scale/Scope**: ~10 users (headroom ~100)

## Constitution Check

- [x] Architecture complete (blocks, boundaries, data, contracts, UI)
- [x] Topology & runtime custody locked (one service per env, same-origin, cookie, custody table); staging DB **D5 locked** (schemas per env)
- [x] Phased delivery with MVP and failable exits
- [x] `research.md` non-sibling alternatives per block (LangGraph Platform, Temporal/Inngest/Hatchet, Procrastinate, Neon, Atlas, Alembic, Braintrust/LangSmith, promptfoo/Inspect, OpenRouter/LiteLLM, Supabase Anonymous Sign-ins, Vercel)
- [x] Orchestrator P1 lock: named LangGraph nodes, unchanged + checkpointer
- [x] P* review triaged — locks table below; governor approved 2026-10-03
- [x] No tasks or implementation started
- [x] Secrets: names only; schema + Settings; CI-only keys declared
- [x] Registry unchanged (same app id); staging footprint via ops packet (P0 `[HITL]`)
- [x] Locks to the letter: A27 (Supabase Storage, checkpointer), D5 baseline one-service, D4 (re-locked 2026-10-03: OpenAI judge + support checker, Anthropic writer)
- [x] **D5** staging database locked (2026-10-03)
- [x] §G.1 delta reconcile for the D4 re-lock recorded in [`PLAN_DELTA.md`](./PLAN_DELTA.md); D8–D10 open (`who: human`) and tasked as `[OD:D#]`

## Project Structure

```text
specs/002-swv2-durable-evals/
├── spec.md · intent.yaml · acceptance.md · SPEC_REVIEW.md
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/{http-api-delta,evals}.md
└── evidence/                # bake-off records, calibration + blinded review results (committed)

apps/smart-writer-v2/
├── app/{persistence/,storage_adapter.py,ownership.py,retention.py,models_config.py,spend.py,migrate.py,worker.py}
├── db/bootstrap/ · db/migrations/ · db/schema.sql
├── evals/{golden/,subset.yaml,judge.py,support.py,run.py,calibrate.py,bakeoff.py}
└── web/                     # source only; no out/ or app/static/ui in git
modules/lab_shared/src/lab_shared/{db/pool.py,checkpoint.py,model_config.py,evals.py}
deploy/railway/staging/smart-writer-v2.yml
.github/workflows/swv2-evals.yml
```

**Structure Decision**: the app owns product-specific schema, evals, and policies; `lab_shared` gets only the four engine pieces V1/RA will plausibly adopt (I-A5 declared consumers).

## Plan review locks *(P\*, [`PLAN_REVIEW.md`](./PLAN_REVIEW.md))*

| ID | Status | Lock |
|----|--------|------|
| **P1** | locked (agent — contract defect) | Sweep claims under a row lock, skips conversations with active jobs, touches reject deleting rows, Storage outbox (data-model § Sweep protocol) |
| **P2** | locked (governor 2026-10-03) | Procrastinate queue; attempts, stalled retry, idempotent publication (data-model § Job execution) |
| **P3** | locked (governor 2026-10-03) | Held-out sealed: generated and scored only at post-mortem (spec US2 #7, SC-013) |
| **P4** | locked (governor 2026-10-03) | Paired main-vs-PR; band = p95 of ≥ 10 no-change pairs; report-only until ≤ 1 false alarm in last 10 (contracts/evals) |
| **P5** | locked (agent — restores "never above $3" letter) | Pre-call reservation, provider token caps, fail closed on unknown price (§ Spend ceiling) |
| **P6** | locked (governor 2026-10-03, D5) | Per-env app/checkpoint/queue schemas + per-env logins + isolation test |
| **P7** | locked (agent) | Content-addressed source snapshots; checker gets captured source text; zero citations score 0 (contracts/evals) |
| **P8** | locked (agent — spec F7/F8 delegated to plan) | Latency workload + nightly-regression owner and 2-working-day bound (contracts/evals § Nightly) |
| **P9** | accepted | Strength — preserve |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New staging environment | FR-006 (staging before prod) | Ephemeral CI Postgres alone does not prove against the real vendor/config |
| Second model provider (Anthropic) in the production runtime, staging, and eval CI | SW-E3 judge independence with an OpenAI judge (D4 re-lock) | Same-family judge rejected by spec D4; keeping OpenAI as writer and moving the judge elsewhere was the superseded Gemini lock |
