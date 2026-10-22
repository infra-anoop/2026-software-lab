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

## 1. Fidelity to the governor's decisions

Finding 1 is the exception. D1 through D8 and D10 through D24 match their named locks. The approach records those locked choices without an additional unsupported choice that I found. D16 is supported by the `wave15-runner-and-chunks` lock notes, which state that the session gathers decisions and does not implement.

## 2. Consistency across the three records

## 3. Evidence behind the reliability decisions

## 4. Failable outcomes

## 5. Rules inventory

## 6. Cost

## What I checked and found fine
