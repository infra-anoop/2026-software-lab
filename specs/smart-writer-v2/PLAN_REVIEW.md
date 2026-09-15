# Plan Architecture review — smart-writer-v2

**Reviewer role**: Independent architecture / plan reviewer (did not author the plan)  
**Brief**: `docs/agent-os/PLAN_REVIEW_PROMPT.md` (Architecture-heavy incl. Learning/SOTA fit; Phasing-light)  
**Posture**: `docs/agent-os/STACK_POSTURE.md`  
**Primary**: `specs/smart-writer-v2/plan.md`  
**Locks**: Approved `spec.md` (F1–F8, R1–R9) — not re-litigated except where the plan contradicts or drops them  
**Companions**: `research.md`, `data-model.md`, `contracts/http-api.md`, `acceptance.md`, `quickstart.md`  
**Date**: 2026-09-14

**Status**: Human-adjudicated **P1–P8**; plan Architecture + Phasing **Approved** (2026-09-15).

---

### A. Executive verdict

**Do not approve architecture yet**

The product shape is coherent: clean-room `smart-writer-v2`, chat turn → clarify-or-job, `generate`/`revise` distinguished in contracts, grounding treated as a pipeline invariant, preview gate named. That is enough to stop arguing V1 port vs rewrite.

It is not enough to task against. The new building block — a Next.js chat client beside FastAPI/JobRunner — has no process topology, no UI-host lock, and no answer to who holds `X-Audit-Secret`. A cold agent will invent a browser-side header and a Python-container deploy for a Node app. `research.md` copies V1 (JobRunner, Tavily, Railway, in-memory) and names HTML-vs-Next, not the STACK_POSTURE alternatives (v0/Vercel-class UI path, managed jobs, vendor web / reader APIs). The constitution check on the plan already leaves alternatives unchecked. Fix or explicitly accept the topology + SOTA forks before `/speckit-tasks`. Phasing order is fine; it is not the gate.

---

### B. Findings table

