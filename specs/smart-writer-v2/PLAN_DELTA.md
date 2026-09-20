# Architecture delta — smart-writer-v2 (constitution §G.1)

**Dogfood of §G.1** after Open Decisions D2–D9 locked 2026-09-20.

| Field | Value |
|-------|-------|
| Feature | `specs/smart-writer-v2/` |
| Date | 2026-09-20 |
| OD locks in this batch | D1–D9 (D2–D9 finish locks; D1 prior) |
| Delta P* review | **not warranted now** — topology intent locked (v0 design + Railway UI); implement T069 chooses one vs two Railway services under that lock. Spawn P* only if cattle split is contested. |

## Classification

| id | arch_impact | One-line lock |
|----|-------------|----------------|
| D1 | content-only | Property seed labels |
| D2 | content-only | Caps 3 / 10 / 8 |
| D3 | architecture-affecting | Wire Logfire; job `elapsed_ms` + `usage` |
| D4 | content-only | Citation + prefs in Settings panel |
| D5 | architecture-affecting | v0 **design**; UI **deploy on Railway** |
| D6 | content-only | Seed preview secret in Infisical |
| D7 | architecture-affecting | Uploads in finish; in-memory bytes |
| D8 | architecture-affecting | Dual-axis scored writer↔assessor required |
| D9 | content-only | Single revise path; explicit regenerate control |

## Artifacts amended

- [x] `plan.md` Architecture (+ finish map; P1/P3 amended)
- [x] `data-model.md` — Job metrics/loop; MaterialRef upload; UploadStore; Rubric; AssessorScore
- [x] `contracts/http-api.md` — job snapshot `elapsed_ms` / `usage` / `loop`
- [x] `research.md` — R6 + topology Decision overturned
- [x] `tasks.md` — Phase 10 T063–T087
- [x] `spec.md` — OD `arch_impact` column; FR-022/023

## Remaining gaps → tasks

| Gap | Task id |
|-----|---------|
| Upload MIME/size defaults in contract text | T073 |
| Railway UI cattle (one vs two services) + README | T069 |
| Catalog rows for scored loop structural checks | T078 |
| Settings panel UI | T065 |
| Logfire + snapshot keys green | T064 |
| Rubric/assess agents + graph wire | T081–T085 |

## `/speckit-analyze` result

| Field | Value |
|-------|-------|
| Date run | 2026-09-20 |
| Outcome | **pass with filed gaps** (above → existing Phase 10 tasks) |
| Notes | Manual §G.1 consistency pass (same intent as `/speckit-analyze`): no contradiction between locked ODs and plan Architecture after amend. `web/README.md` still describes Vercel host — **fix in T069**. No greenfield re-plan. |

## Gate

Architecture-affecting subset (D3, D5, D7, D8) reconciled. Dependent Phase 10 implement/ops packets **may** start (ops T070 still needs human vault action).

## Forbidden (honored)

- No new feature directory for these locks
- No stock plan template wipe
- Human chat: **Architecture delta reconcile done**
