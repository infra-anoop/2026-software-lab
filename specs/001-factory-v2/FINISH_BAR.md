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
| 2026-10-05 | **D5** (trusted-base CI, governor lock after PR review PR-C1) — locked, architecture-affecting → §G.1 [`PLAN_DELTA.md`](./PLAN_DELTA.md). **D6** (when the required `factory/*` checks switch on relative to Slice C's bootstrap merge) — opened by the D5 reconcile | D5 yes; **D6 no** (open, `who: human`) |

### Delta inventory (2026-10-05)

| id / source | Product question (governor altitude) | arch_impact (on lock) | Outcome |
|-------------|--------------------------------------|------------------------|---------|
| D5 | Which code judges a PR in CI, and what may write the merge-deciding statuses | architecture-affecting | locked 2026-10-05 — `main`'s code judges; the head is data; no head code with status write; gate changes apply after merge; Slice C bootstraps; no `pull_request_target` with head code |
| D6 | Branch protection and Slice C's own merge: switch on "factory checks must pass" right after C merges, or before it, with the governor personally marking C's checks as passed | (on lock) | **open** — question in `PLAN_DELTA.md` § D6 |

### Delta outcome

| Field | Value |
|-------|-------|
| Delta rows resolved? | no — D6 open |
| What D6 blocks | Only T101 (applying branch protection) and T103 (Slice C's merge). The delta P* review, Phase 6a tests (T094–T096) and rework (T097–T100) do not depend on D6 |
| **Implement unblocked** (Phase 6a) | **yes after the delta P* review is triaged** (§G.1 step 4); the C merge waits on D6 |
