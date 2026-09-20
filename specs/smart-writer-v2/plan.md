# Implementation Plan: Smart Writer V2

**Branch**: `smart-writer-v2` | **Date**: 2026-09-15 | **Spec**: [`spec.md`](./spec.md)

**Input**: Feature specification from `/specs/smart-writer-v2/spec.md` (**Approved**; F1–F8, R1–R9)

**Lab rule (constitution §E):** Plan = **Architecture** (first-class) + **Phased delivery**.  
Do **not** run `/speckit-tasks` or implement until both sections are human-approved.  
Phasing references architecture; it does not replace it.

**Plan Architecture review:** Report [`PLAN_REVIEW.md`](./PLAN_REVIEW.md). Brief: [`PLAN_REVIEW_PROMPT.md`](../../docs/agent-os/PLAN_REVIEW_PROMPT.md). Posture: [`STACK_POSTURE.md`](../../docs/agent-os/STACK_POSTURE.md).

**Status**: **Approved** — Architecture + Phased delivery (P1–P8). Core stories done. **Finish bar** = Open Decisions D2–D9 (**all locked 2026-09-20**) + Phase 10 tasks. **§G.2:** [`FINISH_BAR.md`](./FINISH_BAR.md) — **Implement unblocked: yes**. **§G.1:** [`PLAN_DELTA.md`](./PLAN_DELTA.md). **Amendments:** dual-axis scored loop (**D8**); **D5** = v0 design + Railway UI deploy; **D7** uploads in-memory; **D9** = single revise path + explicit regenerate.

## Remaining work map (V2 finish)

Governor view — lock **D\*** in product language; agents keep task IDs in git. **Order = execution order only; every row stays required until done or waived.**

| Order | Goal | Open Decision | Tasks |
|------|------|---------------|--------|
| 1 | Preview secret in vault + sync | **D6** locked | T070 |
| 2 | Production worker = latest `main` | — (ops) | T071 |
| 3 | Outer/inner numeric caps in Settings | **D2** locked (3 / 10 / 8) | T063 |
| 4 | Dual-axis scored writer↔assessor loop | **D8** locked | T078–T086 |
| 5 | Observability wired + elapsed/tokens on jobs | **D3** locked | T064 |
| 6 | Citation + prefs in **Settings** panel | **D4** locked | T065 |
| 7 | v0 design → UI live on **Railway** | **D5** locked | T069 |
| 8 | File uploads (in-memory) | **D7** locked | T073–T076 |
| 9 | Outer revise = one path; start over = explicit control | **D9** locked | T087 (verify UI control survives v0 design) |
| 10 | Final green + smoke | — | T068*, T077 |
| — | Property labels | **D1** locked | — |

**Execute posture:** Do not invent open content. Prefer packet + background worker (§H). Sequencing ≠ skipping.

## Review locks (P*)

| ID | Status | Lock |
|----|--------|------|
| **P1** | **amended** (2026-09-20 **D5**) | **Design:** Vercel **v0** generates/refines the Next.js chat UI. **Deploy:** UI ships on **Railway** (same cattle family as the worker) — not Vercel hosting, not Codespaces-only as the product. **Worker:** Railway FastAPI. **Secret custody:** browser never holds preview secret (BFF or equivalent on the Railway UI path). Two surfaces may be one or two Railway services — implement detail in T069; git must declare cattle for the live UI. |
| **P2** | **locked** | **Learning-scope cut:** MVP keeps in-process JobRunner + Tavily (optional) + POST/poll chat. Managed/SOTA alts **explicitly deferred** (not silent): jobs → Inngest/Trigger/Temporal/LangGraph Platform; search → Firecrawl/Jina/vendor web tools; chat protocol → SSE / AI SDK `useChat`. Not product SCs (F5). |
| **P3** | **amended** | **LangGraph:** generate = infer → materials → web → **rubric (dual-axis) → write ↔ assess (scores, ≤8) → provenance**; revise graph may narrow/skip research but **still** runs the scored inner loop (**D8**). PydanticAI `result_type` per node. |
| **P4** | **locked** | **Claim-level provenance in MVP:** `ClaimProvenance` (claim span/quote → `source_id` \| `uncertain`). Retrieval emits **materials_bundle** vs **web_bundle**; SC-004 declare when web yields nothing useful. SC-003/004 hook these fields — not merely nonempty `sources[]`. |
| **P5** | **locked** | **Clarify-before-write in P1:** Grant path with missing Who/Whom/Ask/Why/Evidence ⇒ `type=clarify` only (no generate/revise job). P1 exit includes a must-clarify fixture. Assistant questions are NL-only; do **not** default-expose slot ids (`missing_hints`) to the client. P2 = A-before-B ordering + chips, not “invent clarify.” Clarifiers feed Axis A/B for **rubric construction** (**D8**). |
| **P6** | **accepted** | Strength: clean-room + mode/parent_artifact_id contracts + preview fail-closed + stack-not-as-SC — keep as task-ready bar. |
| **P7** | **in finish** | Uploads (**D7**); Logfire (**D3**); caps (**D2** locked); dual-axis scored loop (**D8** locked); outer revise routing (**D9**) — see Phase 10 |
| **P8** | **accepted** | Phasing order OK; P1 includes clarify-before-write exit (P5). |

