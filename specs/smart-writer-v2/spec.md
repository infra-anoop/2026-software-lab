# Feature Specification: Smart Writer V2

**Feature Branch**: `smart-writer-v2`

**Created**: 2026-09-10

**Status**: Draft — Spec Kit shape aligned; **resume product review locks F2–F7** (F1 locked)

**Input**: Lab coaching locks (A1–D, N1–N14) + independent review triage; app id `smart-writer-v2` (new registry app; V1 `smart-writer` remains legacy)

**Process**: Spec Kit + `.specify/memory/constitution.md` — do not re-argue process here.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Funder-specific grant / donation ask (Priority: P1)

As a nonprofit writer, I want a short (≈1–3 page) grant or donation ask grounded in what *this* funder cares about, so the draft feels specific and credible—not generic charity prose.

**Why this priority**: Beachhead use case and primary product bet.

**Independent Test**: Given org context + named funder with available criteria, produce a draft that includes concrete fit points and provenance for specific claims; can be judged without other stories.

**Acceptance Scenarios**:

1. **Given** a named funder and criteria (upload, link, or retrieved public material), **When** a run completes, **Then** the draft includes at least two concrete fit points tied to those criteria (not only generic nonprofit language).
2. **Given** the draft asserts an org- or funder-specific fact beyond the raw prompt, **When** the draft is inspected, **Then** each such claim has checkable provenance or is omitted / marked uncertain.

---

### User Story 2 - Gap-fill intake (Priority: P2)

As a user who prompts poorly, I want optional Q&A that only asks what my first prompt left unclear (continuum 0…N), so I think harder without a canned interview.

**Why this priority**: Differentiates from blank-box ChatGPT; unlocks better research and steering.

**Independent Test**: Rich prompt → 0 questions; thin prompt → targeted gap questions only; no fixed script.

**Acceptance Scenarios**:

1. **Given** a sufficient first prompt, **When** intake runs, **Then** the system does not force a precanned questionnaire (N may be 0).
2. **Given** missing intent in the first prompt, **When** intake runs, **Then** questions are designed to fill those gaps (not a fixed list).

---

### User Story 3 - Closed property steering (Priority: P3)

As a user, I want to rank a product-owned closed vocabulary of properties (and correct an inferred draft ranking), so steering is crisp without inventing labels mid-flow.

**Why this priority**: Controllable rhetoric/shape without free-text chaos.

**Independent Test**: Infer ranking from prompt → user reorders closed chips → writer/critique prompt program reflects order.

**Acceptance Scenarios**:

1. **Given** a free-text prompt, **When** decode runs, **Then** a draft ranking against the closed list is shown for correction.
2. **Given** a user-ordered property list, **When** draft/critique runs, **Then** properties are woven into the prompt program (not a slogan append).

**Seed vocabulary (non-final; expand at implementation):**  
`emotional` · `humorous` · `persuasive` · `factual` · `concise` · `formal` · `urgent` · `visionary`  
*(One list for style/effect and shape—not separate taxonomies.)*

---

### User Story 4 - Research beyond uploads (Priority: P4)

As a writer, I want user materials **and** web research aimed at audience-fit and citable specificity, so the draft is not merely a paraphrase of my PDF.

**Why this priority**: Core “how did it know that?” aspiration; hard gate is research-used-or-declared + provenance (see Success Criteria).

**Independent Test**: With web enabled, draft uses ≥1 non-upload finding that affects ask/framing/evidence **or** explicitly states no useful external signal.

**Acceptance Scenarios**:

1. **Given** web research enabled and useful public signal exists, **When** the run completes, **Then** at least one non-upload finding affects the draft **or** the run declares no useful signal found.
2. **Given** only user uploads and no useful web signal, **When** the run completes, **Then** the system does not fake differentiated web insight.

---

### User Story 5 - General short-form smoke (Priority: P5)

As a general short-form writer, I want the same engine for other 1–3 page goals, so I am not locked into a grants-only tool.

**Why this priority**: Platform shape; **primacy vs beachhead is Review lock F2 (paused)** — do not treat as equal success bar until F2 locks.

**Independent Test**: One non-grant 1–3 page prompt completes using the same intake/steer/research/draft path (smoke).

**Acceptance Scenarios**:

1. **Given** a non-grant short-form goal, **When** a run completes, **Then** the pipeline runs without grants-only hard failures (exact bar depends on F2).

---

### Edge Cases

