# Plan authoring gates (lab)

**Why this exists:** Independent P* review caught a plan that honored “clean-room app id” while silently copying sibling-app **topology** (FastAPI + in-process JobRunner + shared-secret header + Tavily). Soft reminders were not enough. For longer unattended runs, **authoring must fail closed** on these gaps — review is the backstop, not the first filter.

## What was sub-optimal in the kit

| Gap | Effect |
|-----|--------|
| Clean-room meant only “don’t import V1 packages” | Agents treated V1 **runtime** as free Architecture |
| `STACK_POSTURE` was advisory; `research.md` Alternatives optional in practice | Authors shipped familiar cattle with thin alts (HTML vs Next) |
| Plan template had no **Topology & secret custody** section | Dual Next+FastAPI with no BFF/host lock looked “done” |
| `/speckit-plan` Completion Report only *reminded* about alternatives | Soft checklist; agent marked plan complete anyway |
| No ban on “sibling pattern = sole alternative” | Reuse without SOTA/managed contrast passed the smell test |

## Hard rules (authoring agents — ERROR if violated)

Before reporting `/speckit-plan` complete:

1. **Read** `docs/agent-os/STACK_POSTURE.md` and this file.
2. **`research.md` required rows** for every major block actually used: UI, **UI host/deploy**, API, jobs/orchestration, data store, search/LLM, secrets/preview gate. Each row: Decision / Rationale / Alternatives (≥1 SOTA, managed, and/or OSS — or explicit **Deferred to Pn** with why).
3. **Sibling-app pattern borrow ≠ Architecture exploration.** If Decision cites `apps/<sibling>` or `lab_shared` cattle (JobRunner, audit secret header, Tavily adapter, etc.), Alternatives **MUST** still name a non-sibling managed/SOTA option. “Same as V1” alone is an ERROR.
4. **Clean-room code ≠ clean-room topology.** FR-style “new app id” does not satisfy STACK_POSTURE.
5. **Topology & runtime custody** section in `plan.md` Architecture is mandatory whenever there is a browser UI + protected API: who holds preview secrets, how many runtimes/hosts, how UI talks to API (BFF / same-origin / separate registry units). Folder layout is not topology.
6. **Orchestrator lock:** name the P1 mechanism (e.g. LangGraph nodes list **or** linear pipeline + migrate trigger). Ban sole phrasing “when fit” / “or equivalent” without a lock.
7. If any of 2–6 fail: **do not** claim plan draft complete; either fix artifacts or escalate to the human with the missing locks listed. Do not leave “expect P* to pressure this” as a substitute for authoring.

## Review still required

These gates reduce slop; they do not replace independent **P*** review for first-of-kind plans. Review catches judgment; gates catch missing structure.
