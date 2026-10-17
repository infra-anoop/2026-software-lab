# Review packet: Wave 1.5 funnel (Wave 1 retro, stage 5, step 3)

Spawned per `docs/agent-os/SPAWN_REVIEWER.md`. This is a check of a sorting worksheet, not a spec, plan or test review: no verdict file. Findings are numbered within your report only.

## Meta

| Field | Value |
|-------|-------|
| Packet id | 2026-10-17-funnel-review |
| Status | spawned |
| Gate | Funnel check (register item 71; stage 5 plan, step 3) |
| Under review | `notes/retro/2026-10-wave1.5-funnel.md` |
| Order | `wo-20261016-factory-wave1-retro-session` (amendment-07) |
| Base commit | retro branch `wo/wo-20261016-factory-wave1-retro-session` at the commit that adds this packet |
| Agent mode | spawned-reviewer, background |
| Reviewer | GPT-5.6 Sol (a different model family from the author, register items 74 and 90) |
| Round | 1 of at most 3 |
| Appetite | 90 minutes. Hard stop at 2 hours; push a partial report at 1 hour |

## Why you, and your stance

The orchestrator wrote the funnel and also built Wave 1. Two biases to look for: keeping or rebuilding Wave 1 pieces (principle P17, item 73), and filing work as glue we write when a bought product already does it (principle P15). A third: under-estimating. Disagree plainly where the evidence says so.

## Read first

1. `docs/agent-os/SPAWN_REVIEWER.md`.
2. `notes/retro/2026-10-wave1.5-funnel.md`, all of it.
3. `notes/retro/2026-10-harness-changes.md`: the agreed register (items 1 to 104, principles P1 to P18). The funnel must account for every item.
4. `notes/retro/2026-10-factory-survey.md`: the survey whose keep, replace and adopt calls the funnel follows, and its trial questions.
5. `bus/decisions/wave1-retro-factory-path/lock.yaml`: the locked path.
6. Spot-check the repository facts the funnel cites: `scripts/factory/gates.yaml` (29 checks), `scripts/factory/src/factory/`, `.cursor/hooks.json`, `.specify/`, `specs/001-factory-v2/tasks.md` (phases 9a to 13 for the Wave 2 calls).
7. `notes/retro/sources/factory-design-kit/` for what the design kit already provides (item 104).

Git and the web are your only sources.

## Job

Check the funnel on these questions, each with evidence:
1. **Coverage.** Every register item appears once in the appendix with a capability, a bin and a rank. List any missing, double-counted or misread item.
2. **Bins.** Any item filed as Glue that a bought product (Spec Kit 1.2.1 workflows, GitHub Issues, Actions, rulesets, CODEOWNERS, Logfire, Cursor CLI, Copilot CLI) already covers. Any Habit that really needs a build, or the reverse.
3. **Ranks.** Apply the funnel's own test (section "How to read this"). Name Musts that are really Should or Could, and anything missing that the test makes a Must.
4. **Removals.** Are the retire calls (sections 3a to 3c) consistent with the survey and the register? Is anything kept without meeting item 73's test? Is anything removed whose function nothing replaces?
5. **Estimates.** Are the agent-hour ranges plausible for the described work? Flag the ones you would change, with a reason. The ranges are uncalibrated; judge plausibility, not precision.
6. **Architecture points (section 6).** Check each one. In particular verify the claim about pull requests opened with the default Actions token not triggering workflows, with a dated source.
7. **Leftover stances (section 5).** Any that conflicts with an agreed register item.

Severity per finding: blocker (the funnel would mislead the governor's decision), major (a material change to a bin, rank, removal or estimate), minor. Give a confidence from 0 to 100.

## Deposit

- Write `notes/retro/2026-10-wave1.5-funnel-review.md` in your worktree. Structure: summary (verdict in five lines: sound, sound with changes, or not sound), findings (numbered, each with severity, confidence, section, evidence, recommendation), what you checked and found fine, sources.
- Plain language: the governor may read it. Avoid internal jargon (packet, slice, worktree, fidelity, owned paths).

## Worktree and git (hygiene from Wave 1)

- Your worktree: `/workspaces/2026-software-lab/.worktree-home/.cursor/worktrees/retro-funnel-review`, on branch `review/wo-20261016-factory-wave1-retro-session-funnel`. It is already created. Never use the primary checkout at `/workspaces/2026-software-lab` itself.
- Every shell command starts with `cd /workspaces/2026-software-lab/.worktree-home/.cursor/worktrees/retro-funnel-review &&`. Before each commit, check that `git branch --show-current` prints the review branch; if it prints `main` or anything else, stop and report.
- Use file tools with absolute paths under your worktree for reading and writing.
- Never pass `required_permissions`. Never combine heredoc, echo or redirection with git in one command.
- Commit and push to your review branch only (`git push -u origin review/wo-20261016-factory-wave1-retro-session-funnel`). The orchestrator copies the report onto the retro branch. If the push is refused, leave the commit in place and report.

## Owned paths (may edit)

- `notes/retro/2026-10-wave1.5-funnel-review.md` (in your worktree)

## Forbidden

- Every other file, including the funnel, the register and this packet.
- Product and application code (`apps/`, `modules/`), `deploy/secrets/`, GitHub settings.
- Installing, running or signing up for anything; starting any Wave 1.5 work.

## Definition of done

- [ ] Report committed (and pushed if allowed) with all sections above.
- [ ] All seven questions answered, each with evidence or "found fine".
- [ ] Stop. Do not ask the governor anything; the orchestrator presents the result.

## Governor locks (closed; do not reopen)

| Lock | Value |
|------|-------|
| Factory path | Spec Kit as the engine, GitHub Issues for work, tried on one real order first (decision `wave1-retro-factory-path`) |
| Register | Items 1 to 104 and principles P1 to P18 are agreed; judge the funnel against them, not the items themselves |
| Lanes | Three lanes; every review cross-family |
| Coherence | Wave 1 plus Wave 1.5, including removals, must form one usable factory (governor, 2026-10-17 15:41 PT) |

## Fidelity (constitution §I)

| Lock | letter or intent | Notes |
|------|------------------|-------|
| Reviewer from a different model family | letter | GPT-5.6 Sol |
| Desk research and repository reading only | letter | No installs or runs |

## Stop and report if

- A file named in "Read first" is missing.
- Your shell shows the primary checkout or a branch other than your review branch.
- The hard stop arrives: commit what you have, marked partial.
