# Review packet — Factory v2 delta P* (D5 trusted-base CI)

## Meta

| Field | Value |
|-------|-------|
| Packet id | 2026-10-05-factory-v2-d5-delta-pstar |
| Status | ready |
| Gate | P* (delta, constitution §G.1 step 4) |
| Brief | `docs/agent-os/PLAN_REVIEW_PROMPT.md` (+ `docs/agent-os/STACK_POSTURE.md`) |
| Feature dir | `specs/001-factory-v2/` |
| Commit | `2d7e412` on `wo/wo-20261004-factory-slice-c` |
| Agent mode | spawned-reviewer |

## Context to read first

- `docs/agent-os/SPAWN_REVIEWER.md`
- Brief above (job text below the horizontal rule). This is a **delta** review: review only the architecture changed by lock D5 and its consequences, not the whole plan again.
- `specs/001-factory-v2/PLAN_DELTA.md` (scope, analyze result, open gaps)
- `specs/001-factory-v2/spec.md` Open Decisions D5 (locked) and D6 (open), FR-022a
- `specs/001-factory-v2/plan.md` Architecture (CI topology / trust boundary), `research.md` superseded decision row, `contracts/gates.md`, `tasks.md` T094–T103
- `specs/001-factory-v2/PR_REVIEW_SLICE_C.md` (PR-C1…C6 and triage) and `PR_REVIEW_SLICE_B.md` if present (red-first executes PR code)
- Prior plan review: `specs/001-factory-v2/PLAN_REVIEW.md` — continue P* numbering; do not reuse IDs

## Artifacts under review

- The D5 delta: two-workflow split (`pull_request` read-only evidence job → `workflow_run` trusted gate job running main's code, PR head as data only), red-first via untrusted evidence artifact, bootstrap of Slice C's own PR, CP2 exit proof (first trusted-judged PR + always-pass probe PR).
- Analyze High gaps to rule on explicitly:
  1. PR test code can forge its own red-first evidence (no credential reachable).
  2. Codespace token / future GitHub App can post `factory/*` statuses outside CI — should branch protection pin those checks to the GitHub Actions app as source?
- Open Decision D6 (who: human): when the "factory checks required" branch-protection setting turns on relative to Slice C's merge. Give an architecture opinion only; the governor decides.

## Owned paths (may edit)

- `specs/001-factory-v2/PLAN_REVIEW.md` (append a `## Delta review — D5 (2026-10-05)` section)
- `bus/orders/wo-20261004-factory-slice-c/verdict-05.yaml` (same verdict schema as prior verdicts; family fields required)

## Forbidden paths (do not edit)

- Everything else, including `plan.md`, `spec.md`, contracts, code, tests, workflows, `deploy/secrets/`

## Definition of Done

- [ ] Delta review appended; findings use P* prefix continuing prior numbering; severity + tag (product | process | arch)
- [ ] Explicit ruling on both analyze High gaps and on SOTA fit (is `workflow_run` + artifact the current recommended GitHub pattern; any better-fit alternative, e.g. required-workflow / rulesets / check-run app source pinning)
- [ ] ≥1 strength, ≥1 Debate where a real fork exists
- [ ] verdict-05 written; push branch `review/wo-20261004-factory-slice-c-pstar`; stop

## Out of scope

- Re-reviewing Slices A/B/C code; implementing anything

## Governor locks required

| Lock | Value or `await Debate` |
|------|-------------------------|
| D5 trusted-base CI | locked 2026-10-05 (governor) — do not reopen the choice; review its realization |
| D6 factory-checks-required timing | await governor |
| Spawn-guard log-only | locked 2026-10-04 |

## Fidelity (constitution §I)

| Lock | letter \| intent | Notes |
|------|------------------|-------|
| D5: PR-head code never runs with status-write | letter | attack any path where it could |
| D5: gate changes take effect after merge | letter | |
| No `pull_request_target` + head checkout/execute | letter | |

## Stop / escalate if

- `PLAN_DELTA.md` or the D5 row is missing at the commit above
- Brief and packet disagree on deposit path
