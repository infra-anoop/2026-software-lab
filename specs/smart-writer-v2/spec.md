# Feature Specification: Smart Writer V2

**Feature Branch**: `smart-writer-v2`

**Created**: 2026-09-10

**Status**: **Approved** — F1–F8 + R1–R9; plan Architecture + Phasing **Approved** (P1–P8). Next: `/speckit-tasks`.

**Input**: Independent **product** (F*) + **process** (R*) review triage; app id `smart-writer-v2` (new registry app; V1 `smart-writer` remains legacy). Pre-spec coaching ids A1–D / N1–N14 are **superseded** by F1–F8 (R3) — not cited as binding input.

**Process**: Spec Kit + `.specify/memory/constitution.md` — do not re-argue process here. Process review artifact: [`PROCESS_REVIEW.md`](./PROCESS_REVIEW.md).

**Lab dual intent (F5/R2):** Dogfood vehicle for Agent OS / Spec Kit. **Surface** pass/fail = F1–F4 / SC-001–007. **Lab** success for this loop = human plan/PR adjudication (not harness SC classes). Journey/stack prefs → Plan/Assumptions only.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Funder-specific grant / donation ask (Priority: P1)

As a nonprofit writer, I want a short (≈1–3 page) grant or donation ask grounded in what *this* funder cares about, so the draft feels specific and credible—not generic charity prose.

**Why this priority**: Beachhead use case and primary product bet.

**Independent Test**: Given org context + named funder with available criteria, produce a draft that includes concrete fit points and provenance for specific claims; can be judged without other stories.

**Acceptance Scenarios**:

1. **Given** a named funder and criteria (upload, link, or retrieved public material), **When** a run completes, **Then** the draft includes at least two concrete fit points tied to those criteria (not only generic nonprofit language).
2. **Given** the draft asserts an org- or funder-specific fact beyond the raw prompt, **When** the draft is inspected, **Then** each such claim has checkable provenance or is omitted / marked uncertain.

---

### User Story 2 - Chat iterate with continuity (Priority: P2)

As a writer, I want a **chat-style** loop: I send free-form messages; the product always shows a **complete** output; I send feedback; the next output **improves the previous artifact** instead of throwing it away—unless I ask to start over.

**Why this priority**: Humans rarely accept first output; cold full regen is a known failure mode.

**Independent Test**: Produce output A; send feedback; get output B that is a revise of A (linked version); send “start over”; get a fresh generate.

**Acceptance Scenarios**:

1. **Given** a user message with no prior artifact, **When** the product responds with a writing artifact, **Then** the artifact is complete and visible (not an incomplete stub).
2. **Given** a prior artifact and free-form feedback (no restart), **When** the product runs again, **Then** it uses a **revise** path with prior output + feedback in context — not a silent full re-initialize.
3. **Given** the user requests regenerate/start over, **When** the product runs again, **Then** it may run a fresh **generate** path.
4. **Given** free-form user text, **When** state is updated, **Then** the user is not required to fill Axis/slot forms; internal schema updates are inferred.

---

### User Story 3 - Interleaved clarification Q&A (Priority: P3)

As a user, I want occasional **specific questions** when something critical is missing, interleaved in the same chat—without learning internal labels like “Axis A/B.”

**Why this priority**: Unlocks research + steering (F6) without a canned interview or schema UI.

**Independent Test**: Rich prompt+materials → few/no questions; missing Who/Whom/Ask → targeted questions only; questions never name internal axis IDs.

**Acceptance Scenarios**:

1. **Given** prompt + materials already covering grant intent slots, **When** clarification runs, **Then** intent questions may be zero.
2. **Given** missing grant intent slots, **When** clarification runs, **Then** the system asks **only** for missing slots (not a fixed full script).
3. **Given** weak/conflicting steering inference, **When** clarification runs, **Then** at most a few clarifiers (optional property chips OK); free-form remains primary.
4. **Given** both intent and steering holes on a grant run, **When** prioritizing questions, **Then** intent holes before steering holes (**internal** order).

**F6 — internal intake state (not user-visible taxonomy):**

