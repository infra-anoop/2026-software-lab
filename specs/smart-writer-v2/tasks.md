# Tasks: Smart Writer V2

**Input**: Design documents from `/specs/smart-writer-v2/`  
**Prerequisites**: plan.md (**Approved**, P1–P8), spec.md (**Approved**), research.md, data-model.md, contracts/http-api.md, acceptance.md, quickstart.md

**Tests (lab §V):** Executable app — contract + catalog-auto tests **required**, red before matching impl. Do **not** fake `how: human` catalog rows as pytest. Hybrid rows: test **structural** auto parts only (JSON fields, modes, clarify type).

**T\* review:** After each story’s contract/auto tests are written and red, independent `docs/agent-os/TEST_REVIEW_PROMPT.md` before that story’s implementation. Skip T\* for Phase 1–2 `/health` smoke only.

**Paths:** worker `apps/smart-writer-v2/`; UI `apps/smart-writer-v2/web/`. Do not import `apps/smart-writer` product modules.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Registry app + Next shell + secret **names** (plan P0)

- [x] T001 Create directory layout `apps/smart-writer-v2/app/`, `apps/smart-writer-v2/tests/`, `apps/smart-writer-v2/web/` per `specs/smart-writer-v2/plan.md` Project Structure
- [x] T002 Add `apps/smart-writer-v2/pyproject.toml` (Python >=3.12,<3.13; FastAPI, pydantic-settings, pydantic-ai, langgraph, httpx, lab-shared editable path `../../modules/lab_shared`; pytest/ruff dev group) and `uv.lock` via `cd apps/smart-writer-v2 && uv lock`
- [x] T003 Register `id: smart-writer-v2` in `apps/registry.yaml` (path `apps/smart-writer-v2`, http_server, railway `service_name: smart-writer-v2`, ci watch `modules/lab_shared`) and regenerate `apps/registry.json` with `uv run scripts/validate_app_registry.py --write-json`
- [x] T004 [P] Add secret **names** `SMART_WRITER_V2_AUDIT_SECRET`, `OPENAI_API_KEY`, `TAVILY_API_KEY`, `LOGFIRE_TOKEN` for app `smart-writer-v2` in `deploy/secrets/schema.yaml` (never commit values)
- [x] T005 [P] Scaffold Next.js App Router in `apps/smart-writer-v2/web/package.json` and `apps/smart-writer-v2/web/app/layout.tsx` (no `NEXT_PUBLIC_*` for audit secret)
- [x] T006 [P] Add Railway cattle stub `deploy/railway/production/smart-writer-v2.yml` mirroring `deploy/railway/production/smart-writer.yml` with service name `smart-writer-v2`

**Checkpoint**: `uv sync --locked` works in app dir; registry lists the app

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Health/ready, preview gate, JobRunner, in-memory store, BFF secret custody — **MUST** complete before user stories

**⚠️ CRITICAL**: No user story work until this phase is complete

