# Finish-bar lock batch — template (constitution §G.2)

Copy to `specs/<feature>/FINISH_BAR.md` after `/speckit-tasks` (and `/speckit-analyze`), **before** first implement/ops packet.

**Gate:** `Implement unblocked` must be **yes** before spawning product implement workers.

## Meta

| Field | Value |
|-------|-------|
| Feature | `specs/<feature>/` |
| Date | |
| `/speckit-analyze` run | date + outcome (or path to report notes) |
| Batch status | in_progress \| done |

## Inventory

| id / source | Product question (governor altitude) | arch_impact (on lock) | Outcome |
|-------------|--------------------------------------|------------------------|---------|
| D# or plan phrase | … | content-only \| architecture-affecting \| n/a | open \| locked (summary) \| waived (out of version) |

Promote any plan-only “deferred/Later/optional” finish item to an Open Decision id before locking.

## Batch outcome

| Field | Value |
|-------|-------|
| All inventory rows locked or true-waived? | yes \| no |
| Next gate | none \| §G.1 `PLAN_DELTA.md` required |
| **Implement unblocked** | **yes** \| **no** |

## Delta addendum (re-entry only)

When new ODs or finish deferrals appear after a completed batch, append rows here and reset **Implement unblocked** to **no** until re-locked.

| Date | New rows | Re-lock done? |
|------|----------|---------------|
| | | |

## Forbidden

- Starting implement with open finish-bar rows
- Using `waived` to mean “not right now but still required”
- Skipping analyze when tasks just changed materially