| ID | Severity | Lens | Plan locus | Finding | Suggested resolution (for human) |
|----|----------|------|------------|---------|----------------------------------|
| **P1** | **Blocker** | Boundaries | Architecture: UI / API / preview gate; Technical Context “one registry id”; `contracts/http-api.md` | Chat UI is Next.js; mutating API is FastAPI protected by `X-Audit-Secret`. Plan never says whether the browser calls FastAPI (CORS + secret in the client), Next is a BFF that holds the secret, or FastAPI serves a static export. Registry, Nix image, and Railway manifests in this lab are one Python process per app. In-tree `web/` with one registry id is not a deploy architecture. Preview-gate-before-public-URL (spec Assumptions) fails if the spend key is a frontend header. | Lock **one** topology before tasks: (a) Next BFF (server routes hold secret; browser never sees it) + named second runtime/host, or (b) FastAPI serves exported UI same-origin, or (c) two registry/deploy units. Write cattle implications (Railway service vs Vercel adapter A21). Do not leave “folder = architecture.” |
| **P2** | **Debate** | Learning / SOTA fit | `research.md` R2–R5, R7; plan building blocks; constitution check (alternatives unchecked) | Major blocks lack a SOTA/managed alternative. **UI host**: Next in-tree vs V1 HTML — not Vercel/v0 (the posture’s own example). **Chat protocol**: POST + poll, no Vercel AI SDK / SSE / `useChat`. **Jobs**: V1 `JobRunner` only; no Inngest/Trigger.dev/Temporal/LangGraph Platform. **Search**: Tavily-because-V1; V1’s own retrieval design preferred vendor web tools and named Firecrawl/Jina. **LLM**: “OpenAI or lab-default” with no alternative. Authors note the gap and still ship silence. Copying familiar cattle is a fit *option*; it is not exploration. | Keep F5: stack is not a product SC. Require `research.md` rows for UI host, jobs, search/LLM with one rejected or **explicitly deferred** managed/SOTA option each. Human then locks Railway+JobRunner+Tavily *as a learning-scope cut*, or takes a managed UI-host slice. |
| **P3** | **Debate** | Building blocks | Orchestration; `research.md` R2; Primary Dependencies “LangGraph (when fit)” | Orchestrator is not a building block yet. “LangGraph when the graph benefits” + “linear async in P0/P1 if faster” + “PydanticAI (or equivalent)” leaves the generate/revise/research graph to the implementer. Named modes (`clarify`/`generate`/`revise`) are entry labels, not nodes, state, or skip-research-on-revise rules. Observable-graph learning (constitution VI) is optional ceremony, not a lock. | Either: LangGraph `StateGraph` in P1 with named nodes (infer → materials → web → write → provenance; revise may skip or narrow research) and PydanticAI `result_type`s per node; **or** lock linear pipeline for P1 with a one-line migrate trigger (branching = graph). Strike “or equivalent.” |
| **P4** | **Debate** | Data & contracts | `data-model.md` ArtifactVersion/SourceRecord; plan “claims map to source ids”; F3/F4; SC-003/004 | Grounding is the product bet; the model is a bag of sources. `source_ids` on the artifact does not implement “each org/funder-specific claim has checkable provenance.” F4 roles (`user_material` vs `web`) exist as an enum, not as a retrieval façade that prefers materials for criteria and uses web for differentiation (or SC-004 declare). No EvidenceBundle / claim-span / research-plan entity. Hybrid catalog checks will be prompt theater. | Add a small contract: `ClaimProvenance` (claim span or quote → `source_id` \| `uncertain`) and a retrieval module that emits `materials_bundle` vs `web_bundle` with an explicit no-signal declaration. SC-003 auto/hybrid hooks those fields, not “sources array nonempty.” |
| **P5** | **Debate** | Spec lock fidelity | `data-model.md` transitions (good); `contracts/http-api.md` (weak); Phased P1 vs FR-003a/F6 | Data-model says grant + missing intent slots → clarify, no ArtifactVersion. HTTP contract has a clarify *response* but no failable generate-path rule (no 409/type for “slots missing,” unlike revise-without-parent). P1 exit is a rich-prompt golden path that *skips* clarify; P2 owns “intent-slot clarify ordering.” A P1 vertical can pass while FR-003a never runs. `missing_hints` also leaks slot ids toward the UI (FR-021 risk). | Put the gate in the contract: grant job enqueue requires intent slots filled or returns `type=clarify` (never a long artifact). P1 exit: one fixture that *must* clarify. Keep slot names off the default client payload; questions stay NL-only. P2 = A-before-B ordering + chips, not “invent clarify.” |
| **P6** | **Nit (strength)** | Spec lock fidelity / Cold-agent readiness | `contracts/http-api.md` auto-check hooks; FR-011; F5/F8; R6 | **Strength.** Clean-room + JobRunner-pattern-only is the right V1 cut. `mode` / `parent_artifact_id` / `producing_mode` are task-ready for SC-006/007. Preview-gate fail-closed (401/503) matches B5/A11. Dual intent is respected: Next/LangGraph are prefs, not Ubiquitous SCs. MVP DoD bus = `tasks.md` (R6). `research.md` is honest that SOTA alternatives are thin — rare and useful. | Keep; do not “fix” dual intent by adding LangGraph/v0 as product pass/fail. Use this contract quality as the bar for provenance and clarify. |
| **P7** | **Later** | Building blocks | External systems; R5 file upload; property vocab; A25 Logfire; V1 SSRF notes | Unlocked but not plan-approval-blocking: (1) URL fetch has no SSRF/size/PDF policy (V1 already specified this). (2) Uploads are F4-first-class but absent from the HTTP contract; “P1 if cheap else P2” is chat. (3) Seed vocab in `research.md` (`warm`,`specific`) ≠ spec seed (`emotional`,`visionary`). (4) No observability block despite A25 `LOGFIRE_TOKEN` per app×env. (5) Turn/cost caps “mirror B5” with no numbers. | Tasks may pick V1 fetch hygiene, Logfire Settings, and one vocab list. Human: don’t expand P1 to machine critique or durable DB. |
| **P8** | **Nit** | Phased delivery | Phased delivery table P1 vs P2 | Light only. Order P0 scaffold → P1 vertical → P2 harden → P3 persistence/critique matches the architecture. P1 exit criteria are failable (registry, preview gate, mode/parent, SC-003/004 fixture). Weakness: P1 is the whole product minus chips; P2 holds F6 clarify *ordering* that should already be an orchestrator invariant (P5). Not a hidden task dump. | After P5 lock, one P1 bullet: “missing-slot grant turn returns clarify, not a job.” Leave P2 as chips + citation override + non-grant smoke + one `auto` CI row. |

