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
| beachhead.audience_fit_min | SC-002 | must | named funder + criteria available | ≥2 concrete fit points tied to criteria; not generic-only; prefer materials when present (F4) | hybrid |
| research.prefer_criteria_over_trivia | FR-007b | must | uploaded/linked criterion vs novel web tidbit | Draft emphasis prefers criteria/fit over novelty trivia | human |
| claim.provenance | SC-003 | must | draft asserts org/funder fact beyond raw prompt | Provenance attached or claim omitted/uncertain (grounding invariant; not toggled by `factual` rank — F3) | hybrid |
| research.used_or_declared | SC-004 | must | web research enabled | ≥1 non-upload finding affects draft OR explicit no-signal declaration (grounding invariant — F3) | hybrid |
| engine.nongrant_smoke | SC-005 | should | non-grant run | Same engine completes without grants-only hard fail (smoke; not primary v2.0 bar — F2) | hybrid |
| delight.surprise | SC-aspirational | aspirational | any | Reader notices non-obvious specific research | human |
| grant.default_humor_low | FR-006b | must | grant beachhead default profile | `humorous` de-emphasized or off until user enables | hybrid |
| grant.intent_slots_complete | FR-003a | must | grant beachhead run | Who/Whom/Ask/Why/Evidence present (prompt, materials, or Q&A) before final draft | hybrid |
| intake.axis_a_before_b | FR-003c | must | grant run, both axes incomplete | Intent-slot questions asked before property clarifiers | hybrid |
| intake.property_chips_preferred | FR-003b | should | Axis B ambiguity | Prefer editable property ranking over long property interview | human |
| citation.default_sources_panel | FR-010 | must | grant beachhead, sources exist | Default presentation is sources panel unless user overrides | hybrid |
| citation.skip_ask_if_no_sources | FR-010a | must | no citable sources in run | Do not force citation-format question | hybrid |

## Change log

| Date | Change |
|------|--------|
| 2026-09-12 | Bootstrap from F1 / Spec Kit alignment |
| 2026-09-12 | F2: nongrant_smoke clarified as should/smoke under grant primacy |
| 2026-09-12 | F3: grounding invariant notes; grant.default_humor_low |
| 2026-09-12 | F4: materials vs web roles; prefer_criteria_over_trivia |
| 2026-09-12 | F5: dual intent (lab dogfood + surface gates); no stack checkbox DoD |
| 2026-09-12 | F6: dual intake schemas Axis A intent slots + Axis B properties |
| 2026-09-12 | F7: sources panel default + light override; skip ask if no sources |