- First prompt already complete → N = 0 questions.
- Funder named but no criteria materials / no public signal → audience-fit rules may be N/A; research-used-or-declared must still declare no signal if web enabled.
- Conflicting property ranks (e.g. humorous vs formal) → weave coherently; grant-default profile TBD (F3).
- Citation presentation preference missing → TBD (F7).
- Multi-minute research/write → must not assume a single short-lived serverless request (backend jobs).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST produce drafts targeted at approximately **1–3 pages** unless the user overrides length-related properties.
- **FR-002**: System MUST support grant/donation-ask beachhead without hard-limiting the engine to that vertical alone *(primacy rule: F2)*.
- **FR-003**: System MUST provide adaptive intake Q&A as continuum **0…N** filling gaps in the first prompt (not a fixed script).
- **FR-004**: System MUST expose a **product-owned closed** property vocabulary; users select/prioritize; free-text property invention is out of band for v2.0.
- **FR-005**: System MUST infer a draft property ranking from free text and allow user correction against the closed list.
- **FR-006**: System MUST weave ranked properties into the writer/critique **prompt program**.
- **FR-007**: System MUST accept user-provided materials (links/uploads) **and** perform web research when enabled.
- **FR-008**: System MUST apply provenance rules for org/funder-specific claims beyond the raw prompt.
- **FR-009**: WHEN web research is enabled, System MUST use ≥1 non-upload finding that affects the draft **or** explicitly declare no useful external signal.
- **FR-010**: System MUST collect or apply a citation/sources presentation preference *(exact default vs every-run question: F7)*.
- **FR-011**: Product MUST be a **new** registry app `smart-writer-v2`; legacy `smart-writer` remains available; no V2→V1 back-port requirement.
- **FR-012**: Long-running research/write MUST run as **backend jobs** suitable for multi-minute pipelines.
- **FR-013**: [NEEDS CLARIFICATION F3]: Is grounding always-on pipeline invariant vs ranked property? (`factual` emphasis vs retrieval).
- **FR-014**: [NEEDS CLARIFICATION F6]: Minimal grant intent slots that force N>0 when missing.
- **FR-015**: [NEEDS CLARIFICATION F5]: Learning/stack (v0, LangGraph) are journey preferences—must not be product Ubiquitous pass/fail (expected lock: demote from product gates).

### Key Entities

- **Run / Job**: Long-running write session; status; inputs snapshot; outputs.
- **Intent profile**: Prompt + gap-fill Q&A answers + citation preference.
- **Property ranking**: Ordered closed-vocabulary items (inferred + user-corrected).
- **Source / provenance record**: User material or retrieved web snippet; linked to claims.
- **Draft + critique cycle**: Iterations, scores/feedback as designed in plan.
- **Acceptance check result** (later): Catalog id × run outcome for evals.

## Success Criteria *(mandatory)*

Hard gates are **structural / evidence** checks, not literary taste. (F1 locked.)

### Failable outcome classes

- **SC-001 Length**: Drafts target ≈1–3 pages unless overridden.
- **SC-002 Audience-fit**: WHEN named funder/recipient + available criteria exist, draft includes **≥2 concrete fit points** tied to those criteria; not generic-only nonprofit prose.
- **SC-003 Provenance**: WHEN draft asserts org/funder-specific fact beyond raw prompt, attach checkable provenance or omit/mark uncertain.
- **SC-004 Research-used-or-declared**: WHEN web research enabled, use ≥1 non-upload finding that affects ask/framing/evidence **or** explicitly state no useful external signal found.
- **SC-005 Engine not grants-only**: Non-grant short-form path can run (smoke); full success primacy TBD F2.

### Aspirational (optional — not sole pass/fail)

- “How did it know that?” specificity and strong emotional/rhetorical effect may guide critique and human review.
- Credible funder-fit **without** surprise still passes.

### Acceptance catalog

Detailed check instances: [`acceptance.md`](./acceptance.md) (extensible; not buried in code/prompts).  
Charter keeps stable classes; catalog grows from test runs.

## Review locks *(mandatory before Approved)*

Brief: [`docs/agent-os/SPEC_REVIEW_PROMPT.md`](../../docs/agent-os/SPEC_REVIEW_PROMPT.md) (set `SPEC_PATH` to this file).

| ID | Status | Lock |
|----|--------|------|
| **F1** | **locked** | Failable classes SC-002–004 (+ length); surprise/emotion aspirational; extensible `acceptance.md` catalog. (Also lab constitution §B–C.) |
| F2 | **open** | Beachhead vs general primacy — **resume next** |
| F3 | **open** | Grounding always-on vs property list; grant-default humor |
| F4 | **open** | Web vs uploads emphasis for funder fit (partially reflected in FR/Research; confirm) |
| F5 | **open** | Demote learning/stack from product Ubiquitous gates |
| F6 | **open** | Minimal grant intent slots |
| F7 | **open** | Citations default + override vs every-run question |

**Status → Approved only after Blockers/Debates from review are resolved or explicitly accepted.**

## Assumptions

- Hobbyist scale ~10 users (stretch ~100); not enterprise multi-tenant.
- Users can supply funder URLs/PDFs for serious grant asks; web alone is allowed but not the only path to fit.
- Property vocabulary will grow at implementation; seed list is enough for spec approval.
- Lab learning (v0/Next UI, LangGraph-when-fit) is a **journey preference**, not the product win condition (confirm F5).
- Cattle/secrets/registry invariants apply (`AGENTS.md` / constitution).
- Cost/latency matter but are not primary vs learning + product quality on this journey.
- Preview gate required so public URLs cannot unbounded-spend the lab owner’s model keys (exact design → plan).

## Out of scope (v2.0)

- Enterprise: payments, heavy auth, realtime collab, elaborate compliance history products.
- V1 feature-parity / migrating all users off V1.
- Finalizing full property vocabulary in this document.
- Multi-vertical packaging as separate apps.
- Access to truly secret / non-public information.

## Open questions (plan / locks)

1. **F2–F7** — product locks (see Review locks).
2. Property vocabulary expansion — implementation.
3. Research providers / allowlists — `plan.md`.
4. Monorepo sharing vs clean-room in `smart-writer-v2` — `plan.md`.
5. Golden prompts (grant + non-grant) + catalog growth — plan/tasks.

## Approval

- [ ] Remaining review locks F2–F7 done (or explicitly accepted).
- [ ] Human sets **Status: Approved**.
- [ ] Then `/speckit-plan` (Architecture + Phased delivery) — **not** tasks/implement before plan approval (constitution §E).
