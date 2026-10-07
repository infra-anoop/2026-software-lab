# Handoff — `wo-20261007-factory-per-intent` (T064, catalog `handoff.per_intent_results`)

**Phase:** 1 of 2: red tests only. T* round 1 rejected; the round 1 fixes are in (§ Round 1 resolution), awaiting T* round 2. No `src` change.

**Branch:** `wo/wo-20261007-factory-per-intent`. Claim `024b778` (after the orchestrator dropped `tasks.md` from owned paths in `54bd08b`). Red tests `2d50e4d`. `tasks.md` is not ticked (not owned); T064 completion is reported here.

## Proposed contract (for T* review)

Today the report already has a flat `intents: {<intent id>: [{gate, outcome}]}`, and the text prints one `  <intent>: <gate> <outcome>` line per (intent, gate) pair. Neither says whether an intent held or broke. The tests pin an **additive** shape; the existing `intents` key and its tests are unchanged:

- **JSON** (`data` on exit 0, `error.details` on exit 1): `per_intent: {<intent id>: {result, gates: [{gate, outcome}]}}`. It covers every intent id that a reported gate serves through its `gates.yaml` row, with each gate serving it and that gate's `pass` / `fail` / `overridden` outcome.
- **`result`:** `broken` if any serving gate failed, else `overridden` if any was overridden, else `held`.
- **Text:** under `per intent:`, exactly **one line per intent id**. The line carries the result word and `<gate> <outcome>` for each serving gate. The order of words on the line is not pinned.
- **Statuses:** `--pr` posts the same `factory/<gate-id>` and `factory/gates` statuses (context, state, description, order) as before.

## Tests (`scripts/factory/tests/contract/test_gate_run.py`)

| Test | Pins |
|------|------|
| `test_gate_run_json_per_intent_marks_every_intent_of_a_failing_gate_broken` | `catalog-test-linkage` and `diff-within-owned-paths` fail. `per_intent` equals the registry-derived grouping. I-B7 is broken even though `red-first-proof` passes. I-P2 (served only by `red-first-proof`) is held. The two-intent failing gate is listed as `fail` under both I-B8 and I-A8, and both are broken. |
| `test_gate_run_json_per_intent_result_follows_the_worst_gate[override-only, override-and-failure]` | With `bus.immutable` overridden, I-M2 is `overridden`. If a sibling I-M2 gate (`bus.schema`) also fails, I-M2 is `broken`. In both cases the gate shows as `overridden`. |
| `test_gate_run_text_prints_one_line_per_intent_with_its_result` | Text mode, with one failure and one override: one line per intent, each with its result word and every `<gate> <outcome>`. Anchors: I-B7 broken, I-P2 held, I-M2 overridden. |
| `test_gate_run_pr_report_carries_per_intent_and_posts_unchanged_statuses` | Trusted `--pr` run (the CI job). The exact status sequence is pinned to current behaviour, and that part is **green on base**. Then `per_intent` must be present and correct. |

Every test drives real gate outcomes through the existing `RecordedGates` stubs and real override files. No new fixture and no test seam.

## Red (at `2d50e4d`)

- Focused: 5 of 5 new cases fail on assertions. The four JSON-shaped ones fail with "report has no per_intent mapping". The text one fails with "I-M2: expected one line, got [3 lines]".
- The `--pr` test fails only after its status assertions pass.
- **Full suite:** 5 failed (only these), 1056 passed, 7 xfailed (the known T069/T081 strict xfails).
- `ruff check` and `ruff format --check` pass.
- **Satisfiability probe:** a throwaway pytest plugin in `/tmp` (not committed, now deleted) patched in an implementation that uses `group_by_intent()`. All 5 cases went green with no other failure in the file. The one exception was an artifact of the probe patching `cli_gates.run_gates`.

## Edge cases and open questions (not pinned)

1. **Which intent ids does `group_by_intent()` use?** It prefers a result's own `intent_ids` over the registry row. `factory-check-intent` sets `intent_ids` to the *unmapped* intents when it fails. Passing raw results would therefore list that failure under the unmapped ids instead of I-N1/I-P4. The tests use stubs whose `intent_ids` equal the registry row, so either reading passes. The implementer should pick one and say so in the handoff; the reviewer may want it pinned.
2. **Overridden wording.** An intent held only by an override shows as `overridden`, not `held`. This is a product word choice for the governor.
3. **Subset runs (`--gate`).** Only the selected gates' intents appear. Not separately pinned.
4. **GitHub job summary.** The order's `goal` says "and the CI job summary". The trusted workflow writes only `factory status` to `$GITHUB_STEP_SUMMARY`; `gate run` text lands in the job log. A per-intent job summary needs a workflow edit, which this order forbids (stop condition). Open question for the orchestrator: does the catalog row (`Results reported per intent id`, when "PR linked to a work order") count as met by the run report in the job log? Or does it need a separate workflow order?
5. **Catalog evidence.** `handoff.per_intent_results` stays `planned` until phase 2. After implement it names the four tests above, plus the two added in round 1.

Items 1 and 3 are now pinned (round 1, below). Item 2 is locked by amendment-01. Item 4 is settled by amendment-01: scope is the run report.

## Round 1 resolution

These are the three changes from the orchestrator's triage in `TEST_REVIEW_PER_INTENT.md` § Triage. Only `scripts/factory/tests/contract/test_gate_run.py` changed. T-PI4 (strength) is kept unchanged.

| Finding | Test | What it pins |
|---------|------|--------------|
| T-PI1 (Blocker) | new `test_gate_run_json_per_intent_uses_registry_rows_not_result_intent_ids` | `RecordedGates` takes an optional `intent_ids` override. The `factory-check-intent` stub fails and returns `intent_ids=["I-SENTINEL-NOT-IN-REGISTRY"]`. The sentinel never appears as a `per_intent` key. The gate is listed, as `fail`, under exactly its `gates.yaml` row's intents (expected ids come from `load_registry().get(...)`), and each of those intents is `broken`. A grouping that passes raw results to `group_by_intent()` fails here. |
| T-PI2 (locked: subset runs carry `per_intent`) | new `test_gate_run_json_per_intent_of_a_subset_run_covers_only_the_selected_gate` | `--gate diff-within-owned-paths`, failing: `per_intent` equals exactly that gate's registry intents (I-B8, I-A8), each `{broken, [(gate, fail)]}`, and has no other rows. |
| T-PI3 (locked: legacy `intents` unchanged) | changed `test_gate_run_json_per_intent_marks_every_intent_of_a_failing_gate_broken` | Before the `per_intent` checks, the complete legacy `intents` mapping must equal the registry-derived oracle. This part passes on base, so it guards existing behaviour. After them, legacy `intents` must equal the flattened `per_intent[*].gates`. |

**Red (round 1 head):**
- Focused file: 7 failed, 32 passed.
- Six of the seven fail on "report has no per_intent mapping". The text test still fails on "I-M2: expected one line, got [3 lines]".
- In the changed broad test, the legacy-mapping assertion runs first and passes; the test then goes red at `per_intent`.
- **Full suite:** 7 failed (only these), 1056 passed, 7 xfailed (known T069/T081). `ruff check` and `ruff format --check` pass.
- **Satisfiability probe** (throwaway `/tmp` plugin, deleted): the probe passes fresh registry-only results to `group_by_intent()`. With it, all 39 cases in the file pass.