Minimum finding count met. Debates: P2, P3, P4, P5. Strength: P6. Learning/SOTA: P2. Phasing-primary: P8 only.

---

### C. Adversarial positions (required)

1. **Position: kill or narrow one Architecture building block / boundary** — strongest case

   Kill **in-tree Next.js under the Python registry app** as currently drawn. This lab has never shipped Node: registry, `uv`/Nix image, and Railway YAML assume one FastAPI process. The plan adds a second runtime in `web/` and calls that “one registry id.” That is how you get CORS theater, a preview secret in `fetch()` headers, and a cattle story nobody can write. For a ~10-user grant writer, the split does not earn its complexity. Collapse MVP to **one** of: FastAPI + a thin server-rendered chat thread (learn the V2 *product*), or a **first-class** Next host (BFF + managed deploy) with Python as the job worker only. The hybrid teaches neither Next craft nor Python pipeline discipline; it teaches glue.

   *What would have to be true for the plan’s stance to be right anyway:* The human explicitly wants the Next journey *and* locks secret-custody + host + how `web/` is built/served in git manifests before tasks; one-folder layout is then a packaging convenience, not the architecture.

2. **Position: Architecture under-teaches SOTA / over-self-hosts / skips managed alternatives** — strongest case

   STACK_POSTURE’s worked example is “Vercel+v0 vs in-tree Next on Railway only.” `research.md` R3’s alternatives are V1 HTML and a second registry app — the silent-familiar path the posture exists to catch. Same pattern: jobs = A9 `JobRunner` with no managed queue named; search = Tavily adapter reuse while V1 retrieval docs preferred vendor web tools and listed Firecrawl/Jina; chat = poll, not AI SDK streaming; agents = “when fit / or equivalent.” A21 already stubs a Vercel runtime target. Constitution VI asked for visible SOTA then a lock. This plan moved the old machines into a new folder and labeled Next.js the journey.

   *What would have to be true for the plan’s stance to be right anyway:* The lesson for this loop is grant/revise + Spec Kit gates, not UI-host or durable-jobs ops; Railway+JobRunner+Tavily is an explicit **learning-scope cut** written as deferred alternatives (Later/P3), not omitted ones.

---

### D. Independence / tasks readiness

**No — not yet.** A cold `/speckit-tasks` run from this plan + Approved spec + constitution will invent the expensive boundaries.

| Area | Cold-agent viable? | Gap |
|------|--------------------|-----|
| App identity / clean-room | Yes | FR-011 + research R1 |
| Revise vs generate metadata | Yes | Contracts + data-model; R4 auto subset |
| Preview gate *as an API header* | Yes | Path/status codes named |
| Preview gate *in a chat UI* | **No** | P1: BFF vs browser vs static-export |
| UI host / Node in cattle | **No** | No Vercel/Railway/static decision; registry is Python-shaped |
| Orchestrator implementation | **No** | LangGraph vs linear still chat-shaped (`research.md` R2) |
| Grounding / F4 | **Weak** | Enum on sources; no retrieval façade or claim map (P4) |
| Clarify-before-write | **Weak** | In data-model prose; not a contract assertion (P5) |
| Secrets schema / Logfire | **Weak** | Audit secret named; A25 `LOGFIRE_TOKEN` not in plan |
| Phasing → task slices | Mostly | P0/P1/P2 are ordered; P1 is fat |