| Internal axis | Role | When to ask |
|---------------|------|-------------|
| **A. Grant intent slots** | Substance | If missing after prompt + uploads |
| **B. Property / steering** | Rhetoric/shape | If decode ranking weak/conflicting |

**Axis A — minimal grant slots (internal must-have):** Who asks · Whom · Ask · Why this funder · Evidence of fit/impact  

Non-grant smoke (F2): Axis A N/A or thinner (plan). Users never need to know these names.

---

### User Story 4 - Closed property steering (Priority: P4)

As a writer, I want steering (tone/shape) applied from my free-form messages—and optional light controls—using a product-owned closed vocabulary internally, without inventing property labels myself.

**Why this priority**: Controllable rhetoric/shape without free-text chaos or schema homework.

**Independent Test**: Free-form prompt updates internal ranking; optional chip correction works; grounding/research still runs even if `factual` is ranked low.

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

### User Story 5 - Research: materials + web with clear roles (Priority: P5)

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

### User Story 6 - General short-form smoke (Priority: P6)

As a general short-form writer, I want the same engine for other 1–3 page goals, so I am not locked into a grants-only *codepath*.

**Why this priority**: Keeps the engine general; **not** an equal success bar. **F2 locked:** v2.0 success = grant/donation asks; non-grant is smoke-test only when goals conflict.

**Independent Test**: One non-grant 1–3 page prompt completes on the same intake/steer/research/draft path.

**Acceptance Scenarios**:

1. **Given** a non-grant short-form goal, **When** a run completes, **Then** the pipeline completes without grants-only hard failures (smoke).
2. **Given** a conflict between grant credibility and general-doc convenience, **When** product defaults/evals/MVP are chosen, **Then** grant beachhead wins.

---

### Edge Cases

- Free-form feedback with no prior artifact → treat as initial **generate**.
- Free-form feedback with prior artifact (no restart) → **revise** (continuity); not silent full regen (F8).
- User requests start over / regenerate → **generate** path allowed (F8).
- Clarification Q&A turn may be a short question (not a full 1–3 page artifact).
- Internal intent slots complete from prompt + materials → clarification questions may be zero; steering may still clarify.
- Missing internal intent slots on grant run → ask before producing the long grant artifact; intent before steering (**internal** order) (F6).
- Property list not fully enumerated → see **Open Decisions** (D1); do not invent labels in chat.
- Funder named but no criteria materials / no public signal → audience-fit rules may be N/A; research-used-or-declared must still declare no signal if web enabled.
- Conflicting property ranks → weave coherently; grant default de-emphasizes `humorous` (F3).
- User ranks `factual` low → grounding/research **still on**; only prose emphasis changes (F3).
- Citation presentation: default **sources panel**; override optional; skip ask if no sources (F7).
- Multi-minute research/write → backend jobs (not a single short-lived serverless request).
- Optional machine assessor/writer loop (if used) is separate from **human revise** path (F8).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST produce drafts targeted at approximately **1–3 pages** unless the user overrides length-related properties.
- **FR-002**: System MUST treat **grant/donation-ask as v2.0 success primacy**. The engine MUST remain usable for other 1–3 page goals as a **smoke path**, but when defaults, evals, or MVP phasing conflict, grant credibility wins (F2).
- **FR-003**: System MUST support interleaved clarification Q&A (0…N specific questions, not a fixed script). Internally this fills grant intent slots and/or property steering (F6). Users MUST NOT be required to know internal axis/slot names.
- **FR-003a**: For grant beachhead, System MUST detect the minimal intent slots (Who, Whom, Ask, Why this funder, Evidence) from free-form prompt + materials; IF any are missing, System MUST ask before the long grant artifact — **only** for missing slots (F6).
- **FR-003b**: System MUST infer property ranking from free-form text (FR-005) and MAY ask a **small** number of steering clarifiers when ranking is weak/conflicting; optional property chips allowed; free-form remains primary (F6/F8).
- **FR-003c**: WHEN both intent and steering holes exist on a grant run, System MUST prioritize **intent before steering** internally (F6).
- **FR-004**: System MUST maintain a **product-owned closed** property vocabulary for internal steering; free-text invention of new property labels by end users is out of band for v2.0.
- **FR-005**: System MUST infer a property ranking from free-form text and allow correction (free-form and/or optional chips) against the closed list.
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
- **FR-016**: User-facing messages are **free-form**. System MUST NOT require user-visible forms for internal intent slots / axes (F8).
- **FR-017**: System MUST infer and update **internal** structured state from free-form text (rules and/or LLM) (F8).
- **FR-018**: Each turn that yields a writing artifact MUST present a **complete** user-visible output (F8).
- **FR-019**: WHEN the user sends feedback on an existing artifact and does not request restart, System MUST use a **revise** path (prior output + feedback + relevant internal state)—NOT a silent full re-initialize (F8).
- **FR-020**: System MUST support an explicit **regenerate / start over** path (fresh generate) (F8).
- **FR-021**: Clarifying Q&A and revision feedback share the same conversational surface; Q&A asks specific questions when needed and MUST NOT expose internal axis/slot nomenclature (F6/F8).

