# Finish-bar lock batch — 001-factory-v2 (constitution §G.2)

## Meta

| Field | Value |
|-------|-------|
| Feature | `specs/001-factory-v2/` |
| Date | 2026-10-03 |
| `/speckit-analyze` run | 2026-10-03 — 0 critical, 0 high. Remediated in place: editor spawn warning moved from Wave 2 to Wave 1 (FR-008 is P1); stale `run_record` / D4-C terms → run events / verified mode; blocker-question behavior of `factory handoff` specified (US2 #3); slice packets task added (T016a); deferral-words rule exempts code spans. Coverage: FR-001..FR-037 each map to ≥ 1 task; FR-036 is a design rule carried by `factory.toml` (T002), with its proof in US9 per D1 |
| Batch status | done |

## Inventory

| id / source | Product question (governor altitude) | arch_impact (on lock) | Outcome |
|-------------|--------------------------------------|------------------------|---------|
| D1 | Portability proof, live config drift, secret scan, one-service manifest this version? | content-only | waived (out of version → sprint 03, governor 2026-10-03) |
| D2 | Mutation threshold | content-only | locked — 70% on changed lines |
| D3 | Default reviewer family | content-only | locked — GPT |
| D4 | How the governor is told apart from agents | architecture-affecting | locked before plan approval — GitHub App during Wave 1; plan already carries it, so no §G.1 delta |
| Plan P7 ("Later → tasks") | Interface freeze, integration checkpoints, 3-day target vs 5-day max | n/a | locked into `tasks.md` (CP0–CP2, Phase 2 freeze) |
| Plan "live drift check = P3" | Branch-protection drift check | n/a | covered by D1 waive (snapshot only in T066) |
| tasks T004 "allowed to fail until CP2" | Temporary non-blocking gate job | n/a | closed by T059 within Wave 1 |

## Batch outcome

| Field | Value |
|-------|-------|
| All inventory rows locked or true-waived? | yes |
| Next gate | none |
| **Implement unblocked** | **yes** |

## Delta addendum (re-entry only)

| Date | New rows | Re-lock done? |
|------|----------|---------------|
| | | |
