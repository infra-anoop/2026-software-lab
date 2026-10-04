# Feature Specification: Smart Writer V2 — durable state + measured quality (delta)

**Feature Branch**: `002-swv2-durable-evals` (spec directory; work lands on `main` via PRs)

**Created**: 2026-10-03

**Status**: Approved (2026-10-03 — review Blocker and Debates locked per review-locks table; D3 open by design until bake-off). Amended in place 2026-10-03: D4 re-locked (OpenAI judges, Anthropic writes) with new Open Decisions D8–D10 → [`PLAN_DELTA.md`](./PLAN_DELTA.md)

**Input**: Governor intent session 2026-10-03 → [`intent.yaml`](./intent.yaml). Sprint charter: [`notes/sprints/2026-10-sprint-02.md`](../../notes/sprints/2026-10-sprint-02.md). Backlog locks A27 (durable state), A28 (real migrations).

**Baseline**: This is a **delta** against the frozen v2.0 spec [`specs/smart-writer-v2/spec.md`](../smart-writer-v2/spec.md). Everything in the baseline (grant beachhead primacy, grounding invariant, revise-by-default, dual-axis scored inner loop, D1–D9 locks, SC-001–007) stays in force unless this spec says otherwise. Factory intents in [`specs/001-factory-v2/intent.yaml`](../001-factory-v2/intent.yaml) govern how this work is done.

**Why this feature exists**: Two gaps keep Smart Writer V2 from being a real product and from being a usable test bed for the factory: (1) every deploy erases all user work; (2) nothing measures whether drafts are good, so no change — human or agent — can be shown to improve the product.

**Positioning of the quality gate**: The gate measures consistency against a governor-calibrated synthetic proxy. Transfer to real grant work is checked separately by a held-out slice and a blinded governor review each post-mortem (US2); the gate does not claim more than that.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — My work survives (Priority: P1)

As a writer, my conversations, every draft version, and my uploaded materials are still there after the service is redeployed or restarted; only I (my browser) can see them; each conversation shows when it will be deleted and that it is stored for this browser only; everything it owns is deleted 30 days after I last used it.

**Why this priority**: Today a deploy wipes everything, which makes the product unusable for real work and blocks learning from real usage. (SW-D1, SW-D2, SW-D4, SW-D5, SW-D6)

**Independent Test**: Create conversations with drafts and uploads from two browsers; redeploy and restart; each browser sees exactly its own work; opening a conversation moves its deletion date; items idle past 30 days are gone along with everything they own.

**Acceptance Scenarios**:

1. **Given** a conversation with several draft versions and an upload, **When** the service restarts or is redeployed, **Then** all of it is available to the same browser.
2. **Given** two browsers, **When** each lists conversations, **Then** neither sees the other's.
3. **Given** a conversation idle more than 30 days, **When** retention runs, **Then** it and everything it owns (messages, versions, run state, checkpoints, uploads, source/provenance records) are deleted; **Given** one idle less than 30 days, **Then** it is kept.
4. **Given** a schema change, **When** shipped, **Then** it is applied as a versioned migration, proven against a real database in CI and on staging before production, with a rollback path.
5. **Given** the owning browser opens, views, edits, uploads to, or generates in a conversation (or a job in it completes), **When** that happens, **Then** the conversation's 30-day clock restarts.
6. **Given** any conversation, **When** shown in the UI, **Then** its deletion date and a "stored in this browser only — clearing browser data loses access" notice are visible.

---

### User Story 2 — Every change is measured (Priority: P1)

As the governor, every PR that touches Smart Writer V2 shows how draft quality moved — per quality dimension — as judged by a calibrated reader who thinks like a busy program officer; a PR that makes any one dimension worse beyond normal noise, or that makes cited claims less supported by their sources, is blocked unless overridden with a reason.

**Why this priority**: This is direction A ("measure first") and the factory's fitness function for this workload. (SW-N1, SW-Q1..Q8, SW-E1..E3)

