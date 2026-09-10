---
name: sdd-specify
description: >-
  Turn a PRD or product idea into a Spec-Driven Development spec under specs/.
  Use when the user describes a feature, writes a PRD, asks to specify, or starts
  non-trivial work without an existing spec.
---

# SDD Specify

## Instructions

1. Read `AGENTS.md` and any linked decisions in `notes/architect-backlog.md`.
2. If `specs/<feature>/` exists, update it; else copy `specs/_TEMPLATE.md` → `specs/<feature-slug>/spec.md`.
3. Interview only for **open questions** that block a useful spec. Prefer proposing draft criteria over endless Q&A.
4. Write acceptance criteria in EARS-style (WHEN/WHILE/IF/shall). Keep out-of-scope explicit.
5. Set status to `draft`. Ask the human to mark `approved` before Plan/Packets.
6. Do **not** implement code in this skill.

## Output

- Path to `spec.md`
- Bullet list of open questions (if any)
- Suggested feature slug / next step: Plan (`plan.md`) or Packet
