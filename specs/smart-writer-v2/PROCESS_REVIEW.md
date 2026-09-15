# Process / lab-vehicle review — smart-writer-v2

**Reviewer role**: Independent process reviewer (did not author the spec)  
**Brief**: `docs/agent-os/PROCESS_REVIEW_PROMPT.md`  
**Primary**: `specs/smart-writer-v2/spec.md` (+ `acceptance.md` as catalog companion)  
**Date**: 2026-09-12  

**Triage (human lock-by-lock, 2026-09-15):** R1 accepted · R2 locked (b: human plan/PR) · R3 locked (drop A1–N14) · R4 accepted/deferred · R5 deferred · R6 deferred (`tasks.md` MVP) · R7 locked (R* required here) · R8 accepted · R9 locked (README sync). Locks in `spec.md`.

---

### A. Executive verdict

**Approve process with minor edits**

As a lab vehicle this spec is unusually process-literate: dual intent is explicit, surface Ubiquitous gates stay grant/research/chat-falsifiable, journey/stack prefs are parked in Assumptions/Plan rather than SC checkboxes, and constitution §B–C artifacts exist (`SC-*` + `acceptance.md`). Product review locks F1–F8 give a cold planner real decision surface instead of open product forks.

The remaining process risk is **harness learnability**, not missing Spec Kit shape. Lab-primary dogfood still has no journey-side failable outcomes; pre-spec “coaching locks A1–D / N1–N14” live off the artifact bus; and the catalog is mostly `human`/`hybrid` with FR ids used as classes—fine for product judgment, weak for packet DoD and longer unattended runs. Fix or explicitly accept those before treating process as closed; then Approve → `/speckit-plan`.

---

### B. Findings table

| ID | Severity | Lens | Spec locus | Finding | Suggested resolution (for human) |
|----|----------|------|------------|---------|----------------------------------|
| R1 | Nit (strength) | Dual intent / Learning vs cargo-cult | Lab dual intent (F5); FR-015; Assumptions | **Strength.** Lab dogfood is stated as primary meta-product while surface pass/fail is pinned to F1–F4-style outcomes; stack prefs (v0/Next, LangGraph-when-fit) are explicitly *not* surface Ubiquitous fails. This is the constitution VI / overlay anti-cargo-cult stance done correctly—not folder theater. | Keep; do not “strengthen” by adding LangGraph/v0 as SC. In plan, treat those as Architecture preferences with fit justification. |
| R2 | Debate | Dual intent / Failable outcomes | Success Criteria; FR-015; F5 | Journey is lab-primary, but every failable class is surface-product. A run can pass SC-001–007 and still teach nothing about Spec Kit gates, Architecture-first planning, catalog growth, or packet DoD. Dual intent is narrated; only one side is instrumented. | Either (a) add 1–3 **lab/harness** outcome classes (e.g. plan Architecture+Phasing approved before tasks; catalog checks invoked by named commands; first packet has hard DoD) labeled as lab gates not product Ubiquitous, or (b) explicitly accept that lab learning is measured only by human retrospective / agent-OS notes—not by SC. |
| R3 | Debate | Artifact bus / Independence | Input line; Open questions; Approval | Spec Input cites “Lab coaching locks (A1–D, N1–N14)” that are not artifacts in `specs/smart-writer-v2/` (or linked). Product locks F1–F8 absorb some content, but a cold agent cannot audit what A1–N14 were, whether any remain un-locked, or whether chat still owns process memory. That is human-as-bus residue. | Drop the opaque A1–N14 citation, or add a one-page `notes/` / appendix mapping those ids → F locks / discarded. Anything still binding must live in git. |
| R4 | Debate | Acceptance catalog / Packet readiness | `acceptance.md`; SC-001–007; Constitution §C + V | Catalog exists and is versioned (good). Process concerns: (1) `class` column often cites **FR-*** not stable **SC-***—charter/catalog split blurs; (2) nearly all `how` = human/hybrid—packet DoD for unattended slices will struggle to name failing commands; (3) bootstrap is dense relative to “grow from test runs.” Real gym equipment, soft automation. | Keep product must-checks. For plan/tasks: pick a thin **auto** subset (e.g. revise path distinguishable in API/state; job not sync-only; provenance record present/absent) and map packet DoD to those. Prefer adding SC classes when a check is a stable outcome, else keep FR as `shall` text under an SC class. |
| R5 | Later | Plan gate readiness | Open questions 2–7; Key Entities; Edge (jobs) | Spec is plan-ready on *product* behavior (stories, FRs, edges, entities). Architecture still has large deferred forks (research providers, monorepo share vs clean-room, revise/generate graph, citation control, preview gate). Correctly deferred—but a cold `/speckit-plan` will invent structure unless Open questions are treated as **required Architecture decisions**, not optional research. | No spec rewrite needed. Human: when approving plan, require explicit Architecture subsections for jobs, ArtifactVersion/revise contracts, preview gate, and app boundary (clean-room vs share)—exit criteria per phase referencing SC/catalog ids. |
| R6 | Later | Packet readiness | Dual intent; Out of scope; no packet pointer | Dogfood narrative aims at longer high-quality unattended runs (Agent OS learning), yet the feature never states what a first packet could own (paths, forbidden scope, DoD command list). Overlay §D is optional—but for a journey-primary vehicle, silence invites implement-from-chat once plan exists. | After plan approval, either author one thin `notes/packets/…` wrapper for MVP slice or explicitly defer packets in plan Phased delivery with why. |
| R7 | Nit | Review locks | Review locks table; Approval; Status banner | Product F1–F8 locked with briefs cited—good. Process/R column absent; Status already says “ready for human Approved” while Open Q1 still treats process as optional. For a **recommended** dogfood process pass (constitution §A), that framing understates the gate you just asked for. | After triage: add R* rows (locked / accepted / deferred) to Review locks; clear Open Q1; only then flip Status → Approved. |
| R8 | Nit | Spec Kit shape | User Stories P1–P6; Requirements; Success Criteria | Shape is complete enough to plan: prioritized stories, independent tests, FRs, entities, failable SCs, assumptions, OOS. Not chat-shaped mush. Minor: SC-001 “≈1–3 pages” remains soft falsifiability (human-only in catalog)—acceptable if F1 already accepted softness. | Optional: define a crude auto proxy in plan (token/word band) without making literary quality a must. |
| R9 | Nit | Artifact bus (repo hygiene) | Outside spec: `docs/agent-os/README.md` Legacy note | Agent OS README still says smart-writer-v2 “F2–F7 still open” while this spec claims F1–F8 locked. Cold agents reading the human map get contradictory process state. | Update README legacy line when approving this feature (doc chore, not a product edit). |

