# Wave 1.5 implementation approach review

## Summary

Verdict: **sound with changes**.
The layered direction is credible and gives the governor useful evidence much earlier than the plan it replaces.
It is not ready to approve unchanged: six major gaps would otherwise surface during the build.
The largest are safe repeat/concurrency, the missing producer for the full lane's pre-code tests, and an incomplete cost picture.
There are no blockers; the fixes are bounded amendments to this approach and its sizing, not a change of direction.

## Findings

### 1. Major — The short-workflow design names idempotence but does not design it

**Where:** implementation approach sections 2.4 and 4, Layers 3 to 5; product shape sections 5, 10 and 14.

**Evidence:** Each Spec Kit invocation gets a unique run id and its own local state directory; its native resume command resumes that particular directory. The copied workflow reference does not provide cross-run deduplication or a GitHub-state reconciler ([Spec Kit workflow reference](https://github.github.com/spec-kit/reference/workflows.html), “State and Resume” and “Can I run the same workflow multiple times?”). The approach replaces saved cross-job run state with issue, pull-request, label and commit state, but does not define a durable attempt id, a single legal next-state calculation, a concurrency key, or idempotency keys for pushes, comments, labels and pull requests. Layer 5 merely says those operations become safe to repeat, after Layers 3 and 4 have already used the mutating path. Two label events or a delivery repeated while the first job is live can therefore start two workflows that both see the same state and act. A job killed after an external write but before recording it has the same ambiguity.

**Fix:** Before Layer 3 mutates GitHub, add the minimum recovery contract: one durable attempt/state record per issue; legal state transitions; a concurrency group per work item; stable idempotency keys; read-before-write checks for branch, commit, comment, label, status and pull request; and ownership/lease expiry for a dead job. Move the duplicate/concurrent-trigger and “killed immediately after the external write” trials into Layer 3. Layer 5 can still add retries, deadlines and the watchdog.

### 2. Major — “Superpowers as shipped” is not a machine contract

**Where:** implementation approach sections 2.5, 2.6, 3 and 5 row 2; Layer 4.

**Evidence:** The pinned source really is MIT licensed and contains three prompts and three scripts. Its implementer reply has four status words and a short reply, and its reviewer gives spec-compliance and task-quality verdicts with Critical, Important and Minor findings. But these are Markdown prompt templates, not a versioned field schema. The shipped task reviewer does not emit the proposed separate tests-against-spec verdict, a governor flag or a cause field. The shipped skill also owns a five-round loop and controller rulings, while this approach owns a three-round loop and governor stops (`notes/wave1.5/sources/superpowers-v7.0.0/SKILL.md`, “The Process” and “The fix loop”; `task-reviewer-prompt.md`, “Output Format”). The approach discloses the added fields, but “a thin reader, field for field as Superpowers defines them” implies a machine definition the bought part does not supply.

**Fix:** Call this a pinned lab profile over the shipped prompts, not the packet set unchanged. Define the exact parseable envelope the workflow owns, keep the upstream prompts/scripts unmodified beside the profile, and add adapter tests for all four implementer statuses, both reviewer verdicts, every severity, malformed output and the three lab fields. Size prompt/profile maintenance and repair handling as ours.

### 3. Major — The full lane reviews tests before code without a step that creates the tests

**Where:** implementation approach section 2.6 points 2 to 5; Layer 7; sizing Layer 7.

**Evidence:** The builder is to write the non-example tests and, in the full lane, types and interfaces exist before code. The full lane then requires a separate test review before any code. Layer 7 sequences spec review, plan, plan review, tasks and “the feature's test review before any code,” but has no workflow step that assigns a builder to commit red tests and interface stubs for that reviewer. The sizing has 1.35 / 2.75 hours for the test-review workflow, but no distinct test-authoring order. A reviewer cannot judge tests that do not yet exist.

**Fix:** Add a full-lane test-authoring step after tasks: create interface stubs and red tests only, commit them, and produce an example-to-test manifest. Run the independent test review on that commit; only an accepted verdict starts implementation. State how normal-lane changes obtain their approved example set before the combined build step. Re-size the new authoring/revision path without changing the sprint manager's estimates here.

### 4. Major — Example IDs do not by themselves protect test intent

**Where:** implementation approach section 2.6 points 1, 2 and 7; Layer 4; sizing recommendations 6 and 8.

**Evidence:** An ID-presence check can pass if a test is skipped, asserts nothing, no longer tests the given/when/then behaviour, or maps a non-executable example to a token test. The note says changes to builder-authored tests are visible “with their reasons,” but defines no record that requires a reason or baseline against which a deletion or weakening is detected. It also requires a different author for examples without recording that provenance. The shipped reviewer checks tests generally, but does not provide these mechanics (`task-reviewer-prompt.md`, “Tests” and “Part 1: Spec Compliance”).

**Fix:** Replace the bare ID check with a manifest that maps every example id to one of: automated test, human-observed proof, or an explicitly approved non-automatable check. Reject skipped/expected-failure placeholders unless the manifest carries an approved reason. Record example author, test author, test path and the reviewed test commit. Diff test changes after review, require a structured reason for changes to builder-authored tests, and send protected-example changes through the decision pause. Keep k=3 as a sensible starting heuristic, but allow the spec author to choose 1–5 per requirement and tune it from the recorded causes rather than treating three as a quota.

### 5. Major — Several product-shape obligations disappear without a section 5 row

**Where:** implementation approach sections 4 and 5; product shape sections 4a, 7, 8, 9, 11 and 14; funnel sections 2, 4 and 8.

**Evidence:** Section 5 says every variation is listed, but it does not list the change from one workflow with a lane switch to several stage/event workflows. Nor do the layers carry the Wave 1 failure inventory, an open-decision list with age, per-check reason/severity/track record, the Wave 1 baseline, or a concrete reviewer roster including the product competition seat. These were in the agreed shape or the Must-plus-Should line. Layer 4 also creates change and feature forms, while the product shape names change, order and feature intake; automated order creation may make an order form unnecessary, but that is still a conscious variation.

**Fix:** Add section 5 rows for the multi-workflow topology and any intentionally dropped obligations. Restore the obligations that remain: assign the failure inventory before reliability design, open-decision ageing with decision handling, check metadata in the check audit, the baseline in measurement, and the stage/lane reviewer roster in policy/full-lane work. Say explicitly whether orders are automation-only and therefore need no human issue form. Add sizes for restored work.

### 6. Major — The headline cost comparison hides the bottom-up pessimistic total

**Where:** implementation approach section 4; sizing “Summary” and “Across all layers.”

**Evidence:** The task arithmetic is internally correct: the nine layers total 90 / 206.5 agent-hours; walkthroughs and sprint management add 5.5 / 10.5, for 95.5 / 217. The test-first changes net about +5.25 likely hours, also consistent. The approach instead presents about 155 as the “realistic bad case” and says it is below the locked 182 pessimistic appetite. The sizing explains that 155 is roughly likely × 1.6 and that 217 assumes every task goes badly. Both views can be useful, but comparing the aggregated 155 to an appetite originally labelled pessimistic while omitting the explicit 217 makes the risk look within the ceiling when the bottom-up pessimistic sum is 35 hours above it. Findings 1, 3 and 5 also identify work that is not yet sized; nothing obsolete remains sized for the held-back store.

**Fix:** Show all three numbers together in the approach: 95.5 likely, about 155 correlated/realistic bad case with its method, and 217 sum-of-task pessimistic. State that the last exceeds the 182 ceiling and let the governor decide how to interpret or reshape the risk. Ask the sprint manager to re-size the durable transition/idempotency contract, test-authoring and test-integrity flow, and restored product obligations. Also either adopt or reject explicitly the sizing note's recommendation to move the first Logfire record into Layer 3, so the post-Layer-3 re-estimate has measured run data.

### 7. Minor — One factual phrase is broader than its own evidence

**Where:** implementation approach section 2.1.

**Evidence:** `git diff --shortstat 19a06d3 origin/main` returns `538 files changed, 55921 insertions(+), 36 deletions(-)`, exactly supporting the quoted counts. It does not support “Wave 1 only added things,” because it also records deletions; it supports “almost entirely additive.” The copied GitHub changelog does support the separate claim that pull requests opened by `github-actions[bot]` with the default token create workflow runs that wait for write-user approval ([GitHub changelog, 2026-06-11](https://github.blog/changelog/2026-06-11-bot-created-pull-requests-can-run-workflows-if-approved/)). The supplied sources do not independently establish that an App token avoids that hold, but Layer 2 correctly treats that as an experiment rather than an assumed fact.

**Fix:** Change “only added things” to “was almost entirely additive.” Keep the App behaviour phrased as an unknown until the Layer 2 proof passes.

## What I checked and found fine

- **Fidelity:** Apart from finding 5, the layers preserve the three lanes, cross-family review, governor decisions, feature acceptance, irreversible-harm guards, scorecard, removals and the five exit criteria. The ten declared variations are visible and understandable.
- **Reliability:** The host is independent of the laptop, waits become GitHub events, a decision answer can trigger a new job, and an outside scheduled watchdog is the right bottom-rung alert. Finding 1 is the missing safety design, not a rejection of short workflows.
- **Buying versus building:** Spec Kit does supply commands, prompts, shell steps, gates, loops, branches, per-step runtime/model configuration and local exact-step resume. Its state is documented at `.specify/workflows/runs/<run_id>/`, so the note is right that an ephemeral Actions machine loses it unless it is persisted. Superpowers' contents and MIT licence match the note. Finding 2 is about the adaptation boundary.
- **Layer order and proof:** Install and configure precede the first run; the bought-runtime unknowns are tested before commitment; policy follows a default run; each layer names observable pass/fail evidence and a governor action. Findings 1 and 3 identify the two material ordering holes.
- **Facts:** The Wave 1 diff counts, Spec Kit control-flow and state claims, Superpowers file count/licence/status vocabulary, and default-token approval claim checked out against the provided evidence. Cursor/Copilot dispatch and App-token behaviour remain appropriately assigned to Layer 2 experiments.
- **Clarity:** The purpose, contents, done condition and proof for each layer make the governor's experience and decision points readable. Section 7 collects the settings only he can apply.
- **Test-first shape:** Independent examples, small orders, fast in-step test loops, interfaces first, a wrong-test escape and cause tracking are coherent ways to seek faster convergence. Three examples per requirement is a reasonable tunable starting point, subject to finding 4.
- **Sizing:** Every currently named implementation block has a recognizable task except the gaps identified in findings 1, 3 and 5. The columns, layer totals, test-first delta and likely total reconcile, and the held-back store has been removed rather than double-counted. Finding 6 is the required correction to the risk presentation.

## Re-check of the triage

1. **Closed.** Per-issue concurrency, a stage label moved last, read-before-write markers and the two Layer 3 failure trials form a sufficient small idempotency design; attempt records, leases and a separate state machine are not needed to close the original gap.
2. **Closed.** Section 2.5 now calls the parseable addition a lab-owned profile over unmodified upstream prompts, defines repair/failure behaviour, and the sizing counts it as ours.
3. **Closed.** The full lane now has a sized tests-and-stubs step after tasks, and implementation cannot start until its separate test review accepts.
4. **Closed.** Each example names automated or observed proof; protected tests cannot be removed, skipped or expected to fail; wrong examples go to the governor; and reviewer-visible reports and diffs cover changes to builder-authored tests. Separate provenance records are unnecessary for this workflow.
5. **Closed.** The omitted obligations are restored and sized, while the multi-workflow topology and automation-only order intake are explicit variation rows.
6. **Closed.** The note and sizing show likely, correlated bad-case and all-pessimistic totals together, disclose the ceiling overrun, size the added work and move first-run telemetry into Layer 3.
7. **Closed.** Section 2.1 now says Wave 1 was “almost entirely additive,” matching the measured insertions and deletions.

