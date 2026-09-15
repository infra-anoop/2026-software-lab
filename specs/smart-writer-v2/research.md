# Research — smart-writer-v2

Decisions resolving spec Open questions and Architecture forks (R5).  
Format: Decision / Rationale / Alternatives.

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

**Decision:** **Out of MVP.** Human revise (F8) is the iteration path. Optional writer↔assessor phase = P3+.

**Rationale:** Spec distinguishes machine critique from human revise; V1 loop is costly and not required for SC-001–007 beachhead.

**Alternatives:** Port V1 assessors early (high cost, dilutes F8 learning).

---

## R7. Preview gate & secrets

**Decision:** Mirror V1: `X-Audit-Secret` + `SMART_WRITER_V2_AUDIT_SECRET` in `deploy/secrets/schema.yaml` + Settings. Rate limit + queue caps in-process.

**Rationale:** Architect-backlog B5 pattern; spec Assumptions require preview gate before public spend.

**Alternatives:** Open public demo (rejects Assumptions); OAuth (out of hobbyist scope).

---

## R8. Seed property vocabulary

**Decision:** Closed seed (implementation may extend):  
`factual` (tone/emphasis only — F3), `persuasive`, `concise`, `warm`, `formal`, `humorous` (grant default de-emphasized/off — F3), `specific`, `urgent`.  
Ranking inferred from free-form; optional chips.

**Rationale:** Enough to exercise FR-004–006 without finalizing full taxonomy (OOS).

**Alternatives:** Empty list until runtime (steering vacuous); huge ontology (gold-plate).

---

## R9. Clarify vs job

**Decision:** Missing intent slots → **clarify** response (questions only, may be sync). Sufficient state → enqueue **generate** or **revise** job.

**Rationale:** Edge cases in spec; avoids multi-minute jobs just to ask “Who is the funder?”

**Alternatives:** Everything async (poor UX for Q&A).