- [x] T007 Implement Settings `ALL_ENV_NAMES` in `apps/smart-writer-v2/app/config.py` including `SMART_WRITER_V2_AUDIT_SECRET` (required for mutating routes), `OPENAI_API_KEY`, optional `TAVILY_API_KEY`/`LOGFIRE_TOKEN`
- [x] T008 Add FastAPI app with `GET /health` (public) and `GET /ready` (OpenAI key present, no upstream call) in `apps/smart-writer-v2/app/entrypoints/http.py`
- [x] T009 Implement preview-gate dependency in `apps/smart-writer-v2/app/entrypoints/http.py`: header `X-Audit-Secret`; missing/wrong → 401; unset env on protected routes → 503
- [x] T010 Wire `lab_shared.jobs.JobRunner` lifespan (start/stop) on the FastAPI app in `apps/smart-writer-v2/app/entrypoints/http.py`
- [x] T011 Implement in-memory store in `apps/smart-writer-v2/app/store.py` for `Conversation` (`conversation_id` uuid), `Message` (`role` user|assistant|system), `InternalRunState` per `specs/smart-writer-v2/data-model.md`: `intent_slots` object Who/Whom/Ask/WhyFunder/Evidence as `who`/`whom`/`ask`/`why_funder`/`evidence` strings | null; `property_ranking` list[string] ordered closed vocabulary ids (empty until T049); `humor_enabled` bool Grant default false/off (F3); `web_research_enabled` bool Default true for beachhead unless user disables; `materials` list[MaterialRef] (`uri` string, `label` string | null, `kind` `link` | `upload`); `citation_mode_pref` `panel` | `inline` | `footnotes` | `combo` | null Light override; `last_artifact_id` string | null Head of revise chain
- [x] T012 Add `POST /v1/conversations` (protected) returning `{ conversation_id }` in `apps/smart-writer-v2/app/entrypoints/http.py`
- [x] T013 Add Vercel BFF route `apps/smart-writer-v2/web/app/api/proxy/[...path]/route.ts` that reads `SMART_WRITER_V2_AUDIT_SECRET` from **server** env only and forwards to FastAPI (browser must never send the secret)
- [x] T014 Add scaffold smoke `apps/smart-writer-v2/tests/unit/test_health.py` asserting `GET /health` returns 200 (not a T\* gate)
- [x] T015 Add contract test `apps/smart-writer-v2/tests/contract/test_preview_gate.py` asserting protected `POST /v1/conversations` rejects wrong/missing `X-Audit-Secret` with 401 (contracts/http-api.md hook 3) — must FAIL until T009/T012 exist; T\* not required for this hook alone if US1 suite not yet written

**Checkpoint**: Foundation ready — stories may start

---

## Phase 3: User Story 1 - Funder-specific grant / donation ask (Priority: P1) 🎯 MVP

**Goal**: Complete grant generate path with grounding invariant, claim provenance, grant humor default off, sources panel default `citation_mode=panel`

**Independent Test**: Named funder + materials/criteria → complete artifact with ≥2 fit points (hybrid/human) and structural `claims[]` / `web_signal`; `humor_enabled` false unless user enabled

### Tests for User Story 1 *(required — write FIRST, must FAIL)*

- [x] T016 [P] [US1] Contract test generate success: `mode=generate`, `artifact.parent_artifact_id` JSON null (key present), `producing_mode=generate`, complete `body`; if `sources` nonempty then `citation_mode=panel` in `apps/smart-writer-v2/tests/contract/test_generate_job.py` (http-api.md hook 2; T3 lock)
- [x] T017 [P] [US1] Contract test grant artifact `claims[]`: nonempty on this materials fixture; each claim `excerpt` ⊆ `body`; `grounded` `source_id` ∈ `artifact.sources[].source_id` or `uncertain` with null `source_id` in `apps/smart-writer-v2/tests/contract/test_claim_provenance.py` (hook 4; T1 lock)
- [x] T018 [P] [US1] Contract test web enabled + empty Tavily/noop → `web_signal=none_declared` in `apps/smart-writer-v2/tests/contract/test_web_signal.py` (hook 5; catalog `research.used_or_declared` structural)
- [x] T019 [P] [US1] Contract test grant default `humor_enabled` is false on **job snapshot** (`GET /v1/jobs/{id}`), not conversation `run_state`, in `apps/smart-writer-v2/tests/contract/test_grant_humor_default.py` (catalog `grant.default_humor_low`; T2 lock)
- [x] T020 [US1] Independent test review **T\*** of T016–T019 (+ T015 if not already reviewed) per `docs/agent-os/TEST_REVIEW_PROMPT.md`; deposit `specs/smart-writer-v2/TEST_REVIEW.md`; resolve T\* Blockers before T021+

### Implementation for User Story 1

**⚠️ CRITICAL (I1 / P5):** **T028 is blocked on T043.** Do **not** enqueue generate from `POST .../messages` until the US3 turn router exists (T039–T041 red + T\* T041, then T042–T043). T016–T027 and T029 (tests, models, graph, prompts, citation default) may proceed; T030 after T028.

