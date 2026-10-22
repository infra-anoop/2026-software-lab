# Wave 1.5 reliability, rules and approach review

## Summary

### Pull request #42

Changes needed.

### Pull request #44

Changes needed.

### Pull request #45

Changes needed.

## Findings

### 1. D9 is presented as locked, but its named lock does not lock it

**Severity:** blocker  
**Pull requests:** #42 and #44  
**Files and sections:** `notes/wave1.5/2026-10-reliability-register.md`, decision D9; `notes/wave1.5/2026-10-implementation-approach.md`, section 11; `bus/decisions/wave15-runner-and-chunks/{request,lock}.yaml`; `notes/wave1.5/2026-10-reliability-investigation.md`, section 10

**Evidence:** D9 says the chunk life cycle, failure responses, issue notifications and Cursor key were agreed in principle, and section 11 of the approach maps that decision into the build. The chosen option and notes in `wave15-runner-and-chunks/lock.yaml` lock Copilot from day one, chunk sizing, the generated command policy and overrun handling. They do not lock the life cycle, issue notifications or Cursor key. The report says the governor agreed those items in conversation, but that narrative is not the decision lock named by D9. Merging would therefore present several design details as a locked governor decision without a matching lock.

**Fix:** either add a governor-approved lock that explicitly names the D9 details, or change D9 and the approach's section 11 to present them as proposed design pending a lock.

### 2. Layer 1 still makes Copilot conditional

**Severity:** major  
**Pull request:** #42  
**File and section:** `notes/wave1.5/2026-10-implementation-approach.md`, Layer 1

**Evidence:** Layer 1 says Spec Kit is upgraded with “Copilot's only if Layer 2 needs it.” The same paragraph installs the Copilot command-line agent from day one, and D5 plus section 5 row 13 explicitly reverse the earlier conditional trim. A Layer 1 implementer could follow either instruction.

**Fix:** remove the conditional Copilot phrase and state consistently that both integrations needed by the day-one runtime switch are installed and pinned.

### 3. The reliability report leaves superseded causes and routing as current instructions

**Severity:** major  
**Pull request:** #44  
**File and sections:** `notes/wave1.5/2026-10-reliability-investigation.md`, sections 1, 3, 6 and 7

**Evidence:** the incident 1 row still says GitHub does not document the 12-hour lifetime and calls the cause unconfirmed, while sections 1 and 5 call it documented and confirmed. The summary recommendation and sections 6–7 still route spawned agents through headless processes and a watcher in the codespace, reserving Actions for long or overnight runs. D12–D15 later route every batch task—including reviews, inventories and research write-ups—to Actions, with only interactive work and short attended subtasks in the codespace. Section 7 also places the command-line agent installation in Layer 0, while the amended approach places installation in Layer 1.

**Fix:** correct incident 1's cause, and either rewrite sections 6–7 to the final interactive/batch split and layer placement or label their earlier proposal explicitly superseded by sections 9–12 and the register.

### 4. The inventory recommends keeping the old blanket workflow-dispatch ban

**Severity:** major  
**Pull request:** #45  
**File and sections:** `notes/wave1.5/2026-10-rules-inventory.md`, R35 and section 2.1

**Evidence:** R35 recommends keeping “Never run `gh workflow run`” in the interim rulebook and allowed-command policy. The later reliability design requires one Actions chunk to dispatch the next, and the approach section 10 plus register A10 narrow the rule to dispatch not being available **from the codespace**. Keeping R35 as written would prohibit a required part of the approved batch design.

**Fix:** change R35 to “do not dispatch from the codespace”; allow the trusted Actions control path to start the next chunk, with the exact command mechanism settled in implementation.

### 5. Two inventory passages still claim the outside-read correction was not made

**Severity:** minor  
**Pull request:** #45  
**File and sections:** `notes/wave1.5/2026-10-rules-inventory.md`, section 4.1 conflict 6 and Architect's comments D

**Evidence:** both passages say the approach and `notes/wave1.5/sources/README.md` still give outside-worktree reads as the cause of the freezes. At the reviewed commit, both files correctly identify web requests as the cause and retain the worktree restriction only as hygiene. Inventory row R103 is already accurate.