## Summary

Build new registry app `smart-writer-v2`: a **chat-first** short-form writer with grant/donation beachhead primacy. Free-form messages drive **generate** or **revise** (continuity by default); internal intent slots + closed property ranking are inferred, not shown as forms. Grounding (materials + web, provenance, research-used-or-declared) is a pipeline invariant. Backend **jobs** run multi-minute pipelines; a **preview gate** protects spend. Surface success = SC-001–007 / `acceptance.md`; lab success = human plan/PR adjudication (R2). MVP DoD bus = Spec Kit `tasks.md` (R6).

## Architecture *(mandatory — first-class)*

### System building blocks

- **UI / clients**: Next.js (App Router) chat UI **designed with Vercel v0**, **deployed on Railway** (**D5**). Primary surface: conversational thread + complete artifact pane + default **sources panel** + **Settings** (citation + future prefs — **D4**). Optional property chips as light correction only.
- **UI BFF**: Server routes (or equivalent) on the **Railway UI** path — hold preview secret; proxy/enqueue to FastAPI worker; browser talks only to same-origin UI.
- **API / application services**: New FastAPI app `apps/smart-writer-v2` (registered in `apps/registry.yaml`) on **Railway** (lab Python cattle). Owns HTTP contracts, Settings/secrets wiring, turn routing (clarify vs enqueue generate/revise), job execution.
- **Orchestration / jobs**: In-process `lab_shared.jobs.JobRunner` runs a **LangGraph `StateGraph`** (**P3** amended): generate nodes **infer → materials → web → dual-axis rubric → write ↔ assess (scores, ≤8) → provenance**; revise may narrow/skip research but **keeps** the scored inner loop (**D8**). Modes: `clarify` / `generate` / `revise`. PydanticAI schema-first `result_type`s per node.
- **Agents / prompt program**: PydanticAI schema-first agents for slot/property inference, research planning, **rubric builder**, **writer**, **assessor (scores)**, provenance. Versioned **prompt program** under the app. Clarify fills F6 axes that feed the rubric.
- **Data stores**: MVP = process-local conversation/artifact store co-located with jobs (restart caveat) **plus** job snapshots. Optional Supabase = later phase.
- **External systems**: OpenAI (or lab-default LLM); **Tavily** optional web search (noop/declare if unset — **P2**); Infisical → env. User materials via URL fetch and/or upload. Firecrawl/Jina/vendor-web **deferred**.

### Boundaries & responsibilities

| Block | Owns | Does not own |
|-------|------|--------------|
| Next.js on Railway (UI + BFF; v0-designed) | Chat UX, Settings, artifact display, sources panel, regenerate; **secret custody** in server routes; calls worker | Pipeline graph internals, acceptance catalog |
| FastAPI on Railway | Preview gate enforcement on worker, rate limits, job enqueue/poll, turn/job API, Settings (server), orchestrator | v0 design studio; browser-held secrets |
| Prompt program | Writer templates, property weave, grant humor default | Runtime secrets, deploy manifests |
| `lab_shared` | JobRunner if still chosen (P3), shared helpers | Product-specific grant logic |
| Legacy `smart-writer` | V1 only | V2 requirements; no back-port duty |

