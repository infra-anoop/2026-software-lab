# Agent OS (this lab)

Thin, product-agnostic harness aligned with industry **Spec-Driven Development (SDD)** and the open **[AGENTS.md](https://agents.md/)** standard.

This is not a proprietary invent. Same shape as GitHub Spec Kit / common 2026 practice:

**Specify → Plan → Tasks → Implement**, with humans gating phase boundaries.

```text
┌─────────────────────────────────────────────────────────────┐
│  Portable core (any coding agent)                           │
│  AGENTS.md · specs/ · notes/packets/ · architect-backlog    │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────┐
│  Cursor adapters (optional, richer loading)                 │
│  .cursor/rules/*.mdc · .cursor/skills/sdd-*                 │
└─────────────────────────────────────────────────────────────┘
```

## Mental model (learn once)

| Concept | What it is | Where |
|---------|------------|--------|
| **Constitution** | Durable rules every agent must respect | `AGENTS.md` + `notes/architect-backlog.md` |
| **Spec** | What/why for a feature (source of truth) | `specs/<feature>/spec.md` |
| **Plan** | How (tech approach) | `specs/<feature>/plan.md` |
| **Packet** | Bounded executable unit for one agent run | `notes/packets/<id>.md` |
| **PR** | Delivery + review surface | git branch |

The **shared memory bus** is git. Agents read/write these files; you stop copy/pasting chat between sessions.

## When to use which phase

| Situation | Do this |
|-----------|---------|
| New capability / non-trivial change | Spec → Plan → Packet(s) → Implement |
| Tiny fix (typo, one-liner) | Skip to Implement; still run tests |
| Decision / won’t-do | Lock in `notes/architect-backlog.md` first |
| Long unattended run (30–180 min) | Packet with hard DoD + background agent |

## Cursor skills (invoke by name)

| Skill | Use when |
|-------|----------|
| `sdd-specify` | Turn a PRD / idea into `specs/.../spec.md` |
| `sdd-packet` | Turn an approved plan into a work packet |
| `sdd-implement` | Execute a packet (session or background brief) |

## What stays product-specific

Only thin overlays:

- Lab invariants (Nix, uv, secrets schema, registry) in `AGENTS.md` / `.cursor/rules/lab-invariants.mdc`
- Locked decisions in `notes/architect-backlog.md`

Workflow shape does **not** change when you add a new app.

## Optional later upgrades

- Full [GitHub Spec Kit](https://github.com/github/spec-kit) CLI if you want slash-command automation (`/specify`, `/plan`, `/tasks`, `/implement`)
- Nested `apps/<id>/AGENTS.md` when an app outgrows root guidance
- Hooks that auto-run scoped pytest on agent stop

Start lean; add tooling when friction is real.
