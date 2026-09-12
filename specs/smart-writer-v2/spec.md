# Smart Writer V2 — Product charter

## Meta

| Field | Value |
|-------|-------|
| Feature slug | `smart-writer-v2` |
| Status | **draft** — **product locks paused** (framework: Spec Kit install + lab overlays); resume F2+ later |
| Owner (human) | Lab owner |
| App id | `smart-writer-v2` (new registry app; not an in-place rewrite of `smart-writer`) |
| Related | Legacy app `apps/smart-writer` remains runnable; no back-port of V2 → V1 required |
| Discussion basis | Session coaching locks (A1–D, N1–N14); independent review triage in progress |
| Review locks | See [Review locks](#review-locks) (F1 locked; F2–F7 paused) |
| Process base | Spec Kit + `.specify/memory/constitution.md` (do not re-argue process here) |

## Intent

Smart Writer V2 helps one person produce a **1–3 page**, goal-driven document for **nonprofit grant / donation asks** (beachhead), with a **general short-form** engine underneath. The product constructs and refines intent (adaptive gap-filling, not a fixed questionnaire), runs research over **user materials and the web**, and steers prose via a **product-owned closed vocabulary** of ranked properties woven into a prompt program—while still **inferring** an initial ranking from the user’s free-text prompt.

**Aspirational quality** (not the hard pass/fail bar): drafts that feel more researched, goal-tuned, and emotionally effective than a sloppy ChatGPT session, including occasional “how did it know that?” moments. **Governable success** is defined by the failable outcome classes and the extensible acceptance catalog below—not by literary taste alone.

Secondary intent (lab): use V2 to practice Spec-Driven agentic development and **AI-assisted rich UI** (v0 / Next-style), with learning valued over the cheapest implementation path. LangGraph-style orchestration is acceptable when it fits the multi-step pipeline and remains a mainstream pattern.

## User stories

- As a nonprofit writer, I want a short grant/donation ask grounded in what *this* funder actually cares about, so the draft feels specific and credible—not generic charity prose.
- As a general short-form writer, I want the same engine for other 1–3 page goals, so I am not locked into a grants-only tool.
- As a user who prompts poorly, I want optional Q&A that only asks what my first prompt left unclear, so I think harder without a canned interview.
- As a user, I want to rank a prethought property list (emotional, humorous, persuasive, factual, …), so steering is crisp without inventing labels mid-flow.
- As a reader of the draft, I want moments of “how did it know that?”, so the piece reflects non-obvious but findable research—not a restatement of the org’s own PDF.
- As the lab owner, I want a colorful, agent-built UI and a durable backend job pipeline, so I can learn modern UI + multi-step agent patterns on a real product.

## Acceptance criteria (EARS-style)

### Product outcomes (failable classes — F1)

Hard gates are **structural / evidence** checks, not “is this beautiful writing.” Emotional impact and “surprise” remain valuable but **aspirational**.

- **Ubiquitous**: The system shall produce drafts targeted at approximately **1–3 pages** unless the user overrides length-related properties.
- **Ubiquitous**: The system shall support a **grant / donation-ask** beachhead without hard-limiting the engine to that vertical alone.
- **Ubiquitous — audience-fit**: WHEN the run has a named funder/recipient and available criteria (upload, link, or retrieved public material), the draft shall include **at least two concrete fit points** tied to those criteria, and shall not rely only on generic nonprofit prose with no named criteria.
- **Ubiquitous — provenance**: WHEN the draft asserts an org- or funder-specific fact beyond the user’s raw prompt, the system shall attach **checkable provenance** (user material and/or a retrieved source), or omit / mark the claim as uncertain.
- **Ubiquitous — research-used-or-declared**: WHEN web research is enabled, the draft shall use **at least one non-upload finding** that affects ask, framing, or evidence selection, **or** explicitly state that no useful external signal was found.
- **Aspirational**: “How did it know that?” specificity and strong emotional/rhetorical effect may guide critique and human review; they are **not** sufficient alone to pass or fail a run.

### Acceptance catalog (separate & extensible — F1)

- **Ubiquitous**: Detailed failable checks shall live in a **versioned acceptance catalog** outside application prompt/orchestrator code (e.g. `specs/smart-writer-v2/acceptance.md` or `apps/smart-writer-v2/evals/…`), so the bar can grow from test runs without rewriting the product story.
- **Ubiquitous**: The charter keeps **stable outcome classes**; the catalog holds **extensible check instances** (id, severity must/should/aspirational, preconditions, shall-statement, how checked: auto | human | hybrid).
- Catalog bootstrap and first concrete check ids belong in **plan / packets**; charter approval does not require a full catalog yet.

### Intake

- **Ubiquitous**: The system shall treat Q&A as a **continuum 0…N**, where N is determined by gaps in the user’s first prompt (0 questions is valid).
- **Unwanted**: IF the first prompt is already sufficient, the system shall not force a precanned questionnaire.
- **Event-driven**: WHEN intake runs, the system shall ask questions designed to **fill missing intent**, not a fixed script.

### Steering (properties)

- **Ubiquitous**: The system shall expose a **product-owned closed vocabulary** of properties (seed list below; expanded at implementation / later releases—not blocked on finalizing a large list in this charter).
- **Ubiquitous**: The system shall allow the user to **select and prioritize** properties from that vocabulary (forcing closed choices rather than free-text property invention).
- **Ubiquitous**: The system shall **infer a draft ranking** from the free-text prompt (V1-style decode) and present it for user correction against the closed list.
- **Ubiquitous**: Style/effect and shape/output concerns shall live in **one property list** (not separate dimensional taxonomies that invite endless axes).
- **Event-driven**: WHEN properties are ranked, the system shall weave them into the **prompt program** for writer/critique (not merely append the word “grounding” as a slogan).

**Seed vocabulary (non-final; expand at implementation):**  
`emotional` · `humorous` · `persuasive` · `factual` · `concise` · `formal` · `urgent` · `visionary`

### Research

- **Ubiquitous**: The system shall accept **user-provided materials** (e.g. links/uploads) **and** perform **web research**.
- **Ubiquitous**: Research success is **audience-fit and citable specificity** (see product outcome classes)—not novelty trivia for its own sake, and not PDF-only paraphrase claiming to be research.
- **Event-driven**: WHEN research completes, findings used in the draft shall be **specific and checkable** via the provenance rules above.
- **Example spirit (non-normative / aspirational):** connect org evidence (“90% effort in Santa Clara County; housed 10 people last year”) to funder criteria; or surface a quiet but findable macro fact. Delightful surprise is welcome; **credible funder-fit without surprise still passes**.

### Citations / sources presentation

- **Event-driven**: WHEN collecting intake, the system shall ask a **specific question** about how sources should appear in the output (e.g. inline citations, footnotes, sources panel, or combination)—citation UX is **user input**, not a single hardcoded product default for all runs.

### Application shape

- **Ubiquitous**: The product shall be a **new app** `smart-writer-v2` in the monorepo registry.
- **Ubiquitous**: Legacy `smart-writer` (V1) shall remain available; V2 shall not depend on back-porting features into V1.
- **Ubiquitous**: Long-running research/write work shall run as **backend jobs** suitable for multi-minute pipelines (not assumed to fit a single short-lived serverless request).
- **Optional**: WHERE UI is built, the lab may use **v0 / AI-assisted Next-style UI** for learning; deployment target is **not** required to be Vercel solely because of that choice.

### Learning / stack posture

- **Ubiquitous**: Implementation choices shall prefer **clear, learnable SOTA patterns** (including LangGraph when the graph fits) over minimizing ceremony for its own sake.
- **Unwanted**: IF a pattern is a clear misfit for the pipeline, it shall not be used merely because it is trendy or merely because it is familiar.

## Out of scope (v2.0 charter)

- Enterprise features: payments, heavy authentication, realtime collaboration, elaborate audit/compliance history products.
- Making V1 feature-parity with V2 or migrating all users off V1.
- Finalizing the full property vocabulary in this document (seed only; enlarge at implementation).
- Multi-vertical packaging (legal, academic, humor-only products) as separate apps—general engine is enough.
- Guaranteeing access to truly secret / non-public information (research is web-findable + user-provided).

## Non-goals / constraints

- Scale target: hobbyist **~10** users; stretch aspiration **~100**—design for clarity and learning, not enterprise multi-tenant ops.
- Cattle-first lab invariants still apply (Nix/uv, secrets schema, registry, no UI-only deploy drift)—see `AGENTS.md`.
- Cost/latency: important, but **not** the primary optimization objective versus learning and product quality on this journey.
- Security: no public unbounded spend on the lab owner’s model keys without a basic preview gate (pattern already used on lab apps)—exact gate is a plan item.

## Open questions

**Not** fully resolved for approval yet — independent review triage is in progress (see Review locks). Plan/implementation items:

1. **Property vocabulary expansion** — larger closed list at implementation; charter seed is enough.
2. **Exact intake question for citation mode** — copy/options belong in plan/UI spec (may change when F7 locks).
3. **Research providers / allowlists** — tool choice belongs in `plan.md`.
4. **Monorepo sharing** — reuse vs clean-room inside `smart-writer-v2` belongs in `plan.md`.
5. **Acceptance catalog bootstrap** — create catalog file, seed first check ids under the F1 classes, plus golden prompts (grant + one non-grant); belongs in plan/packets.

---

## Review locks

Decisions from independent review triage. Edit this table as each finding locks; then fold substance into Acceptance / Intent above.

| ID | Status | Lock |
|----|--------|------|
| **F1** | **locked** | Failable outcome classes (audience-fit, provenance, research-used-or-declared) in charter; surprise/emotion aspirational; detailed checks in a **separate extensible acceptance catalog**, not buried in code/prompts. *(Also promoted to lab constitution §B–C — process, not SW-only.)* |
| F2 | **paused** | Beachhead vs general primacy — resume after framework settle |
| F3 | **paused** | Grounding vs property list |
| F4 | **paused** | Web vs uploads for funder fit |
| F5 | **paused** | Learning/stack out of product Ubiquitous |
| F6 | **paused** | Minimal grant intent slots |
| F7 | **paused** | Citations default + override |

---

## Approval

- [ ] Human marks status **approved** (edit this file) when remaining review locks are done and the charter matches intent.
- [ ] After approval: draft `plan.md`, then first executable packet—not before.
