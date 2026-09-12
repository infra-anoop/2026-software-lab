# Feature Specification: Smart Writer V2

**Feature Branch**: `smart-writer-v2`

**Created**: 2026-09-10

**Status**: Draft — Spec Kit shape aligned; **F1–F7 product locks complete** — ready for human **Approved** (optional process review still available)

**Input**: Lab coaching locks (A1–D, N1–N14) + independent **product** review triage; app id `smart-writer-v2` (new registry app; V1 `smart-writer` remains legacy)

**Process**: Spec Kit + `.specify/memory/constitution.md` — do not re-argue process here.

**Lab dual intent (F5):** This feature is a **dogfood vehicle** for Agent OS / Spec Kit learning (meta product). The **surface product** is a grant/donation short-form writer (F2 primacy). Surface pass/fail = F1–F4 style outcomes. Journey/stack prefs belong in Plan/Assumptions — not as surface Ubiquitous gates. Optional **process review**: `docs/agent-os/PROCESS_REVIEW_PROMPT.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Funder-specific grant / donation ask (Priority: P1)

As a nonprofit writer, I want a short (≈1–3 page) grant or donation ask grounded in what *this* funder cares about, so the draft feels specific and credible—not generic charity prose.

**Why this priority**: Beachhead use case and primary product bet.

**Independent Test**: Given org context + named funder with available criteria, produce a draft that includes concrete fit points and provenance for specific claims; can be judged without other stories.

**Acceptance Scenarios**:

1. **Given** a named funder and criteria (upload, link, or retrieved public material), **When** a run completes, **Then** the draft includes at least two concrete fit points tied to those criteria (not only generic nonprofit language).
2. **Given** the draft asserts an org- or funder-specific fact beyond the raw prompt, **When** the draft is inspected, **Then** each such claim has checkable provenance or is omitted / marked uncertain.

---

### User Story 2 - Dual-schema gap-fill intake (Priority: P2)

As a user who prompts poorly, I want optional Q&A that only asks what my first prompt (and materials) left unclear — on **two axes** — so I think harder without a canned interview.

**Why this priority**: Unlocks research + steering; F6.

**Independent Test**: Complete grant prompt+materials → N may be 0; missing Who/Whom/Ask → questions only for those slots; weak property inference → at most a few steering clarifiers; not a fixed full questionnaire.

**Acceptance Scenarios**:

1. **Given** a sufficient first prompt + materials covering grant intent slots, **When** intake runs, **Then** Axis A asks may be N=0.
2. **Given** missing grant intent slots, **When** intake runs, **Then** the system asks **only** for missing Axis A slots (not a fixed script of all questions).
3. **Given** ambiguous or conflicting property steering, **When** intake runs, **Then** Axis B may ask a **small** number of clarifiers; prefer showing inferred rank chips for correction over interviewing every property.
4. **Given** both Axis A and Axis B incomplete on a grant run, **When** prioritizing questions, **Then** **Axis A (intent) before Axis B (properties)**.

**F6 — two intake schemas (one continuum 0…N):**

| Axis | Role | When to ask |
|------|------|-------------|
| **A. Grant intent slots** | Substance: can we write a real ask? | If missing after prompt + uploads |
| **B. Property / steering gaps** | Rhetoric/shape: closed vocabulary | If decode ranking is weak/conflicting; prefer chips over long Q&A |

**Axis A — minimal grant slots (must-have):**

| Slot | Meaning |
|------|---------|
| Who asks | Org / applicant identity |
| Whom | Funder / recipient (named) |
| Ask | What is requested (shape of ask) |
| Why this funder | Fit hook (≥1 sentence or equivalent) |
| Evidence of fit / impact | ≥1 concrete org fact or pointer (may come from uploads) |

Non-grant smoke (F2): Axis A N/A or thinner (plan). Exact question copy → plan/UI.

---

### User Story 3 - Closed property steering (Priority: P3)

As a user, I want to rank a product-owned closed vocabulary of properties (and correct an inferred draft ranking), so steering is crisp without inventing labels mid-flow.

**Why this priority**: Controllable rhetoric/shape without free-text chaos.

**Independent Test**: Infer ranking from prompt → user reorders closed chips → writer/critique prompt program reflects order; grounding/research still runs even if `factual` is ranked low.

**Acceptance Scenarios**:

1. **Given** a free-text prompt, **When** decode runs, **Then** a draft ranking against the closed list is shown for correction.
2. **Given** a user-ordered property list, **When** draft/critique runs, **Then** properties are woven into the prompt program (not a slogan append).
3. **Given** grant beachhead defaults, **When** a new grant-oriented run starts without overrides, **Then** `humorous` is de-emphasized or off-by-default (user may still enable it).

**Seed vocabulary (non-final; expand at implementation):**  
`emotional` · `humorous` · `persuasive` · `factual` · `concise` · `formal` · `urgent` · `visionary`  
*(One list for style/effect and shape—not separate taxonomies.)*

**F3 — grounding vs properties:**  
**Grounding is a pipeline invariant** (research path + SC-003 provenance + SC-004 research-used-or-declared). It is **not** a chip that can be ranked off.  
**`factual` in the list** means prose **emphasis/tone** (more evidence-forward), **not** enable/disable retrieval.

---

### User Story 4 - Research: materials + web with clear roles (Priority: P4)

As a writer, I want **user materials and web research** with clear jobs, so the draft hits **funder/org criteria** and still gains **non-upload differentiation**—not PDF paraphrase and not trivia for its own sake.

**Why this priority**: Audience-fit + differentiated insight (F4).

**Independent Test**: With criteria in uploads/links, fit points come from those materials; web adds non-upload signal or run declares none; flashy web fact never overrides an uploaded criterion.

**Acceptance Scenarios**:

1. **Given** user-provided funder/org criteria materials, **When** the run builds fit, **Then** those materials are first-class for criteria and claimable org evidence.
2. **Given** web research enabled, **When** useful public signal exists outside uploads, **Then** ≥1 non-upload finding affects ask/framing/evidence **or** the run declares no useful external signal.
3. **Given** both an uploaded criterion and a novel web tidbit, **When** they conflict for emphasis, **Then** the draft prefers **audience-fit from materials/criteria** over novelty trivia.

**F4 — source roles:**

| Source | Primary job |
|--------|-------------|
| User uploads / links | Criteria & org evidence |
| Web | Differentiating public signal not in the upload set |

---

### User Story 5 - General short-form smoke (Priority: P5)

As a general short-form writer, I want the same engine for other 1–3 page goals, so I am not locked into a grants-only *codepath*.

**Why this priority**: Keeps the engine general; **not** an equal success bar. **F2 locked:** v2.0 success = grant/donation asks; non-grant is smoke-test only when goals conflict.

**Independent Test**: One non-grant 1–3 page prompt completes on the same intake/steer/research/draft path.

**Acceptance Scenarios**:

1. **Given** a non-grant short-form goal, **When** a run completes, **Then** the pipeline completes without grants-only hard failures (smoke).
2. **Given** a conflict between grant credibility and general-doc convenience, **When** product defaults/evals/MVP are chosen, **Then** grant beachhead wins.

---

### Edge Cases

- First prompt + materials complete Axis A → N may be 0 for intent; Axis B still may clarify steering.
- Missing Axis A on grant run → must ask before final draft; Axis A before Axis B (F6).
- Property list not fully enumerated → seed vocabulary enough; expansion at implementation (F6 Axis B).
- Funder named but no criteria materials / no public signal → audience-fit rules may be N/A; research-used-or-declared must still declare no signal if web enabled.
- Conflicting property ranks (e.g. humorous vs formal) → weave coherently; grant default de-emphasizes `humorous` (F3).
- User ranks `factual` low → grounding/research **still on**; only prose emphasis changes (F3).
- Citation presentation: default **sources panel**; override optional; skip ask if no sources will appear (F7).
- Multi-minute research/write → must not assume a single short-lived serverless request (backend jobs).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST produce drafts targeted at approximately **1–3 pages** unless the user overrides length-related properties.
- **FR-002**: System MUST treat **grant/donation-ask as v2.0 success primacy**. The engine MUST remain usable for other 1–3 page goals as a **smoke path**, but when defaults, evals, or MVP phasing conflict, grant credibility wins (F2).
- **FR-003**: System MUST provide adaptive intake Q&A as continuum **0…N** (not a fixed script), covering **two schemas** (F6): Axis A grant intent slots and Axis B property/steering gaps.
- **FR-003a**: For grant beachhead, System MUST detect the minimal intent slots (Who, Whom, Ask, Why this funder, Evidence) from prompt + materials; IF any are missing, System MUST ask before final draft — **only** for missing slots (F6).
- **FR-003b**: System MUST infer property ranking (FR-005) and MAY ask a **small** number of Axis B clarifiers when ranking is weak/conflicting; prefer editable chips over interviewing every property (F6).
- **FR-003c**: WHEN both axes are incomplete on a grant run, System MUST prioritize **Axis A before Axis B** (F6).
- **FR-004**: System MUST expose a **product-owned closed** property vocabulary; users select/prioritize; free-text property invention is out of band for v2.0.
- **FR-005**: System MUST infer a draft property ranking from free text and allow user correction against the closed list.
- **FR-006**: System MUST weave ranked properties into the writer/critique **prompt program**.
- **FR-006a**: **Grounding MUST be a pipeline invariant** (not a user-ranked off switch): research path when enabled, provenance (SC-003), research-used-or-declared (SC-004). Property `factual` means **emphasis/tone only** (F3).
- **FR-006b**: Grant beachhead MUST use a default property profile that **de-emphasizes or defaults off `humorous`**; user may still enable humor explicitly (F3).
- **FR-007**: System MUST accept user-provided materials (links/uploads) **and** support web research when enabled.
- **FR-007a**: For grant beachhead, user materials MUST be **first-class for funder criteria and org evidence**; web research MUST target **differentiating public signal** not already in uploads (F4).
- **FR-007b**: System MUST NOT prefer novelty web trivia over uploaded/linked criteria when choosing what the draft emphasizes (F4).
- **FR-008**: System MUST apply provenance rules for org/funder-specific claims beyond the raw prompt.
- **FR-009**: WHEN web research is enabled, System MUST use ≥1 non-upload finding that affects the draft **or** explicitly declare no useful external signal.
- **FR-010**: System MUST present sources with a **grant beachhead default of sources panel** (end-matter / panel list). User MAY override to inline, footnotes, panel, or combination via **one** light control — not a mandatory multi-step interview every run (F7).
- **FR-010a**: IF a run will produce no citable sources, System MUST NOT force a citation-format question (F7).
- **FR-010b**: Provenance rules (SC-003) MUST hold regardless of presentation mode — F7 is display only (F7).
- **FR-011**: Product MUST be a **new** registry app `smart-writer-v2`; legacy `smart-writer` remains available; no V2→V1 back-port requirement.
- **FR-012**: Long-running research/write MUST run as **backend jobs** suitable for multi-minute pipelines.
- **FR-013**: *(resolved F3 — see FR-006a / FR-006b)*
- **FR-014**: *(resolved F6 — see FR-003 / FR-003a–c)*
- **FR-015**: **Dual intent (F5):** Surface product Ubiquitous gates = grant/research/steering/jobs outcomes (F1–F4). Lab journey preferences (v0/Next UI, LangGraph-when-fit, Spec Kit practice) are **first-class lab goals** stated in Meta/Plan/Assumptions but **MUST NOT** be surface-product pass/fail checkboxes (e.g. “must use LangGraph” does not fail a good grant draft).

### Key Entities

- **Run / Job**: Long-running write session; status; inputs snapshot; outputs.
- **Intent profile**: Prompt + Axis A slot values + Axis B property ranking + citation preference (F7).
- **Grant intent slots (Axis A)**: Who, Whom, Ask, Why this funder, Evidence — filled from prompt, materials, or Q&A.
- **Property ranking**: Ordered closed-vocabulary items (inferred + user-corrected).
- **Source / provenance record**: User material or retrieved web snippet; linked to claims.
- **Draft + critique cycle**: Iterations, scores/feedback as designed in plan.
- **Acceptance check result** (later): Catalog id × run outcome for evals.

## Success Criteria *(mandatory)*

Hard gates are **structural / evidence** checks, not literary taste. (F1 locked.)

### Failable outcome classes

- **SC-001 Length**: Drafts target ≈1–3 pages unless overridden.
- **SC-002 Audience-fit**: WHEN named funder/recipient + available criteria exist, draft includes **≥2 concrete fit points** tied to those criteria; not generic-only nonprofit prose. Prefer criteria from **user materials** when present (F4).
- **SC-003 Provenance**: WHEN draft asserts org/funder-specific fact beyond raw prompt, attach checkable provenance or omit/mark uncertain. *(Part of grounding invariant — F3.)*
- **SC-004 Research-used-or-declared**: WHEN web research enabled, use ≥1 non-upload finding that affects ask/framing/evidence **or** explicitly state no useful external signal found. *(Grounding — F3; web’s job is differentiation — F4; upload-only fit can still pass SC-002/003.)*
- **SC-005 Engine smoke (non-grant)**: Non-grant short-form path can complete on the same engine. **Does not** redefine v2.0 success; grant beachhead remains the primary bar (F2).

### Aspirational (optional — not sole pass/fail)

- “How did it know that?” specificity and strong emotional/rhetorical effect may guide critique and human review.
- Credible funder-fit **without** surprise still passes.

### Acceptance catalog

Detailed check instances: [`acceptance.md`](./acceptance.md) (extensible; not buried in code/prompts).  
Charter keeps stable classes; catalog grows from test runs.

## Review locks *(mandatory before Approved)*

Briefs: product [`SPEC_REVIEW_PROMPT.md`](../../docs/agent-os/SPEC_REVIEW_PROMPT.md) (**F-***); optional process [`PROCESS_REVIEW_PROMPT.md`](../../docs/agent-os/PROCESS_REVIEW_PROMPT.md) (**R-***).

| ID | Status | Lock |
|----|--------|------|
| **F1** | **locked** | Failable classes SC-002–004 (+ length); surprise/emotion aspirational; extensible `acceptance.md` catalog. (Also lab constitution §B–C.) |
| **F2** | **locked** | **v2.0 success = grant/donation asks.** Non-grant = same-engine **smoke** only; when goals conflict, grant primacy wins (defaults, evals, MVP phasing). |
| **F3** | **locked** | **Grounding = pipeline invariant** (research + SC-003/004), not a ranked off-switch. **`factual` = emphasis/tone only.** Grant default profile **de-emphasizes / offs `humorous`** (user may enable). |
| **F4** | **locked** | **Uploads/links = first-class for criteria & org evidence.** **Web = differentiating public signal** outside uploads. Prefer audience-fit from materials over novelty trivia when they conflict. |
| **F5** | **locked** | **Dual intent:** dogfood/Agent OS learning is lab-primary; surface success = F1–F4 grant bars. Journey/stack = Plan/Assumptions prefs, **not** surface Ubiquitous checkboxes. Product vs process reviews may diverge; human adjudicates. |
| **F6** | **locked** | Intake = **two schemas** in one 0…N continuum: **Axis A** minimal grant slots (Who/Whom/Ask/Why/Evidence); **Axis B** property/steering gaps (chips + sparse clarifiers). Grant runs: **A before B**; missing A → must ask. |
| **F7** | **locked** | **Default = sources panel** for grant beachhead; **one light override** (inline / footnotes / panel / combo). Skip citation UX ask when no sources. Provenance (SC-003) independent of display mode. |

**Status → Approved only after Blockers/Debates from review are resolved or explicitly accepted.**

## Assumptions

- Hobbyist scale ~10 users (stretch ~100); not enterprise multi-tenant.
- Users can supply funder URLs/PDFs for serious grant asks; web alone is allowed but not the only path to fit.
- Property vocabulary will grow at implementation; seed list is enough for spec approval.
- Lab learning (v0/Next UI, LangGraph-when-fit, Spec Kit loop) is a **first-class lab/journey goal** and preferred Plan posture when it fits — **not** a surface-product Ubiquitous fail condition (F5).
- Optional process/lab-vehicle review may be run later via `PROCESS_REVIEW_PROMPT.md`; product review continues with **F** locks.
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

1. Optional: run **process** review (`PROCESS_REVIEW_PROMPT.md`) before or after Approved.
2. Property vocabulary expansion — implementation.
3. Research providers / allowlists — `plan.md`.
4. Monorepo sharing vs clean-room in `smart-writer-v2` — `plan.md`.
5. Golden prompts (grant + non-grant) + catalog growth — plan/tasks.
6. Exact citation UI control placement — plan/UI.

## Approval

- [x] Product review locks F1–F7 done.
- [ ] Optional process review (R-*) triaged if run.
- [ ] Human sets **Status: Approved**.
- [ ] Then `/speckit-plan` (Architecture + Phased delivery) — **not** tasks/implement before plan approval (constitution §E).