### Topology & runtime custody *(P1 amended — D5)*

- **Design tool**: **Vercel v0** — produce/refine the Next.js chat + Settings UI.
- **Runtimes / hosts (production)**: (1) **Railway** — FastAPI job worker. (2) **Railway** — deployed UI (v0 output), with BFF or equivalent so the browser never sees the preview secret.
- **Not the finish bar**: Vercel as production UI host; Codespaces-only UI dogfood as the shipped product.
- **How UI calls API**: Browser → Railway UI/BFF → Railway worker. No browser→worker with audit secret.
- **Cattle manifests**: Git must declare Railway worker **and** Railway UI (one or two services — T069). No UI-only drift.

### Data & persistence

- Entities: see [`data-model.md`](./data-model.md) — `Conversation`, `Message`, `ArtifactVersion`, `InternalRunState`, `SourceRecord`, `Job`/`Run`.
- **Revise vs generate (SC-006/007):** every writing job/run carries `mode: generate | revise` and every `ArtifactVersion` has `artifact_id`, `parent_artifact_id` (nullable), `producing_mode`. Auto-candidate: assert these fields in API/job result.
- Ephemeral vs durable (MVP): jobs + conversation state **in-memory** (restart loses state — same residual as V1 JobRunner). Client may hold last artifact ids for a session. Durable DB deferred.
- Provenance (**P4**): `ClaimProvenance` rows (claim span or quote → `source_id` | `uncertain`); artifact may still list `source_ids`. Retrieval produces **materials_bundle** vs **web_bundle** (F4); web empty → explicit no-signal declaration (SC-004).

### APIs & contracts

- See [`contracts/http-api.md`](./contracts/http-api.md).
- **Preview gate**: shared-secret header (e.g. `X-Audit-Secret` ↔ `SMART_WRITER_V2_AUDIT_SECRET`) on mutating + job routes; `/health` public; `/ready` checks config (OpenAI present). Declare secret **name** in `deploy/secrets/schema.yaml` + Settings — never commit values.
- Rate limit + queue caps mirror lab Pattern B5 posture (in-process).

### UI surfaces

- **Chat thread**: user free-form; assistant returns either clarifying question(s) or complete artifact.
- **Artifact view**: full draft; version indicator; “Regenerate / start over” explicit control.
- **Sources panel** default when sources exist; one control for inline / footnotes / panel / combo (F7).
- UI talks to backend via **async jobs** for generate/revise: browser → Vercel BFF → FastAPI (**POST → job_id → poll** for MVP — **P2**; SSE/`useChat` deferred). Clarify may be sync short response via BFF.

### Major risks / non-goals for this architecture

- In-memory jobs/conversations: multi-instance and restart loss — acceptable MVP; document in quickstart.
- **Required (D8):** dual-axis scored writer↔assessor loop inside each write job (≤8 turns) — **not** optional, **not** thinner than V1’s scored loop; redesign for two rubric dimensions (F6). Distinct from outer human revise (**D9** still open for tactical vs fuller rerun).
- Do **not** make LangGraph/Next/v0 product pass/fail (F5/R1).
- No blind V1 code port; clean-room app with **pattern** reuse only.
- Cost: turn/job caps (**D2**) and preview gate required before any public URL.

## Phased delivery *(mandatory)*

| Phase | Goal | Architecture pieces touched | Exit criteria (failable) |
|-------|------|-----------------------------|--------------------------|
| **P0** Scaffold | Registry app + FastAPI health/ready + secrets schema stub + Next/Vercel shell + BFF stub | API, registry, secrets, Vercel UI shell | `smart-writer-v2` in registry; `uv sync --locked`; `/health` 200; secret **names** in schema; BFF does not expose audit secret to client |
| **P1** MVP vertical | Chat + BFF + jobs + LangGraph generate/revise + materials/URL + Tavily + **claim provenance** + sources panel + revise continuity + **clarify-before-write** | API, JobRunner, LangGraph, agents, Vercel UI+BFF, prompt program | Grant: missing slots → clarify fixture; rich path → complete artifact with `claims[]`; revise `parent_artifact_id`; regenerate = generate; preview gate; humor default off |
| **P2** Beachhead harden | Intent A-before-B ordering; property chips; citation override; non-grant smoke; catalog `auto` CI | Clarify ordering, property UX, acceptance | FR-003b–c; SC-005; ≥1 `auto` catalog row green |
| **P3** Depth (partial) | Durable persistence; richer uploads; managed jobs/SSE/search **still optional** unless prioritized | Data store, Inngest/SSE/Firecrawl if prioritized | Only if human prioritizes |
| **Finish (required)** | Caps (**D2**); dual-axis scored loop (**D8**); Logfire/citation/Vercel/uploads/routing per open ODs | Settings, rubric/assess graph, ops | See Phase 10 `tasks.md` |

