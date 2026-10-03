# Feature Specification: Smart Writer V2 — durable state + measured quality (delta)

**Feature Branch**: `002-swv2-durable-evals` (spec directory; work lands on `main` via PRs)

**Created**: 2026-10-03

**Status**: Draft

**Input**: Governor intent session 2026-10-03 → [`intent.yaml`](./intent.yaml). Sprint charter: [`notes/sprints/2026-10-sprint-02.md`](../../notes/sprints/2026-10-sprint-02.md). Backlog locks A27 (durable state), A28 (real migrations).

**Baseline**: This is a **delta** against the frozen v2.0 spec [`specs/smart-writer-v2/spec.md`](../smart-writer-v2/spec.md). Everything in the baseline (grant beachhead primacy, grounding invariant, revise-by-default, dual-axis scored inner loop, D1–D9 locks, SC-001–007) stays in force unless this spec says otherwise. Factory intents in [`specs/001-factory-v2/intent.yaml`](../001-factory-v2/intent.yaml) govern how this work is done.

**Why this feature exists**: Two gaps keep Smart Writer V2 from being a real product and from being a usable test bed for the factory: (1) every deploy erases all user work; (2) nothing measures whether drafts are good, so no change — human or agent — can be shown to improve the product.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — My work survives (Priority: P1)

As a writer, my conversations, every draft version, and my uploaded materials are still there after the service is redeployed or restarted; only I (my browser) can see them; they are cleaned up 30 days after I last used them.

**Why this priority**: Today a deploy wipes everything, which makes the product unusable for real work and blocks learning from real usage. (SW-D1, SW-D2, SW-D4, SW-D5, SW-D6)

**Independent Test**: Create conversations with drafts and uploads from two browsers; redeploy and restart; each browser sees exactly its own work; items idle past 30 days are gone.

**Acceptance Scenarios**:

1. **Given** a conversation with several draft versions and an upload, **When** the service restarts or is redeployed, **Then** all of it is available to the same browser.
2. **Given** two browsers, **When** each lists conversations, **Then** neither sees the other's.
3. **Given** a conversation idle more than 30 days, **When** retention runs, **Then** it and its uploads are deleted; **Given** one idle less than 30 days, **Then** it is kept.
4. **Given** a schema change, **When** shipped, **Then** it is applied as a versioned migration, proven against a real database in CI and on staging before production, with a rollback path.

---

### User Story 2 — Every change is measured (Priority: P1)

As the governor, every PR that touches Smart Writer V2 shows how draft quality moved — per quality dimension — as judged by a calibrated reader who thinks like a busy program officer; a PR that makes drafts worse beyond normal noise is blocked unless overridden with a reason.

**Why this priority**: This is direction A ("measure first") and the factory's fitness function for this workload. (SW-N1, SW-Q1..Q5, SW-Q7, SW-Q8, SW-E1..E3)

**Independent Test**: Run the eval set on an unchanged build twice (noise band); submit a PR that deliberately degrades drafts — blocked; submit a no-op PR — not blocked; every PR shows per-dimension scores vs the main branch.

**Acceptance Scenarios**:

1. **Given** a PR touching the app, **When** checks run, **Then** per-dimension scores (funder fit, persuasive narrative, evidence of impact, organizational voice) are reported against main, within the per-PR eval budget.
2. **Given** a quality drop larger than the measured noise band, **When** checks finish, **Then** the PR is blocked unless the orchestrator overrides with a reason.
3. **Given** a change that does not affect drafts, **When** checks finish, **Then** it is not blocked (no false positive from noise).
4. **Given** the judge, **When** compared with the governor's hand ratings of 10–15 drafts, **Then** agreement meets the threshold (**D1**) before the gate is allowed to block.
5. **Given** the golden set, **When** reviewed by the governor, **Then** it contains realistic grant scenarios built from public funder RFPs plus at least one non-grant smoke scenario.
6. **Given** the judge, **When** configured, **Then** it is from a different model family than the writer.

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

### User Story 4 — Bounded cost and time (Priority: P1)

As the governor, no single draft can cost more than $3, and a complete draft arrives within about 10 minutes; the real per-draft ceiling is set from measurement.

**Why this priority**: Spend is a fail-closed category (factory I-P9); durable, longer jobs and stronger models raise exposure. (SW-L1, SW-L2)

**Independent Test**: A job engineered to exceed the ceiling stops with a clear reason; golden-set runs report draft latency.

**Acceptance Scenarios**:

1. **Given** a generate or revise job whose spend would exceed the ceiling, **When** it runs, **Then** it stops and reports why; no job exceeds $3.
2. **Given** golden-set runs, **When** measured, **Then** the 95th-percentile time to a complete draft is about 10 minutes or less.

