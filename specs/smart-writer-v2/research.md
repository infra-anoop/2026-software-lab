# Research — smart-writer-v2

Decisions resolving spec Open questions and Architecture forks (R5).  
Format aligned with [`research-template.md`](../../docs/agent-os/research-template.md) / [`STACK_POSTURE.md`](../../docs/agent-os/STACK_POSTURE.md).  
**P* adjudication in progress** — rows updated as locks land.

---

## Block: Topology & runtime custody

- **Decision (locked 2026-09-20 — D5):** **Design** with **Vercel v0**. **Deploy UI on Railway** (shipped product includes that UI). **Worker** on Railway. Browser never holds preview secret (BFF on Railway UI path). **Not:** Vercel as production UI host; **not:** Codespaces-only as the product.
- **Rationale:** Governor wants modern UI craft (v0) and a real deployed product surface on lab cattle (Railway), without conflating design studio with host.
- **Pattern source:** Railway cattle for Python worker; UI service(s) to be declared in T069.
- **Alternatives rejected:** Vercel-as-host (prior P1); Codespaces-only dogfood as finish bar; browser-held audit secret.

---

## Block: Jobs / orchestration (runtime)

- **Decision:** MVP **in-process `lab_shared.jobs.JobRunner`** (A9-class residual: restart/multi-instance loss documented) executing a **LangGraph `StateGraph` (P3)**.
- **Rationale:** P2 learning-scope cut on *managed* queues; P3 takes the observable-graph lesson on the worker.
- **Pattern source:** `modules/lab_shared` JobRunner; V1 LangGraph usage as pattern only.
- **Alternatives considered:** Inngest, Trigger.dev, Temporal, LangGraph Platform checkpointer — **Deferred** (post-MVP). Linear-only pipeline — **rejected** for P1 (P3 lock A).

### LangGraph P1 nodes (generate)

`infer` → `materials` → `web` → `write` → `provenance`  
Revise: may skip or narrow `materials`/`web`; always produces new `ArtifactVersion` with `parent_artifact_id`.

## Block: Search / retrieval

- **Decision:** MVP **Tavily** when key set; else noop + SC-004 declare path. URL extract for user materials first-class (F4). **P4:** retrieval façade emits **materials_bundle** vs **web_bundle**; artifacts carry **ClaimProvenance** (excerpt → source_id | uncertain).
- **Rationale:** Beachhead grounding bet needs claim-level checks, not sources-bag theater.
- **Pattern source:** V1 EvidenceBundle ideas as pattern only.
- **Alternatives considered:** Firecrawl / Jina / vendor web tools — **Deferred**. Artifact-level `sources[]` only — **rejected** for MVP (P4 lock 1).

## Block: Clarify gate (product fidelity)

- **Decision:** **P5** — Grant missing intent slots ⇒ `type=clarify` only in P1; NL questions; no default slot-id leakage; P1 must-clarify fixture.
- **Rationale:** FR-003a / F6; don’t defer the gate to “harden.”
- **Pattern source:** none.
- **Alternatives considered:** Soft MVP (rich-prompt skip clarify until P2) — **rejected**.

- **Decision:** MVP **POST + poll** job status via BFF.
- **Rationale:** Matches worker JobRunner; simpler than streaming for first vertical.
- **Pattern source:** V1 job poll pattern (via BFF, not browser secret).
- **Alternatives considered:** Vercel AI SDK / `useChat` / SSE streaming — **Deferred** (fits Vercel host; pull in when UX latency is the lesson).

---

## R1. App boundary: clean-room vs share V1 code

**Decision:** New clean-room `apps/smart-writer-v2`. Reuse `lab_shared.jobs` and copy **patterns** (HTTP job enqueue, Settings, Tavily adapter shape, prompt-program layout). Do not depend on `apps/smart-writer` Python packages.

**Rationale:** FR-011; V1 carries rubric/N-assessor complexity and failure modes the V2 bet intentionally simplifies for MVP. Clean-room keeps dogfood learning honest.

