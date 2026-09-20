# Architecture delta reconcile — template (constitution §G.1)

Copy to `specs/<feature>/PLAN_DELTA.md` when any Open Decision locks as **architecture-affecting**.

**Gate:** Do not spawn implement/ops workers that depend on those locks until this checklist is complete (and `/speckit-analyze` recorded).

## Meta

| Field | Value |
|-------|-------|
| Feature | `specs/<feature>/` |
| Date | |
| OD locks in this batch | D# … |
| Delta P* review | not warranted \| spawned → `PLAN_REVIEW.md` |

## Classification

| id | arch_impact | One-line lock |
|----|-------------|----------------|
| D# | content-only \| architecture-affecting | |

## Artifacts amended

- [ ] `plan.md` Architecture (+ Phasing if needed)
- [ ] `data-model.md`
- [ ] `contracts/` (if APIs/entities changed)
- [ ] `research.md` overturned Decisions
- [ ] `tasks.md` appended (no renumber of done IDs)
- [ ] `spec.md` OD `arch_impact` column filled

## Remaining gaps → tasks

| Gap | Task id |
|-----|---------|
| | |

## `/speckit-analyze` result

| Field | Value |
|-------|-------|
| Date run | |
| Outcome | pass \| gaps (listed above) |
| Notes | |

## Forbidden

- New feature directory solely for OD fills
- Stock `/speckit-plan` setup that replaces `plan.md` with empty template
- Three soft synonyms in human chat instead of “delta reconcile required / done”
