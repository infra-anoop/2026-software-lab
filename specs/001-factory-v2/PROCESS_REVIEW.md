# Process review — Factory v2

### A. Executive verdict

`Do not approve process yet`

This is a credible dogfood vehicle: lab intent is explicit, observed sprint-01 failures are represented as seeded violations, and the spec preserves surface outcomes rather than treating process artifacts as success. Process approval is blocked by two internal contradictions in the proposed executable policy: mandatory drift gates block categories that the gate framework says may not fail closed, and the traceability removal test cannot produce the stated result at the declared 90% threshold. The bootstrap and constitution-2.0 paths also need stronger evidence contracts so the factory cannot certify its own transition through prose or semantic thinning. Resolve the blockers before planning; the remaining debates can then sharpen scope without changing the product bet.

### B. Findings table

| ID | Severity | Lens | Spec locus | Finding | Suggested resolution (for human) |
|----|----------|------|------------|---------|----------------------------------|
| R1 | Blocker | Learning vs cargo-cult | [process] US3 scenarios 1–5 and 7; FR-012–018; US4 scenario 3; FR-020; I-P9 | The executable policy is contradictory. Red-first, test-seam, owned-path, hidden-deferral, fidelity, and catalog-linkage violations are required to block a PR or refuse issuance, while FR-020 permits fail-closed behavior only for spend, secrets, irreversible operations, or governor-owned decisions and otherwise requires a logged deviation. Most US3 violations are outside those four categories. A plan cannot assign a valid fail mode without violating one of the spec's shalls. | Lock one coherent taxonomy before plan: either add an explicit integrity/acceptance category to the allowed fail-closed set, or change the affected drift checks to non-blocking flags/deviations and revise SC-002 accordingly. Define whether “refuse,” “block,” and a failing required CI check are all `fail_closed`. |
| R2 | Blocker | Failable outcomes + acceptance catalog | [process] US5 independent test; SC-005; `acceptance.md` `trace.coverage`; `intent.yaml` target | The core traceability test is mathematically inconsistent. There are 49 intents and the target is 90%; removing the only mapping from one intent leaves 48/49 intents mapped (about 98%), while removing one mapping from a multiply mapped intent may leave 100% mapped. Therefore “removing any mapping fails” and “coverage drops below target” cannot both follow from the declared metric. This prevents a cold agent from writing the contract test without inventing a different rule. | Separate two gates: schema completeness requires every intent to retain at least one mapping (100% presence), while the 90% score measures a different quality dimension, such as mappings backed by implemented checks rather than merely `planned` or human labels. Make the seeded mutation remove all mappings from one intent and state which gate fails. |
| R3 | Debate | Failable outcomes + acceptance catalog | [process] US8 scenario 2; FR-033–034; check schedule P2; `intent.yaml` conflicts | Constitution 2.0 and lean guidance are on this version's P2 finish bar, but neither has a dedicated failable SC or acceptance-catalog row. “Reflects the resolved conflicts” and “only pointers and rules not yet enforceable” permit a self-modifying factory to pass a version-string check while silently thinning shared-code, ambiguity, fail-mode, or fidelity semantics. The intent file gives source material, not an acceptance contract. | Add catalog rows for each resolved conflict and for preservation of non-enforceable invariants/pointers; use semantic or structural assertions plus independent review rather than a version-only check. Make the constitution diff an explicit governed artifact of a work order. |
| R4 | Debate | Artifact bus / bootstrap | [process] Edge case “bootstrap”; sprint charter Wave 1 | The bootstrap says Wave 1 is held to “manual equivalents” and later checked retroactively, but it defines neither the evidence artifact nor what happens when a new gate rejects the PR that created it. Steelman: some bootstrap exception is unavoidable. Attack: without immutable evidence and a rejection/remediation rule, this is precisely the self-attestation gap the factory is meant to remove. | Specify a bootstrap ledger or verdict message per Wave 1 PR, name the manual checks and reviewer, require retroactive results to be attached, and define reject/remediate/override behavior before Wave 2 may start. |
| R5 | Debate | Packet readiness | [process] `acceptance.md` schema and all `how: auto` rows; FR-018 | The catalog declares that every automatic row must link to a real test/eval once one exists, but its table has no test/eval reference field and every automatic row is currently unlinked. It is reasonable for tests to be planned at spec time; it is not reasonable for the durable catalog shape to make the future invariant unrepresentable without an unmentioned schema change. | Add a nullable `evidence_ref`/`test_eval_id` field now, define the permitted planned sentinel, and make the linkage gate switch from planned to required at the test/task boundary. |
| R6 | Debate | Dual intent / scope discipline | [process] Check scheduling P1/P2; Assumptions; I-M3 | P1 plus P2 is declared the finish bar, while P2 is simultaneously “stretch → Wave 2”; the set includes a broad lint pack, reviewer rubric, correction mining, post-mortem gating, CODEOWNERS policy, constitution rewrite, guidance rewrite, and mutation. Steelman: the factory must be real gym equipment, not a toy schema. Attack: this breadth can consume the sprint and violate the explicit 3-day-plus-2 guardrail without a machine-readable cutoff or true-waive path. | Give each P2 check one unambiguous wave and exit criterion. State which P2 rows are required before Factory v2 approval versus before sprint close, and promote any finish deferral to the later finish-bar inventory rather than leaving “stretch” as scheduling prose. |
| R7 | Later | Spec Kit shape | [process] US1–US9 priorities and dependencies | The stories are testable but not independently viable in the template's sense: US2 depends on bus/visibility, US7 explicitly depends on US1/US3/US4, and eight stories are P1/P2. This weakens story priority as a planning signal and encourages architecture-by-check-list. | In plan, group stories into independently demonstrable slices (observe, enforce, learn) and preserve dependencies explicitly; do not pretend every story is an independent MVP. |
| R8 | Nit | Dual intent | [process] Framing; US1–US9; SC-001–009; acceptance catalog | **Strength:** the spec explicitly makes the factory the product, traces requirements to stable intent ids, names observed failures as seeded violations, separates aspirational scorecard targets from pass/fail outcomes, and preserves a real workload and board/PR outcomes. This satisfies the dogfood requirement better than a folder-and-label process exercise. | Preserve this framing and the seeded-fixture approach while resolving the policy contradictions; do not replace these outcomes with counts of artifacts created. |

