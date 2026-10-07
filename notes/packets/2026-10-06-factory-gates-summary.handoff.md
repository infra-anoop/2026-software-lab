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

`scripts/factory/tests/unit/gates/test_runner.py` (round 0 only) pinned a helper, `summary_status(report, gates)`. It was **deleted in round 1** (T-GS3), and its two cases moved to the CLI level (§ Round 1 resolution).

`scripts/factory/tests/unit/gates/test_registry_checks.py`:

- The shared `required_contexts()` fixture is now the target ruleset: `Factory tests`, `Verify Source / verify`, `factory/gates`, all pinned. `UNPINNED` is now `factory/gates`.
- `test_branch_protection_blocks_without_the_gates_summary_status` (replaces `..._blocks_missing_required_gate_status`): a snapshot without `factory/gates` blocks, naming it.
- Through the fixture, these unchanged tests are now red for the same reason (the gate still wants 25 per-gate contexts): `test_branch_protection_passes_on_expected_ruleset`, `..._passes_when_ruleset_includes_main` (×3), `..._passes_with_code_owner_review_once_identity_verified`, `..._compares_with_the_configured_actions_app_id`. Together they pin "no per-gate contexts required".
- The P9 unpinned and other-app tests now target `factory/gates`. They pass today because today's gate also lists the unpinned context; after the change they are the pinning check for `factory/gates`.

**Already covered, no new test** (a new test would be green on base, and `red-first-proof` rejects that):

- A two-gate `--gate` subset posts no summary: `test_gate_run_pr_posts_one_status_per_gate` asserts the exact set of posted contexts. The full explicit list is pinned in round 1 (T-GS1).
- A moved head posts nothing: `test_ci_trust_boundary.py::test_moved_head_posts_nothing_and_exits_0` asserts `statuses == []`.

## Red output (round 0 head `ba78e9a`; round 1 numbers in § Round 1 resolution)

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
  1. ~~`--gate` listing every CI gate explicitly~~. Ruled by the orchestrator in round 1: any `--gate` use is a subset run (pinned, T-GS1).
  2. A crash while posting the per-gate statuses. The ordering test makes the summary last, so an exception before it leaves `factory/gates` absent.
  3. A rerun on the same SHA that crashes leaves an earlier `factory/gates` from older `main` code in place.
  4. A future gate with id `gates` would collide with the summary context. The registry could reject that id (`registry.py` is not owned here).

## Round 1 resolution (T* `TEST_REVIEW_GATES_SUMMARY.md`, changes-needed)

All three changes are in `scripts/factory/tests/contract/test_gate_run.py`, except the deletion. Source, snapshot JSON and contracts are untouched.

| Finding | Resolution | Test |
|---------|------------|------|
| T-GS1 (Blocker): an explicit full `--gate` list was untested | Orchestrator ruling: any `--gate` use is a subset run. The test first runs the trusted command with no `--gate` and requires a `success` summary. That half is what makes it red today and gives the second half meaning. It then clears the statuses and passes `--gate` once for every installed CI gate: exactly the per-gate contexts, no `factory/gates`. | `test_gate_run_pr_explicit_gate_list_posts_no_summary_even_when_it_names_every_gate` |
| T-GS2 (Blocker): the missing-gate oracle bypassed the CLI | The test goes through the real CLI posting path. It wraps the real `run_gates` and drops `bus.schema` from the returned report, patched on both `factory.gates.runner.run_gates` and the name the CLI imports, `factory.cli.gates.run_gates`. The posted `factory/gates` must be `failure` naming `bus.schema`. The test also checks that the seam bit: no `factory/bus.schema` status was posted. | `test_gate_run_pr_gates_summary_fails_when_the_report_omits_an_installed_gate` |
| T-GS3 (Should): exact-symbol helper over-specified | `tests/unit/gates/test_runner.py` is deleted. Its description-limit case moved to the CLI level: every stubbed gate fails, and the posted summary is at most 140 characters and names at least one failing gate. | `test_gate_run_pr_gates_summary_description_fits_the_status_limit` |
| T-GS4 (Nit, strength) | Controls kept | — |

