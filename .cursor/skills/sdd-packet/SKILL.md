---
name: sdd-packet
description: >-
  Create a bounded work packet under notes/packets/ from an approved spec/plan
  for session or background agents. Use when the user asks for a packet, task
  breakdown, background-agent brief, or ready-to-implement unit of work.
---

# SDD Packet

## Instructions

1. Require an approved `specs/<feature>/spec.md` (or explicit “tiny fix — no spec”).
2. Read `plan.md` if present; if missing and work is non-trivial, draft a short `plan.md` first and pause for approval.
3. Copy `notes/packets/_TEMPLATE.md` → `notes/packets/<id>.md`.
4. Fill owned/forbidden paths tightly. Prefer one PR-sized packet over mega-packets.
5. DoD must name concrete tests/commands. Prefer TDD: list failing tests to add first.
6. Set status `ready`. Propose branch name `packet/<id>` and agent mode (session vs background).
7. Do **not** start implementation unless the user explicitly says to continue into `sdd-implement`.

## Packet id convention

`YYYY-MM-DD-<app-or-area>-<short-slug>` (example: `2026-09-10-smart-writer-plateau-stop`).

## Output

- Path to packet
- One-line launch brief suitable to paste into a background agent
