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
| branch.no_direct_main | SC-003 | I-P10 | must | any actor, including the main session | Commit on `main` / push to `main` refused by the editor hook; GitHub requires a PR with no bypass; snapshot matches | auto | hook half: `scripts/factory/tests/unit/hooks/test_hooks.py::test_shell_guard_denies_direct_main_writes_on_main`, `scripts/factory/tests/unit/hooks/test_hooks.py::test_shell_guard_denies_on_work_branch`; GitHub half: `scripts/factory/tests/unit/gates/test_registry_checks.py::test_branch_protection_blocks_when_pr_not_required`, `scripts/factory/tests/unit/gates/test_registry_checks.py::test_branch_protection_blocks_admin_bypass`, `scripts/factory/tests/unit/gates/test_registry_checks.py::test_branch_protection_blocks_bypass_allowance` |
| board.matches_reality | SC-001 | I-M4 | must | work orders in each lifecycle state | Board state equals state derived from branch/PR/checks for every order | auto | planned |
| bus.no_handwritten_status | SC-001 | I-M2 | must | any bus message | Schema rejects hand-maintained status fields | auto | planned |
| seed.substitution_undeclared | SC-002 | I-B5 | must | work order touches a named lock without fidelity declaration | Issuing is refused | auto | planned |
| seed.substitution_declared | SC-002 | I-B5 | must | work order declares a letter lock; output uses a different tool/host/thinner behavior | PR blocked | auto | planned |
| seed.hidden_deferral | SC-002 | I-B6 | must | spec/plan/tasks parks required work without OD reference | PR blocked | auto | planned |
| seed.not_red_first | SC-002 | I-B7, I-P2 | must | new tests already pass on base | PR blocked | auto | planned |
| seed.test_seam | SC-002 | I-A8 | must | app code adds test-only branching | PR blocked | auto | planned |
| seed.outside_owned_paths | SC-002 | I-B8 | must | diff touches a path not owned by the order | PR blocked | auto | planned |
| seed.jargon_to_governor | SC-002 | I-B3 | must | decision request contains task/finding ids or internal jargon | Rejected before it reaches the governor | auto | planned |
| seed.catalog_unlinked | SC-002 | I-B7 | must | `auto` row reaches its implementing PR still `planned` | PR blocked | auto | planned |
| handoff.per_intent_results | SC-003 | I-G2, I-P4 | must | PR linked to a work order | Results reported per intent id | auto | planned |
| handoff.reviewer_family | SC-003 | I-P3 | must | verdict on a PR | Reviewer family ≠ author family | auto | planned |
| handoff.reviewer_isolated | SC-003 | I-P3 | must | reviewer spawned | Inputs are git artifacts only; verdict records inputs; no conversation/narrative refs | hybrid | planned |
| handoff.open_od_refused | SC-003 | I-X3 | must | order depends on open governor decision | Issuing refused | auto | planned |
| handoff.done_requires_green | SC-003 | I-G2 | must | worker checks failing | Worker cannot report done | auto | planned |
| handoff.concurrency_cap | SC-003 | I-X4 | must | 3 active workers | 4th claim refused; PR without valid claim cannot merge; editor launch logged (advisory) | auto | planned |
| override.reason_required | SC-004 | I-M1 | must | override without reason | Rejected | auto | `scripts/factory/tests/contract/test_cli_contract.py::test_override_refuses_empty_reason`; `scripts/factory/tests/unit/test_bus_models.py::test_override_reason_non_empty` |
| override.surfaced_counted | SC-004 | I-M1 | must | override with reason | Appears on board and per-gate count | auto | per-gate count half: `scripts/factory/tests/contract/test_gate_run.py::test_drift_override_with_reason_passes_and_is_surfaced`, `scripts/factory/tests/contract/test_gate_run.py::test_override_counts_every_override_of_a_gate`, `scripts/factory/tests/contract/test_gate_run.py::test_overridden_gate_text_names_the_reason`; board half: planned (slice A board) |
| gate.fail_mode_category | SC-004 | I-P9 | must | gate registered | Class is `drift` or `governor-only`; governor-only only for spend/secrets/irreversible/governor decisions | auto | `scripts/factory/tests/unit/gates/test_registry_checks.py::test_fail_mode_blocks_class_category_mismatch`, `scripts/factory/tests/unit/gates/test_registry_checks.py::test_check_registry_cli_fails_on_disallowed_category` |
| ci.status_source_pinned | SC-002 | I-G1, I-G5 | must | branch protection on `main` after the D6 sequence (P9, D8, FR-022a) | Every required `factory/*` context is pinned to GitHub Actions as expected source in the snapshot and in the live rule; a status or same-named check from any other source does not satisfy it; the agents' App holds no `statuses: write` | auto | snapshot half: `scripts/factory/tests/unit/gates/test_registry_checks.py::test_branch_protection_blocks_factory_context_without_pinned_source`, `scripts/factory/tests/unit/gates/test_registry_checks.py::test_branch_protection_blocks_factory_context_pinned_to_another_app`, `scripts/factory/tests/unit/gates/test_registry_checks.py::test_branch_protection_blocks_context_list_without_sources`, `scripts/factory/tests/unit/gates/test_registry_checks.py::test_branch_protection_compares_with_the_configured_actions_app_id`, `scripts/factory/tests/contract/test_ci_trust_boundary.py::test_only_the_trusted_job_holds_statuses_write`; live rule and the agents' App: planned (T103, governor D6 probe) |
| ci.redfirst_sealed | SC-002 | I-B7, I-P2 | must | Wave 2, sealed trusted red-first run (D7, FR-012) | Head tests run in a credential-free sandbox (separate user or container, read-only head tree) in a job with no status-write permission (P19); outcomes are recorded by the parent; a head test cannot change its own recorded outcome; the status-writing job runs no head code | auto | planned |
| ci.trusted_base | SC-002 | I-G1, I-G5, I-P5 | must | a PR, including one that edits gates, the registry or either workflow (D5, FR-022a) | Its `factory/*` statuses are decided by `main`'s gate code with the head read as data; no job holding `statuses: write` checks out or executes head code; a head edit that makes a gate always pass does not change its own statuses | auto | `scripts/factory/tests/contract/test_ci_trust_boundary.py::test_evidence_workflow_is_read_only_on_pull_request`, `scripts/factory/tests/contract/test_ci_trust_boundary.py::test_gates_workflow_runs_only_on_completed_evidence_runs`, `scripts/factory/tests/contract/test_ci_trust_boundary.py::test_trusted_job_is_exactly_the_allowlist`, `scripts/factory/tests/contract/test_ci_trust_boundary.py::test_trusted_allowlist_rejects_a_step_it_does_not_list`, `scripts/factory/tests/contract/test_ci_trust_boundary.py::test_trusted_job_checks_out_main_only_without_credentials`, `scripts/factory/tests/contract/test_ci_trust_boundary.py::test_trusted_job_downloads_only_the_triggering_runs_evidence`, `scripts/factory/tests/contract/test_ci_trust_boundary.py::test_pull_request_triggers_hold_no_status_write_secret_or_head_execution`, `scripts/factory/tests/contract/test_ci_trust_boundary.py::test_ci_mode_runs_main_registry_whatever_the_head_registry_says`, `scripts/factory/tests/contract/test_ci_trust_boundary.py::test_ci_mode_never_executes_head_code`, `scripts/factory/tests/contract/test_ci_trust_boundary.py::test_validators_run_mains_script_against_the_head_tree`, `scripts/factory/tests/contract/test_ci_trust_boundary.py::test_red_first_fails_closed_on_bad_evidence_and_other_gates_still_run`, `scripts/factory/tests/contract/test_ci_trust_boundary.py::test_moved_head_posts_nothing_and_exits_0` |
| override.governor_only | SC-004 | I-P9 | must | orchestrator/worker overrides a governor-only gate | Rejected | auto | `scripts/factory/tests/contract/test_gate_run.py::test_governor_only_gate_ignores_orchestrator_override_labelled_drift`, `scripts/factory/tests/contract/test_gate_run.py::test_worker_override_is_not_honored`, `scripts/factory/tests/contract/test_gate_run.py::test_governor_override_needs_verified_identity_in_verified_mode`; `scripts/factory/tests/contract/test_cli_contract.py::test_override_refuses_governor_only_gate_by_non_governor` |
| gate.hook_has_twin | SC-004 | I-G5 | must | editor hook registered | Repository-side equivalent exists | auto | `scripts/factory/tests/unit/gates/test_registry_checks.py::test_hook_twin_blocks_hook_without_registry_row`, `scripts/factory/tests/unit/gates/test_registry_checks.py::test_hook_twin_blocks_row_without_twin`, `scripts/factory/tests/unit/gates/test_registry_checks.py::test_check_hooks_cli_fails_on_untwinned_hook` |
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
| history.no_bookkeeping | SC-008 | I-M2 | must | commits after Wave 1 | Zero status/SHA-only commits to bus files | auto | planned |
| scorecard.computed | SC-009 | I-G1, I-G2, I-G3 | must | sprint close | Scorecard computed from run records for every order | auto | planned |
| routing.zero | SC-010 | I-B4 | must | sprint close | Zero routing corrections | hybrid | planned |
| capture.budget | SC-011 | I-M2 | must | each feature | Governor intent-capture minutes recorded; ≤ ~60 | hybrid | planned |
| wave1.timebox | SC-013 | I-M3 | must | Wave 1 exit | Exit ≤ 5 working days from first order with all P1 checks passing; dates from run records | auto | planned |
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
| 2026-10-04 | Governor lock T-C2-1 (option B): `handoff.concurrency_cap` editor half is log-only — "editor launch warned" → "editor launch logged (advisory)"; Cursor shows hook messages only on denial (FR-008) |
| 2026-10-05 | Slice C evidence (T060): `branch.no_direct_main`, `override.*`, `gate.fail_mode_category`, `gate.hook_has_twin`; `handoff.concurrency_cap` PR and editor halves and `handoff.per_intent_results` (T064) follow after slice A/B merge |
| 2026-10-05 | Governor lock D5 (trusted-base CI, after PR review PR-C1): row `ci.trusted_base` added (FR-022a), evidence `planned` until T094/T097 |
| 2026-10-05 | Delta P* triage: governor locks D6 (probe, then pin), D7 (red-first self-reported in Wave 1; sealed trusted run in Wave 2), D8 (agents' App has no `statuses: write`); rows `ci.status_source_pinned` (P9) and `ci.redfirst_sealed` (D7) added, evidence `planned` until T094/T097/T103 and T104 |
| 2026-10-05 | Slice C Phase 6a (T097): `ci.trusted_base` evidence filled; `ci.status_source_pinned` snapshot half filled, live-rule half `planned` until T103 |
