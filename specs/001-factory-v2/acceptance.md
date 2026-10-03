# Acceptance catalog — 001-factory-v2

Extensible checks for [`spec.md`](./spec.md) Success Criteria. Grow from runs; do not bury in scripts or prompts.
Every `auto` row must link to a test/eval id once it exists (FR-018 applies to this catalog too).

| Field | Meaning |
|-------|---------|
| id | Stable id |
| class | SC-* in spec |
| intents | `intent.yaml` ids served |
| severity | `must` \| `should` \| `aspirational` |
| when | Preconditions |
| shall | Failable statement |
| how | `auto` \| `human` \| `hybrid` |

## Checks

| id | class | intents | severity | when | shall | how |
|----|-------|---------|----------|------|-------|-----|
| board.matches_reality | SC-001 | I-M4 | must | work orders in each lifecycle state | Board state equals state derived from branch/PR/checks for every order | auto |
| bus.no_handwritten_status | SC-001 | I-M2 | must | any bus message | Schema rejects hand-maintained status fields | auto |
| seed.substitution | SC-002 | I-B5 | must | work order touches a named lock without fidelity declaration | Issuing is refused | auto |
| seed.hidden_deferral | SC-002 | I-B6 | must | spec/plan/tasks parks required work without OD reference | PR blocked | auto |
| seed.not_red_first | SC-002 | I-B7, I-P2 | must | new tests already pass on base | PR blocked | auto |
| seed.test_seam | SC-002 | I-A8 | must | app code adds test-only branching | PR blocked | auto |
| seed.outside_owned_paths | SC-002 | I-B8 | must | diff touches a path not owned by the order | PR blocked | auto |
| seed.jargon_to_governor | SC-002 | I-B3 | must | decision request contains task/finding ids | Flagged | auto |
| seed.catalog_unlinked | SC-002 | I-B7 | must | catalog row `how: auto` with no test/eval link | PR blocked | auto |
| handoff.per_intent_results | SC-003 | I-G2, I-P4 | must | PR linked to a work order | Results reported per intent id | auto |
| handoff.reviewer_family | SC-003 | I-P3 | must | verdict on a PR | Reviewer family ≠ author family | auto |
| handoff.open_od_refused | SC-003 | I-X3 | must | order depends on open governor decision | Issuing refused | auto |
| handoff.done_requires_green | SC-003 | I-G2 | must | worker checks failing | Worker cannot report done | auto |
| handoff.concurrency_cap | SC-003 | I-X4 | must | cap of active workers reached | Spawn refused | auto |
| override.reason_required | SC-004 | I-M1 | must | override without reason | Rejected | auto |
| override.surfaced_counted | SC-004 | I-M1 | must | override with reason | Appears on board and per-gate count | auto |
| gate.fail_mode_category | SC-004 | I-P9 | must | gate registered fail-closed outside spend/secrets/irreversible/governor | Registration rejected | auto |
| gate.hook_has_twin | SC-004 | I-G5 | must | editor hook registered | Repository-side equivalent exists | auto |
| trace.coverage | SC-005 | I-N1, I-P4 | must | intent file | Coverage ≥ target; removing a mapping fails | auto |
| rules.cite_checks | SC-006 | I-P6 | must | process docs | Every MUST/NEVER cites a check or is governor-judged | auto |
| mining.correction_recorded | SC-007 | I-P7 | must | governor correction | Correction record exists | hybrid |
| mining.repeat_proposes | SC-007 | I-P7 | must | equivalent correction recorded twice | Rule/check proposal raised | auto |
| mining.postmortem_gate | SC-007 | I-P8 | must | sprint close attempted | Requires post-mortem dispositioning all corrections | auto |
| history.no_bookkeeping | SC-008 | I-M2 | must | commits after Wave 1 | Zero status/SHA-only commits to bus files | auto |
| scorecard.computed | SC-009 | I-G1, I-G2, I-G3 | must | sprint close | Scorecard computed from run records for every order | auto |
| scorecard.targets | aspirational | I-G1, I-G2 | aspirational | sprint close | Drift ≥ 95%, first-pass ≥ 75% | human |
| arch.patterns_flagged | — (US6) | I-A1..I-A8 | should | seeded pattern violations | Each mechanical pattern violation flagged | auto |
| arch.reviewer_cites_catalog | — (US6) | I-A11 | should | any reviewed PR | Findings cite pattern ids | hybrid |

## Change log

| Date | Change |
|------|--------|
| 2026-10-03 | Bootstrap from spec SC-001..009 + US6 seeded fixtures |
