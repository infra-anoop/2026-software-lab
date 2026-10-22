# Wave 1.5 reliability, rules and approach review

## Summary

### Pull request #42

Changes needed.

### Pull request #44

Changes needed.

### Pull request #45

Review in progress.

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

## 5. Rules inventory

## 6. Cost

## What I checked and found fine
