# Review: the factory as one whole

## Summary

**Verdict: not coherent.**
The normal planned-work path has a complete arrival-to-merge loop.
The three-lane rule leaves ordinary unplanned runtime work with no lane.
The full path can create orders before the decision-readiness safeguards it says replaced older documents.
Held-back acceptance, chat-to-engine handoff, feature rejection, and review escalation each lack an operational link.
The removals mostly have successors, but the decision-readiness replacement is named without being placed in the flow.

## Findings

### 1. Unplanned runtime work has no lane

- **Severity:** blocker
- **Confidence:** 99
- **Section:** `notes/retro/2026-10-factory-whole.md` §§1, 4a–4d
- **Evidence:** A normal-lane item must be “an order under an approved plan” (§4b). A light item must have “no runtime effect” (§4c). Full is only “a new feature, or anything that changes the architecture” (§4d). Intake nevertheless offers only an order form and a light-change form (§4a). A production bug fix, dependency repair, or small runtime change under no approved feature plan fits none of those definitions. The register requires three lanes chosen for all incoming work (`notes/retro/2026-10-harness-changes.md`, items 86–89).
- **Why it matters:** A common kind of work reaches intake and then dead-ends. Two careful readers will either invent a fourth class or force the change into a lane whose stated entry condition it does not meet.
- **Fix:** State a total routing rule. For example: runtime work under an existing approved plan is normal; all other runtime work is full unless a specifically defined emergency rule applies. Make the issue forms accept every resulting case and define what happens when the pull-request re-check discovers a mismatch.

### 2. The full path omits the decision-readiness gate that replaces the finish bar and plan delta

- **Severity:** blocker
- **Confidence:** 97
- **Section:** `notes/retro/2026-10-factory-whole.md` §§4d, 7, 12
- **Evidence:** The full flow goes directly from tasks to orders (§4d steps 6–7). Section 12 says the finish bar, plan deltas, and similar documents are “folded into the templates and the workflow's gates,” but no step checks unresolved human decisions after tasks, and no step reconciles plan/contracts/tasks after an architecture-changing decision. Section 7 says a missing decision involves the governor but does not say when code detects one. Today those two safeguards are explicit fail-closed transitions in `.specify/memory/constitution.md` §§G.1–G.2 and `docs/agent-os/FINISH_BAR_TEMPLATE.md`.
- **Why it matters:** A full feature can turn tasks into runnable orders while required product content is still open, or after a late decision has made its plan stale. The stated successor to two retired functions is not present in the described control flow.
- **Fix:** Add an explicit post-tasks decision-readiness step before order creation, and an architecture-reconcile loop after any architecture-changing lock. Name the inputs, code check, outputs, and resume point. If the artifacts themselves are removed, define the structured state that replaces them.

### 3. Chat-produced intent and spec have no handoff into the engine

- **Severity:** major
- **Confidence:** 95
- **Section:** `notes/retro/2026-10-factory-whole.md` §§3, 4d, 5, 15
- **Evidence:** The sprint manager produces intent and spec “in chat” (§4d steps 1–2), while spec review starts in the engine at step 3. Section 3 says chat conclusions are recorded in git. Section 15 says agent and chat drafts do not count until code validates them, and code alone pushes. No actor or step is assigned to validate, commit, and push the intent/spec drafts onto the run branch, nor is there an event that resumes the engine from those files.
- **Why it matters:** The spec-review step has inputs but no described producer that can make them valid engine state under the document's own write rules.
- **Fix:** Add a code-owned “ingest chat draft” transition: named files, branch, validation, commit/push, run identity, and the event that starts or resumes spec review. State what the chat session may write locally and what code must certify.

### 4. Held-back acceptance scenarios have no secure home

- **Severity:** major
- **Confidence:** 98
- **Section:** `notes/retro/2026-10-factory-whole.md` §§4b, 4d, 5, 15
- **Evidence:** A plan worker writes held-back scenarios (§4d step 4); the builder must not receive them, and a fresh evaluator runs them during review (§4b step 4). Section 5's “one home per fact” table gives them no home, writer, or access rule. If they live in the ordinary git branch, omitting them from the brief does not keep a worker with repository access from reading them. The register requires hidden test cases, not hidden requirements (`notes/retro/2026-10-harness-changes.md`, item 41).
- **Why it matters:** The quality control is either not actually held back or is unavailable to the evaluator. The evaluator's result also has no named record or consumer.
- **Fix:** Define who derives the set, where it is stored, which identities can read it, how requirement traceability remains inspectable, how the evaluator reports results, and how a failure returns to revision. Do not call scenarios held back merely because the brief omits their path.

