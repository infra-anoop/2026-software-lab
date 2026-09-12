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
│  · Plan = Architecture + Phased delivery (arch first-class) │
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
| Spec / plan / tasks templates | `.specify/templates/` (+ `overrides/spec.md`, `overrides/plan.md`) |
| Slash-style skills | `.cursor/skills/speckit-*` |
| Spec review brief | `docs/agent-os/SPEC_REVIEW_PROMPT.md` |
| Acceptance catalog template | `docs/agent-os/acceptance-catalog-template.md` |
| Portable summary | `AGENTS.md` |

## Default loop

1. `/speckit-specify` → draft spec  
2. Independent review → lock findings in spec  
3. Human marks **Approved** when Blockers cleared  
4. `/speckit-plan` → **Architecture + Phased delivery** (both required; human approves)  
5. `/speckit-tasks` → `/speckit-implement`  
6. Optional: `notes/packets/` for a long background slice  

**Plan ≠ task list.** Architecture is first-class inside plan (constitution §E).

## Product vs process

| Debate freely (per product) | Do not re-litigate (framework) |
|-----------------------------|-------------------------------|
| Beachhead, UX, domain rules | Spec Kit phase order |
| Property lists, research sources | Independent review before approve |
| Concrete architecture choices | Plan must include Architecture + Phasing |
| Stack *choices that fit* | Failable outcomes + acceptance catalog |
| | Cattle/secrets/registry invariants |

## Legacy notes

- Homemade `specs/_TEMPLATE.md` / `sdd-*` skills are **deprecated**; prefer Spec Kit + overlays.
- `specs/smart-writer-v2/` is aligned to Spec Kit spec shape + `acceptance.md`; product locks **F2–F7** still open.

## Upgrade Spec Kit CLI

```bash
uv tool install specify-cli   # or: uv tool upgrade specify-cli
specify version
```
