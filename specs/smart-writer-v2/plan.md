# Implementation Plan: Smart Writer V2

**Branch**: `smart-writer-v2` | **Date**: 2026-09-15 | **Spec**: [`spec.md`](./spec.md)

**Input**: Feature specification from `/specs/smart-writer-v2/spec.md` (**Approved**; F1–F8, R1–R9)

**Lab rule (constitution §E):** Plan = **Architecture** (first-class) + **Phased delivery**.  
Do **not** run `/speckit-tasks` or implement until both sections are human-approved.  
Phasing references architecture; it does not replace it.

**Status**: Draft plan — awaiting human approval of Architecture + Phased delivery.

## Summary

Build new registry app `smart-writer-v2`: a **chat-first** short-form writer with grant/donation beachhead primacy. Free-form messages drive **generate** or **revise** (continuity by default); internal intent slots + closed property ranking are inferred, not shown as forms. Grounding (materials + web, provenance, research-used-or-declared) is a pipeline invariant. Backend **jobs** run multi-minute pipelines; a **preview gate** protects spend. Surface success = SC-001–007 / `acceptance.md`; lab success = human plan/PR adjudication (R2). MVP DoD bus = Spec Kit `tasks.md` (R6).

## Architecture *(mandatory — first-class)*

### System building blocks

- **UI / clients**: Next.js (App Router) chat UI — lab journey preference when it fits (not a product SC). Primary surface: conversational thread + complete artifact pane + default **sources panel** + one light citation override. Optional property chips as light correction only.
- **API / application services**: New FastAPI app `apps/smart-writer-v2` (registered in `apps/registry.yaml`). Owns HTTP contracts, Settings/secrets wiring, turn routing (clarify vs enqueue generate/revise).
- **Orchestration / jobs**: In-process `lab_shared.jobs.JobRunner` for long runs (same cattle pattern as V1). Pipeline graph: **LangGraph when the generate/revise/research graph benefits** (preference, not Ubiquitous gate). Distinct graph/entry modes: `clarify` (sync-capable), `generate`, `revise`.
- **Agents / prompt program**: PydanticAI (or equivalent schema-first) agents for slot/property inference, research planning, writer, optional later machine critique. Versioned **prompt program** under the app (do not bury acceptance in prompts).
- **Data stores**: MVP = process-local conversation/artifact store co-located with JobRunner (session durability caveat documented) **plus** job snapshots returned to client. Optional Supabase persistence = later phase if multi-instance/restart durability is required.
- **External systems**: OpenAI (or lab-default LLM), Tavily web search (optional key → noop/degraded with SC-004 declare path), Infisical → env for secrets. User materials via URL fetch and/or upload (MVP: URLs first; file upload may trail by one phase if needed).

### Boundaries & responsibilities

| Block | Owns | Does not own |
|-------|------|--------------|
| Next.js UI | Chat UX, artifact display, sources panel, citation override, regenerate affordance | Pipeline logic, secret values, acceptance catalog |
| FastAPI API | Auth/preview gate, rate limits, job enqueue/poll, turn API, Settings | Prose quality judgment, lab process SCs |
| Orchestrator / graph | Mode routing (`generate`/`revise`/`clarify`), research→write order, grounding invariant enforcement | UI layout, Railway UI config |
| Prompt program | Writer/critique templates, property weave, grant humor default | Runtime secrets, deploy manifests |
| `lab_shared` | JobRunner, shared DB helpers if/when used | Product-specific grant logic |
| Legacy `smart-writer` | V1 only | V2 requirements; no back-port duty |

### Data & persistence

- Entities: see [`data-model.md`](./data-model.md) — `Conversation`, `Message`, `ArtifactVersion`, `InternalRunState`, `SourceRecord`, `Job`/`Run`.
- **Revise vs generate (SC-006/007):** every writing job/run carries `mode: generate | revise` and every `ArtifactVersion` has `artifact_id`, `parent_artifact_id` (nullable), `producing_mode`. Auto-candidate: assert these fields in API/job result.
- Ephemeral vs durable (MVP): jobs + conversation state **in-memory** (restart loses state — same residual as V1 JobRunner). Client may hold last artifact ids for a session. Durable DB deferred.
- Provenance: `SourceRecord` list attached to artifact; claims map to source ids where asserted.

### APIs & contracts

- See [`contracts/http-api.md`](./contracts/http-api.md).
- **Preview gate**: shared-secret header (e.g. `X-Audit-Secret` ↔ `SMART_WRITER_V2_AUDIT_SECRET`) on mutating + job routes; `/health` public; `/ready` checks config (OpenAI present). Declare secret **name** in `deploy/secrets/schema.yaml` + Settings — never commit values.
- Rate limit + queue caps mirror lab Pattern B5 posture (in-process).

