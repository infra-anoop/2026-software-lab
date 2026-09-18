# Review packet template

Copy to `notes/packets/<id>.md` (id example: `2026-09-17-swv2-t055`).
Spawn the reviewer per `docs/agent-os/SPAWN_REVIEWER.md`. Do **not** ask the human to paste a brief.

## Meta

| Field | Value |
|-------|-------|
| Packet id | |
| Status | ready \| in_progress \| done |
| Gate | F* \| R* \| P* \| T* |
| Brief | `docs/agent-os/TEST_REVIEW_PROMPT.md` (or SPEC/PROCESS/PLAN) |
| Feature dir | `specs/<feature>/` |
| Commit | |
| Agent mode | spawned-reviewer |

## Context to read first

- `docs/agent-os/SPAWN_REVIEWER.md`
- Brief path above (job text below the horizontal rule)
- Feature `spec.md` / `plan.md` / `contracts/` / tests named below as applicable
- Locked finding IDs (do not reuse F*/R*/P*/T* from earlier slices)

## Artifacts under review

- Paths:
- Pytest / other command results (if T*):

## Owned paths (may edit)

- `specs/<feature>/TEST_REVIEW.md` (or SPEC_REVIEW / PROCESS_REVIEW / PLAN_REVIEW)

## Forbidden paths (do not edit)

- Application / product implementation (`apps/`, `modules/`)
- Spec and plan body except where the brief allows none
- `deploy/secrets/`

## Definition of Done

- [ ] Review deposited at the owned path (append T* slices; do not wipe prior locks)
- [ ] Findings use the correct ID prefix; ≥1 Debate and ≥1 strength when tests/spec exist
- [ ] Stop — human adjudicates Debates; do not implement

## Out of scope

- Matching product implementation
- Asking the human to paste this packet or the brief

## Governor locks required

Locks the implementer must treat as closed after adjudication (or mark Debate unresolved).
Examples: status-code splits, rate-limit scope, numeric caps, “defer P7.”

| Lock | Value or `await Debate` |
|------|-------------------------|
| | |

## Stop / escalate if

- Artifacts under review are missing
- Brief and packet disagree on deposit path
- Required Governor lock is still `await Debate` and would force inventing numbers/scope
