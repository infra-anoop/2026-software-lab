# Review packet — 001 Factory v2 spec, process review (R*)

## Meta

| Field | Value |
|-------|-------|
| Packet id | `2026-10-03-factory-v2-spec-review-r` |
| Gate | R* |
| Brief | `docs/agent-os/PROCESS_REVIEW_PROMPT.md` |
| Feature dir | `specs/001-factory-v2/` |
| Agent mode | spawned-reviewer (model family: GPT — spec D3) |

## Context to read first

- `docs/agent-os/SPAWN_REVIEWER.md`
- `docs/agent-os/PROCESS_REVIEW_PROMPT.md` (job text below the horizontal rule; `SPEC_PATH` = `specs/001-factory-v2/spec.md`)
- `specs/001-factory-v2/intent.yaml`
- `.specify/memory/constitution.md`, `AGENTS.md`, `docs/agent-os/README.md`
- `notes/sprints/2026-10-sprint-02.md`
- Sprint-01 evidence: `notes/packets/` (2026-09-* files), `specs/smart-writer-v2/` (`TEST_REVIEW.md`, `FINISH_BAR.md`, `PLAN_DELTA.md`)

## Process framing for this review

This feature turns the lab's prose process into executable gates and a typed agent bus. It is self-referential: the process must review a spec that rewrites the process. Judge:

- Does the spec actually replace prose with checks, or add a new layer on top (net ceremony)?
- Does it preserve what worked in sprint 01 (background workers, crisp Open Decision batches, cattle) while fixing what didn't (hand-synced status, mutable packets, unstructured handoffs, giant review files)?
- Is the bootstrap (gates built before they exist; retroactive application) sound?
- Is the constitution 2.0 move (FR-033/034) specified tightly enough that a cold agent cannot silently thin it?
- Are spec vs plan boundaries respected (bus transport is deliberately left to plan Architecture)?

## Artifacts under review

- `specs/001-factory-v2/spec.md`, `acceptance.md`, `intent.yaml`

## Owned paths (may edit)

- `specs/001-factory-v2/PROCESS_REVIEW.md` (create)

## Forbidden paths (do not edit)

- `spec.md`, `intent.yaml`, `acceptance.md`, any code, `deploy/secrets/`

## Definition of Done

- [ ] `specs/001-factory-v2/PROCESS_REVIEW.md` deposited per the brief's output format
- [ ] Findings prefixed R; each Debate tagged product or process
- [ ] Stop — do not edit the spec

## Governor locks already closed (do not re-open)

| Lock | Value |
|------|-------|
| Framework | Stay on Spec Kit; overlays become code |
| Bus | Bus v2 is a plan Architecture decision with alternatives + independent review |
| D1 / D2 / D3 | See spec Open Decisions |

## Stop / escalate if

- Spec or intent file missing
- Brief and packet disagree on deposit path
