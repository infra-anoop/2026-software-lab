# Review packet: Wave 1.5 implementation approach (cross-family design review)

One cross-family pass over a design note written by the architect, before it goes to the governor for approval. Not a spec, plan or test review: no verdict file. Findings are numbered within your report only.

## Meta

| Field | Value |
|-------|-------|
| Packet id | 2026-10-19-implementation-approach-review |
| Status | open |
| Gate | Before the governor's decision on the approach; one pass, a second only for a blocker |
| Under review | `notes/wave1.5/2026-10-implementation-approach.md` and the sprint manager's `notes/wave1.5/2026-10-layer-sizing.md`, on branch `wo/wo-20261019-wave15-implementation-approach` |
| Order | `wo-20261019-wave15-implementation-approach` |
| Agent mode | spawned reviewer, background |
| Reviewer | GPT-5.6 Sol (a different model family from the author, Claude Opus 5.5) |
| Appetite | 45 minutes. Hard stop at 75 minutes. Commit and push a skeleton report (headings only) within your first 10 minutes, then a partial report at 45; an earlier reviewer stalled silently, so progress must show in git |

## Why this review exists

The Wave 1 retro agreed a product shape for the factory at the end of Wave 1.5 and a plan to build it. On 2026-10-19 the governor kept the product shape but rejected the build plan as too heavy and too late to judge. He set a new direction with the architect: start from today's `main` and remove Wave 1's machinery; build in layers (install, configure, policy, glue) with fewer intermediate tests; use Spec Kit workflows run as short workflows cut wherever they would wait; use the Superpowers packet set as shipped. The note under review turns that into nine layers and lists every variation from the product shape. Later the same evening the governor and the architect agreed a test-first shape aimed at faster convergence (the note's section 2.6 and section 5 row 10), replacing the held-back acceptance set. The sprint manager sized the layers before that change. The governor will go through the note, the sizing and this review's fixes together, so the review covers costs as well as design. The architect's own designs get a second-model review before the governor sees them.

## Read first

1. The note under review, in full.
2. `notes/retro/2026-10-factory-whole.md` (the product shape) and `notes/retro/2026-10-wave1.5-funnel.md` sections 8 and 9 (the plan being replaced, its value statement and exit criteria).
3. `notes/retro/2026-10-harness-changes.md`, only where the note cites items, and `notes/retro/2026-10-factory-survey.md` for the earlier stack choice.
4. The outside sources, copied into git under `notes/wave1.5/sources/` (see its README): Spec Kit's workflow reference, the Superpowers v7.0.0 subagent-driven-development skill (licence, prompts, scripts), and GitHub's changelog entry on bot-created pull requests. **Do not fetch anything from the web, and do not read any file outside your worktree:** both can wait on an approval prompt nobody sees, which stalled two earlier reviews. If a claim needs a source that is not in the copies, mark it unverified.
5. `notes/wave1.5/2026-10-layer-sizing.md` (the sprint manager's sizing).

## Job

Answer these, each with evidence (file and section, or source URL):
1. **Fidelity to the product shape.** Does the approach deliver the product shape and the exit criteria, except where a row in its section 5 says otherwise? Name any silent variation: something the product shape requires that the layers drop, thin or contradict without a section 5 row.
2. **Reliability of the short-workflow design.** Does cutting workflows at every wait, with state held in GitHub between them, still meet the reliability properties: runs continue with the laptop closed; a killed run repeats nothing irreversible; a decision left overnight resumes the work; a silent stall raises an alert? Name the gaps, for example duplicate or concurrent triggers on the same issue, lost state between workflows, or a step that is not safe to repeat.
3. **Building versus buying.** Is anything still built that a chosen part already provides? Is anything assumed to come with a bought part that does not?
4. **Layer order.** Does each layer run only on parts proven in earlier layers? Is each "done when" something that can fail? Is anything needed earlier than where it is placed, or missing altogether?
5. **Facts.** Check the note's factual claims: Spec Kit workflow capabilities and where a paused run keeps its state; the contents and licence of the Superpowers packet set; the claim that Wave 1 only added files (`git diff --shortstat 19a06d3 origin/main`); that pull requests opened with the default Actions token wait for approval before their checks run.
6. **Clarity.** Could the governor read the note and know what each layer gives him and when he is asked to act?
7. **The test-first shape (section 2.6, row 10).** Does it make first-time-right code more likely and lower the cost per change? Name any gap: for example, how the example-id check works when an example cannot be a single automated test, whether the builder can weaken its own tests unseen, whether the tests-against-spec verdict fits Superpowers' reviewer as shipped, and whether the default of 3 examples per requirement is a sensible start.
8. **The sizing as a cost picture.** Without re-estimating: is the arithmetic consistent, does every task in the note have a size, and is anything sized that the note no longer contains (the held-back store) or missing that it now contains (the test-first shape)? Name what the sprint manager should re-size.

Do not re-argue the governor's direction listed above or the product shape itself. Do not replace the sprint manager's estimates with your own; point out gaps and inconsistencies. Severity per finding: blocker (approving the note would mislead the governor or build something unsafe), major (a gap or contradiction the build would trip on), minor (wording). Give a concrete fix for each.

## Deposit

- Write `notes/wave1.5/2026-10-implementation-approach-review.md` in your worktree. Structure: summary (verdict in five lines: sound, sound with changes, or not sound), findings (numbered, each with severity, file and section, evidence, fix), what you checked and found fine.
- Plain language: the governor may read it. Avoid internal jargon (packet, worktree, owned paths).

## Worktree and git

- Your worktree: `/workspaces/2026-software-lab/.worktree-home/.cursor/worktrees/wave15-approach-review`, on branch `review/wo-20261019-wave15-implementation-approach`. It is already created. Never use the primary checkout at `/workspaces/2026-software-lab` itself.
- Every shell command starts with `cd /workspaces/2026-software-lab/.worktree-home/.cursor/worktrees/wave15-approach-review &&`. Before each commit, check that `git branch --show-current` prints the review branch; if it prints anything else, stop and report.
- Use file tools with absolute paths under your worktree for reading and writing.
- Never pass `required_permissions`. Never combine heredoc, echo or redirection with git in one command.
- Commit and push to your review branch only (`git push -u origin review/wo-20261019-wave15-implementation-approach`). The architect copies the report onto the approach branch. If the push is refused, leave the commit in place and report.
- The governor's usage export (`downloads/usage-events-*.csv`) is outside git and off limits.

## May edit

- `notes/wave1.5/2026-10-implementation-approach-review.md` (in your worktree)

## Forbidden

- Every other file.
- Product and application code (`apps/`, `modules/`), `deploy/secrets/`, GitHub settings.
- Installing, running or signing up for anything; starting any Wave 1.5 work.
- Web requests of any kind, and reading files outside your worktree.

## Definition of done

- [ ] Report committed (and pushed if allowed) with all sections above.
- [ ] All eight questions answered, each with evidence or "found fine".
- [ ] Stop. Do not ask the governor anything; the architect presents the result.

## Stop and report if

- You find a secret value or personal data (report the file and line, never the value).