### Key Entities

- **Message / Turn**: Free-form user text (prompt, clarification answer, or feedback) + product response.
- **ArtifactVersion**: Complete user-visible writing output; optional parent version for revise continuity (F8).
- **InternalRunState**: Invisible structured state (intent slots, property ranking, sources, citation mode, etc.).
- **Run / Job**: Long-running generate or revise work; status; snapshots.
- **Source / provenance record**: User material or retrieved web snippet; linked to claims.
- **Machine critique cycle** (optional): Writer↔assessor-style loops if used in plan — distinct from **human revise** (F8).
- **Acceptance check result** (later): Catalog id × run outcome for evals.

For SC-006/007: revise vs generate MUST be distinguishable in run/artifact metadata (exact fields → plan).

## Success Criteria *(mandatory)*

Hard gates are **structural / evidence** checks, not literary taste. (F1 locked.)

### Failable outcome classes

- **SC-001 Length**: Drafts target ≈1–3 pages unless overridden.
- **SC-002 Audience-fit**: WHEN named funder/recipient + available criteria exist, draft includes **≥2 concrete fit points** tied to those criteria; not generic-only nonprofit prose. Prefer criteria from **user materials** when present (F4).
- **SC-003 Provenance**: WHEN draft asserts org/funder-specific fact beyond raw prompt, attach checkable provenance or omit/mark uncertain. *(Part of grounding invariant — F3.)*
- **SC-004 Research-used-or-declared**: WHEN web research enabled, use ≥1 non-upload finding that affects ask/framing/evidence **or** explicitly state no useful external signal found. *(Grounding — F3; web’s job is differentiation — F4; upload-only fit can still pass SC-002/003.)*
- **SC-005 Engine smoke (non-grant)**: Non-grant short-form path can complete on the same engine. **Does not** redefine v2.0 success; grant beachhead remains the primary bar (F2).
- **SC-006 Revise continuity**: WHEN user feedback follows an artifact without restart, the new writing artifact MUST be a new **ArtifactVersion** linked to the previous artifact and that feedback (F8).
- **SC-007 Regenerate distinct**: WHEN user requests start over / regenerate, the system MUST use the fresh **generate** path (distinguishable from revise) (F8).

### Aspirational (optional — not sole pass/fail)

- “How did it know that?” specificity and strong emotional/rhetorical effect may guide critique and human review.
- Credible funder-fit **without** surprise still passes.
- First complete output often revised; usable-as-is is aspirational (F8).

### Acceptance catalog

Detailed check instances: [`acceptance.md`](./acceptance.md) (extensible; not buried in code/prompts).  
Charter keeps stable classes; catalog grows from test runs.

## Open Decisions *(constitution §G — dogfood)*

Shape was locked in F*/P* reviews; content below was deferred or invented without a sync. Rows make that debt **fail-closed** for remaining a/b/c/d work.

