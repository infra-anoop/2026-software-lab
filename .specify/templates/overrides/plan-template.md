# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Lab rule (constitution §E):** Plan = **Architecture** (first-class) + **Phased delivery**.  
Do **not** run `/speckit-tasks` or implement until both sections are human-approved.  
Phasing references architecture; it does not replace it.

**Plan Architecture review:** After this draft exists, recommended (non-trivial / first-of-kind): spawn per `docs/agent-os/SPAWN_REVIEWER.md` + `docs/agent-os/PLAN_REVIEW_PROMPT.md` (**P-***; Architecture-heavy incl. Learning/SOTA fit, Phasing-light). See `docs/agent-os/STACK_POSTURE.md`. Deposit `PLAN_REVIEW.md`; triage before human approval. Do **not** paste the brief into the human chat.

## Summary

[Extract from feature spec: primary requirement + technical approach]

## Architecture *(mandatory — first-class)*

<!--
  Building blocks and boundaries. Not a task list.
  Keep technology-agnostic where possible; name concrete choices when locked.
  For each major block, research.md must list Alternatives (STACK_POSTURE).
-->

### System building blocks

- **UI / clients**: [e.g., Next/v0 app, CLI, none]
- **API / application services**: [e.g., FastAPI app id, routes responsibility]
- **Orchestration / jobs**: [e.g., in-process JobRunner, queue, LangGraph graph roles]
- **Data stores**: [e.g., Supabase tables, object storage, none]
- **External systems**: [e.g., OpenAI, web search, Infisical — names only]

### Boundaries & responsibilities

| Block | Owns | Does not own |
|-------|------|--------------|
| … | … | … |

### Topology & runtime custody *(mandatory if browser UI + protected API)*

<!--
  Folder layout is NOT topology. Lock before tasks.
  See docs/agent-os/PLAN_AUTHORING_GATES.md rule 5.
-->

- **Runtimes / hosts**: [e.g. Next on Vercel + FastAPI worker on Railway | single FastAPI serves UI | two registry apps]
- **How UI calls API**: [BFF server routes | same-origin | browser→API — last requires justifying secret custody]
- **Preview / spend secret custody**: [who holds it; browser must not]
- **Cattle manifests**: [which git paths declare each runtime]

### Data & persistence

- Key entities / tables (or link `data-model.md` when produced):
- Run/job identity and what is ephemeral vs durable:

### APIs & contracts

- Public HTTP/API surfaces (or link `contracts/`):
- Auth / preview gate (if any):

### UI surfaces (if any)

- Primary screens/flows:
- How UI talks to backend (sync vs job poll):

### Major risks / non-goals for this architecture

- …

## Phased delivery *(mandatory)*

<!--
  High-level order toward the architecture (MVP, wireframes, hookups).
  Each phase should reference Architecture blocks above.
  Detailed work items belong in tasks.md — not here.
-->

| Phase | Goal | Architecture pieces touched | Exit criteria (failable) |
|-------|------|-----------------------------|--------------------------|
| P0 / spike | … | … | … |
| P1 MVP | … | … | … |
| P2 | … | … | … |

**MVP definition**: [one paragraph — what “thin but real” means for this feature]

## Technical Context

**Language/Version**: [e.g., Python 3.12]

**Primary Dependencies**: [e.g., FastAPI, PydanticAI, LangGraph]

**Storage**: [e.g., Supabase / N/A]

**Testing**: [e.g., pytest unit + integration]

**Target Platform**: [e.g., Codespaces + Railway]

**Project Type**: [e.g., monorepo app under apps/<id>]

**Performance Goals**: [or N/A for hobbyist]

**Constraints**: [lab invariants, cost, latency]

**Scale/Scope**: [e.g., ~10–100 users]

## Constitution Check

*GATE: Must pass before tasks/implement. Re-check after architecture edits.*

- [ ] Architecture section complete (blocks, boundaries, data, APIs/UI as applicable)
- [ ] Topology & runtime custody locked if UI + protected API (PLAN_AUTHORING_GATES)
- [ ] Phased delivery present with MVP and exit criteria
- [ ] `research.md` alternatives per major block (STACK_POSTURE) — sibling-only alts = fail
- [ ] Orchestrator P1 lock (named nodes **or** linear + migrate trigger — not “when fit” alone)
- [ ] Plan Architecture review (P*) triaged if run — or explicitly skipped with reason
- [ ] No tasks/implement started before human approval of this plan
- [ ] Secrets/registry/cattle rules respected
- [ ] Learning/stack prefs not smuggled as product gates
- [ ] PLAN_AUTHORING_GATES satisfied (or escalated to human — do not soft-complete)

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file
├── research.md          # Required: use docs/agent-os/research-template.md shape
├── data-model.md        # Optional / from plan
├── quickstart.md        # Optional
├── contracts/           # Optional
├── acceptance.md        # Lab: extensible checks
├── PLAN_REVIEW.md       # Optional: P* deposit
└── tasks.md             # After plan approved (/speckit-tasks)
```

### Source Code (repository root)

```text
apps/<id>/
modules/lab_shared/     # only if shared
deploy/                 # if deploy surface changes
```

**Structure Decision**: [Selected layout and why]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| | | |
