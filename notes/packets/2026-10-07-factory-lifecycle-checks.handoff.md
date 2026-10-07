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
