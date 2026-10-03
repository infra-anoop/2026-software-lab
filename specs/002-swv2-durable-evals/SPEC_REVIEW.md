# Product Spec Review — Smart Writer V2 durable state + measured quality

## A. Executive verdict

**Do not approve yet.**

The durability delta is concrete, preserves the frozen baseline explicitly, and has unusually strong failable outcomes and catalog coverage. The central quality gate is not yet a determinate product rule: “quality drop” does not say how four dimensions combine, how a per-PR subset represents the golden set, or what statistical confidence turns noise into a regression. More importantly, the proposed judge can become a persuasive-prose optimizer whose calibration and golden data share one governor and one synthetic distribution, while factual support is excluded from the score. The retention/key model is internally plausible for an anonymous preview, but the spec has not defined “last use” or the user-visible deletion contract well enough for the claimed real-grant-work value.

## B. Findings table

| ID | Severity | Lens | Spec locus | Finding | Suggested resolution (for human) |
|----|----------|------|------------|---------|----------------------------------|
| F1 | Blocker | Falsifiability / eval gate | US2 scenarios 1–4; FR-010–012; SC-006–007 | The blocking rule is not a determinate rule. “Quality drop exceeds the measured noise band” leaves open whether any one dimension can block, whether dimensions are aggregated, whether gains can offset losses, how the ~$1–2 subset represents the full set, and what confidence/repeat count defines noise. D1 opens only the agreement threshold, not these product semantics. Two conforming planners could build gates that make opposite merge decisions. | Add explicit Open Decisions for (a) per-dimension versus aggregate blocking and trade-offs, (b) per-PR subset selection/rotation, and (c) the run-to-run noise decision rule. Keep the gate report-only until those are locked and calibration passes. |
| F2 | Debate **[product]** | Eval validity / primary bet | Why this feature exists; US2; FR-007–012; Aspirational criteria | Steelman: synthetic organizations avoid private data and make repeatable evals cheap. Attack: the same governor reviews the synthetic golden set, supplies 10–15 calibration ratings, and judges whether top drafts are sendable; this can calibrate the judge to one person's preferences on one authored distribution without showing transfer to real grant work. The spec has no held-out scenarios or post-calibration human audit. | Choose whether “measured quality” means proxy consistency only, or credible transfer. For transfer, require a held-out slice not used for prompt/model selection plus periodic blinded governor review; label the existing gate as proxy-only until that evidence exists. |
| F3 | Debate **[product]** | Grounding / Goodhart risk | Baseline SC-003–004; US2 judge dimensions; FR-013 | Steelman: provenance is more reliably checked structurally than by an aesthetic LLM judge. Attack: the baseline requires a source to be attached or a claim omitted/marked uncertain, but neither the baseline catalog nor this delta requires that the cited source actually entails the claim. Optimizing funder fit, narrative, impact, and voice can therefore reward confident, source-decorated misstatements while the gate stays green. | Keep grounding out of the literary composite if desired, but add a non-compensable support/entailment check (automated plus sampled human review) that must pass before quality scores can approve a regression gate. |
| F4 | Debate **[product]** | Durability / user trust | US1; edge cases; FR-003–004; SC-003 | The locked 30-day/browser-key model is coherent as anonymous ownership, but “last use” is undefined except that job completion counts. Viewing, downloading, opening in another tab, or a failed/retried job could refresh—or not refresh—the deadline. The product also promises real-work durability while allowing irreversible deletion and key loss without requiring a visible expiry warning or recovery/export path. | Do not reopen the locked duration or anonymous key. Lock which user actions refresh retention and require the UI to disclose the exact expiry/key-loss behavior, including a warning before irreversible deletion. If no warning is intended, explicitly accept that this is durable preview storage rather than safe long-lived grant workspace storage. |
| F5 | Debate **[product]** | Model selection / local optimization | US5; FR-015–016; SC-011 | Choosing “per role the cheapest model within D2 of the best quality” assumes roles can be optimized independently. Writer, assessor, extraction, and judge interact; four individually best-value choices may form a worse system than another combination, and using the judge to select the judge is circular unless judge candidates are evaluated against human labels. | Choose between independent role bake-offs and system-level bundle bake-offs. At minimum, require a final end-to-end bake-off of the selected bundle and evaluate judge candidates on held-out human ratings rather than their own quality scores. |
| F6 | Debate **[product]** | Retention / data scope | FR-001–006; Key Entities; acceptance `durable.retention_30d` | The deletion shall names “conversations and uploads,” while persisted scope includes messages, every artifact version, InternalRunState, checkpoints, and potentially derived source/provenance records. A conversation cascade may be intended, but the product privacy promise does not explicitly say all owned derivatives are removed. | Amend FR-004 and the catalog row to enumerate or explicitly cascade-delete all conversation-owned user content and derived state; state whether eval artifacts containing synthetic-only data are outside that lifecycle. |
| F7 | Later | Latency falsifiability | US4 scenario 2; FR-018; SC-010 | “Target p95 ≈ 10 minutes” is only a reporting requirement in SC-010, not a pass/fail latency outcome. “About” also lacks workload and sample conditions. That is acceptable as measurement-first, but it does not support the user-story wording that a complete draft arrives within about ten minutes. | In plan/eval design, define the canonical workload, minimum sample size, warm/cold conditions, and whether >10 minutes fails release or merely opens follow-up work. Keep the spec honest by calling this measured-not-gated unless a hard bar is chosen. |
| F8 | Later | Nightly regression handling | FR-011; sprint charter Evals lane | A larger set runs nightly, but the spec says nothing about what a nightly-only regression does after a PR has merged. This can turn the representative set into a dashboard with no product consequence. | Define in plan/ops policy whether nightly failure blocks subsequent merges, opens a tracked regression, or triggers rollback; include an owner and time bound without making the human the routine unblocker. |
| F9 | Nit | Strength / baseline fidelity | Baseline paragraph; US3; FR-013, FR-019–021; acceptance catalog | Strength: the delta explicitly keeps baseline grant primacy, revise continuity, scored inner loop, grounding, and all baseline `auto` rows in force. US3 also targets the shipped graph rather than a test-only facsimile. This is specific protection against silently thinning the v2.0 product. | Preserve these references through plan and tasks; no spec change required. |

