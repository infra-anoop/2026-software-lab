# Lab stack exploration posture

Durable **Architecture preferences** for this lab — not product Ubiquitous gates (constitution VI / F5).  
Used by `/speckit-plan` authors (`research.md`) and plan Architecture reviewers (`PLAN_REVIEW_PROMPT.md`, **P-***).  
**Hard authoring enforcement:** `docs/agent-os/PLAN_AUTHORING_GATES.md` (ERROR if violated before plan draft complete).

## Intent

Keep the harness **learning-centric**: when choosing building blocks, make **SOTA / managed / OSS alternatives visible**, then lock a fit. Silent “default to what V1 / sibling app did” is a **kit defect**, not an acceptable shortcut.

## Preferences (explore and justify; do not checkbox as SC)

When fit is comparable, prefer:

1. **Managed over self-host** — e.g. Vercel/Netlify for UI, hosted DB/auth, SaaS search — when the lesson is product/agentic process, not operating your own fleet.
2. **Open source / open protocols** when quality and ops cost are comparable to closed freeware-only traps.
3. **Mainstream SOTA UI velocity** — e.g. **v0-class generation → Next.js**, deployable on **Vercel** — when the journey goal includes modern web craft.
4. **Schema-first agents + observable graphs** (PydanticAI, LangGraph with named nodes when used) over ad-hoc prompt spaghetti or “when fit” slogans.
5. **Cattle manifests in git** even when using managed hosts (no UI-only drift).

**Unwanted:** trendy stack with no fit; familiar self-host solely to avoid learning a managed path; stack prefs smuggled into surface product pass/fail; **treating monorepo sibling patterns as explored Architecture**.

## Authoring rule (`research.md`)

For each major Architecture building block (**UI**, **UI host/deploy**, **API**, **jobs/orchestration**, **data store**, **search/LLM**, **secrets / preview gate**), record:

| Field | Requirement |
|-------|-------------|
| Decision | What is locked for this plan |
| Rationale | Fit + learnability |
| Pattern source (if any) | e.g. `lab_shared.jobs`, `apps/smart-writer` HTTP gate — optional |
| Alternatives considered | ≥1 **non-sibling** SOTA / managed / OSS option **or** explicit Deferred to Pn |

**Anti-default:** “Reuse V1 JobRunner / Tavily / audit-header” is allowed as Decision only if Alternatives still lists a managed/SOTA contrast (e.g. Inngest, Vercel+v0, Firecrawl). Sibling-only alternatives (HTML form vs Next) do **not** satisfy this rule for UI host or jobs.

## Topology (when UI + API both exist)

Preferences alone are not enough — lock in `plan.md` **Topology & runtime custody**:

- How many runtimes/hosts (one process vs BFF + worker vs two registry apps)
- Who holds preview/spend secrets (never browser `fetch` headers for spend keys)
- How the UI calls the API

See PLAN_AUTHORING_GATES.md rule 5.

## Reviewer rule (P*)

Flag **missing alternatives** or **topology silence** as Blocker/Debate (topology/secret custody often Blocker).  
Adversarial pressure: “Architecture under-teaches SOTA / over-self-hosts / copies sibling topology.”  
Human locks the choice; do not invent a Ubiquitous “must use Vercel” SC.