- [x] T021 [P] [US1] Add Pydantic models in `apps/smart-writer-v2/app/models.py` per `specs/smart-writer-v2/data-model.md`: `ArtifactVersion` (`parent_artifact_id` string | null Set on **revise**; null on fresh **generate**; `producing_mode` `generate` | `revise`; `citation_mode` `panel` | `inline` | `footnotes` | `combo` Default `panel` when sources exist (F7); `source_ids` list[string]; `claims` list[ClaimProvenance]; `materials_bundle_ids` list[string] F4 materials side; `web_bundle_ids` list[string] F4 web side; `web_signal` `used` | `none_declared` | `disabled` SC-004), `ClaimProvenance` (`status` `grounded` | `uncertain`; `uncertain` ⇒ omit or mark in prose; null `source_id`), `SourceRecord` (`kind` `user_material` | `web`; `bundle` `materials` | `web`)
- [x] T022 [P] [US1] Add seed property vocabulary list `factual`,`persuasive`,`concise`,`warm`,`formal`,`humorous`,`specific`,`urgent` in `apps/smart-writer-v2/app/properties.py` (research.md R8; `factual` tone-only)
- [x] T023 [US1] Implement URL materials fetch (SSRF/size limits — P7) in `apps/smart-writer-v2/app/retrieval/url_fetch.py`
- [x] T024 [US1] Implement retrieval façade emitting `materials_bundle` vs `web_bundle` in `apps/smart-writer-v2/app/retrieval/bundles.py`
- [x] T025 [US1] Implement Tavily optional search (no key → empty bundle) in `apps/smart-writer-v2/app/retrieval/tavily.py`
- [x] T026 [US1] Implement LangGraph generate `StateGraph` nodes infer → materials → web → write → provenance in `apps/smart-writer-v2/app/orchestrator/generate_graph.py` with PydanticAI `result_type` per node in `apps/smart-writer-v2/app/agents/`
- [x] T027 [US1] Add versioned prompt program grant defaults (humor off) in `apps/smart-writer-v2/app/prompts/programs/grant_default/`
- [x] T028 [US1] **Blocked on T043.** Enqueue generate jobs from `POST /v1/conversations/{id}/messages` only when grant intent slots who/whom/ask/why_funder/evidence are all filled; if any missing, do **not** enqueue (P5 — T043 returns `type=clarify`, no `job_id`); `GET /v1/jobs/{job_id}` success shape per `specs/smart-writer-v2/contracts/http-api.md` in `apps/smart-writer-v2/app/entrypoints/http.py`
- [x] T029 [US1] Default `citation_mode=panel` when sources exist on artifact in `apps/smart-writer-v2/app/orchestrator/generate_graph.py`
- [x] T030 [US1] Chat UI generate + artifact pane + sources panel (poll via BFF, no client audit secret) in `apps/smart-writer-v2/web/app/page.tsx`

**Checkpoint**: US1 independently testable (generate + provenance shape + humor default)

---

## Phase 4: User Story 2 - Chat iterate with continuity (Priority: P2) 🎯 MVP

**Goal**: Feedback → revise linked ArtifactVersion; explicit regenerate → generate

**Independent Test**: Artifact A; feedback → B with `parent_artifact_id`; “start over” → generate, parent null

### Tests for User Story 2 *(required — FIRST, must FAIL)*

- [x] T031 [P] [US2] Contract test successful revise: job `mode=revise`, `artifact.parent_artifact_id` non-null, `producing_mode=revise` in `apps/smart-writer-v2/tests/contract/test_revise_job.py` (hook 1; catalog `revise.continuity_default` structural)
- [x] T032 [P] [US2] Contract test `client_intent=regenerate` → `mode=generate`, `parent_artifact_id` null in `apps/smart-writer-v2/tests/contract/test_regenerate_job.py` (hook 2; catalog `regenerate.explicit`)
- [x] T033 [P] [US2] Contract test revise without parent → 409 in `apps/smart-writer-v2/tests/unit/test_revise_parent.py` (T17: helper, not POST `parent_artifact_id`)
- [x] T034 [US2] Independent **T\*** review of T031–T033; append to `specs/smart-writer-v2/TEST_REVIEW.md`; Blockers before T035

