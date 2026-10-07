# Test review — per-intent gate results

## A. Executive verdict

**Do not implement against these tests yet.** Round 1 rejects because the fixtures copy each gate registry row into `GateResult.intent_ids`, so an implementation can use result-supplied ids and still pass despite amendment-01 requiring the `gates.yaml` row to be authoritative. The five new cases are honestly red for missing report behavior, and the PR case strongly pins the existing status sequence. One narrow fixture change and regression is sufficient to clear the blocker.

## B. Findings

| ID | Severity | Lens | Locus | Finding | Suggested resolution |
|----|----------|------|-------|---------|----------------------|
| T-PI1 | Blocker | Lock fidelity | `RecordedGates`, amendment-01 ruling 2 | **product. Root-cause class:** the test fixture makes `GateResult.intent_ids` identical to each registry row, so the two candidate sources are observationally indistinguishable. **Consequence:** an implementation can call `group_by_intent(results, registry)`, which prefers result-supplied ids, and report `factory-check-intent` under unmapped ids instead of I-N1/I-P4; the governor then sees the wrong intent as held or broken. **Likelihood:** high because the existing helper already has exactly that preference and the handoff identifies it as the open edge. **Smallest sufficient fix:** make one stub return a conflicting sentinel `intent_ids` list and assert the sentinel is absent while every registry-row intent is present with that gate's outcome. | Add one CLI-level JSON regression with deliberately conflicting result ids; derive the expected ids only from `load_registry().get(gate_id).intents`. |
| T-PI2 | Debate | Scope | `test_gate_run_json_per_intent_*`; handoff edge 3 | **product.** Every new assertion uses a full registry run. A passing implementation may special-case full runs while a supported `--gate` run emits unrelated intents, omits the selected gate's registry intents, or derives from result ids. The CLI contract supports subset runs, but amendment-01 does not explicitly state whether the richer per-intent section is guaranteed there. | Lock one choice: preferably add a one-gate test requiring exactly that reported gate's registry intents and no unrelated rows; otherwise state that the richer section is full-run-only. |
| T-PI3 | Debate | Backward compatibility | top-level `intents` report field | **product.** The packet calls the new shape additive and says the existing `intents` key is unchanged, but the new tests never pin the complete legacy mapping. An implementation can add correct `per_intent` while dropping or corrupting legacy rows other than the single old I-M2 assertion. | In the broad JSON case, assert legacy `intents` equals the flattened `per_intent[*].gates` mapping for every registry-derived intent, or explicitly retire the legacy key in the contract. |
| T-PI4 | Nit | Strength | `test_gate_run_pr_report_carries_per_intent_and_posts_unchanged_statuses` | **process. Strength:** the PR regression asserts every status's SHA, context, state, description, and posting order before checking the new report. It therefore protects the stated unchanged-status boundary and fails only afterward on the missing `per_intent` field. | Keep this regression unchanged. |

## C. Adversarial positions

1. **Position: these tests would go green while a spec lock fails.** Return registry ids from the ordinary stubs, implement grouping through `group_by_intent(results, registry)`, and the suite passes. In production, `factory-check-intent` can return unmapped ids in `GateResult.intent_ids`; the helper prefers those ids, directly violating the amendment's registry-row ruling. **What would have to be true for the suite to be right anyway:** every gate result would need a permanent invariant that its `intent_ids` exactly equal its registry row, but no such contract exists and the named gate intentionally violates it.

2. **Position: these tests over-constrain implementation / test the wrong layer.** The tests freeze a second nested JSON key named `per_intent` even though `contracts/cli.md` promises only “prints per-intent results” and the existing report already has `intents`. This rejects a compatible enrichment of the existing field. **What would have to be true for the suite to be right anyway:** the handoff's proposed additive JSON shape must be treated as the accepted command contract for this order.

## D. Catalog / contract coverage map

| Catalog id or contract hook | Test file / name | Can fail today? | Gap |
|-----------------------------|------------------|-----------------|-----|
| `handoff.per_intent_results` / FR-024 | `test_gate_run_json_per_intent_marks_every_intent_of_a_failing_gate_broken` | yes | Cannot distinguish registry ids from result-supplied ids. |
| amendment-01 “registry row serves” | same JSON test | yes | Fixture duplicates both sources; forbidden source still passes. |
| amendment-01 “overridden, never held” | `test_gate_run_json_per_intent_result_follows_the_worst_gate` | yes | Covered for override-only and override-plus-failure. |
| text report, one row per intent | `test_gate_run_text_prints_one_line_per_intent_with_its_result` | yes | Full run only; subset behavior is not locked. |
| unchanged PR statuses | `test_gate_run_pr_report_carries_per_intent_and_posts_unchanged_statuses` | yes | SHA, context, state, description, and order are pinned. |
| additive legacy `intents` field | existing `test_gate_run_reports_results_per_intent` | yes | Only one I-M2 membership is pinned, not the complete mapping. |

## E. Edit list

- `scripts/factory/tests/contract/test_gate_run.py`: let one `RecordedGates` entrypoint emit a conflicting sentinel `intent_ids`.
- `scripts/factory/tests/contract/test_gate_run.py`: assert that sentinel never appears and registry-row ids do.
- `scripts/factory/tests/contract/test_gate_run.py`: add one explicit `--gate` case after the product scope is locked.
- `scripts/factory/tests/contract/test_gate_run.py`: pin the complete legacy `intents` mapping or explicitly retire it.

## F. Questions for the human

1. Should explicit `--gate` subset runs carry the same richer per-intent section, limited to the selected reported gates?
2. Is the existing top-level `intents` field a compatibility contract that must remain complete, or may this order replace it with `per_intent`?

## Review evidence

- Reviewed commit: `0879802`.
- Focused command: `nix develop /workspaces/2026-software-lab -c bash -c 'cd scripts/factory && uv run --locked pytest -q tests/contract/test_gate_run.py'`.
- Result: 5 failed, 32 passed. All five failures are assertions at the intended missing behavior; there were no collection or fixture errors.
