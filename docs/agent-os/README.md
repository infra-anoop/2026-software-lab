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
│  · Independent spec review brief                            │
│  · Failable outcomes + extensible acceptance catalog        │
│  · Optional notes/packets for long background runs          │
│  · Cattle / secrets / registry (constitution + AGENTS.md)   │
└─────────────────────────────────────────────────────────────┘
```

## Learn once

| Concept | Where |
|---------|--------|
| Constitution | `.specify/memory/constitution.md` |
| Spec / plan / tasks templates | `.specify/templates/` (+ `overrides/spec.md`) |
| Slash-style skills | `.cursor/skills/speckit-*` |
| Spec review brief | `docs/agent-os/SPEC_REVIEW_PROMPT.md` |
| Acceptance catalog template | `docs/agent-os/acceptance-catalog-template.md` |
| Portable summary | `AGENTS.md` |

## Default loop

1. `/speckit-specify` (or equivalent) → draft spec  
2. Independent review (fresh session + review brief) → lock findings in spec  
3. Human marks **Approved** when Blockers cleared  
4. `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`  
5. Optional: wrap a task slice in `notes/packets/` for a long background run  

## Product vs process

| Debate freely (per product) | Do not re-litigate (framework) |
|-----------------------------|-------------------------------|
| Beachhead, UX, domain rules | Spec Kit phase order |
| Property lists, research sources | Independent review before approve |
| Stack *choices that fit* | Failable outcomes + acceptance catalog |
| | Cattle/secrets/registry invariants |

## Legacy notes

- Homemade `specs/_TEMPLATE.md` / `sdd-*` skills are **deprecated**; prefer Spec Kit + overlays.
- In-flight specs (e.g. `specs/smart-writer-v2/`) may still use older shape until migrated after framework settle.
- Product locks on Smart Writer V2 are **paused** until you resume product debate on the Spec Kit base.

## Upgrade Spec Kit CLI

```bash
uv tool install specify-cli   # or: uv tool upgrade specify-cli
specify version
```
