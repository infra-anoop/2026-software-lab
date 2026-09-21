# Architecture delta — smart-writer-v2 (constitution §G.1)

**Dogfood of §G.1** after Open Decisions D2–D9 locked 2026-09-20.  
**Addendum:** **D5 re-lock** 2026-09-21 (one Railway service + V1-style secret).

| Field | Value |
|-------|-------|
| Feature | `specs/smart-writer-v2/` |
| Date | 2026-09-20 (base); **2026-09-21** (D5 amend) |
| OD locks in this batch | D1–D9; **D5 re-locked** |
| Delta P* review | **not warranted** — governor explicitly chose simpler topology (V1-style gate + one service); overturns BFF custody. Spawn P* only if one-service static-serve approach proves infeasible. |

## Classification

| id | arch_impact | One-line lock |
|----|-------------|----------------|
| D1 | content-only | Property seed labels |
| D2 | content-only | Caps 3 / 10 / 8 |
| D3 | architecture-affecting | Wire Logfire; job `elapsed_ms` + `usage` |
| D4 | content-only | Citation + prefs in Settings panel |
| D5 | architecture-affecting | **re-lock:** v0 design; **one** Railway service; **V1-style** browser secret (not BFF / not second UI service) |
| D6 | content-only | Seed preview secret in Infisical (**one** service; UI types same secret) |
| D7 | architecture-affecting | Uploads in finish; in-memory bytes |
| D8 | architecture-affecting | Dual-axis scored writer↔assessor required |
| D9 | content-only | Single revise path; explicit regenerate control |

## Artifacts amended

### 2026-09-20 (original batch)

- [x] `plan.md` Architecture (+ finish map; P1/P3 amended)
- [x] `data-model.md` — Job metrics/loop; MaterialRef upload; UploadStore; Rubric; AssessorScore
- [x] `contracts/http-api.md` — job snapshot `elapsed_ms` / `usage` / `loop`
- [x] `research.md` — R6 + topology Decision
- [x] `tasks.md` — Phase 10 T063–T087
- [x] `spec.md` — OD `arch_impact` column; FR-022/023

### 2026-09-21 (D5 re-lock)

- [x] `spec.md` — D5 re-lock + D6 custody note
- [x] `plan.md` — P1, building blocks, topology, technical context, structure
- [x] `research.md` — Topology block overturned
- [x] `FINISH_BAR.md` — D5 row + delta addendum
- [x] `tasks.md` — T069 (+ T070 note / T076 secret wording)
- [x] `notes/packets/2026-09-21-swv2-d5-one-service-ui.md` — implement packet

## Remaining gaps → tasks

| Gap | Task id |
|-----|---------|
| Serve v0 UI from FastAPI same-origin + V1-style secret field; remove BFF custody / `-ui` cattle | **T069** (redefined) |
| Upload MIME/size defaults in contract text | T073 |
| Catalog / scored loop (done) | T078+ |
| Settings panel UI | T065 (done) |
| Logfire + snapshot keys | T064 |
| Uploads UI without BFF assumption | T076 |

## `/speckit-analyze` result

| Field | Value |
|-------|-------|
| Date run | 2026-09-21 |
| Outcome | **pass with filed gaps** — D5 artifacts aligned; T069 carries implement |
| Notes | Manual §G.1 consistency pass after D5 re-lock. Historical P0/P1 phase rows still mention BFF as **shipped MVP history**; finish topology is one-service + V1-style. No greenfield re-plan. |

## Gate

Architecture-affecting subset including **D5 re-lock** reconciled. Dependent T069 implement packet **may** start.

## Forbidden (honored)

- No new feature directory for these locks
- No stock plan template wipe
- Human chat: **Architecture delta reconcile done** (D5 re-lock)