**Independent Test**: Run paired main-vs-main comparisons on an unchanged build repeatedly (noise band); submit a PR that degrades only one dimension — blocked; submit a PR that degrades source support — blocked; submit a no-op PR — not blocked; every PR shows per-dimension and support scores vs main.

**Acceptance Scenarios**:

1. **Given** a PR touching the app, **When** checks run, **Then** per-dimension scores (funder fit, persuasive narrative, evidence of impact, organizational voice) and the source-support rate are reported against main, within the per-PR eval budget.
2. **Given** a drop in **any one** dimension larger than that dimension's measured noise band, **When** checks finish, **Then** the PR is blocked unless the orchestrator overrides with a reason; gains in other dimensions do not offset it.
3. **Given** a change that does not affect drafts, **When** checks finish, **Then** it is not blocked (no false positive from noise).
4. **Given** the judge, **When** compared with the governor's hand ratings of 10–15 drafts, **Then** it is within 1 point (5-point scale) of the governor on ≥ 80% of drafts for every dimension (**D1**) before the gate is allowed to block.
5. **Given** the golden set, **When** reviewed by the governor, **Then** it contains realistic grant scenarios built from public funder RFPs plus at least one non-grant smoke scenario.
6. **Given** the judge, **When** configured, **Then** it is from a different model family than the writer (judge and support checker: OpenAI; writer: Anthropic — **D4**); configuring an OpenAI model as the writer is refused.
7. **Given** the golden set, **When** split, **Then** a sealed held-out slice exists that is never used for prompt, model, or judge selection; its drafts are generated and scored **only at the post-mortem** (no nightly or per-PR runs).
8. **Given** a post-mortem, **When** held, **Then** the governor blind-reviews about 5 drafts (including held-out ones) and the agreement with judge scores is recorded.
9. **Given** a draft's cited claims, **When** evaluated, **Then** each is checked for whether its source actually supports it, by a model of a different family than the writer; a support rate worse than main beyond noise blocks the PR regardless of quality scores; the governor spot-checks a sample of support judgments at post-mortem.

---

### User Story 3 — Tests tell the truth (Priority: P1)

As the governor, the test suite exercises the real pipeline — with models substituted only at the model boundary — and the application contains no test-only branches.

**Why this priority**: Today most tests run a separate LLM-free pipeline selected by sniffing the API key, so passing tests say little about the shipped path. (SW-T1, SW-T2, SW-Q6, SW-B1)

**Independent Test**: Search the app for test-only branching — none; run tests with a stub model — every pipeline step executes; baseline contract suite stays green; claim provenance is checked on the real path.

**Acceptance Scenarios**:

1. **Given** application code, **When** checked, **Then** it contains no key sniffing or alternate test pipeline.
2. **Given** the test suite, **When** run, **Then** every pipeline step (infer, materials, web, rubric, write↔assess, provenance; and the revise path) is executed.
3. **Given** the baseline acceptance catalog, **When** the suite runs, **Then** every baseline `auto` row still passes.

---

### User Story 4 — Bounded cost, measured time (Priority: P1)

As the governor, no single draft can cost more than $3; time to a complete draft is measured against a 10-minute target (measured, not gated, this version); the real per-draft ceiling is set from measurement.

**Why this priority**: Spend is a governor-only gate category (factory I-P9); durable, longer jobs and stronger models raise exposure. (SW-L1, SW-L2)

**Independent Test**: A job engineered to exceed the ceiling stops with a clear reason; golden-set runs report draft latency.

**Acceptance Scenarios**:

1. **Given** a generate or revise job whose spend would exceed the ceiling, **When** it runs, **Then** it stops and reports why; no job exceeds $3.
2. **Given** golden-set runs, **When** measured, **Then** the 95th-percentile time to a complete draft is reported against the 10-minute target.

---

### User Story 5 — The right models, chosen by evidence (Priority: P2)

As the governor, each pipeline role (writer, assessor, infer, extraction, judge) uses a configured model chosen by evidence: per-role bake-offs pick the cheapest candidate not distinguishable from the best beyond noise, the chosen bundle is then checked end to end, and any model change re-runs the full eval set.

