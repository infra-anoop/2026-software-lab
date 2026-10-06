# Handoff — `wo-20261006-factory-status-test` (T102, PR-C3)

**Phase:** 2 of 2: implemented (see § Implementation). T* rounds 1 and 2 rejected and round 3 accepted (`verdict-03`); the tests are frozen. PR review round 2 accepted (`verdict-05`). The governor locked T-ST3 as option B (`amendment-05`, § T-ST3 governor lock); every focused test is green.

**Branch:** `wo/wo-20261006-factory-status-test` from `origin/main` `2a591f9` (Slices A and B merged). PR [#25](https://github.com/infra-anoop/2026-software-lab/pull/25).

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
| `test_blocks_a_governor_wait_with_no_recorded_decision` | missing decision request blocks, naming order and decision (T-ST3 rule 2, locked) |
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

## Implementation (after T* round 3 accept, `verdict-03`)

`scripts/factory/src/factory/gates/repo/status_test.py`, `run(ctx)`, uses `main`'s installed code only:

1. If `head_sha` does not resolve to a commit, the gate fails and names the sha.
2. It lists the head's bus with `factory.bus.store.list_bus_paths` (a git `ls-tree` at the sha). The order folders are the ids under `bus/orders/<id>/`.
3. It builds a head-only `BusView` with `main`'s strict read model (`factory.lifecycle.view.load_messages` / `load_order` at the head sha; `main_ref` = the head, `on_main` judged against `base_sha`).
4. It derives with `factory.lifecycle.derive.derive_from_view`, which calls `derive_order` per record. It uses an offline `GitHubPort` with no PRs, reviews, checks or statuses (it writes nothing), and `now` is the head commit time.
5. It blocks, naming the gate, when an order folder is missing from the derived board, an order shows twice, or the board shows an order with no folder.
6. A `BusError` or `GitError` returns a failure; nothing escapes.

Nothing from the head is imported, run or checked out (D5).

**T-ST3 tests, as implemented.** No code was added for either one.
- **`test_fails_closed_on_a_malformed_bus_file` (both cases) passes without special-casing.** `main`'s lifecycle loader is strict: `load_messages` → `load_file` raises `BusError` on an unreadable or schema-invalid file. So the derivation cannot run, and the gate fails closed (step 6), as the original dispatch required ("fails closed on malformed bus data"). If the governor picks option A, the gate would load tolerantly instead. That is a small change, and it would also mean the board silently loses that file.
- **`test_blocks_a_governor_wait_with_no_recorded_decision` stays red.** `main`'s derivation shows a placeholder, and the gate adds no rule for it.

**Acceptance:** the I-M4 `board.matches_reality` evidence names the gate's pass, dropped-events, derivation-sabotage and no-head-code tests.

**Full suite** (`uv run pytest`, `scripts/factory`): **690 passed, 24 failed**. All 24 are owned elsewhere or parked:
- 1, the parked T-ST3 test above.
- 23 in `tests/contract/test_cli_contract.py`, each a `factory` CLI command that is still "not implemented" on `main`:
  - Slice C: `override` (×4 incl. envelopes), `gate run` (×2), `hook shell-guard` (×2), `check hooks` (×2), `check registry` (×2), `check immutability` (×2).
  - T069: `retro` (×2).
  - T081: `correction new` (×2), `sprint close` (×3).
- None is caused by this order.

`ruff check .`, `ruff format --check` and `factory check schema` pass.

### Manual equivalent, result (T-ST5)

1. Focused tests: 8 passed, 1 failed (the parked T-ST3 test).
2. The gate over this repository's own head bus (head `35776f9`, base `origin/main` `2a591f9`) **blocks**:

   > `factory-status-test: bus/orders/wo-20261003-factory-p0/ is on the head bus but order wo-20261003-factory-p0 is not on the derived board (its folder holds no order)`

   This is a true finding on `main`'s bus, not a gate defect. The P0 contracts order predates orders. Its folder on `main` holds `amendment-01..03` and `verdict-01..04` but no `order.yaml`. Slices A and B got FR-037 reconstructed orders; P0 did not. So today's board drops P0's record. The other three order folders (Slice A, Slice B, this order) derive cleanly.

**Needed before this gate can be green on `main`:** an FR-037 bootstrap `bus/orders/wo-20261003-factory-p0/order.yaml`, reconstructed from `notes/packets/2026-10-03-factory-v2-p0-contracts.md` as for Slices A and B. It lies outside this order's owned paths (a stop condition), so it is not written here. The orchestrator decides whether to add it in this PR by amendment or in a separate bus change.

## P0 bootstrap order (`amendment-03`, orchestrator decision 2026-10-06)

`amendment-03` adds `bus/orders/wo-20261003-factory-p0/order.yaml`, that file only, to the owned paths. The order is an FR-037 reconstruction from `notes/packets/2026-10-03-factory-v2-p0-contracts.md`, in Slice A/B shape:
- `actor_verified: false`, `depends_on_decisions: []`.
- `size_minutes: 1`, with the true size in `refs`: about 6.5 h from `acc6721` to the accepting `verdict-04` (`d69d137`), then CI follow-ups to the PR #9 merge (`8cd8cb7`).
- Owned paths are the packet's as they stood before `amend-01`.
- Tasks T001–T015.
- Intents: I-A3 (the one T001–T015 cite) and I-M2 (the packet's no-status-fields lock).
- Locks come from the packet's Fidelity table, each with tokens P0's code carries: `pydantic`/`typer`/`httpx`/`pyyaml`, `scripts/factory`, `extra="forbid"`, `concurrency_cap = 3` / `autonomy_horizon_minutes = 60`.
- `checks` are gate ids only: the packet's manual-equivalent gates (red-first, owned paths, test seam) plus the two verdict gates.

**No claim or handoff was added.** With `main` simulated at this head, `main`'s `derive_snapshot` shows P0 as `merged`, which needs only `order.yaml` on `main`. The scorecard's run-record requirement is discussed below.

**Sprint membership is unchanged.** Like Slices A and B, `refs` name only the packet, not `notes/sprints/2026-10-sprint-02.md`.

**Gate over this repo's head (`de32177`, base `2a591f9`): passes.** The message is "every order folder on the head bus is on main's derived board".

**Scorecard** (`compute_scorecard`, no GitHub, so `wave1_exit` cannot be confirmed in either run):

| View | orders | runs | first-pass acceptance | rework loops | wave1_start | wave1_exit |
|------|--------|------|-----------------------|--------------|-------------|------------|
| unscoped, before (`main` = `origin/main`) | 4 | 0 | 0.0 | 4 | 2026-10-05T17:00:32Z | null |
| unscoped, after merge (`main` simulated at `de32177`) | 5 | 0 | 0.0 | 5 | 2026-10-05T17:00:32Z | null |
| `--sprint 2026-10-sprint-02`, before and after | 0 | 0 | null | 0 | null | null |

P0's first verdict was a reject, so unscoped rework loops rise by one. Wave 1 start is unchanged, because P0's issue is dated from this reconstruction commit, which is later than the start.

**Wave 1 exit implication.** No retro has landed, so in the unscoped view P0 joins the Wave 1 cohort. The exit then also needs a P0 run record (`run_complete`), as it already needs one for every other cohort order. No order has one today. The sprint-scoped view is untouched, since no order cites the sprint file.

**Full suite after the change:** 690 passed, 24 failed. These are the same 24 as in § Implementation: the parked T-ST3 test, and 23 CLI commands not implemented on `main` (Slice C, T069, T081). Ruff and `factory check schema` pass.

## PR code review round 1 (`verdict-04`, reject; triage in `amendment-04`)

- **PR-ST1, accepted (Blocker): unexpected exceptions escaped `run`.** An invalid UTF-8 head bus blob raised `UnicodeDecodeError`.
  - **Fix:** one catch-all at the `run` boundary. Any exception other than the `BusError` and `GitError` already handled returns a failed `GateResult`. The result names the error type, the head sha, and the file when the exception carries a `path`; the exception text is not echoed.
  - **Regression:** `test_fails_closed_on_an_unexpected_error_reading_the_head` (invalid UTF-8 in a head bus file). It was red at `d011497` ("raised instead of failing closed: UnicodeDecodeError") and is green at `c4b038f`.
  - This is a **PR-review fix, not a T* change**; the T*-accepted tests are unchanged.
- **PR-ST-L1, accepted as Later, owner Slice C (trusted-job resource limits).** Git object reads have no subprocess timeout, and bus blobs have no size bound before UTF-8/YAML parsing. This should be addressed once, in the shared git/bus loader and the trusted job, not in this gate.

**Results at `c4b038f`:**
- Focused file: 9 passed, 1 failed (the parked T-ST3 test).
- Full suite: **691 passed, 24 failed**. The 24 are the same as before: 1 parked T-ST3 test, and 23 CLI commands not implemented on `main` (Slice C, T069, T081).
- `ruff check`, `ruff format --check` and `factory check schema` pass.
- Manual gate run over this repo's head (`c4b038f`, base `2a591f9`): **passes**.

## T-ST3 governor lock (`amendment-05`)

The governor's decision, verbatim:

> **T-ST3 = option B, block both (governor, 2026-10-06 09:16 PT).**
> 1. A malformed or unreadable head bus file blocks. This already works through `main`'s strict loader, so keep it.
> 2. An order waiting on the governor with no recorded decision request on the bus blocks, naming the order and the decision.

- `amendment-05` records the lock and supersedes the order's `goal` to state both rules. Owned paths and stop conditions are unchanged.
- `TEST_REVIEW_STATUS_TEST.md` § Triage marks T-ST3 closed.
- `handoff.yaml` drops its governor question, which this lock answers.
- **Rule 1:** no code change. `main`'s strict loader raises `BusError` and the gate fails closed (§ Implementation, step 6).
- **Rule 2:** `status_test.py` now checks every board entry with the `blocked_on_governor` overlay. Each of its order's `depends_on_decisions` that is neither locked nor requested on the head bus blocks, with the message "order `<id>` waits on the governor for decision `<decision>`, which has no decision request on the head bus". An order that is blocked only by a handoff question has no decision id and is not affected.
- The tests are frozen; none was added or changed.

**Results at `7025864`:**
- Focused file: **10 passed**.
- Full suite: **692 passed, 23 failed**. All 23 are CLI commands not implemented on `main` (Slice C, T069, T081), the same list as in § Implementation.
- `ruff check`, `ruff format --check` and `factory check schema` pass.
- Manual gate run over this repo's head (`7025864`, base `2a591f9`): **passes**, with the message "every order folder on the head bus is on main's derived board, and every governor wait has a recorded decision request".