### Implementation for User Story 2

- [x] T035 [US2] Implement LangGraph revise graph (may skip/narrow materials/web; prior artifact + feedback in state) in `apps/smart-writer-v2/app/orchestrator/revise_graph.py`
- [x] T036 [US2] Route `client_intent=auto` to revise when `last_artifact_id` set in `apps/smart-writer-v2/app/entrypoints/http.py`; `regenerate` forces generate
- [x] T037 [US2] Persist new `ArtifactVersion` linked to parent + feedback message in `apps/smart-writer-v2/app/store.py`
- [x] T038 [US2] UI regenerate/start-over control and version indicator in `apps/smart-writer-v2/web/app/page.tsx` (BFF poll)

**Checkpoint**: US1 + US2 independently testable

---

## Phase 5: User Story 3 - Interleaved clarification Q&A (Priority: P3) 🎯 MVP (P5 lock)

**Goal**: Missing Who/Whom/Ask/Why/Evidence → `type=clarify` only; NL questions; no slot ids in client JSON

**Independent Test**: Empty Whom/Ask fixture → clarify, no `job_id`

### Tests for User Story 3 *(required — FIRST, must FAIL)*

- [x] T039 [P] [US3] Contract test grant turn with empty whom/ask → `type=clarify`, no `job_id`, assistant `text` has no tokens `whom`/`ask`/`Axis` as slot labels in `apps/smart-writer-v2/tests/contract/test_clarify_before_write.py` (hook 6; catalog `grant.intent_slots_complete` structural)
- [x] T040 [P] [US3] Contract test default clarify payload omits `missing_hints` in `apps/smart-writer-v2/tests/contract/test_clarify_no_slot_leak.py` (FR-021)
- [x] T041 [US3] Independent **T\*** review of T039–T040; append `specs/smart-writer-v2/TEST_REVIEW.md`; Blockers before T042

### Implementation for User Story 3

- [x] T042 [US3] Infer/update intent slots from free-form text in `apps/smart-writer-v2/app/agents/infer_state.py` (PydanticAI `result_type`)
- [x] T043 [US3] Turn router (**hard blocker for T028**): grant + any of who/whom/ask/why_funder/evidence missing → clarify sync response, never enqueue job, in `apps/smart-writer-v2/app/entrypoints/http.py`
- [x] T044 [US3] NL-only clarify copy (no axis/slot names) in `apps/smart-writer-v2/app/agents/clarify.py`
- [x] T045 [US3] Render clarify messages in chat thread in `apps/smart-writer-v2/web/app/page.tsx`

**Checkpoint**: Clarify-before-write fixture green; US1 generate still works when slots filled

---

## Phase 6: User Story 4 - Closed property steering (Priority: P4)

**Goal**: Infer ranking from free-form; optional chips; weave into prompt program; `factual` does not disable grounding

**Independent Test**: Free-form updates ranking; grounding still runs if `factual` ranked low

### Tests for User Story 4 *(required — FIRST, must FAIL)*

- [x] T046 [P] [US4] Contract/unit test inferred ranking only uses closed ids from `apps/smart-writer-v2/app/properties.py` in `apps/smart-writer-v2/tests/contract/test_property_ranking_closed.py`
- [x] T047 [P] [US4] Test `factual` low still runs web/materials nodes (grounding invariant) in `apps/smart-writer-v2/tests/contract/test_factual_not_grounding_off.py`
- [x] T048 [US4] Independent **T\*** review of T046–T047 if those files exist; append `TEST_REVIEW.md`; Blockers before T049

### Implementation for User Story 4