**Why this priority**: Models are hardcoded to one 2024-era model in five places; choices should be evidence-driven. P2 because it depends on US2. (SW-M1..M3)

**Independent Test**: Change one role's model in configuration; the full eval set runs; the bake-off record shows the decision rule applied per role and the end-to-end bundle result.

**Acceptance Scenarios**:

1. **Given** application code, **When** checked, **Then** no model id is hardcoded outside typed configuration.
2. **Given** a bake-off, **When** completed, **Then** each role's choice is recorded with scores and costs, the selected bundle is compared end to end against the current bundle, and the governor locks it.
3. **Given** a model configuration change, **When** a PR is opened, **Then** the full eval set runs (not only the per-PR subset).
4. **Given** judge candidates, **When** compared, **Then** they are ranked by agreement with the governor's calibration ratings, never by their own quality scores.

---

### User Story 6 — Jobs are never silently lost (Priority: P2)

As a writer, if the service restarts while my draft is being produced, the job resumes from its last completed step or ends with a clear failure I can retry — it never just disappears.

**Why this priority**: Pipeline-step checkpointing is a deliberate engine-learning choice (A27); the product promise is only "never silently lost". (SW-D3)

**Independent Test**: Interrupt a job mid-pipeline; restart; the job resumes or is explicitly failed.

**Acceptance Scenarios**:

1. **Given** a job interrupted mid-pipeline, **When** the service restarts, **Then** the job resumes from its last completed step or is marked failed with a reason.

---

### User Story 7 — The shipped UI is built, not committed (Priority: P2)

As the governor, the UI is built as part of producing the deployable image; built assets are not committed to the repository.

**Why this priority**: Manual build-and-commit is error-prone and noisy. (SW-S1)

**Independent Test**: Built UI assets are absent from the repository; the deployable image serves the UI.

---

### Edge Cases

- A browser key is lost → that browser's conversations are unreachable (accepted until accounts — SW-D4); the UI notice (US1 #6) says so in advance.
- A job completes after its conversation passes 30 days idle → completion counts as use; retention restarts.
- An upload exceeds limits → baseline D7 limits still apply.
- The eval budget would be exceeded on a PR → the run stops at the budget and the PR reports partial results as "incomplete", not as a pass.
- The noise band is not yet measured → the gate reports but does not block until measured.
- The judge is not yet calibrated (D1 unmet) → the gate reports but does not block.
- The nightly full set finds a regression the per-PR subset missed → a regression item opens on the factory board, owned by the orchestrator, and every subsequent app PR reports it until resolved or overridden with a reason (plan defines time bound).
- A migration fails on staging → production deploy does not proceed.
- Legacy V1 / Research Auditor → untouched this sprint (SW-X4).

## Requirements *(mandatory)*

### Functional Requirements

**Durability**

- **FR-001**: Conversations, messages, every draft version, and internal run state MUST persist across deploys and restarts. (SW-D1)
- **FR-002**: Uploaded materials MUST persist across deploys and restarts. (SW-D2)
- **FR-003**: Every conversation MUST belong to an anonymous per-browser key; a browser MUST see only its own conversations. (SW-D4)
- **FR-004**: A conversation and everything it owns — messages, all draft versions, internal run state, job checkpoints, stored uploads, source/provenance records — MUST be deleted 30 days after last use. "Use" = the owning browser opening, viewing, editing, uploading to, or generating in the conversation, or a job in it completing. Eval artifacts built only from synthetic golden-set data are outside this lifecycle. (SW-D5)
- **FR-004a**: The UI MUST show each conversation's deletion date and a notice that it is stored for this browser only and is lost if browser data is cleared. (SW-D4, SW-D5)
- **FR-005**: Jobs MUST checkpoint per pipeline step; an interrupted job MUST resume or be marked failed with a reason. (SW-D3)
- **FR-006**: Schema changes MUST ship as versioned migrations, proven against a real database in CI and on staging before production, with a rollback path. (SW-D6)

