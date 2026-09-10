# Work packet template

Copy to `notes/packets/<id>.md` (id example: `2026-09-10-sw-rubric-persist`).
One packet → one agent run → one branch → one PR when possible.

## Meta

| Field | Value |
|-------|-------|
| Packet id | |
| Status | ready \| in_progress \| blocked \| done |
| Feature / spec | `specs/<feature>/` |
| Branch | `packet/<id>` |
| Agent mode | session \| background |

## Goal

One sentence.

## Context to read first

- `AGENTS.md`
- Spec / plan paths:
- Locked decisions (IDs):

## Owned paths (may edit)

- `apps/<id>/...`

## Forbidden paths (do not edit)

- `deploy/secrets/` unless listed
- Other apps unless listed

## Definition of Done

Checklist the agent must prove before stopping:

- [ ] Acceptance tests added/updated: `…`
- [ ] Commands green: `cd apps/<id> && uv run pytest …`
- [ ] No invariant violations (secrets, registry, locks)
- [ ] PR opened / ready with summary of decisions (or changes listed if no remote)

## Out of scope

- …

## Stop / escalate if

- Missing product/ops decision
- DoD cannot be met without expanding owned paths
- Conflict with `notes/architect-backlog.md`

## Handoff notes (agent fills at end)

- What changed:
- Tests run:
- Open questions for human:
