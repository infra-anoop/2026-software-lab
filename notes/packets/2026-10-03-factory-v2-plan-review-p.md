# Review packet — 001 Factory v2 plan, Architecture review (P*)

## Meta

| Field | Value |
|-------|-------|
| Packet id | `2026-10-03-factory-v2-plan-review-p` |
| Gate | P* |
| Brief | `docs/agent-os/PLAN_REVIEW_PROMPT.md` + `docs/agent-os/STACK_POSTURE.md` + `docs/agent-os/PLAN_AUTHORING_GATES.md` |
| Feature dir | `specs/001-factory-v2/` |
| Agent mode | spawned-reviewer (model family: GPT — spec D3) |

## Context to read first

- `docs/agent-os/SPAWN_REVIEWER.md`
- `docs/agent-os/PLAN_REVIEW_PROMPT.md` (job text; `PLAN_PATH` = `specs/001-factory-v2/plan.md`)
- `specs/001-factory-v2/spec.md` (Approved), `intent.yaml`, `acceptance.md`, `SPEC_REVIEW.md`, `PROCESS_REVIEW.md`
- `notes/sprints/2026-10-sprint-02.md`, `AGENTS.md`, `.specify/memory/constitution.md`
- Current reality: `notes/packets/` (sprint-01 bus), `.github/workflows/`, `scripts/`

## Architecture framing for this review

The factory is the product. Pressure the plan as an architecture for a one-engineer software factory, not as an app:

- **Bus choice**: are typed append-only files in git + derived lifecycle the right call versus GitHub Issues/Projects, Beads, Linear, or an event store? Is "derive everything on read" robust (latency, GitHub API limits, offline)?
- **Enforceability**: which gates can an agent with the same credentials as the governor trivially bypass? Is the identity decision (spec D4) framed with honest consequences? Is "recorded-only until D4 locks" an acceptable interim, or a hidden fidelity delta?
- **Execution**: is entry-only-through-`factory claim` plus `subagentStart` hook realistic for Cursor subagents and cloud agents?
- **Gates**: red-first proof design, deferral-words rule, Semgrep choice, mutation approach — sound, or gameable / noisy?
- **SOTA fit**: does `research.md` exercise non-sibling alternatives for every block? Is anything over-built for 1 governor + 3 workers (I-X1)?
- **Phasing-light**: does P0 → P1 (3 slices) → P1b → P2 respect the 3-day Wave 1 time-box and cap 3?

## Artifacts under review

- `specs/001-factory-v2/plan.md`, `research.md`, `data-model.md`, `contracts/*.md`, `quickstart.md`

## Owned paths (may edit)

- `specs/001-factory-v2/PLAN_REVIEW.md` (create)

## Forbidden paths (do not edit)

- Every other file.

## Definition of Done

- [ ] `specs/001-factory-v2/PLAN_REVIEW.md` deposited per the brief's output format
- [ ] Findings prefixed P; severity Blocker / Debate / Later / Nit; Debates tagged product / process / arch
- [ ] Stop — do not edit the plan

## Governor locks already closed (do not re-open)

| Lock | Value |
|------|-------|
| Framework | Stay on Spec Kit; overlays become code |
| Gate classes | Drift gates block, orchestrator may override with reason; governor-only for spend/secrets/irreversible/governor decisions |
| Worker cap | 3 |
| Seeds | All block |
| Wave 1 exit | P1 only, 3 days + ≤2 slip; P2 by sprint close |
| Repeats | Orchestrator links, governor confirms |
| D1 / D2 / D3 | P3 out (sprint 03) / mutation 70% / GPT reviewers |

## Stop / escalate if

- Plan or spec missing
- Brief and packet disagree on deposit path
