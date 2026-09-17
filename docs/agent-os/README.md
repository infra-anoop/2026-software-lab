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
│  · Progressive HITL (human Debates; lighter downstream)     │
│  · Failable outcomes + extensible acceptance catalog        │
│  · Optional notes/packets for long background runs          │
│  · Cattle / secrets / registry (constitution + AGENTS.md)   │
└─────────────────────────────────────────────────────────────┘
```

## Learn once

| Concept | Where |
|---------|--------|
| Constitution | `.specify/memory/constitution.md` |
| Spec / plan / tasks templates | `.specify/templates/` (+ `overrides/spec.md`, `overrides/plan.md`) |
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
8. Write failing contract/catalog-auto tests → **spawn T*** (`SPAWN_REVIEWER.md`) when those tests exist → `/speckit-implement`
9. Optional: implement `notes/packets/` for a long background slice; **required:** review packets at F*/R*/P*/T*

**Plan ≠ task list.** Architecture is first-class inside plan (constitution §E).  
**Progressive HITL:** human adjudicates Debates at spec + Architecture; later stages may auto-accept Nit/Later under explicit policy (§F).

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
