# PR review — Factory user's guide

## Decision

**Reject.** The guide is substantially faithful to the canonical sources and its per-intent walk-through matches the order records and verdicts, but R-UG1 is a blocker because it overstates the credential isolation of the factory's trust root.

## Findings

| id | severity | tag | location in the guide | issue | fix |
|----|----------|-----|-----------------------|-------|-----|
| R-UG1 | Blocker | process | §4, “Credentials by role,” first bullet | “CI's trusted job holds the only token allowed to post `factory/*` results” is unsafe and contradicts the guide's own §7 plus `plan.md` and `contracts/gates.md`. The Codespace user token can post statuses, and another Actions workflow can post the same context; source pinning prevents a non-Actions source from satisfying the required check, but it does not make the trusted job's token uniquely capable. A governor relying on this sentence could treat the known fake-green gap as closed before the App design closes it. | State the exact boundary: by policy only the trusted job posts `factory/*`; its token is the only factory CI job token granted `statuses: write`; the Codespace account and other Actions workflows remain technically capable, while the required `factory/gates` context is source-pinned to GitHub Actions. Keep the known fake-green gap explicit until the App work closes it. |
| R-UG2 | Nit | process | §6, “AskQuestion prompts” | The exact “two to four options, recommended first” presentation is not a rule in the listed canonical sources. The paragraph does identify it as current kickoff-skill behavior, but amid a guide that says it adds no rules it reads like a durable factory contract and is implementation detail rather than a principle. | Label it explicitly as the current Cursor kickoff convention, not canonical factory policy, or remove the exact option-count/order details and retain only the sourced requirement for plain choices with stakes and architecture consequences. |
| R-UG3 | Nit | product | “Open questions for the governor,” question 5 | The main-branch statement is accurate at reviewed SHA `a2f782c`: `bus/decisions/` is empty there. However, a first decision request now exists on the unmerged `wo/wo-20261007-factory-retro-additions` branch (`wave1-token-usage`), so “every decision to date” and the broad question are stale without a branch qualifier. | Say that `main` has no decision requests yet, while the first request is being exercised on the unmerged retro-additions branch; narrow the question to whether that new practice is now the expected Wave 1 path. |
| R-UG4 | Nit | product | §§2, 5, and 7, task/requirement references such as `FR-012b`, `T104`, `I-G2`, and `D7` | The guide defines T-star review notation but not the recurring source-id prefixes. A non-coding governor must infer whether each id is an intent, requirement, task, or decision. | Add one short legend at first use: `I-` intent, `FR-` requirement, `T` task, and `D` decision. Keep the plain-language name before each id. |
| R-UG5 | Nit | process | §1, “State is derived, never hand-written” | “No file holds a `status: done` field” overstates the scope. The schema prohibition and derived lifecycle apply to bus messages/work-order state, while other repository artifacts legitimately carry approval status or task checkboxes. | Change this to “No bus record holds a hand-maintained work-status field”; keep the derived-state explanation unchanged. |

## Accuracy spot-check

Checked more than 15 concrete claims against the named sources, including: product/workload framing; SNR; Spec Kit phase gates; failable outcomes and catalog evidence; Wave 1 red-first limitations; different-family review and recorded inputs; intent presence/effective coverage; cattle discipline; letter-versus-intent fidelity; progressive HITL; the three-round harm bar; all four roles; ambiguity handling; Wave boundaries; gate classes and overrides; trusted-base evaluation; Open Decision, plan-delta, and finish-bar semantics; work-order fields and append-only records; claim cap/overlap behavior; required check names; board sections; App/T036b/T065 state; and the known rough edges.

The per-intent example matches `wo-20261007-factory-per-intent`: order at 16:00, claim at 16:00:30, amendment at 16:20, rejected test review at 16:24, accepted test review at 16:35, accepted PR review at 17:00, handoff at 17:05, run-complete at 17:06:47, 66.3 minutes, zero governor interrupts, and two deviations. PR #30's merge and subsequent task bookkeeping also match the main-branch records.

## Triage (orchestrator, round 1)

All five findings accepted; the worker applies them as the reviewer proposes. For R-UG3: since this review, the first decision request merged to `main` (PR #34, `bus/decisions/wave1-token-usage/`), so open question 5 becomes "decision requests started on 10-07; should every governor decision go this way from now on?"

## Round 2

### Decision

**Accept.** R-UG1 through R-UG5 are resolved, and the fixes introduced no regression within the round-2 scope.

### Findings

| id | severity | tag | location in the guide | issue | fix |
|----|----------|-----|-----------------------|-------|-----|
| — | — | — | — | No findings. | — |