### UI surfaces

- **Chat thread**: user free-form; assistant returns either clarifying question(s) or complete artifact.
- **Artifact view**: full draft; version indicator; “Regenerate / start over” explicit control.
- **Sources panel** default when sources exist; one control for inline / footnotes / panel / combo (F7).
- UI talks to backend via **async jobs** for generate/revise (POST → `job_id` → poll); clarify may be sync short response.

### Major risks / non-goals for this architecture

- In-memory jobs/conversations: multi-instance and restart loss — acceptable MVP; document in quickstart.
- Do **not** port V1 full N-assessor rubric loop as MVP requirement; optional machine critique is a later phase (distinct from human revise).
- Do **not** make LangGraph/Next/v0 product pass/fail (F5/R1).
- No V1 feature-parity; clean-room app with **pattern** reuse only.
- Cost: turn/job caps and preview gate required before any public URL.

## Phased delivery *(mandatory)*

| Phase | Goal | Architecture pieces touched | Exit criteria (failable) |
|-------|------|-----------------------------|--------------------------|
| **P0** Scaffold | Registry app + FastAPI health/ready + secrets schema stub + empty Next shell | API, registry, secrets, UI shell | `smart-writer-v2` in registry; `uv sync --locked`; `/health` 200; secret **names** in schema; no implement of pipeline yet |
| **P1** MVP vertical | Chat turn API + jobs + generate path + materials/URL + web research stub/Tavily + provenance + sources panel + revise continuity + regenerate | API, JobRunner, orchestrator generate/revise, agents writer+infer, UI chat+artifact+sources, prompt program seed | Grant golden path: complete artifact; `mode`/`parent_artifact_id` distinguish revise vs generate (**auto** catalog candidate); preview gate enforced; SC-003/004 hybrid-checkable on fixture run; humor default off for grant profile |
| **P2** Beachhead harden | Intent-slot clarify ordering; property chips optional; citation override; non-grant smoke; catalog growth | Clarify path, property UX, acceptance checks | FR-003a–c behaviors; SC-005 smoke; ≥1 catalog row marked `auto` green in CI |
| **P3** Depth (optional) | Durable persistence and/or optional machine critique loop; richer uploads | Data store, optional assessor graph | Only if human prioritizes; not required for v2.0 beachhead bar |

**MVP definition (P1):** Thin but real dogfood — user can chat a grant ask with links, get a **complete** grounded draft with sources panel, send feedback and get a **revise** (linked version), or explicitly regenerate. Jobs + preview gate on. Not: full V1 rubric theater, multi-tenant, or durable multi-instance store.

## Technical Context

**Language/Version**: Python 3.12 (API); TypeScript/Node for Next.js UI

**Primary Dependencies**: FastAPI, Pydantic / PydanticAI, LangGraph (when fit), `lab_shared.jobs`, Next.js, httpx; Tavily optional

**Storage**: MVP in-memory (jobs + conversation); Supabase optional later

**Testing**: pytest (API/orchestrator/contracts); UI smoke later; acceptance catalog hybrid + thin auto

**Target Platform**: Codespaces + Railway (cattle manifests when shipping)

**Project Type**: Monorepo app `apps/smart-writer-v2` (+ `apps/smart-writer-v2-web` **or** `apps/smart-writer-v2/web` — prefer `web/` inside app **or** sibling; **decision**: `apps/smart-writer-v2/` backend + `apps/smart-writer-v2/web/` Next app in-tree to keep one registry id unless tooling forces split)

**Performance Goals**: Multi-minute jobs OK; clarify turns fast; hobbyist scale

**Constraints**: Cattle/secrets/registry; preview gate; cost caps; no durable pip; grounding invariant

**Scale/Scope**: ~10 users (stretch ~100)

## Constitution Check

*GATE: Must pass before tasks/implement. Re-check after architecture edits.*

- [x] Architecture section complete (blocks, boundaries, data, APIs/UI as applicable)
- [x] Phased delivery present with MVP and exit criteria
- [ ] No tasks/implement started before human approval of this plan *(hold)*
- [x] Secrets/registry/cattle rules respected (names in schema; new app registration in P0)
- [x] Learning/stack prefs not smuggled as product gates (F5/R1/R2)

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

**Structure Decision**: **Clean-room** new app `smart-writer-v2` (FR-011). Reuse **patterns** and `lab_shared.jobs` from V1; do not import V1 product modules. In-tree `web/` keeps one product folder for MVP.

## Complexity Tracking

> No constitution violations requiring justification.