**Fix:** mark conflict 6 resolved and update the architect's comment to say the correction is present.

### 6. The cost note omits the new task-routing and permission-policy work

**Severity:** major  
**Pull request:** #42  
**File and sections:** `notes/wave1.5/2026-10-implementation-approach.md`, section 11 Cost; section 4 interactive and batch work; Layer 0

**Evidence:** section 11 names only Copilot from day one, the image and “chunk machinery” as newly unsized work. D12–D15 also add planning-time task classification, host routing, promotion of a subtask from interactive to batch, and git-only handover between modes. D17–D20 add refusal logging and review, generated deny forms and a version-upgrade conformance suite. Those are build and ongoing-process costs, not merely wording changes, and they are not clearly included in the three named buckets.

**Fix:** add task-mode routing and the expanded permission-policy/conformance work to A7's explicit sizing list, or state which existing unsized bucket includes each and size that bucket accordingly.

## 1. Fidelity to the governor's decisions

Finding 1 is the exception. D1 through D8 and D10 through D24 match their named locks. The approach records those locked choices without an additional unsupported choice that I found. D16 is supported by the `wave15-runner-and-chunks` lock notes, which state that the session gathers decisions and does not implement.

## 2. Consistency across the three records

Findings 2 through 5 are the remaining contradictions. The approach otherwise reflects the corrected cause of the freezes, Copilot from day one behind `AI_ENV`, the daytime codespace watcher versus long-term scheduled watcher, the ready-made batch environment in Layer 1, and the completed 240-minute codespace action.

## 3. Evidence behind the reliability decisions

Found fine, subject to the explicit evidence limits already in the report. Each incident's chosen response addresses either its supported cause or, where the cause is unknown, the observable failure:

- Incidents 1–3 are addressed by moving batch work off the codespace, the 240-minute interactive codespace and durable git checkpoints. The cited GitHub documentation for the 12-hour lifetime was not copied into this review input, so that external confirmation is **unverified, outside source**; the report's four observed 12-hour stops remain internal supporting evidence.
- Incidents 4–6 have unknown vendor causes. The hard job limit, restart from the last push, issue status and scheduled watcher address silence and lost notices without pretending to remove the vendor cause.
- Incidents 7, 9 and 10 are supported by the prompt and headless trials. D17–D20 follow the 13 Cursor trials: no override flag, correct deny patterns, structured status and version-pinned conformance tests. Copilot remains documentation-only and is correctly scheduled for confirmation in Layer 2.
- Incident 8 is addressed by an explicit dispatch from one Actions chunk to the next, rather than by relying on a codespace token.
- Incident 11 supports separating setup failure from work failure and removing per-command downloads. Whether the same package-index failures occur on GitHub runners is correctly left for measurement; the image decision also rests on preserving the chunk's time budget.

The report goes furthest at incident 5 (“probably the same class” as incident 4), but labels the cause unknown and chooses a generic time-limit response, so it does not turn that hypothesis into a false root-cause claim.

## 4. Failable outcomes

Found fine. Every register action has an observable artifact, setting read-back, branch absence, green pull request, recorded decision, measured figure or named trial. “Proposal or a recorded ‘not now’” for A14 is weak as a product result but still objectively checkable as a decision outcome.

Layers 0–2 also have falsifiable completion checks:

- Layer 0 names repository-state checks, green CI, a test pull request, rule-text uniqueness, an allow-list refusal and deliberate watcher failures.
- Layer 1 requires each named part to run in both environments at a pinned version, and requires the checkout-matching image to run tests and a type checker.
- Layer 2 requires a recorded pass or fail for all four unknowns and defines a stop on any failure.

No “done when” in those scopes depends only on a mood or an unobservable quality claim.

## 5. Rules inventory

Finding 4 is the substantive recommendation error and finding 5 is stale commentary. The sampled enforcement and bypass claims otherwise matched their sources:

- R1, R2, R4 and R76 match the committed live-settings exports: pull requests, deletion and non-fast-forward rules are active; the three status checks are required; strict freshness is off; approval count is zero; code-owner review is off; there are no listed bypass actors.
- R27 matches `scripts/factory/src/factory/gates/pr/verdict.py`: it checks that a verdict exists, derives and compares declared model families, and checks for a handoff, but never tests the verdict's accept/reject decision.
- R29 matches `factory.toml`: identity mode is `recorded`, so a written governor actor is not independently verified.
- R43 matches `.github/workflows/db-bootstrap-tests.yml`: the tests are path-filtered and the workflow is absent from the required-check list, so it warns in practice rather than blocking merge.
- R76 matches `.github/CODEOWNERS` and the settings export: ownership is declared, but GitHub does not currently require code-owner approval.

The keep/rewrite/drop reasons on those sampled rows follow the cited evidence and the approved approach, apart from the superseded R35 recommendation. Comparing the inventory against all of `AGENTS.md` and the constitution found no omitted rule; combined or rewritten rules are explicitly cross-referenced rather than silently absent.

## 6. Cost

Finding 6 is the additional likely work not flagged by the cost paragraph. D10–D11 and D19's block/status path can reasonably be included in the named chunk machinery, and D21–D24 are covered by the image bucket. The task-mode routing and permission conformance work need an explicit home before tranche 1 is re-sized.

## What I checked and found fine

- All six decision locks and their requests against register D1–D24.
- All eleven incidents against the report's evidence, register closure and final approach.
- Every register action's done condition and Layers 0–2 completion criteria.
- Rules inventory summary and recommendations in full; sampled hard, warned and prose rows against committed settings, code and source rules.
- `AGENTS.md` and the constitution for inventory omissions.
- The corrected freeze cause, Copilot switch, watcher placement, batch environment and codespace timeout across the three records.

## Triage (architect, 2026-10-22)

The text above is the reviewer's, unchanged (reviewer commit `810a69f`). All six findings are accepted. Each fix is a separate commit on the pull request named.

| # | Finding | Triage | Fix | Pull request |
|---|---------|--------|-----|--------------|
| 1 | D9 has no lock that names its details | Accepted. The governor's words exist ("Your narrative - all looks good to me - including notifications and cursor API key", chat, 2026-10-21 10:16 PT), but they were recorded only in the report, not in a lock. Every other lock in this series was recorded by the architect from the governor's chat words, so a lock recorded now from the same words follows the same practice. One difference is stated in the lock: the report's section 10 was written by the architect right after that message, from the narrative he approved, so its wording is put to him for confirmation | New decision `wave15-chunk-lifecycle` (request and lock); register D9 and approach section 11 cite it; the governor confirms the section 10 wording | #44, #42 |
| 2 | Layer 1 still makes Copilot conditional | Accepted. Stale phrase left from before D5 | Layer 1 installs both Spec Kit integrations, pinned | #42 |
| 3 | The report leaves superseded causes and routing as current | Accepted | Incident 1's cause corrected (documented, confirmed); the summary's recommendation and sections 6 and 7 marked superseded by sections 9 to 12 and the register; the status line updated | #44 |
| 4 | R35 keeps the blanket ban on starting workflows | Accepted | R35 reworded: not from the codespace; the trusted Actions chain may start the next chunk, the exact mechanism settled at build time | #45 |
| 5 | Conflict 6 and comment D say the outside-read correction is not made | Accepted. True when written (2026-10-20), stale since pull request #42's commit `930852e` | Both marked resolved, citing that commit | #45 |
| 6 | The cost note omits task-mode routing and the permission-policy work | Accepted | Section 11's cost paragraph names five unsized items: Copilot from day one, the image, the chunk machinery, task-mode routing (D12 to D15) and the permission policy with its conformance test (D17 to D20). The sprint manager's sizing order (`wo-20261022-wave15-a7-sizing`, register A7) already lists the last two | #42 |

Verdict files: the packet asked for `decision: revise` and severities blocker, major and minor, which the Wave 1 record schema does not accept (rules inventory, conflict 8). The three verdicts on the pull request branches are translated (revise to reject, major to blocker, minor to nit), each finding keeping the reviewer's severity in its text; the originals are at reviewer commit `810a69f`. The round-2 packet uses the schema's words.

Round 2: because finding 1 was a blocker, a short cross-family re-check of these fixes follows, under the same packet.