- [x] T049 [US4] Infer property ranking from free-form in `apps/smart-writer-v2/app/agents/infer_state.py` and store `property_ranking` on `InternalRunState` in `apps/smart-writer-v2/app/store.py`
- [x] T050 [US4] Weave ranking into writer prompt program in `apps/smart-writer-v2/app/prompts/render.py`
- [x] T051 [US4] Optional property chips (correction only; free-form primary) in `apps/smart-writer-v2/web/app/components/PropertyChips.tsx`
- [x] T052 [US4] Prioritize intent-slot questions before property clarifiers when both incomplete (FR-003c) in `apps/smart-writer-v2/app/agents/clarify.py`

**Checkpoint**: Steering works without inventing property labels; grounding still on

---

## Phase 7: User Story 5 - Research: materials + web with clear roles (Priority: P5) 🎯 MVP overlap with US1

**Goal**: Uploads/links = criteria/org evidence; web = differentiation; prefer criteria over trivia (human/hybrid — no fake auto)

**Independent Test**: Materials vs web bundles attached; web unused → declare

### Tests for User Story 5 *(required — FIRST, must FAIL)*

- [x] T053 [P] [US5] Contract test artifact `materials_bundle_ids` vs `web_bundle_ids` populated from `SourceRecord.bundle` in `apps/smart-writer-v2/tests/contract/test_bundle_roles.py` (F4 structural)
- [x] T054 [P] [US5] Reuse/extend `test_web_signal.py` for `web_research_enabled=false` → `web_signal=disabled` in `apps/smart-writer-v2/tests/contract/test_web_disabled.py`
- [x] T055 [US5] Independent **T\*** review of T053–T054; append `TEST_REVIEW.md`; Blockers before T056

### Implementation for User Story 5

- [x] T056 [US5] Ensure generate/revise graphs set bundle ids and F4 preference in writer context (materials criteria over web trivia) in `apps/smart-writer-v2/app/orchestrator/generate_graph.py` and `apps/smart-writer-v2/app/prompts/programs/grant_default/`
- [x] T057 [US5] Accept `materials: [{ uri, label }]` on `POST .../messages` (`kind=link`) in `apps/smart-writer-v2/app/entrypoints/http.py` (file upload deferred P7/P3)

**Checkpoint**: F4 roles visible in artifact JSON; SC-004 structural auto green

---

## Phase 8: User Story 6 - General short-form smoke (Priority: P6)

**Goal**: Non-grant 1–3 page path on same engine without grants-only hard fail (SC-005 should/smoke)

**Independent Test**: Non-grant prompt completes same intake/research/draft path

### Tests for User Story 6 *(required — FIRST, must FAIL)*

- [x] T058 [P] [US6] Contract/integration test non-grant prompt completes job without requiring grant intent slots in `apps/smart-writer-v2/tests/contract/test_nongrant_smoke.py` (catalog `engine.nongrant_smoke` structural)
- [x] T059 [US6] Independent **T\*** review of T058; append `TEST_REVIEW.md`; Blockers before T060

### Implementation for User Story 6

- [x] T060 [US6] Turn router: non-grant → skip Axis A must-ask; still generate/revise on same graphs in `apps/smart-writer-v2/app/entrypoints/http.py`

**Checkpoint**: Grant primacy defaults unchanged; smoke path exists

---

## Phase 9: Polish & Cross-Cutting (P7 deferred + cattle)

