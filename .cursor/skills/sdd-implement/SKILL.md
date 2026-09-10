---
name: sdd-implement
description: >-
  Execute a work packet from notes/packets/ with TDD bias, scoped edits, and
  DoD verification. Use when implementing a packet, running a background brief,
  or continuing after sdd-packet.
---

# SDD Implement

## Instructions

1. Read the packet end-to-end. Obey owned/forbidden paths and stop/escalate rules.
2. Read listed context (`AGENTS.md`, spec/plan, backlog IDs).
3. **TDD bias**: add/adjust failing acceptance tests from DoD before production code when practical.
4. Implement the minimum change that satisfies DoD.
5. Run the packet’s verification commands. Fix until green or escalate with evidence.
6. Update packet status (`in_progress` → `done` or `blocked`) and fill **Handoff notes**.
7. Open or prepare a PR summary focused on decisions and DoD proof — not a file laundry list.
8. Do not expand scope. Do not “while I’m here” refactors outside owned paths.

## Background-agent launch brief (template)

```text
Execute packet notes/packets/<id>.md exactly.
Follow AGENTS.md invariants.
Do not edit forbidden paths.
Stop when DoD is green or when an escalate condition hits.
Update the packet handoff notes before finishing.
```

## Done means

DoD checkboxes proven by commands run in this session — not claimed verbally.
