# Packet — Factory v2 Slice A — bus, board, orders, claims, identity, scorecard (Wave 1, bootstrap)

## Meta

| Field | Value |
|-------|-------|
| Packet id | `2026-10-04-factory-v2-slice-a` (order id `wo-20261004-factory-slice-a`) |
| Status | implemented — Slice A tests green; PR not opened (orchestrator) |
| Feature / spec | `specs/001-factory-v2/` |
| Branch | `wo/wo-20261004-factory-slice-a` (isolated worktree) |
| Agent mode | **background** |
| Spawn | `docs/agent-os/SPAWN_WORKER.md` |
| Tasks | T017–T025 (US1), T026–T038 except T033 (US2) — T033 T* review is spawned by the orchestrator after your red tests land; pause after red tests and say so in an interim handoff |

## Goal

Implement bus, board, orders, claims, identity, scorecard against the frozen P0 contracts, test first, so CP1 (each slice green on its own) is reached by working day 2 (max day 4).

## Context to read first

- `AGENTS.md`, `docs/agent-os/SPAWN_WORKER.md`
- `specs/001-factory-v2/tasks.md` — your task ids below are the spec; quoted constraints are verbatim requirements
- `specs/001-factory-v2/{plan.md,data-model.md,contracts/*.md,research.md,acceptance.md}`
- `scripts/factory/src/factory/api.py` — frozen at CP0; changing it needs an amendment from the orchestrator (stop and ask in the handoff)
- Locks: cap 3, horizon 60, D2 70%, D3 GPT reviewers, D4 GitHub App identity

## Owned paths (may edit)

- `scripts/factory/src/factory/{lifecycle,board,metrics,github,identity,orders}/**`
- `scripts/factory/src/factory/cli/{board,orders}.py`
- `scripts/factory/tests/contract/test_{status,orders,claim,handoff,pr_and_verdict,bus_pr}.py`, `scripts/factory/tests/unit/test_{lifecycle,github_adapter,no_bookkeeping,scorecard,identity}.py`, `scripts/factory/tests/fixtures/github_recorded/**`
- `deploy/secrets/schema.yaml` (add `tooling:` section, names only), `scripts/validate_secrets_schema.py`, `scripts/test_validate_secrets_schema.py`
- `specs/001-factory-v2/acceptance.md` (evidence cells for this slice's rows), `specs/001-factory-v2/tasks.md` (this slice's checkboxes)

## Forbidden paths (do not edit)

- `scripts/factory/src/factory/{api.py,bus/,config/,cli/app.py,cli/exit_codes.py,gates/registry.py}`, `scripts/factory/tests/fixtures/` (frozen at CP0 — ask for an amendment)
- Other slices' paths; `apps/**`, `modules/**`, `.specify/**`, other specs

## Parallelism

| Field | Value |
|-------|-------|
| `[P]` tasks in this packet | yes |
| Disjoint from other in-flight packets? | yes — slices A, B, C own disjoint paths; `gates.yaml` rows are append-only per slice |

## Definition of Done

- [x] Red first: every new test was committed failing (assertion failure) before the commit that makes it pass; list the pairs of commits in the handoff
- [x] `uv run --project scripts/factory pytest` green for this slice's tests; `ruff check scripts/factory` clean; type hints on all signatures; no `os.getenv` outside `factory/config/`
- [x] `specs/001-factory-v2/acceptance.md` evidence filled (real test ids) for this slice's rows; `tasks.md` checkboxes ticked for this slice's tasks only
- [x] Handoff `notes/packets/<this-packet-id>.handoff.md`: what changed, commands + results, deviations (why + conservative choice), open questions (`blocker_governor` / `non_blocking`), manual equivalents of P1 gates run by hand (bootstrap verdict input, FR-037)
- [x] Commits on the packet branch only; no push to `main`; no force-push

## Out of scope

- Wave 2 (US6–US8, mutation), Phase 8 ops steps, Phase 9 retro
- Editing frozen P0 contracts

## Governor locks required

| Lock | Value |
|------|-------|
| Cap | 3 |
| Horizon | 60 minutes |
| Reviewer family | GPT |
| Identity | GitHub App (recorded-only until live) |

## Fidelity (constitution §I — required)

| Lock | fidelity | How this packet honors it |
|------|----------|---------------------------|
| Cap 3 at claim + merge (FR-008 waive) | letter | `factory claim` refuses at active ≥ 3; claim is an atomic fast-forward push |
| Git is the lease authority (review P4) | letter | no database, no lock server; release + stale derived from git |
| GitHub App identity (D4-A) | letter | installation tokens minted from `FACTORY_GITHUB_APP_ID` + `FACTORY_GITHUB_APP_PRIVATE_KEY`; recorded-only mode until the App exists |
| httpx REST, no gh CLI | letter | `factory.github.rest` only |

## Stop / escalate if

- A frozen interface is insufficient → stop; describe the needed amendment in the handoff (non_blocking unless it changes product behavior)
- Any edit needed outside Owned paths
- A test cannot be made red by a real assertion