### C. Adversarial positions

1. **Position: this feature is a weak lab vehicle — strongest case**

   It risks measuring the factory by the amount of factory machinery it creates. Forty-nine intents, thirty-six requirements, nine outcome classes, a typed message taxonomy, a pattern catalog, a gate registry, scorecards, correction mining, and a constitution rewrite can all become internally consistent while no unattended run improves. Several metrics count mappings or records rather than effective enforcement, and most checks are still `planned`. The self-referential bootstrap lets the system author the rules by which it later judges itself.

   *What would have to be true for the spec's process stance to be right anyway:* seeded violations must exercise real PRs, Wave 1 must leave immutable independently reviewed evidence, and the scorecard must compare actual governor-found drift/rework against the machinery's verdicts—not merely count artifacts.

2. **Position: kill or change one process choice in the spec — strongest case**

   Change “intent coverage ≥90%” as currently defined. Steelman: a visible percentage gives the governor one comprehensible signal and allows a small residue of honestly human judgment. Attack: because any planned or human mapping counts, the score rewards annotation, not enforcement; meanwhile the spec separately requires every intent to have a mapping, making 90% redundant and its removal test false. It invites gaming exactly where the feature claims to prevent cargo-cult traceability.

   *What would have to be true for the spec's process stance to be right anyway:* 100% mapping presence must be a schema invariant, while the 90% metric must measure implemented, passing, non-duplicative evidence coverage with explicit treatment of human-only judgments.

### D. Independence / harness test

No. A cold agent can run specify→review, but it cannot produce a non-invented plan and contract suite from the current artifacts. It must choose whether US3 drift violations block or merely log deviations (R1), invent traceability semantics that reconcile 100% presence with a 90% target (R2), and decide how constitution-2.0 semantic preservation and bootstrap evidence are proved (R3–R4). Bus transport is correctly reserved for plan Architecture, and the spec otherwise supplies enough entities, scenarios, locks, and acceptance classes to proceed once those process semantics are locked.

### E. Edit list (process-only)

- **US3 / FR-020:** Define one fail-mode taxonomy and reconcile every “blocked,” “refused,” and “flagged” outcome against it.
- **US5 / SC-005:** Split 100% mapping presence from the 90% effective-evidence metric; repair the removal mutation.
- **Acceptance catalog:** Add a nullable test/eval evidence-reference field and its lifecycle rule.
- **US8:** Add explicit acceptance rows for each constitution conflict resolution and lean-guidance preservation.
- **Bootstrap edge case:** Name the immutable manual-equivalent evidence, independent reviewer, retroactive check, and failure disposition.
- **Check scheduling:** Remove “stretch → 2” ambiguity by assigning every P2 check a wave and finish checkpoint.
- **Scorecard definitions:** Distinguish `planned`, `exists`, passing, human-judged, and effective mappings in coverage.
- **Plan inputs:** Carry observe→enforce→learn dependency slices forward without treating the check list as Architecture.

### F. Questions for the human

1. Should integrity gates such as red-first, owned paths, and hidden deferral be allowed to block, or must they proceed with logged deviations under the narrow fail-closed policy?
2. Should intent coverage mean 100% have some mapping plus ≥90% have implemented evidence, or is a different denominator intended?
3. What immutable evidence must exist for each Wave 1 “manual equivalent,” and does any failed retroactive gate prevent Wave 2?
4. Must constitution 2.0 preserve each conflict resolution through explicit acceptance rows, or is independent human review the intended semantic gate?
5. Which P2 checks are required for Factory v2 approval, and which are only sprint-close obligations?
