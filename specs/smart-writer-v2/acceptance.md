# Acceptance catalog — smart-writer-v2

Extensible checks for [`spec.md`](./spec.md) Success Criteria. Grow from test runs; do not bury in prompts/orchestrator code.

| Field | Meaning |
|-------|---------|
| id | Stable id |
| class | Maps to SC-* in spec |
| severity | `must` \| `should` \| `aspirational` |
| when | Preconditions (else N/A) |
| shall | Failable statement |
| how | `auto` \| `human` \| `hybrid` |

## Checks

| id | class | severity | when | shall | how |
|----|-------|----------|------|-------|-----|
| length.target_1_3_pages | SC-001 | must | no length override | Draft targets approximately 1–3 pages | human |
| beachhead.audience_fit_min | SC-002 | must | named funder + criteria available | ≥2 concrete fit points tied to criteria; not generic-only | hybrid |
| claim.provenance | SC-003 | must | draft asserts org/funder fact beyond raw prompt | Provenance attached or claim omitted/uncertain | hybrid |
| research.used_or_declared | SC-004 | must | web research enabled | ≥1 non-upload finding affects draft OR explicit no-signal declaration | hybrid |
| engine.nongrant_smoke | SC-005 | should | F2 pending | Non-grant short-form path completes without grants-only hard fail | hybrid |
| delight.surprise | SC-aspirational | aspirational | any | Reader notices non-obvious specific research | human |

## Change log

| Date | Change |
|------|--------|
| 2026-09-12 | Bootstrap from F1 / Spec Kit alignment |
