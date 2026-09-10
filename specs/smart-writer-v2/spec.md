# Smart Writer V2 — Product charter

## Meta

| Field | Value |
|-------|-------|
| Feature slug | `smart-writer-v2` |
| Status | **draft** (awaiting human approval) |
| Owner (human) | Lab owner |
| App id | `smart-writer-v2` (new registry app; not an in-place rewrite of `smart-writer`) |
| Related | Legacy app `apps/smart-writer` remains runnable; no back-port of V2 → V1 required |
| Discussion basis | Session coaching locks (A1–D, N1–N14) |

## Intent

Smart Writer V2 helps one person produce a **1–3 page**, goal-driven document that is **more researched, more goal-tuned, and more emotionally effective** than a sloppy ChatGPT session. The beachhead use case is **nonprofit grant / donation asks**; the engine is a **general short-form writer**. The product constructs and refines intent (adaptive gap-filling, not a fixed questionnaire), runs **differentiating web research** (plus user uploads/links), and steers prose via a **product-owned closed vocabulary** of ranked properties woven into a prompt program—while still **inferring** an initial ranking from the user’s free-text prompt.

Secondary intent (lab): use V2 to practice Spec-Driven agentic development and **AI-assisted rich UI** (v0 / Next-style), with learning valued over the cheapest implementation path. LangGraph-style orchestration is acceptable when it fits the multi-step pipeline and remains a mainstream pattern.

## User stories

- As a nonprofit writer, I want a short grant/donation ask grounded in what *this* funder actually cares about, so the draft feels specific and credible—not generic charity prose.
- As a general short-form writer, I want the same engine for other 1–3 page goals, so I am not locked into a grants-only tool.
- As a user who prompts poorly, I want optional Q&A that only asks what my first prompt left unclear, so I think harder without a canned interview.
- As a user, I want to rank a prethought property list (emotional, humorous, persuasive, factual, …), so steering is crisp without inventing labels mid-flow.
- As a reader of the draft, I want moments of “how did it know that?”, so the piece reflects non-obvious but findable research—not a restatement of the org’s own PDF.
- As the lab owner, I want a colorful, agent-built UI and a durable backend job pipeline, so I can learn modern UI + multi-step agent patterns on a real product.

## Acceptance criteria (EARS-style)

### Product outcomes

- **Ubiquitous**: The system shall produce drafts targeted at approximately **1–3 pages** unless the user overrides length-related properties.
- **Ubiquitous**: The system shall support a **grant / donation-ask** beachhead without hard-limiting the engine to that vertical alone.
- **Ubiquitous**: The system shall combine **grounding** (research-backed specificity) with **emotional / rhetorical effectiveness** (not facts-only and not vibes-only).

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
- **Ubiquitous**: Web research shall be treated as the primary lever for **differentiated insight** (e.g. funder criteria, past leanings, value alignment; under-covered but citable facts)—not only summarization of the user’s PDF.
- **Event-driven**: WHEN research completes, the draft shall be able to use findings in a way that a careful reader can recognize as **specific and checkable**, including quiet/non-frontpage facts when relevant.
- **Example spirit (non-normative):** connect org evidence (“90% effort in Santa Clara County; housed 10 people last year”) to funder criteria found via research; or surface a specific macro fact that is findable but not cliché for the topic.

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

Resolved enough for **charter approval**. Remaining items are **plan / implementation**, not blockers to approve intent:

1. **Property vocabulary expansion** — produce a larger closed list at implementation (owner may use a separate session or external LLM); charter seed is enough.
2. **Exact intake question for citation mode** — copy/options belong in plan/UI spec.
3. **Research providers / allowlists** — tool choice (search API, browsing, etc.) belongs in `plan.md`.
4. **Monorepo sharing** — how much to reuse from V1 (`lab_shared`, retry helpers, job runner patterns) vs clean-room inside `smart-writer-v2` belongs in `plan.md`.
5. **Eval suite** — golden prompts (grant + one non-grant) and “surprise/specificity” rubrics belong in plan/packets.

---

## Approval

- [ ] Human marks status **approved** (edit this file) when the charter matches intent.
- [ ] After approval: draft `plan.md`, then first executable packet—not before.