`research.md` left these forks **chat-shaped**: “LangGraph when fit,” “linear if faster,” “PydanticAI or equivalent,” “upload P1 if cheap else P2,” “expect P\* to pressure Vercel/v0.” Alternatives were not recorded per STACK_POSTURE major block (UI host, jobs, search/LLM). The plan’s own constitution check flags this.

Do not start `/speckit-tasks` until P1 is locked and P2–P5 are human-accepted or rewritten into Architecture/contracts.

---

### E. Edit list (Architecture-first)

Max 10. Prefer Architecture / research / contracts. No rewrite in this session.

1. **Architecture — UI / API boundary** — Lock process topology and secret custody (Next BFF vs FastAPI-served static vs two deploy units); browser must not send `X-Audit-Secret`.
2. **research.md — UI host/deploy** — Add Decision/Rationale/**Alternatives** for Vercel+v0 (or Netlify) vs in-tree Next on Railway; defer explicitly if Railway-only is the cut.
3. **research.md — jobs** — Name one managed/durable alternative (LangGraph Platform checkpointer, Inngest/Trigger, Temporal, or Redis queue) and reject or defer vs `JobRunner`+A9.
4. **research.md — search/LLM** — Name vendor-web-tools and/or Firecrawl/Jina/Exa vs Tavily; lock URL-extract + SSRF policy pointer.
5. **Architecture — orchestrator** — Lock LangGraph nodes for P1 *or* lock linear + migrate trigger; drop “when fit” / “or equivalent.”
6. **data-model.md + contracts** — Add claim→source (or `uncertain`) and materials vs web bundles; SC-003/004 hooks those fields.
7. **contracts/http-api.md** — Grant generate/revise enqueue only after intent slots filled; otherwise `type=clarify`. Fixture in P1 exit. Default-omit `missing_hints` to the UI.
8. **Architecture — observability** — Logfire (A25) as a named block; `LOGFIRE_TOKEN` in secrets schema with the V2 audit secret.
9. **research.md R8 vs spec seed** — One closed vocabulary list; stop drifting labels.
10. **Phased P1 (light)** — One failable clarify-before-write bullet; do not move citation override or chips into P1.

---

### F. Questions for the human (max 5)

Only questions that change **Architecture approval**.

1. **UI host + topology:** For v2.0 MVP, lock (a) FastAPI + in-tree Next on Railway with a **server-side BFF** (and accept Node in the cattle path), (b) **Vercel (v0-class Next) for UI** + Railway FastAPI for jobs (A21 adapter becomes real), or (c) **no Next in P1** (server-rendered/HTMX thread; Next deferred)?
2. **Orchestrator:** Is **LangGraph in P1** a lock (named generate/revise graphs), or is a **linear pipeline** accepted until branching, with migrate criteria written down?
3. **Grounding contract:** Must MVP persist **claim-level** provenance (quote/span → source or uncertain), or is an artifact-level `sources[]` plus human SC-003 judgment an explicit accept?
4. **Clarify gate:** Must P1 **refuse** a grant writing job when Who/Whom/Ask/Why/Evidence are missing (FR-003a in the contract), or is a rich-prompt golden path without that fixture an accepted MVP cut?
5. **Learning-scope cut:** Confirm Railway + in-memory `JobRunner` + Tavily as **deferred managed alternatives** (not silent defaults)? If yes, say so in `research.md`. If no, which managed slice is in architecture: UI host, jobs, or search?

---

*End of plan Architecture review. Human adjudicates **P-***; record locks on `plan.md`. Nits/Later (P6–P8) may be batched. Debates stay human at this gate (constitution §F).*