### 5. Feature acceptance occurs after merge and has no rejection path

- **Severity:** major
- **Confidence:** 96
- **Section:** `notes/retro/2026-10-factory-whole.md` §§3, 4b, 4d, 7
- **Evidence:** Every order in a full feature runs the normal lane (§4d step 7), whose steps 8–9 merge the pull request and close the issue. Only afterward does the governor receive feature acceptance (§4d step 8). The governor is said to own acceptance (§3), but the document does not say what a rejection produces, who consumes it, whether the feature remains open, or how corrective work re-enters the flow.
- **Why it matters:** The gate has no effective “no” branch. It can report dissatisfaction, but cannot govern the already-merged feature or initiate a defined correction loop.
- **Fix:** Define acceptance state and both outcomes. Either place acceptance before the final merge/release boundary, or state that rejection keeps the feature open and code creates linked corrective orders under the same approved plan, followed by another acceptance gate.

### 6. “Needs the governor” is assigned to the reviewer but represented only as an author disposition

- **Severity:** major
- **Confidence:** 98
- **Section:** `notes/retro/2026-10-factory-whole.md` §§3–5; design-kit review contracts
- **Evidence:** The actor table says reviewers escalate by marking a finding “needs the governor”; convergence says that mark stops the loop at once (§4b). The agreed funnel says the reviewer marks it and the author cannot downgrade it (`notes/retro/2026-10-wave1.5-funnel.md` §5). But the starting design kit has no such field in `ReviewVerdict` or `Finding`; only the reviser's later `Disposition.action` can be `needs_human` (`notes/retro/sources/factory-design-kit/.factory/schemas/packets.py`). Its controller does not inspect that disposition until the following round. Section 5 of the whole-factory file does not name the required adaptation.
- **Why it matters:** Implementers can reasonably build two incompatible controllers: immediate reviewer-owned escalation, or author-owned escalation after another review round. The latter contradicts the ruling and can spend a round after a required stop.
- **Fix:** Put a non-downgradable governor-needed field in the finding/verdict contract and have convergence gate immediately on it before revision. State how the governor's lock resolves the finding and where the loop resumes.

### 7. Cutover accepts all new work before two lanes exist

- **Severity:** major
- **Confidence:** 94
- **Section:** `notes/retro/2026-10-wave1.5-funnel.md` §9 versus `notes/retro/2026-10-factory-whole.md` §§4, 11, 15
- **Evidence:** The agreed shape cuts over after Core: “the new path takes all new work; the old queue takes none.” Light and full lanes are then added during Build-out. The whole-factory invariants require one way of working, and its final flow presents all three lanes as usable. During that interval, a newly arrived light change or full feature cannot use its stated lane; routing it through normal would violate the lane definitions, while using the old path would violate cutover.
- **Why it matters:** The migration has a deliberate dead zone even though the final-state design says each phase uses only proven parts and no second way returns.
- **Fix:** At cutover, provide at least a proven lane switch with temporary light/full handling, or narrow cutover explicitly to eligible normal work and queue other arrivals without processing them. Record that temporary rule as part of the one path, not as an informal fallback.

### 8. The scorecard drops the agreed split by lane

- **Severity:** major
- **Confidence:** 99
- **Section:** `notes/retro/2026-10-factory-whole.md` §9
- **Evidence:** Section 9 defines four units—wave, feature, order, task—but does not split results by lane. The register explicitly says “Scorecard numbers are split by lane too, to show whether the lanes sort work correctly” (`notes/retro/2026-10-harness-changes.md`, item 89). The funnel carries the scorecard as Must (`notes/retro/2026-10-wave1.5-funnel.md`, C12).
- **Why it matters:** This is a direct contradiction with the agreed register, and removes the evidence needed to tell whether light, normal, and full routing is working.
- **Fix:** Add lane as a required scorecard dimension for all five measures, alongside the four aggregation units.

