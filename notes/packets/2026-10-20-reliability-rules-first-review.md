# Review packet: amendment to the Wave 1.5 implementation approach (reliability and rules first)

One cross-family pass over an amendment the architect made to an approved design note, recording choices the governor made on 2026-10-20. Small and focused: check that the amendment says what the governor decided, and that the note stays consistent.

## Meta

| Field | Value |
|-------|-------|
| Packet id | 2026-10-20-reliability-rules-first-review |
| Status | open |
| Gate | Before the amendment merges; one pass, a second only for a blocker |
| Under review | The diff of `notes/wave1.5/2026-10-implementation-approach.md` against `origin/main` (e911e34), plus `bus/decisions/wave15-reliability-rules-first/`, on branch `wo/wo-20261020-wave15-reliability-rules-first` |
| Order | `wo-20261020-wave15-reliability-rules-first` |
| Agent mode | spawned reviewer, background |
| Reviewer | GPT-5.6 Sol (a different model family from the author, Claude Opus 5.5) |
| Appetite | 25 minutes. Hard stop at 45 minutes. Commit and push a skeleton report (headings only) within your first 10 minutes, so progress shows in git |

## Why this review exists

The governor approved the Wave 1.5 implementation approach on 2026-10-19. On 2026-10-20 he recalibrated two points. First, keep Wave 1's good rules: rules are likely more useful than machinery, so every rule is inventoried and reviewed before Layer 0 removes anything, and the kept rules seed the policy layer. Second, unattended reliability comes first: an investigation into the hangs, automatic recovery, and reliability pieces such as the agents' allowed commands in Layer 0. He chose: both pieces finish before Layer 0 builds anything; the architect leads them; the note is amended now. The lock file records his words. The architect wrote the amendment; a second model family checks it before it merges.

## Read first

1. `bus/decisions/wave15-reliability-rules-first/request.yaml` and `lock.yaml` (what was decided).
2. The diff: `git diff origin/main -- notes/wave1.5/2026-10-implementation-approach.md`, then the note in full.
3. Only where the amendment cites them: `notes/retro/2026-10-harness-changes.md` (principles P1 to P4, items 1 to 24), `notes/retro/2026-10-wave1-items.md` sections A and B, `notes/retro/2026-10-wave1-agenda.md` sections 7, 8, 17 and 18.

**Do not fetch anything from the web, and do not read any file outside your worktree:** both can wait on an approval prompt nobody sees, which stalled two earlier reviews. If a claim needs an outside source, mark it unverified.

## Job

Answer these, each with evidence (file and section):
1. **Fidelity to the decision.** Does the amendment record what the lock says the governor decided, no more and no less? Name anything added that he did not decide, or anything he decided that is missing.
2. **Consistency.** Does any text left in the note still contradict the amendment (for example, Wave 1's rules being removed outright, the hook count, the tranche figures, row 5, the open items)? Is the arithmetic in section 4 consistent?
3. **Failable outcomes.** Can the new Layer 0 "done when" and the section 2.7 outputs fail? Is anything named without a way to tell whether it was done?
4. **Retro concerns table (section 10).** Is each "before" and "now" accurate against the note and the cited retro records? Name any concern from the cited retro sections that the table misses and the design does not cover.

Do not re-argue the governor's decisions or the approved approach. Severity per finding: blocker (merging would misrecord the governor's decision), major (a contradiction or gap the next step would trip on), minor (wording). Give a concrete fix for each.

## Deposit

- Write `notes/wave1.5/2026-10-reliability-rules-first-review.md` in your worktree. Structure: summary (verdict in three lines: accept, or changes needed), findings (numbered, each with severity, file and section, evidence, fix), what you checked and found fine.
- Write `bus/orders/wo-20261020-wave15-reliability-rules-first/verdict-01.yaml`, following the shape of `bus/orders/wo-20261019-wave15-implementation-approach/verdict-01.yaml`: `decision: accept` if there are no blocker or major findings, otherwise `decision: revise`; `reviewer_model: gpt-5.6-sol`, `reviewer_family: openai`; `inputs` listing every file you read, each at the commit sha named in your spawn message; `refs` naming this packet and your report.
- Plain language: the governor may read the report. Avoid internal jargon (packet, worktree, owned paths).

## Worktree and git

- Your worktree: `/workspaces/2026-software-lab/.worktree-home/.cursor/worktrees/wave15-amend-review`, on branch `review/wo-20261020-wave15-reliability-rules-first`. It is already created. Never use the primary checkout at `/workspaces/2026-software-lab` itself.
- Every shell command starts with `cd /workspaces/2026-software-lab/.worktree-home/.cursor/worktrees/wave15-amend-review &&`. Before each commit, check that `git branch --show-current` prints the review branch; if it prints anything else, stop and report.
- Use file tools with absolute paths under your worktree for reading and writing.
- Never pass `required_permissions`. Never combine heredoc, echo or redirection with git in one command.
- Commit and push to your review branch only (`git push -u origin review/wo-20261020-wave15-reliability-rules-first`). The architect copies the report and verdict onto the amendment branch. If the push is refused, leave the commit in place and report.

## May edit

- `notes/wave1.5/2026-10-reliability-rules-first-review.md` (in your worktree)
- `bus/orders/wo-20261020-wave15-reliability-rules-first/verdict-01.yaml` (in your worktree)

## Forbidden

- Every other file.
- Product and application code (`apps/`, `modules/`), `deploy/secrets/`, GitHub settings.
- Installing, running or signing up for anything; starting any Wave 1.5 work.
- Web requests of any kind, and reading files outside your worktree.

## Definition of done

- [ ] Report and verdict committed (and pushed if allowed).
- [ ] All four questions answered, each with evidence or "found fine".
- [ ] Stop. Do not ask the governor anything; the architect presents the result.

## Stop and report if

- You find a secret value or personal data (report the file and line, never the value).