| id | shape_locked | content_open | who | before | status |
|----|--------------|--------------|-----|--------|--------|
| **D1** | Closed property vocabulary; dual intake axes (F6); `factual` = tone only (F3) | Exact label list for v2.0 seed | human | Before changing `app/properties.py` / steering chips beyond the ratified seed | **locked** — ratified post-hoc as shipped seed: `factual`, `persuasive`, `concise`, `warm`, `formal`, `humorous`, `specific`, `urgent` (research R8). Reopen only by flipping status to `open`. |
| **D2** | Preview gate + rate limit + queue exist (B5/A9); unbounded spend still blocked by secret | Numeric turn/cost caps: max write jobs per conversation, max clarify turns, any HTTP iteration-style cap | human | Before turn/cost Settings work (tasks polish) | **open** |
| **D3** | `LOGFIRE_TOKEN` named in secrets schema (A25); no product SC for Logfire (F5) | Whether to wire Logfire init this cycle (noop if unset) vs leave deferred | human | Before observability init work | **open** |
| **D4** | Citation modes = panel / inline / footnotes / combo; default panel when sources exist; skip ask if no sources (F7) | Light control placement/UX in chat (where it lives; never block send when no sources) | human | Before citation override UI | **open** |
| **D5** | Topology: Vercel UI+BFF + Railway worker (P1); thin env names documented | Whether/when to provision live Vercel + Infisical→Vercel + worker URL (production browser dogfood) | human | Before fat UI-host ops packet | **open** |
| **D6** | Preview secret **name** in schema; mutating `/v1` fail-closed without it | Seed `SMART_WRITER_V2_AUDIT_SECRET` in Infisical (and later Vercel) | human | Before production mutating API / live BFF dogfood | **open** |
| **D7** | Materials via **links** in MVP; uploads first-class in F4 | Whether file-upload HTTP is in-scope next vs stay P3 deferred | human | Before upload contract/tasks | **open** (default stay deferred unless prioritized) |

**Fail closed:** Implement must not invent D2–D7 content while `open` + `who: human`. Pose in product language; record the lock here; then resume.

## Review locks *(mandatory before Approved)*

Briefs: product [`SPEC_REVIEW_PROMPT.md`](../../docs/agent-os/SPEC_REVIEW_PROMPT.md) (**F-***); process [`PROCESS_REVIEW_PROMPT.md`](../../docs/agent-os/PROCESS_REVIEW_PROMPT.md) (**R-***). Report: [`PROCESS_REVIEW.md`](./PROCESS_REVIEW.md).

| ID | Status | Lock |
|----|--------|------|
| **F1** | **locked** | Failable classes SC-002–004 (+ length); surprise/emotion aspirational; extensible `acceptance.md` catalog. (Also lab constitution §B–C.) |
| **F2** | **locked** | **v2.0 success = grant/donation asks.** Non-grant = same-engine **smoke** only; when goals conflict, grant primacy wins (defaults, evals, MVP phasing). |
| **F3** | **locked** | **Grounding = pipeline invariant** (research + SC-003/004), not a ranked off-switch. **`factual` = emphasis/tone only.** Grant default profile **de-emphasizes / offs `humorous`** (user may enable). |
| **F4** | **locked** | **Uploads/links = first-class for criteria & org evidence.** **Web = differentiating public signal** outside uploads. Prefer audience-fit from materials over novelty trivia when they conflict. |
| **F5** | **locked** | **Dual intent:** dogfood/Agent OS learning is lab-primary; surface success = F1–F4 grant bars. Journey/stack = Plan/Assumptions prefs, **not** surface Ubiquitous checkboxes. Product vs process reviews may diverge; human adjudicates. |
| **F6** | **locked** | **Internal** intake state: intent slots + property steering; interleaved Q&A for holes only; **A before B** internally; users never required to know axis names. |
| **F7** | **locked** | **Default = sources panel** for grant beachhead; **one light override** (inline / footnotes / panel / combo). Skip citation UX ask when no sources. Provenance (SC-003) independent of display mode. |
| **F8** | **locked** | **Chat loop:** free-form user messages; complete outputs; internal schema inferred (axes not user-facing). **Revise-by-default** on feedback (continuity); explicit **regenerate** for fresh generate. Q&A interleaved as specific questions when needed. |
| **R1** | **accepted** | Dual intent / anti-cargo-cult stance is correct; do not add stack prefs as SC. |
| **R2** | **locked** | Lab success for this dogfood loop = **human plan/PR adjudication only** — no harness SC classes. Surface falsifiability remains SC-001–007. |
| **R3** | **locked** | Coaching locks A1–D / N1–N14 **superseded** by F1–F8; opaque citation dropped from Input. |
| **R4** | **accepted** | Keep product catalog; thin **auto** subset + further SC hygiene → plan/tasks (not Approve blocker). |
| **R5** | **deferred** | Open Architecture forks (jobs, ArtifactVersion/revise, preview gate, app boundary, etc.) are **required plan decisions** — not optional research. No spec rewrite. |
| **R6** | **deferred** | MVP DoD bus = Spec Kit **`tasks.md`**; thin `notes/packets/` only if a later slice is long/unattended — confirm in plan Phasing. |
| **R7** | **locked** | Process R* triage **required for this dogfood vehicle** before Approved; global template stays optional for non-dogfood features. |
| **R8** | **accepted** | Spec Kit shape sufficient; SC-001 soft length remains human (F1). |
| **R9** | **locked** | Agent OS README feature status kept in sync with spec locks. |