**MVP definition (P1):** Thin but real dogfood — Vercel chat → BFF → Railway jobs; missing grant slots **clarify** first; else complete grounded draft with **claim provenance** + sources panel; feedback → **revise**; explicit regenerate. Preview gate on. **Complete V2 (finish bar):** adds **D8** scored dual-axis inner loop + **D2** caps + remaining open ODs — not a silent skip.

## Technical Context

**Language/Version**: Python 3.12 (API); TypeScript/Node for Next.js UI

**Primary Dependencies**: FastAPI, Pydantic / PydanticAI, **LangGraph (P1 lock)**, `lab_shared.jobs`, Next.js (Vercel), httpx; Tavily optional

**Storage**: MVP in-memory (jobs + conversation); Supabase optional later

**Testing**: pytest (API/orchestrator/contracts); UI smoke later; acceptance catalog hybrid + thin auto

**Target Platform**: Codespaces (dev); **Vercel v0** (UI design); **Railway** (worker + deployed UI)

**Project Type**: Monorepo — `apps/smart-writer-v2/` FastAPI worker (registry) + `apps/smart-writer-v2/web/` Next app **designed via v0**, **deployed on Railway**; BFF on UI path (**D5**).

**Performance Goals**: Multi-minute jobs OK; clarify turns fast; hobbyist scale

**Constraints**: Cattle/secrets/registry; preview gate; cost caps; no durable pip; grounding invariant

**Scale/Scope**: ~10 users (stretch ~100)

## Constitution Check

*GATE: Must pass before tasks/implement. Re-check after architecture edits.*

- [x] Architecture section complete (blocks, boundaries, topology, data, APIs/UI)
- [x] Topology & runtime custody locked (P1)
- [x] Phased delivery present with MVP and exit criteria
- [x] `research.md` alternatives per major block (STACK_POSTURE) — P2 deferred alts explicit
- [x] Orchestrator P1 lock (LangGraph named nodes — P3)
- [x] Plan Architecture review (P*) triaged (P1–P8)
- [x] Human approved Architecture + Phased delivery
- [x] `/speckit-tasks` generated (`tasks.md`) — T* when contract tests exist, then implement
- [x] Secrets/registry/cattle rules respected (names in schema; BFF custody — P1)
- [x] Learning/stack prefs not smuggled as product gates (F5/R1/R2)
- [x] PLAN_AUTHORING_GATES posture addressed via P* locks (topology + non-sibling alts)

## Approval

- [x] P1–P8 human-adjudicated
- [x] Human approves **Architecture + Phased delivery** (this plan)
- [x] Then `/speckit-tasks` (tests required) → T* review when contract/auto tests exist → implement.

## Project Structure

### Documentation (this feature)

```text
specs/smart-writer-v2/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/           # Phase 1
├── acceptance.md        # Lab catalog
└── tasks.md             # After plan approved (/speckit-tasks)
```

### Source Code (repository root)

```text
apps/smart-writer-v2/
  app/                 # FastAPI, orchestrator, agents, retrieval, prompts
  web/                 # Next.js chat UI
  tests/
modules/lab_shared/    # JobRunner reuse only unless a second consumer appears
deploy/secrets/schema.yaml   # SMART_WRITER_V2_* names
deploy/railway/        # when shipping
```

**Structure Decision**: **Clean-room** FastAPI worker `smart-writer-v2` (FR-011) + Next UI (`web/`) **designed with v0**, **deployed on Railway** (**D5**). Reuse `lab_shared.jobs` + patterns only — not V1 product modules. Cattle declares worker + UI.

## Complexity Tracking

> No constitution violations requiring justification.
