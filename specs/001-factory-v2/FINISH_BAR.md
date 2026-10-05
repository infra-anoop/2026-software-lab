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
| 2026-10-05 (round 2, after the delta P* review) | **D6** locked (probe, then pin); **D7** (red-first strength per wave) and **D8** (agents' App has no `statuses: write`) added and locked, all architecture-affecting → §G.1 round 2 in [`PLAN_DELTA.md`](./PLAN_DELTA.md) | yes — D6, D7, D8 |

### Delta inventory (2026-10-05)

| id / source | Product question (governor altitude) | arch_impact (on lock) | Outcome |
|-------------|--------------------------------------|------------------------|---------|
| D5 | Which code judges a PR in CI, and what may write the merge-deciding statuses | architecture-affecting | locked 2026-10-05 — `main`'s code judges; the head is data; no head code with status write; gate changes apply after merge; Slice C bootstraps; no `pull_request_target` with head code |
| D6 | Branch protection and Slice C's own merge: switch on "factory checks must pass" right after C merges, or before it, with the governor personally marking C's checks as passed | (on lock) | locked 2026-10-05 (architecture-affecting) — probe, then pin: C merges on bootstrap review + approval; merges freeze; a non-merging probe gets trusted statuses; every `factory/*` context required with GitHub Actions pinned as source; live rule verified; merges reopen |
| D7 | How much to trust the CI red-first result before a sealed run exists | architecture-affecting | locked 2026-10-05 — Wave 1 self-reported (stated in the status), T* re-run is the proof of record; Wave 2 sealed trusted run (T104) |
| D8 | May the agents' GitHub App write commit statuses | architecture-affecting | locked 2026-10-05 — no; only CI posts `factory/*` statuses |

### Delta outcome

| Field | Value |
|-------|-------|
| Delta rows resolved? | yes — D5–D8 locked (round 2, 2026-10-05) |
| Next gate | Narrow P* confirmation of the round-2 reconcile (§G.1 step 4) |
| **Implement unblocked** (Phase 6a) | **yes once the narrow P* confirmation passes**; Phase 6a stays tests-first (T094–T096 before T097–T098) |
