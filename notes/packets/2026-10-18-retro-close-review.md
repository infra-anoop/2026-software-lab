# Review packet: the Wave 1 retro branch before it merges (retro close)

Spawned per `docs/agent-os/SPAWN_REVIEWER.md`. One cross-family pass over the retro's records as a set, before the retro's pull request. Not a spec, plan or test review: no verdict file. Findings are numbered within your report only.

## Meta

| Field | Value |
|-------|-------|
| Packet id | 2026-10-18-retro-close-review |
| Status | spawned |
| Gate | Retro close, one pass (no further rounds unless a blocker) |
| Under review | everything the retro branch `wo/wo-20261016-factory-wave1-retro-session` changes against `origin/main` |
| Order | `wo-20261016-factory-wave1-retro-session` (amendment-09) |
| Base commit | the retro branch commit that adds this packet |
| Agent mode | spawned-reviewer, background |
| Reviewer | GPT-5.6 Sol (a different model family from the author) |
| Appetite | 45 minutes. Hard stop at 75 minutes; commit a partial report at 45 |

## Why this review exists

The retro is closed (decision `wave1-retro-close`). Its records reach `main` in one pull request, and two fresh sessions (an architect and a Wave 1.5 sprint manager) will start from them with no memory of the retro. The whole-factory file already passed three focused rounds. This pass checks the set, not the design.

## Read first

1. `docs/agent-os/SPAWN_REVIEWER.md`.
2. `git diff --stat origin/main...HEAD` in your worktree, then the files below.
3. `notes/retro/2026-10-architect-handover.md` (the entry point for both new sessions).
4. `notes/retro/2026-10-wave1-items.md`, the "Retro outcome" section.
5. `notes/retro/2026-10-harness-changes.md`, `notes/retro/2026-10-wave1.5-funnel.md` (status line, governor rulings, sections 8 and 9), the status block of `notes/retro/2026-10-factory-whole.md`.
6. `bus/decisions/wave1-retro-*/` and `bus/decisions/wave1-token-usage/`.

## Job

Answer these, each with evidence (file and section):
1. **Handover sufficiency.** Could a fresh session, reading only the handover and what it points to, act as architect or as Wave 1.5 sprint manager without asking the governor anything the records already settled? Name anything it needs and cannot find, and any pointer that leads nowhere.
2. **Cross-record consistency.** Do the handover, the items outcome table, the funnel's status and section 9, the register and the decision locks agree on what was decided (path, appetite, shape, first order, roles, close)? Name contradictions, including stale status lines that still say "draft" or "next" where the work is done.
3. **Decision records.** Does each lock match its request's options and quote the governor's words? Is anything recorded as decided without a quoted governor yes?
4. **Hygiene.** Any secret value, password, token, email address or personal data in the diff (names of secrets are fine). Any file outside the order's files in amendment-09. Any change to rule paths (constitution, `AGENTS.md`, `.cursor/rules/`, `docs/agent-os/`, factory checks, rubrics, workflows, CODEOWNERS); there should be none.

Do not re-argue agreed content, estimates or the design. Severity per finding: blocker (merging would mislead the new sessions or leak data), major (a contradiction or gap a new session would trip on), minor (wording). Give a confidence from 0 to 100 and a concrete fix.

## Deposit

- Write `notes/retro/2026-10-retro-close-review.md` in your worktree. Structure: summary (verdict in five lines: ready to merge, ready with changes, or not ready), findings (numbered, each with severity, confidence, file, evidence, fix), what you checked and found fine.
- Plain language: the governor may read it. Avoid internal jargon (packet, slice, worktree, fidelity, owned paths).

## Worktree and git (hygiene from Wave 1)

- Your worktree: `/workspaces/2026-software-lab/.worktree-home/.cursor/worktrees/retro-close-review`, on branch `review/wo-20261016-factory-wave1-retro-session-close`. It is already created. Never use the primary checkout at `/workspaces/2026-software-lab` itself.
- Every shell command starts with `cd /workspaces/2026-software-lab/.worktree-home/.cursor/worktrees/retro-close-review &&`. Before each commit, check that `git branch --show-current` prints the review branch; if it prints `main` or anything else, stop and report.
- Use file tools with absolute paths under your worktree for reading and writing.
- Never pass `required_permissions`. Never combine heredoc, echo or redirection with git in one command.
- Commit and push to your review branch only (`git push -u origin review/wo-20261016-factory-wave1-retro-session-close`). The orchestrator copies the report onto the retro branch. If the push is refused, leave the commit in place and report.
- The governor's usage export (`downloads/usage-events-*.csv`) is outside git and off limits.

## Owned paths (may edit)

- `notes/retro/2026-10-retro-close-review.md` (in your worktree)

## Forbidden

- Every other file.
- Product and application code (`apps/`, `modules/`), `deploy/secrets/`, GitHub settings.
- Installing, running or signing up for anything; starting any Wave 1.5 work.

## Definition of done

- [ ] Report committed (and pushed if allowed) with all sections above.
- [ ] All four questions answered, each with evidence or "found fine".
- [ ] Stop. Do not ask the governor anything; the orchestrator presents the result.

## Governor locks (closed; do not reopen)

| Lock | Value |
|------|-------|
| Factory path | Spec Kit as the engine, GitHub Issues for work (decision `wave1-retro-factory-path`) |
| Appetite and shape | Must plus Should; probe, core, cutover, build-out, removal (funnel section 9) |
| Whole-factory file | Reviewed coherent and agreed by the governor (2026-10-18) |
| Retro close | Decision `wave1-retro-close` |

## Fidelity (constitution §I)

| Lock | letter or intent | Notes |
|------|------------------|-------|
| Reviewer from a different model family | letter | GPT-5.6 Sol |
| Scope: the set of records, not the design | letter | No estimates, no re-arguing locks |

## Stop and report if

- The diff touches a rule path.
- You find a secret value or personal data (report the file and line, never the value).
