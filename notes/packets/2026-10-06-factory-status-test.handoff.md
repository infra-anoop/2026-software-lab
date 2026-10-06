# Handoff — `wo-20261006-factory-status-test` (T102, PR-C3)

**Phase:** 1 of 2: red tests only (constitution §V). No implementation. T* round 1 rejected the tests (`verdict-01`); its Blockers are fixed (see § T* round 1). Next: the T* round 2 review and the governor's T-ST3 choice, then implement `factory.gates.repo.status_test:run` and fill the I-M4 `board.matches_reality` evidence in `acceptance.md`.

**Branch:** `wo/wo-20261006-factory-status-test` from `origin/main` `2a591f9` (Slices A and B merged). No PR opened.

## Proposed oracle (for T* review)

The contract row says only "repo (unit)", and the Slice C plan delta (M3) leaves the oracle to T102 test-first + T*. The tests propose this oracle:

- The gate reads every bus file at `head_sha` from git and runs `main`'s installed lifecycle derivation over that data alone, with no GitHub data.
- It **passes** when every bus file parses, every order directory on the head bus yields one board entry, and every governor wait the board reports points at a recorded decision request.
- Otherwise it **blocks**, naming the gate and the file, order or decision.
- **D5:** the head is only data. The gate never imports, runs or checks out head code. It does not trust `ctx.bus_snapshot` to be complete, because Slice C's runner loads that snapshot tolerantly and skips files that do not parse.

Two "inconsistent" cases are a choice the reviewer should confirm. Both pass `bus.schema`, and `main`'s derivation handles each silently:

1. A claim or handoff with no order: `load_order` returns None, so the board drops work that is in flight.
2. An order that waits on a decision with no request on the bus: the board shows a placeholder prompt instead of the governor's question.

## Tests (`scripts/factory/tests/unit/gates/repo/test_status_test.py`)

| Test | Behaviour |
|------|-----------|
| `test_passes_on_a_valid_head_bus` | ready, in-flight, released, and waiting-on-a-recorded-decision orders pass |
| `test_judges_the_head_commit_not_the_checkout` | broken untracked bus files in the working tree are ignored |
| `test_blocks_order_events_the_board_would_drop` | claim + handoff with no order blocks, naming the order |
| `test_blocks_when_main_derivation_omits_a_head_order` | (T-ST1, reworked for T-ST6) `main`'s per-record `derive_order` is wrapped to rename a valid order's lifecycle: the gate blocks naming that order and must have called `derive_order` |
| `test_blocks_a_governor_wait_with_no_recorded_decision` | missing decision request blocks, naming order and decision (T-ST3 open) |
| `test_executes_no_head_code` | head ships a pass-always gate, marker-writing conftests and `sitecustomize`, and (round 1, T-ST2) a marker-writing copy of the `factory` package: still blocks, no marker, no checkout, no worktree, no write |
| `test_fails_closed_on_a_malformed_bus_file[invalid-yaml, schema-invalid]` | an unparseable or schema-invalid head file blocks, naming the path |
| `test_fails_closed_when_the_head_commit_is_unreadable` | an unknown head sha blocks, naming it |

**Red (round 1 and round 2 heads):** 9 of 9 fail on the assertion. **Red (original phase 1):** 8 of 8 failed on the assertion `factory.gates.repo.status_test:run is not implemented`. No collection errors (the entrypoint is imported inside the tests). `ruff check` and `ruff format --check` pass. A throwaway script confirmed the fixture data: the valid, orphan-event and missing-decision buses pass `validate_bus`, and both malformed files fail it and are dropped from a tolerant snapshot.

## Deviations (bootstrap, disclosed)

- **`size_minutes: 50`** is the dispatch timebox, an estimate within the 60-minute horizon, not a measured size. Stated in the order's `refs`, following Slice B.
- **Owned paths** add this note (`notes/packets/2026-10-06-factory-status-test.handoff.md`) to the four dispatched paths, as Slice B's amendments did for its handoff. Without it, `diff-within-owned-paths` blocks this file.
- **`factory-status-test` is not in `checks`.** Under D5, `main`'s code judges this PR, and `main` has no entrypoint for this gate until the order merges. The PR carries a bootstrap verdict instead (T102).
- **D5 lock:** declared as `fidelity: letter` with the token "head is only data". D5 is recorded on Slice C's branch, not yet in `main`'s `spec.md`.

