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
| research.prefer_criteria_over_trivia | SC-002 | must | uploaded/linked criterion vs novel web tidbit | Draft emphasis prefers criteria/fit over novelty trivia | human |
| claim.provenance | SC-003 | must | draft asserts org/funder fact beyond raw prompt | Provenance attached or claim omitted/uncertain (grounding invariant; not toggled by `factual` rank — F3) | hybrid |
| research.used_or_declared | SC-004 | must | web research enabled | ≥1 non-upload finding affects draft OR explicit no-signal declaration (grounding invariant — F3) | hybrid |
| engine.nongrant_smoke | SC-005 | should | non-grant run | Same engine completes without grants-only hard fail (smoke; not primary v2.0 bar — F2) | hybrid |
| delight.surprise | SC-aspirational | aspirational | any | Reader notices non-obvious specific research | human |
| grant.default_humor_low | SC-002 | must | grant beachhead default profile | `humorous` de-emphasized or off until user enables | hybrid |
| grant.intent_slots_complete | SC-002 | must | grant beachhead run | Who/Whom/Ask/Why/Evidence present (prompt, materials, or Q&A) before final draft | hybrid |
| intake.axis_a_before_b | SC-002 | must | grant run, both axes incomplete | Intent-slot questions asked before property clarifiers | hybrid |
| intake.property_chips_preferred | SC-002 | should | Axis B ambiguity | Prefer editable property ranking over long property interview | human |
| citation.default_sources_panel | SC-003 | must | grant beachhead, sources exist | Default presentation is sources panel unless user overrides | hybrid |
| citation.skip_ask_if_no_sources | SC-003 | must | no citable sources in run | Do not force citation-format question | hybrid |
| chat.free_form_input | SC-006 | must | any user message | No required user-visible Axis/slot forms | hybrid |
| revise.continuity_default | SC-006 | must | feedback on prior artifact, no restart | New ArtifactVersion linked to prior + feedback; revise path not silent full regen | auto |
| regenerate.explicit | SC-007 | must | user requests start over | Fresh generate path used | hybrid |
| loop.scores_and_stop | SC-002 | must | succeeded generate or revise job | Job snapshot has non-null `rubric_id` + `loop` with nonempty `scores[]` (per-turn dimension scores + feedback), numeric `aggregate_score`, and `stop_reason` ∈ {max_iterations, targets_met, error} — not thinner than V1 scored loop | auto |
| loop.iterations_cap | SC-002 | must | succeeded generate or revise job | `loop.iterations` ∈ 1…`loop.max_iterations` and `loop.max_iterations` ≤ 8 (Settings inner max); stop by score gate (`targets_met`) or cap (`max_iterations`) | auto |
| rubric.dual_axis | SC-002 | must | succeeded generate or revise job | Rubric for the job has ≥1 Axis A (intent) and ≥1 Axis B (property) dimension; snapshot exposes `loop.axis_a_dimension_count` ≥ 1 and `loop.axis_b_dimension_count` ≥ 1 | auto |

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
| 2026-09-13 | F8: chat free-form; revise-by-default; regenerate explicit; axes internal |
| 2026-09-15 | R4 hygiene: class column prefers SC-*; auto subset deferred to plan |
| 2026-09-18 | T061: `revise.continuity_default` → `how: auto` (green `test_revise_job.py`; plan P2 exit) |
| 2026-09-20 | T078: D8 scored loop structural rows (`loop.scores_and_stop`, `loop.iterations_cap`, `rubric.dual_axis`) |
| 2026-09-20 | T086: confirm `loop.*` / `rubric.dual_axis` remain `how: auto` (structural); assessor prose / score-quality stays hybrid/human |
