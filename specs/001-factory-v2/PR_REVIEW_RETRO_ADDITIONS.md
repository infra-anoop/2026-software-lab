# PR review — retro additions

## Decision

reject

## Findings

| id | severity | tag | location | issue | fix |
|----|----------|-----|----------|-------|-----|
| R-RX1 | Blocker | process | Section 13, “Where it lives” | The statement that both the spec-review prompt and spec template are rule paths is false. `docs/agent-os/SPEC_REVIEW_PROMPT.md` is protected by `.github/CODEOWNERS` and named by `AGENTS.md` rule 11 through `docs/agent-os/`; `.specify/templates/overrides/spec.md` is not covered by either rule-path list. This would cause the governor to act on an inaccurate approval claim. | Name the two concrete paths and say only the review prompt is currently a rule path. If protection for the spec template is desired, present that policy change separately rather than describing it as already in force. |
| R-RX2 | Debate | process | Section 14, “What git cannot measure” | The repo does not establish that stored agent transcripts omit tool output, or that tool output is “most of the tokens.” No transcript evidence was available in this review environment, so both assertions are unverifiable here. | State only what was verified, or qualify both claims as an unverified limitation and request a measured Cursor usage export before drawing token-allocation conclusions. |
| R-RX3 | Debate | process | Section 17, option A and option B | The 2,000–4,000-token wake-up estimate has no stated measurement basis, and “re-reads the whole context, so it costs far more” ignores unknown caching and billing behavior. Option B’s near-zero context claim also depends on an alert bridge that can notify the orchestrator without an AI poll; that mechanism is not named. | Keep the qualitative comparison, mark numeric costs as unmeasured, distinguish context-window growth from per-call input usage, and name the non-AI notification mechanism required by option B. |

## Triage (orchestrator, round 1)

| id | Ruling | Change |
|----|--------|--------|
| R-RX1 (Blocker) | Accept | Section 13 names both files. Only `docs/agent-os/SPEC_REVIEW_PROMPT.md` is a rule path; protecting the spec template is listed as a separate choice |
| R-RX2 (Debate, process) | Accept | Section 14 cites Cursor's transcript note for "tool calls and results are excluded", drops "most of the tokens", and draws no token conclusions before the usage export |
| R-RX3 (Debate, process) | Accept | Section 17 marks the numbers as an unmeasured guess, separates context growth from per-call token use, names Cursor's watched background-terminal output as option B's alert path, and states that path's limit |

The branch also gained section 18 and a governor decision request after this review was started (`f5ee83d`, `fd53ba1`); round 2 covers them.

## Round 1 review notes

The five governor items are all present, the Wave 1.5 candidates remain choices, the orchestrator’s preference is labeled as its lean, the user-guide order exists on `origin/wo/wo-20261007-factory-users-guide`, and the change neither finishes Wave 1 nor starts Wave 2. The reviewed diff is within the order’s owned paths.
