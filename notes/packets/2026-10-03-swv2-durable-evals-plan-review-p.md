# Review packet — 002 SWV2 durable state + measured quality, plan Architecture review (P*)

## Meta

| Field | Value |
|-------|-------|
| Packet id | `2026-10-03-swv2-durable-evals-plan-review-p` |
| Gate | P* |
| Brief | `docs/agent-os/PLAN_REVIEW_PROMPT.md` + `docs/agent-os/STACK_POSTURE.md` + `docs/agent-os/PLAN_AUTHORING_GATES.md` |
| Feature dir | `specs/002-swv2-durable-evals/` |
| Agent mode | spawned-reviewer (model family: GPT) |

## Context to read first

- `docs/agent-os/SPAWN_REVIEWER.md`, `docs/agent-os/PLAN_REVIEW_PROMPT.md` (`PLAN_PATH` = `specs/002-swv2-durable-evals/plan.md`)
- `specs/002-swv2-durable-evals/spec.md` (Approved), `intent.yaml`, `acceptance.md`, `SPEC_REVIEW.md`
- Baseline: `specs/smart-writer-v2/spec.md`, `plan.md`, `contracts/`, `PLAN_REVIEW.md`
- `notes/architect-backlog.md` (A27–A29), `notes/sprints/2026-10-sprint-02.md`
- Code: `apps/smart-writer-v2/app/` (store, orchestrator, agents, config, entrypoints), `modules/lab_shared/src/lab_shared/jobs.py`, `flake.nix`, `deploy/`
- Factory plan the work runs under: `specs/001-factory-v2/plan.md`

## Architecture framing for this review

- **Durability**: is checkpoint + startup recovery with an in-process JobRunner sound for "never silently lost"? Gaps (crash during recovery, double-run, checkpoint cleanup)?
- **Data**: psycopg + hand SQL + dbmate vs Alembic/Atlas/Supabase CLI; cascade + Storage deletion order; `last_used_at` semantics; checkpoint rows not FK-linked.
- **Ownership**: HttpOnly cookie vs Supabase anonymous auth; same-origin assumptions; 404-on-foreign.
- **Evals**: is the noise band (k=3, range with floor) statistically defensible or will it flap / be too loose? Subset representativeness; held-out leakage paths; judge seeing only RFP + draft; ledger mechanics.
- **Letter locks**: A27 (Supabase Storage, checkpointer), baseline D5 one service, D4 Gemini. Any silent substitution?
- **Staging D5 options**: honest consequences?
- **lab_shared scope**: are the four shared modules justified (designed for reuse) or premature?
- **Phasing-light**: lanes and ordering under cap 3 shared with factory P2.

## Artifacts under review

- `specs/002-swv2-durable-evals/plan.md`, `research.md`, `data-model.md`, `contracts/*.md`, `quickstart.md`

## Owned paths (may edit)

- `specs/002-swv2-durable-evals/PLAN_REVIEW.md` (create)

## Forbidden paths

- Every other file.

## Definition of Done

- [ ] `PLAN_REVIEW.md` deposited per the brief's output format; findings prefixed P; severity Blocker / Debate / Later / Nit; Debates tagged product / process / arch
- [ ] Stop — do not edit the plan

## Governor locks already closed (do not re-open)

A27–A29; spec D1 (within 1 point on ≥ 80%, every dimension), D2 (noise margin), D4 (Gemini); review locks F1–F9 in the spec (per-dimension non-compensable gate, held-out + blinded review, support gate, retention use + disclosure, bundle check, cascade).