- [x] T061 [P] Mark ≥1 catalog row `how: auto` in `specs/smart-writer-v2/acceptance.md` matching a green contract test (plan P2 exit; e.g. `revise.continuity_default` or `regenerate.explicit`)
- [x] T062 [P] Rate limit + queue caps (B5-class) in `apps/smart-writer-v2/app/entrypoints/http.py` and tests in `apps/smart-writer-v2/tests/contract/test_rate_limit.py`
- [ ] T063 [P] Turn/cost cap Settings in `apps/smart-writer-v2/app/config.py` (P7)
- [ ] T064 [P] Logfire init from `LOGFIRE_TOKEN` in `apps/smart-writer-v2/app/obs.py` (P7)
- [ ] T065 Citation override control (inline/footnotes/panel/combo) and skip ask if no sources in `apps/smart-writer-v2/web/app/components/CitationMode.tsx` (F7; after MVP)
- [x] T066 Document restart/in-memory loss and local run in `specs/smart-writer-v2/quickstart.md` and `apps/smart-writer-v2/README.md`
- [x] T067 [P] Vercel cattle pointer: git-declared env names for BFF (no UI-only secret) in `deploy/` adapter stub or `apps/smart-writer-v2/web/README.md` (P1 A21)
- [x] T068 `cd apps/smart-writer-v2 && uv run ruff check app/ tests/` and `uv run pytest` green for contract suite

---

## Dependencies & Execution Order

```text
Phase 1 Setup
    → Phase 2 Foundational (blocks all stories)
        → US1 tests + models/graph T016–T027  [MVP]
        → US3 clarify-before-write T039–T045  [MVP — P5; MUST before T028]
        → US1 enqueue + UI T028–T030          [MVP; blocked on T043]
        → US2 (revise/regenerate)             [MVP]
        → US5 (bundle roles)                  [MVP overlap]
        → US4 (property chips/weave)          [plan P2]
        → US6 (non-grant smoke)               [plan P2]
        → Polish
```

**MUST (I1 / P5):** T028 MUST NOT start until T043 is done. After Foundational, US1 contract tests T016–T020 and impl T021–T027 may run in parallel with writing US3 tests T039–T041, but **T039–T041 + T041 T\* + T042–T043 before T028**. Do not “enqueue first and add clarify later.”

Story completion for MVP (plan P1): **US1 + US2 + US3 + US5**. US4 chips + US6 = plan P2.

## Parallel examples

### User Story 1 tests (after Foundational)

```text
T016, T017, T018, T019  [P] together
then T020 T* review (sequential)
then T021, T022 [P]
then T023–T027 (graph/prompts; may overlap US3 tests)
then T039–T041 [P] + T041 T* + T042–T043  **before T028**
then T028–T030
```

### User Story 2 tests

```text
T031, T032, T033 [P]
then T034 T*
then T035–T038
```

## Implementation strategy

### MVP first (plan P1)

1. Phase 1 Setup  
2. Phase 2 Foundational  
3. US1 tests/models/graph (T016–T027) **and** US3 clarify (T039–T045); **T043 before T028**  
4. US1 enqueue + UI poll (T028–T030)  
5. US2 revise/regenerate  
6. US5 bundle ids  
7. **STOP** — T\* done for those contract files; hybrid/human catalog (audience-fit, length, surprise) remain human  

### Incremental

- Plan P2: US4 chips + FR-003c + US6 smoke + T061 auto catalog + T065 citation override  
- Plan P3: uploads, durable DB, SSE, managed jobs — **out of these tasks unless human prioritizes**

## Notes

- [P] = different files, no incomplete deps  
- Verify contract tests **fail** before impl of that slice  
- After T016–T019 exist and are red: **spawn** T* per `docs/agent-os/SPAWN_REVIEWER.md` (`FEATURE_DIR=specs/smart-writer-v2/`). Do **not** paste the brief into the human chat.  
- Do not pytest `length.target_1_3_pages`, `delight.surprise`, or `research.prefer_criteria_over_trivia` as auto  
- Commit after each logical group  

## Task count

| Slice | IDs | Count |
|-------|-----|-------|
| Setup | T001–T006 | 6 |
| Foundational | T007–T015 | 9 |
| US1 | T016–T030 | 15 |
| US2 | T031–T038 | 8 |
| US3 | T039–T045 | 7 |
| US4 | T046–T052 | 7 |
| US5 | T053–T057 | 5 |
| US6 | T058–T060 | 3 |
| Polish | T061–T068 | 8 |
| **Total** | T001–T068 | **68** |
