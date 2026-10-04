# Packet — Factory v2 Slice C — gate framework, PR gates, hooks, CI workflow (Wave 1, bootstrap)

## Meta

| Field | Value |
|-------|-------|
| Packet id | `2026-10-04-factory-v2-slice-c` (order id `wo-20261004-factory-slice-c`) |
| Status | blocked — until CP0 merges and the P0 test review (T016) is triaged |
| Feature / spec | `specs/001-factory-v2/` |
| Branch | `wo/wo-20261004-factory-slice-c` (isolated worktree) |
| Agent mode | **background** |
| Spawn | `docs/agent-os/SPAWN_WORKER.md` |
| Tasks | T050–T053, T055–T060 (US4), then T064 once slice B's `intent.coverage.group_by_intent()` is on `main` — T054 T* review is spawned by the orchestrator after your red tests land; pause after red tests and say so in an interim handoff |

## Goal

Implement gate framework, PR gates, hooks, CI workflow against the frozen P0 contracts, test first, so CP1 (each slice green on its own) is reached by working day 2 (max day 4).

## Context to read first

- `AGENTS.md`, `docs/agent-os/SPAWN_WORKER.md`
- `specs/001-factory-v2/tasks.md` — your task ids below are the spec; quoted constraints are verbatim requirements
- `specs/001-factory-v2/{plan.md,data-model.md,contracts/*.md,research.md,acceptance.md}`
- `scripts/factory/src/factory/api.py` — frozen at CP0; changing it needs an amendment from the orchestrator (stop and ask in the handoff)
- Locks: cap 3, horizon 60, D2 70%, D3 GPT reviewers, D4 GitHub App identity

## Owned paths (may edit)

- `scripts/factory/src/factory/gates/{runner.py,overrides.py,retro.py}`, `scripts/factory/src/factory/gates/{pr,repo}/**`, `scripts/factory/src/factory/hooks/**`
- `scripts/factory/src/factory/cli/gates.py`, `scripts/factory/src/factory/cli/checks.py` (hooks/registry/immutability subcommands only)
- `scripts/factory/tests/contract/test_gate_run.py`, `scripts/factory/tests/unit/gates/{test_registry_checks.py,pr/**}`, `scripts/factory/tests/unit/hooks/**`
- `.cursor/hooks.json`, `.github/workflows/factory-gates.yml`
- `scripts/factory/gates.yaml` — append/adjust only the rows for your gates
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

- [ ] Red first: every new test was committed failing (assertion failure) before the commit that makes it pass; list the pairs of commits in the handoff
- [ ] `uv run --project scripts/factory pytest` green for this slice's tests; `ruff check scripts/factory` clean; type hints on all signatures; no `os.getenv` outside `factory/config/`
- [ ] `specs/001-factory-v2/acceptance.md` evidence filled (real test ids) for this slice's rows; `tasks.md` checkboxes ticked for this slice's tasks only
- [ ] Handoff `notes/packets/<this-packet-id>.handoff.md`: what changed, commands + results, deviations (why + conservative choice), open questions (`blocker_governor` / `non_blocking`), manual equivalents of P1 gates run by hand (bootstrap verdict input, FR-037)
- [ ] Commits on the packet branch only; no push to `main`; no force-push

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
| Two gate classes (F1/R1) | letter | `drift` = orchestrator override with reason; `governor-only` = governor only, verified via `IdentityPort` when mode is `verified` |
| No direct commits/pushes to `main` (I-P10, governor 2026-10-03) | letter | `shell-guard` denies them for every actor; `branch-protection-require-pr` checks the snapshot |
| Hooks advisory, CI authoritative (review P3) | letter | every hook has a registry `hook_twin_of`; hooks offline < 300 ms |
| Cursor hooks format | letter | per `/home/vscode/.cursor/skills-cursor/create-hook/SKILL.md` |

## Stop / escalate if

- A frozen interface is insufficient → stop; describe the needed amendment in the handoff (non_blocking unless it changes product behavior)
- Any edit needed outside Owned paths
- A test cannot be made red by a real assertion
