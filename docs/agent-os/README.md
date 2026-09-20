# Agent OS (this lab)

**Process base = [GitHub Spec Kit](https://github.com/github/spec-kit)** (installed).  
Lab taste = thin **overlays** in constitution + template overrides — not a second homemade methodology.

```text
┌─────────────────────────────────────────────────────────────┐
│  Spec Kit (.specify/)                                       │
│  constitution · templates · scripts · /speckit-* skills     │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────┐
│  Lab overlays (stable process — do not re-argue per app)    │
│  · Product review + optional process/lab-vehicle review     │
│  · Plan Architecture review (P*; SOTA/alternatives via STACK_POSTURE) │
│  · Plan authoring gates (fail-closed; topology + non-sibling alts)   │
│  · Plan = Architecture + Phased delivery (arch first-class) │
│  · Test-first for executable apps + independent T* test review      │
│  · Progressive HITL (product locks human; process policy agent) │
│  · Open Decisions (shape vs content; fail closed — §G)          │
│  · Finish-bar lock batch before first implement (§G.2)            │
│  · Architecture delta reconcile after arch-affecting OD locks (§G.1) │
│  · Orchestrator / workers (packet + background default — §H)  │
│  · Failable outcomes + extensible acceptance catalog        │
│  · notes/packets for workers + required review packets        │
│  · Cattle / secrets / registry (constitution + AGENTS.md)   │
└─────────────────────────────────────────────────────────────┘
```

## Learn once

| Concept | Where |
|---------|--------|
| Constitution | `.specify/memory/constitution.md` |
| Spec / plan / tasks templates | `.specify/templates/` (+ `overrides/spec.md`, `overrides/plan.md`, `overrides/tasks-template.md`) |
| Open Decisions (§G) | Spec template section + constitution §G; tasks `[HITL]` / `[OD:D#]` / `[POLICY]` |
| Finish-bar batch (§G.2) | After tasks + analyze: `FINISH_BAR.md` governor locks before first implement |
| Architecture delta (§G.1) | After architecture-affecting OD locks: amend plan/data-model/contracts; `PLAN_DELTA.md`; `/speckit-analyze`; then implement |
| Spawn reviewers | `docs/agent-os/SPAWN_REVIEWER.md` |
| Spawn workers (§H) | `docs/agent-os/SPAWN_WORKER.md` + `notes/packets/_WORKER_PROMPT.md` |
| Slash-style skills | `.cursor/skills/speckit-*` |
| Spec review brief (product) | `docs/agent-os/SPEC_REVIEW_PROMPT.md` |
| Spec review brief (process) | `docs/agent-os/PROCESS_REVIEW_PROMPT.md` |
| Plan review brief (architecture) | `docs/agent-os/PLAN_REVIEW_PROMPT.md` |
| Test review brief (contract/auto) | `docs/agent-os/TEST_REVIEW_PROMPT.md` |
| Spawn reviewers (no human paste) | `docs/agent-os/SPAWN_REVIEWER.md` |
| Lab stack exploration posture | `docs/agent-os/STACK_POSTURE.md` |
| Plan authoring gates (hard) | `docs/agent-os/PLAN_AUTHORING_GATES.md` |
| Research template | `docs/agent-os/research-template.md` |
| Acceptance catalog template | `docs/agent-os/acceptance-catalog-template.md` |
| Portable summary | `AGENTS.md` |

## Default loop

1. `/speckit-specify` → draft spec  
2. **Product** review (required) — **spawn** (`SPAWN_REVIEWER.md`) → lock **F-***; optional **process** review → **R-***  
3. Human marks **Approved** when Blockers cleared (Debates only; do not paste briefs)  
4. `/speckit-plan` → **Architecture + Phased delivery**  
5. **Plan Architecture** review (recommended for non-trivial / first-of-kind) — **spawn** → lock **P-***  
6. Human approves plan Architecture + Phasing  
7. `/speckit-tasks` (test tasks **required** for executable apps)  
8. `/speckit-analyze` + **§G.2** `FINISH_BAR.md` (governor lock batch) → **§G.1** if architecture-affecting locks  
9. Write failing contract/catalog-auto tests → **spawn T*** (`SPAWN_REVIEWER.md`) when those tests exist → implement via **packet + worker** (`SPAWN_WORKER.md`; prefer background)  
10. Optional: long ops packets; **required:** review packets at F*/R*/P*/T*

**Plan ≠ task list.** Architecture is first-class inside plan (constitution §E).  
**Progressive HITL:** human adjudicates product Debates + Open Decisions; process Nit/Later/process-T* may be agent-adjudicated (§F–G).  
**§H:** Main chat orchestrates; workers do real work; `[P]` parallelism is automatic from the task graph.

## Dual channels (governor vs router)

Do **not** use chat as the task router. Two channels stay separate:

| Channel | For | Not for |
|---------|-----|---------|
| **Conversation** | Coaching, trade-offs, locking Debates / product numbers / ops HITL — in **product language** | “What task is next?” / pasting F*/R*/P*/T* briefs / asking the human to learn T0xx IDs |
| **Git packets** (`notes/packets/`) | DoD, owned paths, spawn prompts, stop conditions, routing, finding IDs | Inventing unlocked numbers or vault seeds |

### Human-facing altitude

Agents keep intermediate vocabulary (task IDs, finding IDs, `clarify`/`enqueue`, file paths) **in git**. Chat with the human is **governor altitude**:

- Bad: “Lock T41: all POST messages vs enqueue-only.”
- Good: “Should we rate-limit *every* chat turn (including cheap clarifying questions), or only turns that start an expensive write job? Stakes: abuse vs dogfood friction.”

If the human must open `tasks.md` to understand the question, the agent failed the harness.

**Open Decisions (§G):** deferred product *content* (lists, numbers, enums) with locked *shape* must live in the spec Open Decisions table. Implement fails closed — stop and ask in product language; never invent a seed list to keep the run going.

**Finish-bar lock batch (§G.2):** after `/speckit-tasks` (+ `/speckit-analyze`), before first implement: deposit `FINISH_BAR.md`, inventory open ODs + plan/tasks finish deferrals, human lock or true-waive all rows, set **Implement unblocked: yes**. Then §G.1 if needed. See `FINISH_BAR_TEMPLATE.md`.

**Architecture delta (§G.1):** when an OD lock is **architecture-affecting** (topology, new pipeline, new entities, deploy host), agents MUST amend `plan.md` / data-model / contracts in place, deposit `PLAN_DELTA.md` (see `PLAN_DELTA_TEMPLATE.md`), run `/speckit-analyze`, and **only then** spawn dependent implement packets. Do **not** greenfield re-plan or wipe `plan.md`. Content-only locks skip this gate.

Unlocked product numbers and vault seeds are **run killers** for multi-hour agents. Put them in Open Decisions and/or the packet **Governor locks required** table (or Out of scope) before the run starts.

## Product vs process vs architecture

| Debate freely (per product) | Do not re-litigate (framework) |
|-----------------------------|-------------------------------|
| Beachhead, UX, domain rules | Spec Kit phase order |
| Property lists, research sources | Product + optional process review at spec |
| Concrete architecture + stack fit | Plan Architecture review (P*) + `STACK_POSTURE.md` |
| Stack *choices that fit* | Failable outcomes + acceptance catalog; never stack-as-SC |
| | Cattle/secrets/registry invariants |

## Constitution changelog

| Version | Note |
|---------|------|
| 1.8.0 | §G.2 Finish-bar lock batch before first implement; `FINISH_BAR.md`; analyze CRITICAL for open ODs / finish deferrals |
| 1.7.0 | §G.1 Architecture delta reconcile after architecture-affecting Open Decision locks; `PLAN_DELTA.md`; analyze before dependent implement |
| 1.6.1 | §G: `waived` = out of product version; “not right now but still required” stays `open` |
| 1.6.0 | §H orchestrator/workers: packet + background worker default; auto `[P]` parallel; tiny-glue exception; `SPAWN_WORKER.md` |
| 1.5.1 | §G: `waived` = deferred this cycle; must re-ask in product language before later implement |
| 1.5.0 | §G Open Decisions (shape vs content, fail closed); §F product vs process pauses; tasks `[HITL]`/`[OD]`/`[POLICY]`; T* Debate tags |
| 1.4.3 | §F human-facing language: chat = product/ops choices; IDs stay in git; combing tasks.md for jargon is a harness defect |
| 1.4.2 | Implement continues after T* lock; no “what next”; stop at tasks.md MVP checkpoint; extra workers only for [P]/long packet |
| 1.4.1 | Spawn reviewers from git packets (`SPAWN_REVIEWER.md`); do not paste briefs to the human |
| 1.4.0 | §V test-first required for executable apps; T* test review overlay |
| 1.3.2 | PLAN_AUTHORING_GATES; topology section; research template; fail-closed plan authoring |
| 1.3.1 | VI + STACK_POSTURE; P* Learning/SOTA fit lens |
| 1.3.0 | §E plan Architecture review (P*); §F progressive HITL |
| 1.2.0 | Dual reviews; plan = Architecture + Phasing |

## Legacy notes

- Homemade `specs/_TEMPLATE.md` / `sdd-*` skills are **deprecated**; prefer Spec Kit + overlays.
- `specs/smart-writer-v2/` **Approved** spec + plan (P1–P8). Next `/speckit-tasks` (required tests) → T* when contract tests exist → implement.

## Upgrade Spec Kit CLI

```bash
uv tool install specify-cli   # or: uv tool upgrade specify-cli
specify version
```
