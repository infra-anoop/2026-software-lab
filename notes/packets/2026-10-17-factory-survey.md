# Review packet: off-the-shelf factory survey (Wave 1 retro, stage 4)

Spawned per `docs/agent-os/SPAWN_REVIEWER.md`. This is a survey, not a spec, plan or test review: no finding IDs, no verdict file.

## Meta

| Field | Value |
|-------|-------|
| Packet id | 2026-10-17-factory-survey |
| Status | ready |
| Gate | Survey (desk research), register items 72 to 75 |
| Brief | `notes/retro/2026-10-factory-landscape.md`, section "Survey brief" (agreed by the governor 2026-10-17 13:43 PT) |
| Order | `wo-20261016-factory-wave1-retro-session` (amendment-04) |
| Base commit | retro branch `wo/wo-20261016-factory-wave1-retro-session` at the commit that adds this packet |
| Agent mode | spawned-reviewer, background |
| Reviewer | GPT-5.6 Sol (a different model family from the builder, register item 74) |
| Round | 1 of at most 3 (constitution §J) |
| Appetite | Half a day. Hard stop 4 hours after start; push a partial report at 2 hours |

## Why you, and your stance

The orchestrator who wrote this packet also built Wave 1 and is biased toward keeping it (register item 74). Principle P17: no Wave 1 piece is kept by default; keeping needs a reason (item 73). Judge the candidates, including "keep building", on evidence. Disagree with the brief where the evidence says so, and say so plainly.

## Read first

1. `docs/agent-os/SPAWN_REVIEWER.md`.
2. `notes/retro/2026-10-factory-landscape.md`, all of it. The "Survey brief" section is your job; the rest is the wide list and checked facts (as of 2026-10-17; re-verify anything you rely on).
3. `notes/retro/2026-10-harness-changes.md`: the agreed register (items 1 to 80, principles P1 to P17). "Coverage" and "reliability by design" are judged against it, theme 2 especially.
4. `notes/retro/2026-10-wave1-items.md`: what happened in Wave 1.
5. The Wave 1 pieces, for the keep, replace or adopt calls: the job queue under `bus/` (orders, amendments, claims, handoffs, verdicts, decisions), the `factory` command in `scripts/factory/`, the checks in `scripts/factory/gates.yaml` and `scripts/factory/src/factory/gates/`, editor hooks in `.cursor/hooks.json` and `scripts/factory/src/factory/hooks/`, the process layer (`.specify/memory/constitution.md`, `AGENTS.md`, `docs/agent-os/`, `.cursor/rules/`, `.cursor/skills/`), the spec and contracts in `specs/001-factory-v2/`, and the installed Spec Kit (`.specify/integration.json`, `.specify/workflows/`).

Git and the web are your only sources. The landscape file links the main sources.

## Job

Do the survey described in the brief:
1. Apply the three filters (portability, tool cost, operating burden) to paths A to D. A path that fails a filter is reported as failing, with evidence, and not scored further.
2. Score passing paths on the eight criteria, with evidence for each cell. Blends (for example A with C's queue) are allowed if the evidence points there.
3. Pick one option for each part: agent runtime, different-family reviewer, host and trigger, work queue, merge controls.
4. Give a keep, replace or adopt call for each Wave 1 piece listed above, with the reason (item 73's test: captures our culture with no product equivalent, or leads current practice in a way that matters, and is cheap to maintain).
5. Recommend one path, then write the strongest argument against your own recommendation.
6. List the open questions only a hands-on trial can answer. The trial itself is not yours; it happens in Wave 1.5 on one real order.

Rules of evidence: cite a source for every factual claim, dated 2026 where possible (release notes, docs, repository pages, issues). Mark anything you could not verify as "unverified". Do not install, run or sign up for anything.

## Deposit

- Write `notes/retro/2026-10-factory-survey.md` in your worktree. Structure: summary (recommendation in five lines), filters table, criteria table, parts, Wave 1 pieces, recommendation and the case against it, open questions for the trial, sources.
- Plain language: the governor reads it. Avoid the factory's internal jargon (packet, slice, worktree, fidelity, owned paths); say what you mean.

## Worktree and git (hygiene from Wave 1)

- Your worktree: `/workspaces/2026-software-lab/.worktree-home/.cursor/worktrees/retro-survey`, on branch `review/wo-20261016-factory-wave1-retro-session-survey`. It is already created. Never use the primary checkout at `/workspaces/2026-software-lab` itself.
- Every shell command starts with `cd /workspaces/2026-software-lab/.worktree-home/.cursor/worktrees/retro-survey &&`. Before each commit, check that `git branch --show-current` prints the review branch; if it prints `main` or anything else, stop and report.
- Use file tools with absolute paths under your worktree for reading and writing.
- Never pass `required_permissions`. Never combine heredoc, echo or redirection with git in one command.
- Commit and push to your review branch only (`git push -u origin review/wo-20261016-factory-wave1-retro-session-survey`). Push the partial report at 2 hours, the final when done. The orchestrator copies it onto the retro branch.

## Owned paths (may edit)

- `notes/retro/2026-10-factory-survey.md` (in your worktree)

## Forbidden

- Every other file, including the landscape file, the register, the brief and this packet.
- Product and application code (`apps/`, `modules/`), `deploy/secrets/`, GitHub settings.
- Starting any Wave 1.5 work or trial.

## Definition of done

- [ ] Report pushed to the review branch with all sections above.
- [ ] Every path either fails a filter with evidence, or is scored on all eight criteria with evidence.
- [ ] One recommendation and the strongest case against it.
- [ ] Stop. Do not ask the governor anything; the orchestrator presents the result.

## Governor locks (closed; do not reopen)

| Lock | Value |
|------|-------|
| Filters | Portability (at least two first-class, maintained runtimes, each with at least two model families; no single-vendor runtimes); tool cost (open source or small personal subscription; model usage cost is not a criterion); operating burden fits one person |
| Cursor's role | Home of the conversations; unattended steps run on any qualifying runtime |
| Shortlist | A Spec Kit native; B AI-SDLC behind Spec Kit; C GitHub-native; D keep building. Archon, DoorDash Agentic Orchestrator, Super Simple Software Factory, StrongDM and Symphony are reference designs only |
| Method | Desk research only |

## Fidelity (constitution §I)

| Lock | letter or intent | Notes |
|------|------------------|-------|
| Reviewer from a different model family | letter | GPT-5.6 Sol |
| Desk research only | letter | No installs, runs or sign-ups |
| Shortlist | letter | You may argue in the report that a reference design should have been a candidate; do not score it |

## Stop and report if

- A file named in "Read first" is missing.
- Your shell shows the primary checkout or a branch other than your review branch.
- The hard stop arrives: push what you have, marked partial.