---

### User Story 5 — The right model per role, chosen by evidence (Priority: P2)

As the governor, each pipeline role (writer, assessor, extraction, judge) uses a configured model chosen by a bake-off on the eval set — the cheapest within a small margin of the best — and any model change re-runs the full eval set.

**Why this priority**: Models are hardcoded to one 2024-era model in five places; choices should be evidence-driven. P2 because it depends on US2. (SW-M1..M3)

**Independent Test**: Change one role's model in configuration; the full eval set runs; the bake-off record shows the decision rule applied per role.

**Acceptance Scenarios**:

1. **Given** application code, **When** checked, **Then** no model id is hardcoded outside typed configuration.
2. **Given** a bake-off, **When** completed, **Then** each role's choice is recorded with scores and costs, and the governor locks it.
3. **Given** a model configuration change, **When** a PR is opened, **Then** the full eval set runs (not only the per-PR subset).

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

- A browser key is lost → that browser's conversations are unreachable (accepted until accounts — SW-D4).
- A job completes after its conversation passes 30 days idle → completion counts as use; retention restarts.
- An upload exceeds limits → baseline D7 limits still apply.
- The eval budget would be exceeded on a PR → the run stops at the budget and the PR reports partial results as "incomplete", not as a pass.
- The noise band is not yet measured → the gate reports but does not block until measured.
- The judge is not yet calibrated (D1 unmet) → the gate reports but does not block.
- A migration fails on staging → production deploy does not proceed.
- Legacy V1 / Research Auditor → untouched this sprint (SW-X4).

## Requirements *(mandatory)*

### Functional Requirements

**Durability**

- **FR-001**: Conversations, messages, every draft version, and internal run state MUST persist across deploys and restarts. (SW-D1)
- **FR-002**: Uploaded materials MUST persist across deploys and restarts. (SW-D2)
- **FR-003**: Every conversation MUST belong to an anonymous per-browser key; a browser MUST see only its own conversations. (SW-D4)
- **FR-004**: Conversations and uploads MUST be deleted 30 days after last use. (SW-D5)
- **FR-005**: Jobs MUST checkpoint per pipeline step; an interrupted job MUST resume or be marked failed with a reason. (SW-D3)
- **FR-006**: Schema changes MUST ship as versioned migrations, proven against a real database in CI and on staging before production, with a rollback path. (SW-D6)

**Measured quality**

- **FR-007**: The product MUST have a golden set of grant scenarios (public funder RFPs + synthetic orgs) plus ≥1 non-grant smoke scenario, reviewed by the governor. (SW-Q8)
- **FR-008**: A judge MUST score drafts on funder fit, persuasive narrative, evidence of impact, and organizational voice, reading as a busy program officer. (SW-Q1..Q5)
- **FR-009**: The judge MUST be from a different model family than the writer. (SW-E3)
- **FR-010**: Judge agreement with the governor's hand ratings MUST be measured; the eval gate MUST NOT block until agreement meets **D1**. (SW-Q7)
- **FR-011**: Every PR touching the app MUST report per-dimension scores against main within ~$1–2 eval spend; a larger set runs nightly. (SW-N1, SW-E2)
- **FR-012**: A PR whose quality drop exceeds the measured noise band MUST be blocked, overridable with a reason. (SW-E1)
- **FR-013**: Grounding MUST remain a structural pipeline invariant checked through claim provenance on the real path — not a judge dimension. (SW-Q6)

**Models**

- **FR-014**: Each role's model MUST come from typed configuration; no hardcoded model ids. (SW-M1)
- **FR-015**: A bake-off MUST choose per role the cheapest model within **D2** of the best quality; the governor locks the result. (SW-M2)
- **FR-016**: Any model configuration change MUST trigger the full eval set. (SW-M3)

**Limits**

- **FR-017**: A job MUST stop when its spend would exceed the per-draft ceiling (**D3**; never above $3). (SW-L1)
- **FR-018**: Time to a complete draft MUST be measured; target p95 ≈ 10 minutes. (SW-L2)

**Test and ship hygiene**

- **FR-019**: Application code MUST NOT contain test-only branching or an alternate test pipeline. (SW-T1)
- **FR-020**: Tests MUST execute every pipeline step with models substituted only at the model boundary. (SW-T2)
- **FR-021**: Baseline acceptance `auto` rows MUST remain green. (SW-B1)
- **FR-022**: The UI MUST be built during image production; built assets MUST NOT be committed. (SW-S1)

### Key Entities

