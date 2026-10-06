# Handoff — `wo-20261006-factory-status-test` (T102, PR-C3)

**Phase:** 1 of 2: red tests only (constitution §V). No implementation. Next: spawn the T* review of the test file, then implement `factory.gates.repo.status_test:run` and fill the I-M4 `board.matches_reality` evidence in `acceptance.md`.

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
| `test_blocks_a_governor_wait_with_no_recorded_decision` | missing decision request blocks, naming order and decision |
| `test_executes_no_head_code` | head ships a pass-always gate and marker-writing modules: still blocks, no marker, no checkout, no worktree, no write |
| `test_fails_closed_on_a_malformed_bus_file[invalid-yaml, schema-invalid]` | an unparseable or schema-invalid head file blocks, naming the path |
| `test_fails_closed_when_the_head_commit_is_unreadable` | an unknown head sha blocks, naming it |

**Red:** 8 of 8 fail on the assertion `factory.gates.repo.status_test:run is not implemented`. No collection errors (the entrypoint is imported inside the tests). `ruff check` and `ruff format --check` pass. A throwaway script confirmed the fixture data: the valid, orphan-event and missing-decision buses pass `validate_bus`, and both malformed files fail it and are dropped from a tolerant snapshot.

## Deviations (bootstrap, disclosed)

- **`size_minutes: 50`** is the dispatch timebox, an estimate within the 60-minute horizon, not a measured size. Stated in the order's `refs`, following Slice B.
- **Owned paths** add this note (`notes/packets/2026-10-06-factory-status-test.handoff.md`) to the four dispatched paths, as Slice B's amendments did for its handoff. Without it, `diff-within-owned-paths` blocks this file.
- **`factory-status-test` is not in `checks`.** Under D5, `main`'s code judges this PR, and `main` has no entrypoint for this gate until the order merges. The PR carries a bootstrap verdict instead (T102).
- **D5 lock:** declared as `fidelity: letter` with the token "head is only data". D5 is recorded on Slice C's branch, not yet in `main`'s `spec.md`.

## For the implement phase

- `factory/gates/repo/` has no `__init__.py` on `main`; Slice C adds it and `_git.py` (`passed`/`failed`/`outcome`). This order owns only `status_test.py`, so it either imports as a namespace package until C merges or reuses `factory.gates.drift._common`. Slice C's `__init__.py` then merges cleanly.
- The derivation needs a view built from one commit: `main`'s `BusView` and `derive_order` with an offline `GitHubPort` (no PRs, no statuses).