**Measured quality**

- **FR-007**: The product MUST have a golden set of grant scenarios (public funder RFPs + synthetic orgs) plus ≥1 non-grant smoke scenario, reviewed by the governor. The set MUST include a held-out slice never used for prompt, model, or judge selection. (SW-Q8)
- **FR-008**: A judge MUST score drafts on funder fit, persuasive narrative, evidence of impact, and organizational voice, reading as a busy program officer. (SW-Q1..Q5)
- **FR-009**: The judge MUST be from a different model family than the writer — the judge and the support checker are OpenAI models and the writer is an Anthropic model (**D4**); writer candidates therefore exclude OpenAI. Which other pipeline roles must also stay off OpenAI is **D9**. (SW-E3)
- **FR-010**: Judge agreement with the governor's hand ratings MUST be measured as the share of calibration drafts where judge and governor are within 1 point on a 5-point scale, per dimension; the eval gate MUST NOT block until that share is ≥ 80% for every dimension (**D1**). (SW-Q7)
- **FR-011**: Every PR touching the app MUST report per-dimension and source-support scores against main within ~$1–2 eval spend, on a per-PR subset covering every scenario category outside the held-out slice (selection/rotation defined in plan). The full tuning set runs nightly (never the held-out slice); a nightly-only regression opens a board item per Edge Cases. (SW-N1, SW-E2)
- **FR-012**: Each PR eval MUST score main and the PR side by side on the same subset (paired). A PR MUST be blocked if any single dimension drops vs main by more than that dimension's noise band, calibrated from paired no-change comparisons (statistic defined in plan); gains in other dimensions MUST NOT offset. The gate MUST stay report-only until about 10 no-change comparisons show it rarely false-alarms (threshold in plan). Overridable by the orchestrator with a reason. (SW-E1)
- **FR-013**: Grounding MUST remain a structural pipeline invariant checked through claim provenance on the real path — not a judge quality dimension. (SW-Q6)
- **FR-013a**: Each cited claim in eval drafts MUST be checked for whether its source supports it, by a model of a different family than the writer. A support rate worse than main beyond noise MUST block the PR regardless of quality scores (orchestrator override with reason). The governor spot-checks a sample at each post-mortem. (SW-Q6, SW-E1)
- **FR-013b**: At each post-mortem the governor MUST blind-review about 5 drafts (including held-out ones); agreement with judge scores is recorded. (SW-Q7)

**Models**

- **FR-014**: Each role's model MUST come from typed configuration; no hardcoded model ids. (SW-M1)
- **FR-015**: A per-role bake-off MUST choose the cheapest candidate not distinguishable from the best beyond measured noise on every dimension (**D2**); the selected bundle MUST then beat or match the current bundle end to end; judge candidates MUST be ranked by agreement with governor calibration ratings, not their own scores; candidate families follow D4 (writer: Anthropic; judge and support checker: OpenAI) and D9 (other roles); the governor locks the result. (SW-M2)
- **FR-016**: Any model configuration change MUST trigger the full eval set. (SW-M3)

**Limits**

- **FR-017**: A job MUST stop when its spend would exceed the per-draft ceiling (**D3**; never above $3). (SW-L1)
- **FR-018**: Time to a complete draft MUST be measured and reported against a 10-minute p95 target; this version does not gate on it (canonical workload and sample defined in plan). (SW-L2)

**Test and ship hygiene**

- **FR-019**: Application code MUST NOT contain test-only branching or an alternate test pipeline. (SW-T1)
- **FR-020**: Tests MUST execute every pipeline step with models substituted only at the model boundary. (SW-T2)
- **FR-021**: Baseline acceptance `auto` rows MUST remain green. (SW-B1)
- **FR-022**: The UI MUST be built during image production; built assets MUST NOT be committed. (SW-S1)

### Key Entities

