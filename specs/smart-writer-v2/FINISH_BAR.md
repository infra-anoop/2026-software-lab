# Finish-bar lock batch — smart-writer-v2 (constitution §G.2)

**Retroactive dogfood (2026-09-20):** Governor locked D2–D9 in chat; §G.1 [`PLAN_DELTA.md`](./PLAN_DELTA.md) completed. This file records the §G.2 gate so implement is explicitly unblocked.

| Field | Value |
|-------|-------|
| Feature | `specs/smart-writer-v2/` |
| Date | 2026-09-20 |
| `/speckit-analyze` run | 2026-09-20 — consistency pass recorded in `PLAN_DELTA.md` (pass with gaps → Phase 10 tasks) |
| Batch status | **done** |

## Inventory

| id / source | Product question (governor altitude) | arch_impact | Outcome |
|-------------|--------------------------------------|-------------|---------|
| D1 | Property seed labels | content-only | **locked** (prior) |
| D2 | Spend caps (jobs / clarifies / inner turns) | content-only | **locked** — 3 / 10 / 8 |
| D3 | Wire observability + elapsed/tokens on jobs | architecture-affecting | **locked** — wire for finish |
| D4 | Citation control placement | content-only | **locked** — Settings panel |
| D5 | UI design tool vs deploy host + secret custody | architecture-affecting | **re-locked 2026-09-21** — v0 design; **one** Railway service; V1-style browser secret |
| D6 | Seed preview secret in vault | content-only | **locked** — yes for finish |
| D7 | File uploads in finish + storage | architecture-affecting | **locked** — yes; in-memory |
| D8 | Dual-axis scored quality loop required? | architecture-affecting | **locked** — required for complete V2 |
| D9 | Outer revise routing + start-over indication | content-only | **locked** — single revise path; explicit regenerate control |
| plan P7 / research R6 (historical) | “Machine critique / Logfire / uploads / caps deferred” | — | **Promoted into D2–D8** (no longer silent plan deferral) |

## Batch outcome

| Field | Value |
|-------|-------|
| All inventory rows locked or true-waived? | **yes** |
| Next gate | §G.1 **done** — see `PLAN_DELTA.md` |
| **Implement unblocked** | **yes** |

## Delta addendum (re-entry only)

| Date | New rows | Re-lock done? |
|------|----------|---------------|
| 2026-09-21 | **D5 re-lock** (one service + V1-style secret; drop BFF custody / second UI service) | **yes** — see `PLAN_DELTA.md` § D5 re-lock |