### 9. “Code writes every record” conflicts with workers writing report and review files

- **Severity:** minor
- **Confidence:** 93
- **Section:** `notes/retro/2026-10-factory-whole.md` §§4b, 5, 15
- **Evidence:** Workers produce “a report file” and reviewers produce verdict files (§4b). Section 5 likewise says agents draft review records. Yet §5 says factory code “writes all records,” and invariant 1 says code alone writes locks while broadly saying agents draft files. The register's more precise rule is that agents write named files and code validates and commits the records (`notes/retro/2026-10-harness-changes.md`, item 91).
- **Why it matters:** The intended trust boundary is recoverable from the register, but the whole-factory wording lets readers disagree about whether code generates record contents or only validates and persists agent drafts.
- **Fix:** Say: agents draft report, verdict, revision, and decision-request payloads; code validates and persists them; code itself authors state transitions, issue updates, statuses, pushes, pull requests, and locks.

## Answers to the five review questions

### 1. Logic

The normal planned-work loop has actors, outputs, consumers, a three-round exit, retry limits, merge, and close-out. It is logically complete for an order under an approved plan. The factory is not complete for all work: unplanned runtime work has no lane (finding 1); full-lane chat artifacts have no validated handoff (finding 3); held-back scenarios have no usable custody chain (finding 4); and feature rejection has no consumer or next step (finding 5). Review and retry loops otherwise have stated exits.

### 2. Consistency

The material inconsistencies are the missing decision-readiness transitions despite their claimed replacement (finding 2), reviewer-owned versus author-owned governor escalation (finding 6), cutover before all accepted work can run (finding 7), and omission of the agreed lane split from the scorecard (finding 8). The six blocking checks, three-round cap, cross-family rule, appetite, selected path, cast, and no-two-ways invariant otherwise agree with the register and funnel.

### 3. Ambiguity

The largest ambiguities are which lane owns ordinary runtime maintenance, how chat output becomes engine input, where held-back scenarios live, what feature acceptance can reject, and who sets the governor-needed bit. “Code writes records” also has two plausible readings (finding 9). The details explicitly left to the Wave 1.5 plan in §14 do not by themselves break the final flow, except that held-back custody and decision readiness are not on that acceptable-open list.

### 4. Completeness of removals

Orders, amendments, claims, handoffs, the status board, lifecycle, metrics, most checks, three hooks, hand-written briefs, chat spawning, and the large command all have stated successors or explicit drops. The only materially incomplete replacement is the finish-bar/plan-delta function: §12 names templates and workflow gates as successor, but §4 never places those gates or defines their state (finding 2). The user's guide, historical contracts, and private notes have stated fates.

### 5. Usability as a whole

A new session could run a normal planned order from the description. It could not safely run the whole factory without consulting the older constitution and design-kit controller to invent the missing transitions. The strongest pressures back toward the old way are: using chat to bridge intent/spec into git, manually deciding a lane for runtime maintenance, consulting old finish-bar and plan-delta rules, exposing or manually carrying held-back tests, and asking the governor in chat when the verdict format cannot express escalation.

## What I checked and found fine

- The normal-lane review loop has a finite exit: convergence, a governor-needed stop, or the round-three gate.
- Agent-step failure has a finite exit: two automatic resumes, then an alert.
- The review confidence threshold and low-confidence handling match register item 94.
- Cross-family review applies in all three lanes and matches items 90 and 95.
- The six blocking checks match the corrected register item 33.
- The main Wave 1 removals each have a stated successor or explicit retirement.
- Rule-path approval, irreversible-harm guards, secret handling, and pull-request-only `main` remain intact.
- The selected Spec Kit/GitHub Issues path, Must-plus-Should line, early cutover intent, and no parallel old/new handling are not reopened here.

## Sources

- `notes/retro/2026-10-factory-whole.md`
- `notes/retro/2026-10-harness-changes.md`
- `notes/retro/2026-10-wave1.5-funnel.md`
- `notes/retro/2026-10-factory-survey.md`
- `notes/retro/sources/factory-design-kit/`
- `scripts/factory/gates.yaml`
- `.cursor/hooks.json`
- `.specify/memory/constitution.md`
- `AGENTS.md`
- `docs/agent-os/`
