# Packet — Factory v2 P0: contract freeze (Wave 1, bootstrap)

## Meta

| Field | Value |
|-------|-------|
| Packet id | `2026-10-03-factory-v2-p0-contracts` (order id `wo-20261003-factory-p0`) |
| Status | ready |
| Feature / spec | `specs/001-factory-v2/` |
| Branch | `wo/wo-20261003-factory-p0` (isolated worktree) |
| Agent mode | **background** |
| Spawn | `docs/agent-os/SPAWN_WORKER.md` |
| Tasks | `specs/001-factory-v2/tasks.md` T001–T015 (Phase 1 + Phase 2, except T016/T016a which the orchestrator does) |

## Goal

Create the `factory` uv project and freeze every cross-slice contract (message models, registry, frozen interfaces, CLI skeleton, shared fixtures, red contract + seed tests), so three slice workers can run in parallel against it.

## Context to read first

- `AGENTS.md`, `docs/agent-os/SPAWN_WORKER.md`
- `specs/001-factory-v2/tasks.md` (Phase 1–2 task text is the spec for this packet; quoted constraints are verbatim requirements)
- `specs/001-factory-v2/plan.md` (§ Architecture, § Project Structure), `data-model.md`, `contracts/{cli,messages,gates,hooks}.md`, `research.md` § Red-first
- Locks: D2 70%, D3 GPT, D4 GitHub App (identity is an interface only in P0)

## Owned paths (may edit)

- `scripts/factory/**` (new)
- `factory.toml` (new)
- `bus/**/.gitkeep` (new)
- `.github/workflows/factory-gates.yml` (new)
- `.github/workflows/verify-source.yml` — only the `pytest scripts/` line (add `--ignore=scripts/factory`)
- `specs/001-factory-v2/data-model.md` — only the Gate line (add `entrypoint`), per T009; and the Lock line (via amend-01)
- `specs/001-factory-v2/tasks.md` — checkboxes for T001–T015 only
- `specs/001-factory-v2/contracts/cli.md` — only the JSON envelope section (via amend-01)

Amendment `wo-20261003-factory-p0.amend-01` (`bus/orders/wo-20261003-factory-p0/amendment-01.yaml`, orchestrator-authorized 2026-10-04) supersedes the order's `owned_paths` with the list above.

## Forbidden paths (do not edit)

- `apps/**`, `modules/**`, `deploy/**`, `.specify/**`, `.cursor/**`, `AGENTS.md`, other specs
- Anything not listed above

## Parallelism

| Field | Value |
|-------|-------|
| `[P]` tasks in this packet | yes (T003–T005), done by this one worker |
| Disjoint from other in-flight packets? | yes (the concurrent SWV2 task-authoring worker owns only `specs/002-swv2-durable-evals/`) |

## Definition of Done

- [ ] `cd scripts/factory && uv sync --locked` succeeds; `uv.lock` committed
- [ ] `uv run --project scripts/factory factory check schema` exits 0 on `scripts/factory/tests/fixtures/messages/`; `factory check schema --write` generates `scripts/factory/schemas/<kind>.schema.json` for every kind; the stale-schema check fails when a model changes without regeneration
- [ ] `uv run --project scripts/factory pytest scripts/factory/tests/unit/test_bus_models.py` green
- [ ] `scripts/factory/tests/contract/test_cli_contract.py` and `scripts/factory/tests/seeds/test_seeds.py` are collected and **fail with real assertion failures** (not import/collection errors) for every unimplemented command or gate. Do not use `xfail`; leave them plainly red, and the slice workers turn them green. Mark them with `pytest.mark.contract` / `pytest.mark.seed` so the `factory-tests` CI job can run `-m "not contract and not seed"` until CP1 (put that selector in `factory-gates.yml` with a comment naming CP1)
- [ ] `uv run --project scripts/factory ruff check scripts/factory` clean
- [ ] Every function signature is type-hinted; no `os.getenv`/`os.environ` outside `scripts/factory/src/factory/config/`
- [ ] Interfaces in `scripts/factory/src/factory/api.py` match T010 exactly (names and fields), with docstrings stating each is frozen at CP0
- [ ] `gates.yaml` lists every P1 gate id from `contracts/gates.md` (class/category/intents/scope/entrypoint/priority); the entrypoint may point at a module that does not exist yet
- [ ] Commits on branch `wo/wo-20261003-factory-p0`; final handoff note at `notes/packets/2026-10-03-factory-v2-p0-contracts.handoff.md` listing: what changed, commands run with results, **deviations** (each with why + the conservative choice made), open questions classed `blocker_governor` / `non_blocking`, and **manual equivalents** of the P1 gates you ran by hand (red-first shown for the model tests, all changed paths inside owned paths, no test-only branching in non-test code) — this feeds the bootstrap verdict (FR-037)

## Out of scope

- Any gate logic, lifecycle derivation, board, GitHub REST, identity, hooks (slices A/B/C)
- The T* review spawn (T016) and slice packets (T016a) — orchestrator
- Pushing to `main` or opening a PR (orchestrator merges after the bootstrap verdict)

## Governor locks required

| Lock | Value |
|------|-------|
| Concurrency cap | 3 (`factory.toml concurrency_cap = 3`) |
| Autonomy horizon | 60 minutes |
| Reviewer family default | GPT (`[families]` maps `gpt` → `openai`) |
| Identity | GitHub App (D4-A); P0 ships only `IdentityPort` |

## Fidelity (constitution §I — required)

| Lock | fidelity | How this packet honors it |
|------|----------|---------------------------|
| Pydantic v2 + Typer + httpx + PyYAML (plan Technical Context) | letter | exactly these libraries; no substitutes (no click-only CLI, no dataclasses for messages, no requests) |
| uv project at `scripts/factory/` (plan Structure Decision) | letter | own `pyproject.toml` + `uv.lock` there; not `modules/lab_shared`, not `apps/` |
| Append-only YAML bus with no status fields (FR-002/003) | letter | `extra="forbid"` + forbidden keys at any depth |
| Cap 3 / horizon 60 | letter | in `factory.toml` |

## Stop / escalate if

- A frozen interface in T010 cannot be expressed as written → stop, write the question in the handoff as `blocker_governor` only if it changes product behavior; otherwise choose the conservative option and record a deviation
- Any need to edit outside Owned paths
- `uv sync` needs network that the sandbox refuses after retrying with full permissions
