# Acceptance catalog — 001-factory-v2

Extensible checks for [`spec.md`](./spec.md) Success Criteria. Grow from runs; do not bury in scripts or prompts.

**Evidence lifecycle (FR-018):** every `auto` row carries `evidence`. The sentinel `planned` is allowed until the work order that implements the row; that work order's PR must not merge until `evidence` names an existing test or eval id.

| Field | Meaning |
|-------|---------|
| id | Stable id |
| class | SC-* in spec |
| intents | `intent.yaml` ids served |
| severity | `must` \| `should` \| `aspirational` |
| when | Preconditions |
| shall | Failable statement |
| how | `auto` \| `human` \| `hybrid` |
| evidence | Test/eval id, or `planned` (see lifecycle), or `n/a` for `human` |

## Checks

| id | class | intents | severity | when | shall | how | evidence |
|----|-------|---------|----------|------|-------|-----|----------|
| branch.no_direct_main | SC-003 | I-P10 | must | any actor, including the main session | Commit on `main` / push to `main` refused by the editor hook; GitHub requires a PR with no bypass; snapshot matches | auto | planned |
| board.matches_reality | SC-001 | I-M4 | must | work orders in each lifecycle state | Board state equals state derived from branch/PR/checks for every order | auto | `scripts/factory/tests/contract/test_status.py::test_status_json_sections_match_each_lifecycle_state`; `scripts/factory/tests/unit/test_lifecycle.py` |
| bus.no_handwritten_status | SC-001 | I-M2 | must | any bus message | Schema rejects hand-maintained status fields | auto | `scripts/factory/tests/unit/test_bus_models.py::test_forbidden_key_at_top_level`; `scripts/factory/tests/contract/test_status.py::test_status_json_sections_match_each_lifecycle_state` |
| seed.substitution_undeclared | SC-002 | I-B5 | must | work order touches a named lock without fidelity declaration | Issuing is refused | auto | `scripts/factory/tests/contract/test_orders.py::test_order_new_refuses_touched_named_lock_without_fidelity` |
| seed.substitution_declared | SC-002 | I-B5 | must | work order declares a letter lock; output uses a different tool/host/thinner behavior | PR blocked | auto | planned |
| seed.hidden_deferral | SC-002 | I-B6 | must | spec/plan/tasks parks required work without OD reference | PR blocked | auto | planned |
| seed.not_red_first | SC-002 | I-B7, I-P2 | must | new tests already pass on base | PR blocked | auto | planned |
| seed.code_before_test_review | SC-002 | I-B7, I-P3 | must | work branch changes non-test owned code before a test-review `accept` verdict is on the branch | PR blocked (FR-012b; Wave 2) | auto | planned |
| seed.test_seam | SC-002 | I-A8 | must | app code adds test-only branching | PR blocked | auto | planned |
| seed.outside_owned_paths | SC-002 | I-B8 | must | diff touches a path not owned by the order | PR blocked | auto | planned |
| seed.jargon_to_governor | SC-002 | I-B3 | must | decision request contains task/finding ids or internal jargon | Rejected before it reaches the governor | auto | planned |
| seed.catalog_unlinked | SC-002 | I-B7 | must | `auto` row reaches its implementing PR still `planned` | PR blocked | auto | planned |
| handoff.per_intent_results | SC-003 | I-G2, I-P4 | must | PR linked to a work order | Results reported per intent id | auto | planned |
| handoff.reviewer_family | SC-003 | I-P3 | must | verdict on a PR | Reviewer family ≠ author family | auto | `scripts/factory/tests/contract/test_pr_and_verdict.py::test_verdict_refuses_same_family_reviewer` |
| handoff.reviewer_isolated | SC-003 | I-P3 | must | reviewer spawned | Inputs are git artifacts only; verdict records inputs; no conversation/narrative refs | hybrid | machine half: `scripts/factory/tests/contract/test_pr_and_verdict.py::test_verdict_refuses_input_that_is_not_a_git_path`; `scripts/factory/tests/contract/test_pr_and_verdict.py::test_verdict_refuses_input_absent_from_git` |
| handoff.open_od_refused | SC-003 | I-X3 | must | order depends on open governor decision | Issuing refused | auto | `scripts/factory/tests/contract/test_orders.py::test_order_issue_refuses_open_human_decision_in_plain_language`; `scripts/factory/tests/contract/test_claim.py::test_claim_refuses_blocked_on_governor` |
| handoff.done_requires_green | SC-003 | I-G2 | must | worker checks failing | Worker cannot report done | auto | `scripts/factory/tests/contract/test_handoff.py::test_handoff_requires_deviations_key`; `scripts/factory/tests/contract/test_handoff.py::test_handoff_blocker_governor_exits_2_and_waits_on_board`; gate half: `scripts/factory/tests/contract/test_cli_contract.py::test_handoff_refuses_while_a_gate_fails` (needs slice B `diff-within-owned-paths`) |
| handoff.concurrency_cap | SC-003 | I-X4 | must | 3 active workers | 4th claim refused; PR without valid claim cannot merge; editor launch logged (advisory) | auto | claim half: `scripts/factory/tests/contract/test_claim.py::test_claim_refuses_at_active_cap_of_three`; `scripts/factory/tests/contract/test_claim.py::test_stale_claim_still_counts_toward_cap`; `scripts/factory/tests/contract/test_claim.py::test_claim_fast_forward_exactly_one_of_two_concurrent_wins`; `scripts/factory/tests/contract/test_claim.py::test_closed_unmerged_pr_frees_capacity`; `scripts/factory/tests/contract/test_claim.py::test_open_pr_still_holds_a_slot`; `scripts/factory/tests/contract/test_claim.py::test_lost_claim_race_at_the_push_is_refused`; `scripts/factory/tests/contract/test_claim.py::test_identical_same_second_claims_have_one_winner` (PR-merge and editor halves: slice C) |
| override.reason_required | SC-004 | I-M1 | must | override without reason | Rejected | auto | planned |
| override.surfaced_counted | SC-004 | I-M1 | must | override with reason | Appears on board and per-gate count | auto | planned |
| gate.fail_mode_category | SC-004 | I-P9 | must | gate registered | Class is `drift` or `governor-only`; governor-only only for spend/secrets/irreversible/governor decisions | auto | planned |
| override.governor_only | SC-004 | I-P9 | must | orchestrator/worker overrides a governor-only gate | Rejected | auto | planned |
| gate.hook_has_twin | SC-004 | I-G5 | must | editor hook registered | Repository-side equivalent exists | auto | planned |
| trace.presence | SC-005 | I-P4 | must | intent file | Removing all mappings from any intent fails | auto | planned |
| trace.effective_coverage | SC-005 | I-N1, I-P4 | must | sprint close | ≥ 90% of intents backed by implemented passing non-human check or governor-judged | auto | planned |
| rules.cite_checks | SC-006 | I-P6 | must | governed process documents | Every MUST/NEVER carries `[check: <id>]` or `[governor-judged]` | auto | planned |
| constitution.c1_shared_code | SC-006 | I-A5 | must | constitution 2.0 | States designed-for-reuse rule with declared consumers | hybrid | planned |
| constitution.c2_ambiguity_split | SC-006 | I-B1 | must | constitution 2.0 | States split-by-owner ambiguity rule | hybrid | planned |
| constitution.c3_narrow_fail_closed | SC-006 | I-P9 | must | constitution 2.0 | States the locked fail-mode taxonomy | hybrid | planned |
| constitution.c4_repeat_corrections | SC-006 | I-P7 | must | constitution 2.0 | States repeat-correction immediate proposal | hybrid | planned |
| constitution.invariants_preserved | SC-006 | I-B5, I-O1, I-O2 | must | constitution 2.0 diff | Every still-unenforceable invariant survives as rule or pointer; independent verdict confirms no thinning | hybrid | planned |
| mining.correction_recorded | SC-007 | I-P7 | must | governor correction | Correction record exists | hybrid | planned |
| mining.repeat_proposes | SC-007 | I-P7 | must | orchestrator links a new correction to a pattern or prior correction | Rule/check proposal raised; link appears in next governor batch; rejected link withdraws proposal | auto | planned |
| mining.postmortem_gate | SC-007 | I-P8 | must | sprint close attempted | Requires post-mortem dispositioning all corrections | auto | planned |
| history.no_bookkeeping | SC-008 | I-M2 | must | commits after Wave 1 | Zero status/SHA-only commits to bus files | auto | `scripts/factory/tests/unit/test_no_bookkeeping.py::test_status_only_bus_rewrite_is_counted`; `scripts/factory/tests/unit/test_no_bookkeeping.py::test_event_append_is_not_bookkeeping` |
| scorecard.computed | SC-009 | I-G1, I-G2, I-G3 | must | sprint close | Scorecard computed from run records for every order | auto | `scripts/factory/tests/unit/test_scorecard.py::test_scorecard_computes_intent_yaml_metrics`; `scripts/factory/tests/unit/test_scorecard.py::test_scorecard_includes_fr035_run_totals` |
| routing.zero | SC-010 | I-B4 | must | sprint close | Zero routing corrections | hybrid | planned |
| capture.budget | SC-011 | I-M2 | must | each feature | Governor intent-capture minutes recorded; ≤ ~60 | hybrid | planned |
| wave1.timebox | SC-013 | I-M3 | must | Wave 1 exit | Exit ≤ 5 working days from first order with all P1 checks passing; dates from run records | auto | `scripts/factory/tests/unit/test_scorecard.py::test_scorecard_wave1_exit_when_every_order_merged`; `scripts/factory/tests/unit/test_scorecard.py::test_scorecard_wave1_not_exited_unless_every_p1_gate_implemented_and_green`; `scripts/factory/tests/unit/test_scorecard.py::test_scorecard_wave1_not_exited_until_every_order_has_run_record_and_acceptance`; `scripts/factory/tests/unit/test_scorecard.py::test_scorecard_cli_wave1_exit_after_rework_accepted`; `scripts/factory/tests/unit/test_scorecard.py::test_scorecard_wave1_exit_survives_later_orders`; `scripts/factory/tests/unit/test_scorecard.py::test_scorecard_sprint_scopes_wave1` |
| bootstrap.verdicts | SC-012 | I-G1, I-M1 | must | each Wave 1 PR | Bootstrap verdict + retroactive gate results; failures remediated/overridden before Wave 2 orders | auto | planned |
| scorecard.targets | aspirational | I-G1, I-G2 | aspirational | sprint close | Drift ≥ 95%, first-pass ≥ 75% | human | n/a |
| arch.patterns_flagged | — (US6) | I-A1..I-A8 | should | seeded pattern violations | Each mechanical pattern violation flagged | auto | planned |
| arch.reviewer_cites_catalog | — (US6) | I-A11 | should | any reviewed PR | Findings cite pattern ids | hybrid | planned |

## Change log

| Date | Change |
|------|--------|
| 2026-10-03 | Bootstrap from spec SC-001..009 + US6 seeded fixtures |
| 2026-10-03 | Review triage: `evidence` column + lifecycle (F10/R5); presence vs effective coverage (R2); reviewer isolation (F3); routing, capture budget (F4); constitution rows (R3); bootstrap (R4); declared-substitution seed (F5) |
| 2026-10-03 | Governor correction: branch + PR for every change, main session included (I-P10, FR-005a) — row `branch.no_direct_main` |
| 2026-10-03 | Plan review locks: claim-level cap (FR-008 waive), git leases, App identity, assertion red-first |
| 2026-10-03 | Governor locks: two-class gates (F1/R1), cap 3 (F2), all seeds block (F5), Wave 1 exits on P1 (F6/R6), orchestrator-linked repeats (F7) |
| 2026-10-04 | Governor: enforce "tests reviewed before code" in Wave 2 (FR-012b) — row `seed.code_before_test_review` |
