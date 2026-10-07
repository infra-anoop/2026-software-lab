# Handoff — `wo-20261006-factory-gates-summary` (T107)

**Phase:** 1 of 2: red tests only, for T* review. No source, snapshot or contract edits yet.

**Branch:** `wo/wo-20261006-factory-gates-summary` from `origin/main` `ac60d43` (order commit `6bc6a09`).

**Decision (governor lock, letter token `factory/gates`):** `specs/001-factory-v2/PLAN_DELTA.md` § Round 5; `tasks.md` T107; order `bus/orders/wo-20261006-factory-gates-summary/order.yaml`.

## What the tests pin

`factory gate run --pr N` (all CI gates, no `--gate`) posts one more commit status, `factory/gates`, on the head SHA, after every per-gate status. It is `success` only when every CI gate in the installed (`main`'s) registry ran and each outcome is `pass` or `overridden`; otherwise it is `failure`, naming the failing gates, within `STATUS_DESCRIPTION_LIMIT` (140). Per-gate statuses are unchanged. `branch-protection-require-pr` requires `factory/gates` (pinned to `github.actions_app_id`, P9) instead of one `factory/<gate-id>` per P1 gate.

## New and changed tests

`scripts/factory/tests/contract/test_gate_run.py`. These run the trusted job's command (`--pr --expect-head --evidence`, with a valid empty red-first bundle) and stub every CI gate entrypoint (`RecordedGates`):

| Test | Pins |
|------|------|
| `test_gate_run_pr_posts_gates_summary_success_when_every_gate_passes` | every gate passes, so `factory/gates` is `success`, posted once on the head |
| `test_gate_run_pr_gates_summary_fails_naming_each_failing_gate` | two failing gates: `failure`, both ids named, a passing gate not named |
| `test_gate_run_pr_gates_summary_counts_overridden_as_success` | a failing gate with an honored drift override counts as passed |
| `test_gate_run_pr_posts_gates_summary_after_every_gate_status` | `factory/gates` is the last status posted, after one status per CI gate |
| `test_gate_run_pr_gates_summary_follows_the_installed_registry_not_the_head` | the head's `gates.yaml` drops `bus.immutable` and adds `head-only-gate`: the summary still fails on `bus.immutable` and does not name `head-only-gate` |

`scripts/factory/tests/unit/gates/test_runner.py` (new). These pin a pure function, `factory.gates.runner.summary_status(report, gates) -> (state, description)`, looked up with `getattr` so the test fails on an assertion, not an import error:

| Test | Pins |
|------|------|
| `test_summary_fails_naming_a_registered_ci_gate_that_did_not_run` | an installed CI gate missing from the report gives `failure`, naming it |
| `test_summary_description_fits_the_status_limit_when_every_gate_fails` | all 25 fail: description ≤ 140 characters and still names the first failing gate |

`scripts/factory/tests/unit/gates/test_registry_checks.py`:

- The shared `required_contexts()` fixture is now the target ruleset: `Factory tests`, `Verify Source / verify`, `factory/gates`, all pinned. `UNPINNED` is now `factory/gates`.
- `test_branch_protection_blocks_without_the_gates_summary_status` (replaces `..._blocks_missing_required_gate_status`): a snapshot without `factory/gates` blocks, naming it.
- Through the fixture, these unchanged tests are now red for the same reason (the gate still wants 25 per-gate contexts): `test_branch_protection_passes_on_expected_ruleset`, `..._passes_when_ruleset_includes_main` (×3), `..._passes_with_code_owner_review_once_identity_verified`, `..._compares_with_the_configured_actions_app_id`. Together they pin "no per-gate contexts required".
- The P9 unpinned and other-app tests now target `factory/gates`. They pass today because today's gate also lists the unpinned context; after the change they are the pinning check for `factory/gates`.

**Already covered, no new test** (a new test would be green on base, and `red-first-proof` rejects that):

- A `--gate` subset posts no summary: `test_gate_run_pr_posts_one_status_per_gate` asserts the exact set of posted contexts.
- A moved head posts nothing: `test_ci_trust_boundary.py::test_moved_head_posts_nothing_and_exits_0` asserts `statuses == []`.

## Red output (phase 1 head)

- Focused files: 14 failed, 76 passed.
  - The 5 contract tests fail on `expected one factory/gates status, got 0` (exit codes and the red-first judge pass first).
  - The 2 unit tests fail on `factory.gates.runner.summary_status(report, gates) is missing`.
  - The 7 snapshot tests fail on `blocked a clean change: required status checks miss factory/bus.schema, …`, or `message does not mention 'factory/gates'` for the replaced test.
- Full suite: 14 failed, 1041 passed, 7 xfailed. The base was 1048 passed and 7 xfailed. The only failures are those 14, and the 7 known strict xfails (T069/T081) are unchanged.
- `ruff check` and `ruff format --check` pass.

## Notes for phase 2 and the reviewer

- `test_branch_protection_passes_on_the_committed_snapshot` goes red after the gate change until `deploy/github/branch-protection.json` drops the 25 per-gate entries and adds `factory/gates` (phase 2, owned).
- `test_branch_protection_blocks_without_head_registry` is unchanged. The gate should keep failing closed when the head registry is missing, even though it no longer derives contexts from it.
- Edge cases the decision leaves open (not pinned):
  1. `--gate` listing every CI gate explicitly. The suggested reading is "summary only when `--gate` is absent".
  2. A crash while posting the per-gate statuses. The ordering test makes the summary last, so an exception before it leaves `factory/gates` absent.
  3. A rerun on the same SHA that crashes leaves an earlier `factory/gates` from older `main` code in place.
  4. A future gate with id `gates` would collide with the summary context. The registry could reject that id (`registry.py` is not owned here).