- **Browser key** — anonymous owner of conversations.
- **Conversation / Message / ArtifactVersion / InternalRunState** — baseline entities, now durable; conversation owns all derived records for deletion.
- **Stored upload** — durable upload bytes + metadata, owned via conversation.
- **Job checkpoint** — last completed pipeline step for a job.
- **Golden scenario** — funder RFP excerpt + synthetic org materials + prompt + expectations; tagged tuning or held-out.
- **Judge score** — per-dimension scores for a draft from the judge.
- **Support judgment** — per cited claim: supported / not supported by its source, with checker model.
- **Calibration rating** — governor's hand rating of a draft, per dimension (calibration or blinded post-mortem review).
- **Eval run** — scores for a build over the golden set (per-PR subset or nightly full), with cost and latency.
- **Bake-off record** — per-role model candidates, scores, costs, decision; end-to-end bundle comparison.

## Success Criteria *(mandatory)*

### Failable outcome classes

- **SC-001 Survival**: After a redeploy and a restart, 100% of seeded conversations, draft versions, and uploads are available to their owning browser.
- **SC-002 Isolation**: Zero cases of one browser key seeing another's conversations.
- **SC-003 Retention**: Items idle > 30 days are deleted together with every owned record type in FR-004; items idle < 30 days remain; each "use" action in FR-004 restarts the clock (100% in seeded fixtures).
- **SC-004 No silent loss**: 100% of interrupted jobs end resumed or explicitly failed.
- **SC-005 Measured**: 100% of PRs touching the app report per-dimension and support scores vs main within the per-PR budget.
- **SC-006 Gate is right**: A seeded regression in any single dimension beyond its noise band is blocked even when other dimensions improve; a seeded support regression is blocked; a no-op change is not blocked.
- **SC-007 Calibrated**: Judge within 1 point of governor on ≥ 80% of calibration drafts for every dimension before the gate blocks.
- **SC-008 Truthful tests**: Zero test-only branches in app code; every pipeline step executed by tests; baseline `auto` rows green.
- **SC-009 Spend bound**: Zero jobs exceed $3; a job engineered to exceed the ceiling stops with a reason.
- **SC-010 Latency measured**: p95 time to complete draft on the golden set is reported against the 10-minute target (not gated).
- **SC-011 Evidence-based models**: Every role's model has a bake-off record including the end-to-end bundle comparison; judge candidates ranked by calibration agreement; model changes trigger the full eval set.
- **SC-012 Migration safety**: Migrations pass against a real database in CI and on staging before production.
- **SC-013 Held-out honesty**: Held-out scenarios appear in zero runs before the post-mortem (per-PR, nightly, bake-off, prompt, judge selection); held-out scores and a blinded governor review are recorded at sprint post-mortem.
- **SC-014 Retention disclosure**: 100% of conversations in the UI show a deletion date and the browser-only notice.

### Aspirational

- Eval scores rise across the sprint on the same golden set (bake-off + measured prompt pass in Wave 3).
- The governor agrees the top-scored drafts are the ones they would send; held-out scores track tuning-slice scores.

### Acceptance catalog

Check instances: [`acceptance.md`](./acceptance.md).

## Delivery lanes *(Wave 2 — from sprint charter)*

| Lane | Stories | Ordering constraint |
|------|---------|---------------------|
| Models + tests | US3, US5 (config part) | First to touch the generate/revise graph |
| Evals | US2, US5 (bake-off) | Needs per-role model config |
| Durability | US1, US6 | Checkpointing after the Models lane's graph changes |
| Ship | US7, US4 latency measurement | Independent (the latency report rides the Evals nightly run, which owns the harness → plan P2b) |

US4 spend ceiling (FR-017) lands with the Models + tests lane.

## Open Decisions *(constitution §G)*