**The T-GS2 seam is allowed by `test-seam-ban`.** That gate only scans added non-test code under `app_roots` (`apps/`) for test-only branches. A pytest `monkeypatch` in a test file is outside its scope. The seam binds only to the existing `run_gates` name the CLI already imports. An implementation that computes the summary from anything other than the returned report, for example the selected gate list, fails this test.

**Red-first expectations.** All 8 new or changed summary tests are red today on a real assertion (`expected one factory/gates status, got 0`), including the T-GS1 case, because of its first half. No test is green on base.

**Round 1 red output:**
- Focused files: 15 failed (8 contract, 7 snapshot).
- Full suite: 15 failed, 1041 passed, 7 xfailed (the known T069/T081 strict xfails). The only failures are those 15.
- `ruff check` and `ruff format --check` pass.

## Implementation (phase 2)

T* round 2 accepted (`TEST_REVIEW_GATES_SUMMARY.md` § Round 2, cherry-picked as `5f8851d`'s content). Commits: `4becd75` (implementation and snapshot), `3015313` (orchestrator amendment-01: this order owns `test_ci_trust_boundary.py`), `7a93957` (that test, contracts, T107 tick).

**What changed:**
- `gates/runner.py`: adds `SUMMARY_CONTEXT = "factory/gates"` and `summary_status(report, gates)`.
  - A gate fails the summary when it is missing from the report, or when its outcome is neither `pass` nor `overridden`.
  - The description reads "N failed: …; M did not run: …", cut to 140 characters. The per-gate truncation is shared through `_fit`.
- `cli/gates.py`: a `--pr` run with no `--gate` posts `factory/gates` last.
  - It builds the summary from the report it just posted, checked against the installed registry's CI gates.
  - A failing summary also exits 1 (`GATE_FAILURE`), including when the report omits a gate but no gate failed. The orchestrator accepted this.
  - A moved head still returns before anything is posted.
- `gates/repo/branch_protection.py`: requires `[factory/gates]` instead of the per-P1 contexts. It still fails closed on an unreadable head registry. Docstring amended.
- `deploy/github/branch-protection.json`: the required checks are exactly `Factory tests`, `Verify Source / verify` and `factory/gates`, all 15368. Nothing else changed.
- `tests/contract/test_ci_trust_boundary.py::test_ci_mode_runs_main_registry_whatever_the_head_registry_says` (amendment-01): the full-run status set gains `factory/gates`, and that status must be `failure` (`bus.immutable` fails in that scenario).
- `contracts/gates.md`: four places amended, worded "Amended 2026-10-06 (governor, `PLAN_DELTA.md` Round 5)": the intro sentence (plus the `factory-gates.yml` reports cell), the Status source paragraph, Bootstrap step 3, and the `branch-protection-require-pr` row. `acceptance.md` is unchanged, since no row cites the per-gate contexts.
- `tasks.md`: T107 ticked, with a Done note.

**Suite:** 1056 passed, 7 xfailed (the known T069/T081 strict xfails). `ruff check` and `ruff format --check` pass.

**Local gates** (`factory gate run --base origin/main --head HEAD` at `7a93957`): 22 passed, 3 failed, 0 overridden. No overrides were written. All three failures are missing bus messages, not code problems:
- `spawn-concurrency-cap`: "order wo-20261006-factory-gates-summary has no claim at head; run `factory claim wo-20261006-factory-gates-summary`".
- `verdict.reviewer-family-differs`: "order wo-20261006-factory-gates-summary has no verdict at head (not reviewed)".
- `verdict.inputs-isolated`: "order wo-20261006-factory-gates-summary has no verdict at head (not reviewed)".