Minimum finding count met; Debates: R2, R3, R4; strength: R1.

---

### C. Adversarial positions (required)

1. **Position: this feature is a weak lab vehicle**

   Surface product complexity (research roles, provenance, dual intake, revise continuity, jobs, citation UX) will dominate agent attention. Spec Kit overlays are *documented*, but learning leverage is thin: no harness SCs, human-heavy catalog, no packet DoD sketch, opaque pre-history (A1–N14). You get a hard product gym and a soft process gym—agents will optimize grant drafts, not Architecture-first discipline. Dual-intent prose without journey instrumentation is how labs cargo-cult SDD while shipping another app.

   *What would have to be true for the spec’s process stance to be right anyway:* Lab learning is intentionally measured only by human adjudication of plan/PRs and by *not* polluting product Ubiquitous gates; this feature’s job is to supply real surface falsifiability so process practice has stakes; packet/auto checks are correctly deferred to plan/tasks once Architecture exists.

2. **Position: kill or change one process choice — “process review optional” framing for this dogfood vehicle**

   Constitution §A marks process review optional-but-recommended for dogfood. This spec’s Status/Approval treat R* as skippable while declaring lab dual intent primary and product F locks complete. That invites Approve → plan without a process pass—exactly when the vehicle most needs one. Optional-as-default becomes review theater: the brief exists, the checkbox exists, the gate does not.

   *What would have to be true for the spec’s process stance to be right anyway:* Human already decided product locks absorb process concerns; this session *is* the process pass; optional remains correct for non-dogfood features and should stay optional in the template—even if *this* feature’s Approval checklist requires R* triage before Approved.

---

### D. Independence / harness test

**Mostly yes for specify→plan; gaps for full cold loop.**

| Phase | Cold-agent viable? | Gap |
|-------|--------------------|-----|
| Specify (done) | Yes | Opaque A1–N14 Input (R3) |
| Product review | Yes (done; F locks in-spec) | — |
| Process review | Yes (this artifact) | Must be filed + triaged into Review locks |
| Plan (Architecture + Phasing) | **Conditional** | Open questions list the Architecture decisions but do not constrain building blocks; Key Entities name Run/Job/ArtifactVersion without contracts. Agent can draft plan from override template + spec, but will guess providers/share-boundary/preview unless human adjudicating plan is attentive. |
| Tasks / packet | **Weak today** | Catalog `how` mostly non-auto; no packet sketch; DoD commands not nameable from spec alone |

Constitution + AGENTS.md + override templates are sufficient process truth; the feature does **not** require the human to paste prior chat *if* A1–N14 are retired and R* locks are written back into `spec.md`.

---

### E. Edit list (process-only)

Max 10; section + one-line change. No rewrite.

1. **Input** — Remove or git-link “A1–D, N1–N14”; retain only F-lock provenance.  
2. **Success Criteria / dual intent** — Add optional **lab/harness** failable classes *or* one Assumption: “lab success = human plan/PR adjudication only.”  
3. **Review locks** — Add rows for R1–R* after triage (locked / accepted / deferred).  
4. **Status** — Stop saying “ready for Approved” until R* triage + human Accept.  
5. **Approval** — Check process review when R* resolved; keep plan gate checkbox.  
6. **Open questions** — Close Q1 once process review filed; leave 2–7 as plan Architecture prompts.  
7. **Assumptions** — One line: first MVP packet deferred until plan Architecture approved (or point to future packet id).  
8. **acceptance.md** (catalog) — Prefer SC-* in `class`; move FR-only rows under nearest SC; mark 2–3 checks `auto` candidates for plan.  
9. **Key Entities** — One sentence each on what makes revise vs generate *distinguishable* for SC-006/007 (contract hint, not design).  
10. **docs/agent-os/README.md** (repo map) — Fix stale “F2–F7 still open” when feature approved.

---

### F. Questions for the human (max 5)

1. For this dogfood vehicle, is **lab success** (a) instrumented with harness SCs/packet DoD, or (b) explicitly human-only retrospective—so process can Approve without new SC classes?  
2. Must **R\* triage** be mandatory before Status → Approved on smart-writer-v2, or do you keep process optional even here?  
3. Are **A1–D / N1–N14** fully superseded by F1–F8, or does any coaching lock still bind and need a git appendix?  
4. Should the **first plan MVP phase** exit criteria require at least one **automated** catalog check (jobs/revise/provenance), or is hybrid/human acceptable through first dogfood loop?  
5. Will the first long run use a **`notes/packets/`** wrapper, or is Spec Kit `tasks.md` alone the DoD bus for v2.0 MVP?

---

*End of process review. Human adjudicates; do not treat this document as auto-approval.*