| id | shape_locked | content_open | who | before | status | arch_impact | fidelity |
|----|--------------|--------------|-----|--------|--------|-------------|----------|
| **D1** | Judge must agree with governor hand ratings before the gate blocks | Agreement threshold | human | Before the eval gate blocks | **locked** (2026-10-03) — within 1 point (5-point scale) on ≥ 80% of calibration drafts, every dimension | content-only | letter |
| **D2** | Best-value rule: cheapest within a small margin of best quality | Margin size | human | Before bake-off lock | **locked** (2026-10-03) — not distinguishable from the best beyond measured noise, on every dimension | content-only | letter |
| **D3** | Hard outer limit $3 per draft; real ceiling from measurement | Real per-draft ceiling | human | After bake-off measurement, before production uses new models | open (by design — governor sets after measurement; governor confirmed 2026-10-03: stays open until the bake-off reports costs, all building except the production model switch proceeds) | content-only | |
| **D6** | Model-change PRs run the full eval set (FR-011), which can exceed the per-PR budget | Spend budget for a model-change PR's full run | human | Before the eval workflow ships | **locked** (2026-10-03) — **$10** per model-change PR; beyond that the run waits for governor approval | content-only | letter |
| **D7** | The nightly full tuning run has no spend cap | Nightly spend cap | human | Before the eval workflow ships | **locked** (2026-10-03) — **$5** per night; if the estimate is higher the run is skipped and flagged on the factory board | content-only | letter |
| **D4** | Judge is a different model family from the writer; needs a second provider key in the vault | Which provider/family judges | human | Before Evals lane | **re-locked** (2026-10-03, governor) — **OpenAI** judges (judge + support checker); the **writer is Anthropic**; bake-off writer candidates exclude OpenAI. Vault/CI key for the writer side: `ANTHROPIC_API_KEY` (production, staging, eval CI); `OPENAI_API_KEY` stays (judge in eval CI). Superseded lock (2026-10-03): Google Gemini judges, writer candidates exclude Gemini. Reconcile → [`PLAN_DELTA.md`](./PLAN_DELTA.md) | architecture-affecting (runtime provider + vault secret + provider adapter) | letter |
| **D8** | The writer is Anthropic (D4); the eval baseline (plan P2b) must score Anthropic drafts before the bake-off (P3) picks the writer, so the models work (P1a) ships an Anthropic default | Which Anthropic model is the interim default writer until the bake-off lock (also the interim model for any role D9 moves off OpenAI, unless the governor names another) — options and cost-per-draft in [`FINISH_BAR.md`](./FINISH_BAR.md) § Delta 2026-10-03 | human | Before the P1a models default ships (tasks T105 before T030) | **locked** (2026-10-03) — Anthropic **mid tier (current Sonnet)**, about $0.25 per draft; T105 records the exact current model id + price before T030 | | |
| **D9** | Only the writer's family is fixed by D4; the assessor (scores each inner turn and steers the writer's revisions), infer (slots, ranking, search query), and extraction (claim → source mapping) roles never author draft text | Which of assessor / infer / extraction must also stay off OpenAI (and therefore off the judge's family) — options in [`FINISH_BAR.md`](./FINISH_BAR.md) § Delta 2026-10-03 | human | Before the P1a models default ships (tasks T106 before T030; T026 role-family clause) | **locked** (2026-10-03) — **writer and assessor** stay off OpenAI (both use the D8 model); infer and extraction may stay on OpenAI | | |
| **D10** | Judge and support checker are OpenAI (D4); at the bake-off, judge candidates are ranked by agreement with the governor's calibration ratings (FR-015, US5 #4); no OpenAI model is named for the eval baseline before then | Which OpenAI model judges, and which checks source support, from the first live eval run (P2b) until the bake-off re-ranks judges — options in [`FINISH_BAR.md`](./FINISH_BAR.md) § Delta 2026-10-03 | human | Before the eval settings default ships and before any live eval run (tasks T107 before T082) | **locked** (2026-10-03) — governor calibration ratings pick the judge between OpenAI's **current flagship** and its **previous generation**; a **small, cheap OpenAI model** checks citations; T107 records exact ids + prices | | |
| **D5** | Migrations proven on staging before production (FR-006); SWV2 has no staging footprint today | Staging database form: schema inside the SWV2 project / separate Supabase project / Neon branch — consequences in plan "Staging database" | human | Before the staging footprint is created and before any production migration | **locked** (2026-10-03) — **staging schemas inside the SWV2 Supabase project** (app, checkpoints, queue), a separate database login per environment, separate upload bucket | **arch** (cost, ops steps, vendor letter) | letter |

## Review locks *(mandatory before Approved)*

Report: [`SPEC_REVIEW.md`](./SPEC_REVIEW.md) (F1–F9). Reviewer family: GPT.

| ID | Status | Lock |
|----|--------|------|
| **F1** | locked (governor + agent) | Governor: any one dimension beyond its noise blocks, no offsetting (FR-012). Agent → plan: subset selection/rotation and noise statistic; gate reports-only until noise measured and D1 met (Edge Cases) |
| **F2** | locked (governor) | Proxy gate + held-out slice never used for selection + blinded governor review each post-mortem (FR-007, FR-013b, SC-013, positioning note) |
| **F3** | locked (governor) | Non-compensable source-support check by a different family; regression vs main blocks; governor spot-checks (FR-013a, US2 #9) |
| **F4** | locked (governor) | Any open/view/edit/upload/generate or job completion resets the clock; deletion date + browser-only notice always visible (FR-004, FR-004a, SC-014) |
| **F5** | locked (agent — restores "best value" at system level) | Per-role bake-off + end-to-end bundle check; judge candidates ranked by calibration agreement (FR-015, US5 #4) |
| **F6** | locked (agent — restores intent letter) | Deletion cascades through every owned record; synthetic eval artifacts outside lifecycle (FR-004) |
| **F7** | locked (agent) / Later → plan | Latency labelled measured-not-gated (US4, FR-018); plan defines canonical workload and sample |
| **F8** | locked (agent) / Later → plan | Nightly-only regression opens an orchestrator-owned board item reported on later PRs (Edge Cases, FR-011); plan sets time bound |
| **F9** | accepted | Strength: baseline preservation — keep references through plan and tasks |
| **Plan review** | locked (governor 2026-10-03) | Sealed held-out (US2 #7, SC-013); paired PR comparison + report-only until no-change false-alarm check (FR-012); Postgres job queue; D5 staging schemas — see plan review locks |
| **D4 re-lock** | locked (governor 2026-10-03; recorded by orchestrator) | OpenAI judges and checks support; Anthropic writes; judge ≠ writer family unchanged at letter fidelity (US2 #6, FR-009, FR-013a); interim models and role families raised as D8–D10; §G.1 reconcile → [`PLAN_DELTA.md`](./PLAN_DELTA.md) |

## Assumptions

- Postgres via Supabase (A27) in the shared lab project `2026-software-lab`, in SWV2's own schemas with its own logins and buckets (backlog A31) — ops HITL: governor runs the role bootstrap and creates the buckets; names go in the secrets schema.
- Anthropic API key (`ANTHROPIC_API_KEY`) in the vault for the writer — production, staging, and eval CI (D4) — ops HITL. The OpenAI key already in the vault also serves the judge and support checker in eval CI (D4).
- Uploads move to object storage in the same Supabase project.
- Single Railway replica remains acceptable; the in-process rate limiter stays in memory.
- Baseline D7 upload limits unchanged.
- Shared pieces (durable store, model config, eval harness, checkpointer wiring) may live in `modules/lab_shared` as designed-for-reuse modules declaring intended consumers (factory I-A5); V1/RA adopt them in a subsequent sprint (SW-X4).
- Hobbyist scale (~10 users; headroom ~100).

## Out of scope (this version)

- Accounts / sign-in, document editor, streaming, export (a subsequent workspace direction) — SW-X1, SW-X2.
- Funder-intelligence research (a subsequent direction) — SW-X3.
- V1 / Research Auditor adoption — SW-X4.
- Prompt/quality improvements beyond the Wave 3 bake-off and measured prompt pass.
- Gating on latency (measured only).
