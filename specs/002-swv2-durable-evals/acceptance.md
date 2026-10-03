# Acceptance catalog — 002-swv2-durable-evals

Delta catalog. Baseline rows in [`../smart-writer-v2/acceptance.md`](../smart-writer-v2/acceptance.md) stay in force (SW-B1).

**Evidence lifecycle (factory FR-018):** `planned` until the implementing work order; that PR must not merge until `evidence` names an existing test or eval id. `n/a` for `human`.

| id | class | intents | severity | when | shall | how | evidence |
|----|-------|---------|----------|------|-------|-----|----------|
| durable.survives_restart | SC-001 | SW-D1, SW-D2 | must | seeded conversations, versions, uploads | All present to owning browser after restart and redeploy | auto | planned |
| durable.browser_isolation | SC-002 | SW-D4 | must | two browser keys | Neither lists the other's conversations | auto | planned |
| durable.retention_30d | SC-003 | SW-D5 | must | items idle >30d and <30d | Older deleted with every owned record type (messages, versions, run state, checkpoints, uploads, provenance); newer kept | auto | planned |
| durable.retention_refresh | SC-003 | SW-D5 | must | each "use" action in FR-004 | Clock restarts | auto | planned |
| durable.retention_disclosure | SC-014 | SW-D4, SW-D5 | must | any conversation in UI | Deletion date + browser-only notice visible | auto | planned |
| durable.no_silent_loss | SC-004 | SW-D3 | must | job interrupted mid-pipeline | Resumes or explicitly failed | auto | planned |
| eval.per_pr_scores | SC-005 | SW-N1, SW-E2 | must | PR touching the app | Per-dimension + support scores vs main within budget | auto | planned |
| eval.blocks_single_dimension | SC-006 | SW-E1 | must | seeded regression in one dimension beyond its noise, others improved | PR blocked | auto | planned |
| eval.blocks_support_regression | SC-006 | SW-Q6, SW-E1 | must | seeded drop in source support beyond noise | PR blocked regardless of quality scores | auto | planned |
| eval.no_false_positive | SC-006 | SW-E1 | must | no-op change | PR not blocked | auto | planned |
| eval.calibrated | SC-007 | SW-Q7 | must | calibration ratings exist | Within 1 point on ≥ 80% of drafts, every dimension, before gate blocks | hybrid | planned |
| eval.judge_family | SC-005 | SW-E3 | must | judge / support checker configured | Family ≠ writer family | auto | planned |
| eval.golden_set_reviewed | SC-005 | SW-Q8 | must | golden set | Governor-reviewed; grant + ≥1 non-grant; held-out slice tagged | human | n/a |
| eval.heldout_unused | SC-013 | SW-Q8 | must | bake-off, prompt, judge-selection runs | Zero held-out scenarios used | auto | planned |
| eval.blinded_review | SC-013 | SW-Q7 | must | sprint post-mortem | Blinded review of ~5 drafts + support spot-check recorded | human | n/a |
| tests.no_seams | SC-008 | SW-T1 | must | app code | No test-only branching | auto | planned |
| tests.all_steps | SC-008 | SW-T2 | must | test suite | Every pipeline step executed | auto | planned |
| tests.baseline_green | SC-008 | SW-B1 | must | baseline auto rows | Pass | auto | planned |
| limits.spend_stop | SC-009 | SW-L1 | must | job would exceed ceiling | Stops with reason; never > $3 | auto | planned |
| limits.latency_reported | SC-010 | SW-L2 | must | golden-set run | p95 draft time reported vs 10-minute target | auto | planned |
| models.bakeoff_record | SC-011 | SW-M2 | must | each role | Record with scores, costs, end-to-end bundle comparison; governor-locked | hybrid | planned |
| models.judge_by_agreement | SC-011 | SW-M2, SW-Q7 | must | judge candidates | Ranked by calibration agreement, not own scores | auto | planned |
| models.swap_full_eval | SC-011 | SW-M3 | must | model config changed | Full eval set runs | auto | planned |
| migrations.proven | SC-012 | SW-D6 | must | schema change | Passes on real DB in CI and on staging before prod | auto | planned |
| quality.governor_agrees | aspirational | SW-Q1..Q4 | aspirational | sprint close | Governor agrees top-scored drafts are sendable | human | n/a |

## Change log

| Date | Change |
|------|--------|
| 2026-10-03 | Bootstrap from spec SC-001..012 |
| 2026-10-03 | Review locks: evidence column; per-dimension blocking; support gate; held-out + blinded review; retention refresh/disclosure/cascade; judge-by-agreement; bundle check |
