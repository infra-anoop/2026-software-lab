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
| Agent mode | **background** (default) \| session |
| Spawn | `docs/agent-os/SPAWN_WORKER.md` + `_WORKER_PROMPT.md` |

## Goal

One sentence (product altitude OK).

## Context to read first

- `AGENTS.md`
- `docs/agent-os/SPAWN_WORKER.md`
- Spec / plan paths:
- Open Decisions / locked IDs:

## Owned paths (may edit)

- `apps/<id>/...`

## Forbidden paths (do not edit)

- `deploy/secrets/` unless listed
- Other apps unless listed

## Parallelism

| Field | Value |
|-------|-------|
| `[P]` tasks in this packet | yes \| no |
| Disjoint from other in-flight packets? | yes \| no \| n/a |

If yes+yes, main may spawn this worker alongside others. If paths overlap, serial only.
## Definition of Done

Checklist the agent must prove before stopping:

- [ ] Acceptance tests added/updated: `…`
- [ ] Commands green: `cd apps/<id> && uv run pytest …`
- [ ] No invariant violations (secrets, registry, locks)
- [ ] PR opened / ready with summary of decisions (or changes listed if no remote)

## Out of scope

- …

## Governor locks required

List product numbers, vault seeds, host account HITL, or other decisions the agent must **not** invent.
Prefer linking **Open Decisions** ids from `spec.md` (`D1`, …) when they already exist (constitution §G).
Feature must have `FINISH_BAR.md` with **Implement unblocked: yes** (§G.2) unless this packet is tiny-glue / Out-of-scope excludes finish-bar work.
If any listed lock is **architecture-affecting**, require feature `PLAN_DELTA.md` (§G.1) complete before Status `ready`.
If a lock is missing, put the task in **Out of scope** or Status `blocked` — do not stall a multi-hour run guessing.

| Lock | Value or `blocked until human` |
|------|--------------------------------|
| | |

## Stop / escalate if

- Missing product/ops decision
- DoD cannot be met without expanding owned paths
- Conflict with `notes/architect-backlog.md`
- A Governor lock row is empty / blocked and the DoD depends on it

## Handoff notes (agent fills at end)

- What changed:
- Tests run:
- Open questions for human:
