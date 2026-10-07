# Handoff — `wo-20261007-factory-lifecycle-checks` (T105)

**Phase:** 1 of 2: red tests only, for T* review. No source edits.

**Branch:** `wo/wo-20261007-factory-lifecycle-checks` from `origin/main` `581ed18`. Order `b356c73`, revised before claim in `b1cf790` (drops `specs/001-factory-v2/tasks.md`; the first claim was refused for overlapping `wo-20261007-factory-app-token` on that path). Claim `183c57f`. Red tests `b85e504`.

**Decision pointers:** `bus/orders/wo-20261004-factory-slice-b/amendment-06.yaml` decision 2 (each consumer judges only its own `checks` kind); `specs/001-factory-v2/tasks.md` T105; `data-model.md` § WorkOrder (`checks`: "Gate ids or catalog row ids; each exists") and § Lifecycle (`accepted`); `contracts/gates.md` § Override resolution. Out of scope: T066a (required checks from branch protection).

**`tasks.md` is not owned:** T105 is not ticked. Completion is reported here (orchestrator instruction).

## What the tests pin

`derive_snapshot` with an accepting verdict and an open PR, keyed by the kind of each id in the order's `checks`:

- A **registered gate id** needs its own green `factory/<gate-id>` status on the PR head, or a failed status plus an override naming that gate. Unchanged behaviour.
- A **catalog row id** (a row in an `acceptance.md`; the demo row is `demo.adds`) is satisfied by `factory/catalog-test-linkage`: green, or failed and overridden for `catalog-test-linkage`. A `factory/<row-id>` status does not count, and neither does an override naming the row id.
- An id that is **neither** is never satisfied, even with a green `factory/<id>` status. The order stays `in_review`.

Any other outcome stays `in_review` (the existing state name).

## New tests (`scripts/factory/tests/unit/test_lifecycle.py`)

All of them use one helper, `derived_state(repo, checks, statuses, overrides)`. It asserts that the fixture ids are registered (or, for the row ids, not registered) in `load_registry()`, adds the demo feature (with its catalog) before issuing the order, then claims, hands off, opens the PR, posts statuses and overrides, accepts, and returns the derived state.

| Test | Pins |
|------|------|
| `test_catalog_row_is_satisfied_by_the_catalog_linkage_status` | a row is accepted with green `factory/catalog-test-linkage` and no `factory/demo.adds` |
| `test_catalog_row_needs_a_green_linkage_status_not_its_own[failure\|pending\|None]` | a green `factory/demo.adds` does not satisfy the row while linkage is failing, pending or missing |
| `test_catalog_row_counts_an_override_of_the_linkage_gate_only[linkage-overridden]` | a failed linkage plus a drift override of `catalog-test-linkage` is accepted |
| `test_catalog_row_counts_an_override_of_the_linkage_gate_only[row-id-overridden]` | an override naming `demo.adds` does not count, even over a failed `factory/demo.adds` |
| `test_an_id_that_is_neither_a_gate_nor_a_catalog_row_fails_closed` | `demo.adds-typo` with green `factory/demo.adds-typo` and green linkage stays `in_review` |

**Already covered, no new test.** The gate-id cases (green, failed, pending, missing, counted override, override of another gate, unrelated run pending) are `CHECK_CASES` in `test_accepted_needs_verdict_and_full_required_check_set`. Today's code already implements them, so a duplicate would be green on base, and `red-first-proof` rejects that. They stay as the regression guard for phase 2.

## Red output (head `b85e504`)

- `test_lifecycle.py`: 7 failed, 21 passed. Each failure is the state assertion:
  - The positive row case and `linkage-overridden` fail on "got in_review": today the code looks for `factory/demo.adds`.
  - The three linkage-state cases, `row-id-overridden` and the unknown-id case fail on "got accepted": today any green or overridden `factory/<id>` counts.
- Full suite: 7 failed, 1056 passed, 7 xfailed. The base was 1056 passed, 7 xfailed. The only failures are those 7, and the 7 known strict xfails (T069/T081) are unchanged.
- `ruff check` and `ruff format --check` pass.

## Notes for the reviewer and phase 2

- **Unknown ids fail closed by contract, not by worker pin.** `data-model.md` says each id exists, and amendment-06 says an id that is neither "blocks". The test applies that rule to lifecycle.
- **`row-id-overridden` posts a stray `factory/demo.adds` failure.** The trusted job never posts a status for a row. Without the stray status the case would be green on base, so it would not be red.
- Edge cases left open (not pinned):
  1. **An id that is both a registered gate and a catalog row.** The linkage gate classifies rows first (amendment-08, `test_a_catalog_row_sharing_a_gate_id_is_still_judged`). Should lifecycle need only linkage, or linkage plus `factory/<id>`? This needs an orchestrator ruling.
  2. **Which tree lifecycle reads catalog rows from:** the order branch / PR head, or `main`. The fixture has the row on both. The linkage gate reads the head.
  3. **Which registry lifecycle classifies gate ids against:** the installed (`main`'s) registry under D5, or the head's `gates.yaml`. The fixture ids are in both.
  4. **A gate-id status failing beside a green linkage status in a mixed list.** This guards against linkage vouching for gate ids. It cannot be red on base (today's code already keeps it `in_review`), so it is not pinned. `CHECK_CASES` never sets a linkage status.
  5. **A governor-only override by a non-governor.** The `Override` model rejects it at parse, so lifecycle never sees one. No lifecycle test.

## Round 1 resolution (T* `TEST_REVIEW_LIFECYCLE_CHECKS.md`, rejected; orchestrator triage + amendment-01)

Edge cases 1–4 above are now ruled by amendment-01 (1: catalog row first; 2: installed registry; 3: PR-head catalog) and pinned. Only `test_lifecycle.py` changed; there are no source edits.

| Finding | Resolution | Test |
|---------|------------|------|
| T-LC1 (Blocker): precedence and source boundaries were unobservable | One classification matrix, four orders in one fixture repo, one snapshot, a whole-map state assertion:<br>• `collision`: `pr-links-order` (an installed gate) added as a row on the head only, green linkage, no own status → `accepted`.<br>• `head-only-gate`: `head-only-gate` added only to the head's `scripts/factory/gates.yaml`, with a green own status and green linkage → `in_review`.<br>• `head-only-row`: `demo.head-only` added only to the head's `acceptance.md`, green linkage → `accepted`.<br>• `gate-without-own-status`: see T-LC2. | `test_check_kinds_follow_the_installed_registry_and_the_head_catalog` |
| T-LC2 (Debate, process): linkage might vouch for a registered gate | Folded in as the matrix's fourth row: `test-seam-ban` has no own status, linkage is green → `in_review`. | same |
| T-LC3, T-LC4 (Nit, strength) | Kept unchanged | — |

**Fixture helpers.**
- `accept_order(..., head_files=...)` is the body of `derived_state`, extracted. It commits `head_files` on the work branch only, after the order commit and before the PR head is recorded. `derived_state` and the existing round 0 tests behave as before.
- `head_registry_with` appends one drift gate to the planted `gates.yaml`. The test checks that the result parses with `load_registry`.
- `head_catalog_with` appends one row to `DEMO_ACCEPTANCE`.
- The guards assert that the installed registry has `pr-links-order`, `catalog-test-linkage` and the two required gates, and has neither head-only id.

**Red output (round 1):**
- The matrix fails on the state assertion, with exactly three differing items: `collision` in_review≠accepted, `head-only-gate` accepted≠in_review, `head-only-row` in_review≠accepted. `gate-without-own-status` already matches today, as the triage expected.
- `test_lifecycle.py`: 8 failed, 21 passed.
- Full suite: 8 failed, 1056 passed, 7 xfailed. The only failures are the 7 round 0 nodes plus the matrix, and the 7 known strict xfails (T069/T081) are unchanged.
- `ruff check` and `ruff format --check` pass.