## For the implement phase

- `factory/gates/repo/` has no `__init__.py` on `main`; Slice C adds it and `_git.py` (`passed`/`failed`/`outcome`). This order owns only `status_test.py`, so it either imports as a namespace package until C merges or reuses `factory.gates.drift._common`. Slice C's `__init__.py` then merges cleanly.
- The derivation needs a view built from one commit: `main`'s `BusView` and `derive_order` with an offline `GitHubPort` (no PRs, no statuses).

## T* round 1 (`verdict-01`, reject; triage in `amendment-01`)

The orchestrator triaged round 1 under constitution §J: fix each root cause once, with at most one test per class.

- **T-ST1, accepted (Blocker): the oracle was not pinned.** A scanner that never derived the board could pass. The new `test_blocks_when_main_derivation_omits_a_head_order` wraps `factory.lifecycle.derive.derive_from_view`, and any alias of it in the gate module, so that `main`'s derived snapshot drops one valid order. The gate must block, naming that order, and must have called the derivation. This pinned `derive_from_view` as the derivation entrypoint, which round 2 found too narrow (T-ST6, below).
- **T-ST2, accepted (Blocker): the D5 sentinel missed head imports of the `factory` package.** The existing `test_executes_no_head_code` now also ships marker-writing head copies of 18 `factory` modules: the package root, `api`, the `bus` loader, models and schema, `config.settings`, `orders.git`, `lifecycle` (`view`, `derive`), `board` (`render`), `gates`, and the shared drift helpers. It keeps the single marker assertion; no parallel test was added.
- **T-ST3, open (Debate, product, `who: human`).** Should this gate also block malformed bus files, which `bus.schema` already does, and decision waits with no recorded request, which replaces `main`'s visible placeholder? Neither the orchestrator nor the worker adjudicated it. `test_fails_closed_on_a_malformed_bus_file` and `test_blocks_a_governor_wait_with_no_recorded_decision` stay unchanged until the governor chooses.
- **T-ST4, noted:** strength; the controls are kept.
- **T-ST5, accepted (Later).** Manual equivalent for the omitted self-gate, below.

### Bootstrap manual equivalent for `factory-status-test` (T-ST5)

`factory-status-test` is not in this order's `checks`, because `main`'s code judges this PR (D5) and has no entrypoint for the gate until merge. Before the bootstrap verdict, the gate's evidence is reproduced by hand at the PR head:

1. `cd scripts/factory && uv run pytest tests/unit/gates/repo/test_status_test.py`: every case green.
2. The implemented gate runs over this repository's own head bus: a `GateContext` for the PR head, with `run(ctx)` called from this branch's code. The result passes, and its messages are recorded in this handoff.
3. The reviewer reruns steps 1 and 2 and lists them under `manual_equivalents` in the bootstrap verdict.

Step 2 runs this branch's gate code, not `main`'s. That is the D5 bootstrap exception this order already carries: the governor approves the merge, and the gate judges later PRs from `main` once merged.

## T* round 2 (`verdict-02`, reject; triage in `amendment-02`)

- **T-ST6, accepted (Blocker): an implementation symbol stood in for the contract behaviour.** Requiring a call to `derive_from_view` would reject a valid gate that calls `main`'s per-record `derive_order` directly. Following the reviewer's smallest fix, the same test now wraps and spies on `factory.lifecycle.derive.derive_order`, plus any alias of it in the gate module. `main`'s `derive_from_view` calls `derive_order` through the module, so both paths go through the wrapper. The wrapper renames the `WORKING` order's lifecycle. The gate must block naming `WORKING`, and must have called `derive_order`. No other test changed and none was added.
- **T-ST2:** resolved.
- **T-ST3:** still open for the governor; not reviewed this round.
- **Red:** 9 of 9 on the not-implemented assertion, with no collection errors.