- **Browser key** — anonymous owner of conversations.
- **Conversation / Message / ArtifactVersion / InternalRunState** — baseline entities, now durable.
- **Stored upload** — durable upload bytes + metadata, owned via conversation.
- **Job checkpoint** — last completed pipeline step for a job.
- **Golden scenario** — funder RFP excerpt + synthetic org materials + prompt + expectations.
- **Judge score** — per-dimension scores for a draft from the judge.
- **Calibration rating** — governor's hand rating of a draft, per dimension.
- **Eval run** — scores for a build over the golden set (per-PR subset or nightly full), with cost and latency.
- **Bake-off record** — per-role model candidates, scores, costs, decision.

## Success Criteria *(mandatory)*

### Failable outcome classes

- **SC-001 Survival**: After a redeploy and a restart, 100% of seeded conversations, draft versions, and uploads are available to their owning browser.
- **SC-002 Isolation**: Zero cases of one browser key seeing another's conversations.
- **SC-003 Retention**: Items idle > 30 days are deleted; items idle < 30 days remain (100% in seeded fixtures).
- **SC-004 No silent loss**: 100% of interrupted jobs end resumed or explicitly failed.
- **SC-005 Measured**: 100% of PRs touching the app report per-dimension scores vs main within the per-PR budget.
- **SC-006 Gate is right**: A seeded quality regression beyond the noise band is blocked; a no-op change is not blocked.
- **SC-007 Calibrated**: Judge–governor agreement meets **D1** before the gate blocks.
- **SC-008 Truthful tests**: Zero test-only branches in app code; every pipeline step executed by tests; baseline `auto` rows green.
- **SC-009 Spend bound**: Zero jobs exceed $3; a job engineered to exceed the ceiling stops with a reason.
- **SC-010 Latency measured**: p95 time to complete draft on the golden set is reported; target ≈ 10 minutes.
- **SC-011 Evidence-based models**: Every role's model has a bake-off record; model changes trigger the full eval set.
- **SC-012 Migration safety**: Migrations pass against a real database in CI and on staging before production.

### Aspirational

- Eval scores rise across the sprint on the same golden set (bake-off + measured prompt pass in Wave 3).
- The governor agrees the top-scored drafts are the ones they would send.

### Acceptance catalog

Check instances: [`acceptance.md`](./acceptance.md).

## Delivery lanes *(Wave 2 — from sprint charter)*

| Lane | Stories | Ordering constraint |
|------|---------|---------------------|
| Models + tests | US3, US5 (config part) | First to touch the generate/revise graph |
| Evals | US2, US5 (bake-off) | Needs per-role model config |
| Durability | US1, US6 | Checkpointing after the Models lane's graph changes |
| Ship | US7, US4 latency measurement | Independent |

US4 spend ceiling (FR-017) lands with the Models + tests lane.

## Open Decisions *(constitution §G)*

| id | shape_locked | content_open | who | before | status | arch_impact | fidelity |
|----|--------------|--------------|-----|--------|--------|-------------|----------|
| **D1** | Judge must agree with governor hand ratings before the gate blocks | Agreement threshold | human | Before the eval gate blocks | open | | |
| **D2** | Best-value rule: cheapest within a small margin of best quality | Margin size | human | Before bake-off lock | open | | |
| **D3** | Hard outer limit $3 per draft; real ceiling from measurement | Real per-draft ceiling | human | After bake-off measurement, before production uses new models | open | | |
| **D4** | Judge is a different model family from the writer; needs a second provider key in the vault | Which provider/family judges | human | Before Evals lane | open | | |

## Review locks *(mandatory before Approved)*

| ID | Status | Lock |
|----|--------|------|
| (from review) | TBD | … |

## Assumptions

- Postgres via Supabase (A27) in a dedicated project for this app (backlog P6: one project per app) — ops HITL: governor creates the project; names go in the secrets schema.
- Second LLM provider key in the vault for the judge (D4) — ops HITL.
- Uploads move to object storage in the same Supabase project.
- Single Railway replica remains acceptable; the in-process rate limiter stays in memory.
- Baseline D7 upload limits unchanged.
- Shared pieces (durable store, model config, eval harness, checkpointer wiring) may live in `modules/lab_shared` as designed-for-reuse modules declaring intended consumers (factory I-A5); V1/RA adopt later.
- Hobbyist scale (~10 users; stretch ~100).

## Out of scope (this version)

- Accounts / sign-in, document editor, streaming, export (later workspace direction) — SW-X1, SW-X2.
- Funder-intelligence research (later direction) — SW-X3.
- V1 / Research Auditor adoption — SW-X4.
- Prompt/quality improvements beyond the Wave 3 bake-off and measured prompt pass.