## C. Adversarial positions

### 1. Position: kill or narrow the primary product bet

Do not make this eval gate the factory fitness function yet. A synthetic set, one governor, 10–15 calibration drafts, and an LLM judge can create precise-looking movement without measuring grant success. Once blocking is enabled, agents and humans will optimize against the proxy; repeated use of the same set makes leakage and rubric gaming increasingly likely. Narrow the deliverable to an eval report, noise characterization, and blinded validation study. Permit blocking only after the report predicts held-out human preference and the per-dimension gate semantics are locked.

**What would have to be true for the spec to be right anyway:** the selected judge and gate must reliably predict blinded human rankings on held-out, realistic scenarios across repeated runs, not merely agree on the calibration set.

### 2. Position: change the anonymous durability pillar

“Survives deploy” is not enough to call this safe for real grant work. A browser-local bearer key can be lost through routine browser clearing or device change, and 30-day deletion is short relative to grant cycles. With no accounts, recovery, export, or required warning, durable infrastructure may increase user trust more than actual recoverability. Narrow the positioning to anonymous preview continuity, make expiry and key loss unmistakable, and avoid implying workspace-grade durability until accounts or export exist.

**What would have to be true for the spec to be right anyway:** target users must understand and accept one-browser, unrecoverable, 30-day storage and still find deploy survival materially useful for their actual workflow.

## D. Independence test

**No.** A new agent can plan the persistence shape and test-hygiene work, but cannot plan a trustworthy blocking eval from this spec without inventing product policy.

Missing decisions that remain chat-shaped:

- Whether one regressing dimension blocks or dimensions combine, and whether gains may offset losses.
- How the per-PR subset is selected or rotated and how it represents the full golden set.
- The statistical definition of the noise band and the agreement metric, not only D1's eventual threshold.
- Which actions count as “last use” for retention and what expiry warning the user receives.
- Whether model roles are selected independently or the final model bundle must win end to end.
- What operational consequence follows a regression found only by the nightly full set.

## E. Edit list for the authoring session

1. **Open Decisions** — add rows for gate aggregation/trade-offs, subset selection, and noise-band decision semantics before blocking.
2. **US2 / FR-010** — name the judge–governor agreement metric separately from the still-open numeric threshold.
3. **US2 / FR-007–012** — require held-out validation or explicitly label the gate a proxy-consistency gate rather than demonstrated real-work quality.
4. **FR-013 / acceptance catalog** — add a non-compensable source-support/entailment check in addition to provenance presence.
5. **FR-004 / retention acceptance** — define “last use” and all actions that refresh the 30-day clock.
6. **US1 / Edge Cases** — require clear user disclosure of browser-key loss and expiry; decide whether advance deletion warning is mandatory.
7. **FR-004** — state that deletion cascades through messages, versions, InternalRunState, checkpoints, stored uploads, and owned provenance/source records.
8. **FR-015 / SC-011** — require final end-to-end validation of the selected model bundle and human-label evaluation for judge candidates.
9. **FR-011** — state what happens when the nightly full set finds a regression missed by per-PR checks.
10. **FR-018 / SC-010** — align the story promise with either a hard latency gate or an explicitly measurement-only target.

## F. Questions for the human

1. Should a significant drop in any one quality dimension block, or may gains in other dimensions compensate through an aggregate?
2. Is the first release's gate allowed to mean only “stable against our synthetic proxy,” or must it first predict blinded preference on held-out realistic grants?
3. Must source support be a non-compensable gate, even though grounding remains outside the literary judge score?
4. For the locked 30-day policy, which user actions refresh retention, and must the product warn before permanent deletion?
5. Should models be chosen independently per role, or must the final four-model bundle also pass an end-to-end best-value comparison?
