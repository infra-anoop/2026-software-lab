# Acceptance catalog — 002-swv2-durable-evals

Delta catalog. Baseline rows in [`../smart-writer-v2/acceptance.md`](../smart-writer-v2/acceptance.md) stay in force (SW-B1).
Every `auto` row must link to a test/eval id once it exists (factory FR-018).

| id | class | intents | severity | when | shall | how |
|----|-------|---------|----------|------|-------|-----|
| durable.survives_restart | SC-001 | SW-D1, SW-D2 | must | seeded conversations, versions, uploads | All present to owning browser after restart and redeploy | auto |
| durable.browser_isolation | SC-002 | SW-D4 | must | two browser keys | Neither lists the other's conversations | auto |
| durable.retention_30d | SC-003 | SW-D5 | must | items idle >30d and <30d | Older deleted; newer kept | auto |
| durable.no_silent_loss | SC-004 | SW-D3 | must | job interrupted mid-pipeline | Resumes or explicitly failed | auto |
| eval.per_pr_scores | SC-005 | SW-N1, SW-E2 | must | PR touching the app | Per-dimension scores vs main within budget | auto |
| eval.blocks_regression | SC-006 | SW-E1 | must | seeded regression beyond noise band | PR blocked | auto |
| eval.no_false_positive | SC-006 | SW-E1 | must | no-op change | PR not blocked | auto |
| eval.calibrated | SC-007 | SW-Q7 | must | calibration ratings exist | Agreement ≥ D1 before gate blocks | hybrid |
| eval.judge_family | SC-005 | SW-E3 | must | judge configured | Family ≠ writer family | auto |
| eval.golden_set_reviewed | SC-005 | SW-Q8 | must | golden set | Governor-reviewed; grant + ≥1 non-grant | human |
| tests.no_seams | SC-008 | SW-T1 | must | app code | No test-only branching | auto |
| tests.all_steps | SC-008 | SW-T2 | must | test suite | Every pipeline step executed | auto |
| tests.baseline_green | SC-008 | SW-B1 | must | baseline auto rows | Pass | auto |
| limits.spend_stop | SC-009 | SW-L1 | must | job would exceed ceiling | Stops with reason; never > $3 | auto |
| limits.latency_reported | SC-010 | SW-L2 | must | golden-set run | p95 draft time reported | auto |
| models.bakeoff_record | SC-011 | SW-M2 | must | each role | Bake-off record exists, governor-locked | hybrid |
| models.swap_full_eval | SC-011 | SW-M3 | must | model config changed | Full eval set runs | auto |
| migrations.proven | SC-012 | SW-D6 | must | schema change | Passes on real DB in CI and on staging before prod | auto |
| quality.governor_agrees | aspirational | SW-Q1..Q4 | aspirational | sprint close | Governor agrees top-scored drafts are sendable | human |

## Change log

| Date | Change |
|------|--------|
| 2026-10-03 | Bootstrap from spec SC-001..012 |