**Alternatives:** Monorepo share of V1 agents (faster, inherits complexity); package extract mid-flight (premature).

---

## R2. Orchestration: LangGraph vs linear async

**Decision:** Prefer **LangGraph** for `generate` / `revise` graphs when there are multiple nodes (infer → research → write → provenance). Allow a linear async pipeline in P0/P1 spike if it ships faster — migrate to graph when branching (clarify vs write, revise skip-research) appears. **Not** a product SC.

**Rationale:** Constitution VI + F5 — fit + learnability; V1 already uses LangGraph.

**Alternatives:** Pure functions only (harder to observe); always LangGraph from commit 1 (ceremony risk).

---

## R3. UI: Next.js chat vs FastAPI HTML

**Decision:** **Next.js** chat UI under `apps/smart-writer-v2/web/`. FastAPI serves API only (no form-HTML primary UX like V1).

**Rationale:** Lab journey preference (Assumptions); chat/revise UX (F8) fits SPA/thread model; keeps API contract testable without HTML coupling.

**Alternatives:** V1-style server HTML (faster spike, weaker chat UX); separate registry web app (extra registry/deploy surface for MVP).

---

## R4. Persistence

**Decision:** MVP **in-memory** conversation + JobRunner (document restart/multi-instance loss). P3 optional Supabase if durability needed.

**Rationale:** Matches current lab job residual; unblocks P1 without schema migration tax; ArtifactVersion still first-class in API payloads for SC-006/007.

**Alternatives:** Supabase from day one (correcter ops, slower MVP); client-only state (weaker server revise continuity).

---

## R5. Research providers

**Decision:** **Tavily** when `TAVILY_API_KEY` set; otherwise noop search + SC-004 must **declare** no useful external signal (or skip web path explicitly). URL extract for user links first-class (F4). File upload: P1 if cheap; else P2.

**Rationale:** V1 already has Tavily adapter pattern; optional key avoids hard dependency.

**Alternatives:** Brave/SerpAPI (extra secrets); upload-only MVP (fails differentiation story when web enabled).

---

## R6. Machine critique loop

**Decision (amended 2026-09-20 — Open Decision D8):** **Required for V2 complete.** Each write job runs writer↔assessor with **scores**, rubric from **both** F6 axes (intent substance + property steering), max **8** inner turns. Redesign OK; capability **not thinner** than V1’s scored loop. Human revise (F8) remains the **outer** HITL loop (**D9** = tactical vs fuller rerun — still open).

**Rationale:** Spec always distinguished machine critique from human revise; plan incorrectly deferred critique as “out of MVP.” Governor lock restores nested loops.

**Alternatives rejected:** Skip loop / one-shot write only; thinner-than-V1 stub scores; blind V1 port without dual-axis redesign.

---

## R7. Preview gate & secrets

**Decision:** Mirror V1: `X-Audit-Secret` + `SMART_WRITER_V2_AUDIT_SECRET` in `deploy/secrets/schema.yaml` + Settings. Rate limit + queue caps in-process.

**Rationale:** Architect-backlog B5 pattern; spec Assumptions require preview gate before public spend.

**Alternatives:** Open public demo (rejects Assumptions); OAuth (out of hobbyist scope).

---

## R8. Seed property vocabulary

- **Decision (single list — P7):** `factual` (tone only — F3), `persuasive`, `concise`, `warm`, `formal`, `humorous` (grant default off — F3), `specific`, `urgent`. Ranking inferred from free-form; optional chips. No label drift across docs.
- **Rationale:** Enough for FR-004–006 without full taxonomy (OOS).
- **Alternatives:** Empty list (vacuous) / huge ontology (gold-plate) — rejected.

---

## R9. Clarify vs job

**Decision:** Missing intent slots → **clarify** response (questions only, may be sync). Sufficient state → enqueue **generate** or **revise** job.

**Rationale:** Edge cases in spec; avoids multi-minute jobs just to ask “Who is the funder?”

**Alternatives:** Everything async (poor UX for Q&A).