**Status → Approved only after Blockers/Debates from review are resolved or explicitly accepted.**

## Assumptions

- Hobbyist scale ~10 users (stretch ~100); not enterprise multi-tenant.
- Users can supply funder URLs/PDFs for serious grant asks; web alone is allowed but not the only path to fit.
- **Property vocabulary:** see Open Decision **D1** (ratified seed) — do not treat Assumptions as license to invent new labels.
- Lab learning (v0/Next UI, LangGraph-when-fit, Spec Kit loop) is a **first-class lab/journey goal** and preferred Plan posture when it fits — **not** a surface-product Ubiquitous fail condition (F5).
- **Lab measurement (R2):** Lab success is judged by human plan/PR adjudication and keeping Spec Kit rails — **not** by harness SC classes. Catalog `auto` checks / optional harness lint may grow later in plan/tasks.
- **Catalog automation (R4):** Thin auto-candidate checks (e.g. revise vs generate distinguishable) named in plan MVP exit criteria; not required to invent a full auto suite before Approve.
- **MVP DoD bus (R6):** Spec Kit `tasks.md` for v2.0 MVP; packets optional later for long unattended slices.
- Process review for this dogfood vehicle is filed and **human-adjudicated** (`PROCESS_REVIEW.md`); global template remains optional for non-dogfood features (R7).
- Iterative improvement via chat feedback is the **normal** path; cold full regen is opt-in (F8).
- Cattle/secrets/registry invariants apply (`AGENTS.md` / constitution).
- Cost/latency matter but are not primary vs learning + product quality on this journey.
- Preview gate required so public URLs cannot unbounded-spend the lab owner’s model keys — secret seed = Open Decision **D6**.

## Out of scope (v2.0)

- Enterprise: payments, heavy auth, realtime collab, elaborate compliance history products.
- V1 feature-parity / migrating all users off V1.
- Expanding property vocabulary beyond D1 without reopening D1.
- Multi-vertical packaging as separate apps.
- Access to truly secret / non-public information.
- Instrumenting lab success via harness SC classes in this feature’s surface Ubiquitous set (R2).

## Open questions (resolved → Open Decisions / plan)

Historical prompts; living debt is the **Open Decisions** table above.

1. Property vocabulary → **D1** (locked).
2. Research providers / allowlists → plan P2 deferred alts (locked learning-scope cut).
3. Clean-room `smart-writer-v2` → plan (done).
4. Golden prompts + thin auto → T061 done for ≥1 auto row; hybrid/human remain.
5. Citation UI control → **D4**.
6. Turn/cost caps → **D2**; Logfire → **D3**.
7. Preview gate / jobs → implemented; vault seed → **D6**; fat Vercel → **D5**.

## Approval

- [x] Product review locks F1–F8 done.
- [x] Process review R1–R9 human-adjudicated (R7 required for this dogfood vehicle).
- [x] Human sets **Status: Approved**.
- [x] Plan Architecture review (**P-***) triaged — see `PLAN_REVIEW.md`.
- [x] Human approves **plan.md** Architecture + Phased delivery.
- [x] `/speckit-tasks` + implement through plan P2 core (Open Decisions dogfood for remaining polish/ops).