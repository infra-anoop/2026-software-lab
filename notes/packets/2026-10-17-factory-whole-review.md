# Review packet: the factory as one whole (Wave 1 retro, stage 5, step 6)

Spawned per `docs/agent-os/SPAWN_REVIEWER.md`. A focused review of one design description, not a spec, plan or test review: no verdict file. Findings are numbered within your report only.

## Meta

| Field | Value |
|-------|-------|
| Packet id | 2026-10-17-factory-whole-review |
| Status | spawned |
| Gate | Coherence review (governor's addition to the stage 5 plan, 2026-10-17 15:41 PT) |
| Under review | `notes/retro/2026-10-factory-whole.md` |
| Order | `wo-20261016-factory-wave1-retro-session` (amendment-07) |
| Base commit | retro branch `wo/wo-20261016-factory-wave1-retro-session` at the commit that adds this packet |
| Agent mode | spawned-reviewer, background |
| Reviewer | GPT-5.6 Sol (a different model family from the author) |
| Round | 1 of at most 3 |
| Appetite | 90 minutes. Hard stop at 2 hours; commit a partial report at 1 hour |

## Why this review exists

The governor asked that Wave 1 plus Wave 1.5, including what is removed, form one logical, usable factory: it may be imperfect and leave much in the backlog, but it must hold together. Your job is that one question. **Judge only logic, consistency and ambiguity.** Do not re-argue agreed choices (the register, the path, the lanes, the appetite), and do not review estimates or product value.

## Read first

1. `docs/agent-os/SPAWN_REVIEWER.md`.
2. `notes/retro/2026-10-factory-whole.md`, all of it.
3. `notes/retro/2026-10-harness-changes.md`: the agreed register (items 1 to 104, principles P1 to P18). The whole-factory file must not contradict it.
4. `notes/retro/2026-10-wave1.5-funnel.md`: sections 3 (what is removed), 5 (leftovers), the governor rulings, 6 (architecture points) and 9 (the Wave 1.5 shape).
5. `notes/retro/2026-10-factory-survey.md`: parts and Wave 1 pieces.
6. `notes/retro/sources/factory-design-kit/` (the review loop the factory starts from).
7. For what exists today: `scripts/factory/gates.yaml`, `.cursor/hooks.json`, `.specify/memory/constitution.md`, `AGENTS.md`, `docs/agent-os/`.

Git is your only source; no web research is needed unless a claim about a product's behaviour looks wrong.

## Job

Answer these, each with evidence (file and section):
1. **Logic.** Can every kind of work (light, normal, full) get from arrival to merge using only the parts, actors and steps described? Name any step with no actor, any input with no producer, any output with no consumer, any loop with no exit, any dead end.
2. **Consistency.** Name any contradiction inside the file (between sections, tables and invariants) and any contradiction with the register, the funnel's rulings or the Wave 1.5 shape.
3. **Ambiguity.** Name any term used in two senses, any responsibility claimed by two actors or by none, any rule two careful readers would apply differently, and any "who decides" left open that matters for running the factory. Items listed in section 14 as left to the plan are acceptable as open, unless leaving one open breaks the logic now.
4. **Completeness of removals.** Does every Wave 1 function removed or retired have a stated successor or a stated decision to drop it? Name any orphaned function.
5. **Usability as a whole.** Could a new session, reading this file and the sources, run the factory without a second, older way of working creeping back? Name what would push it back to the old way.

Severity per finding: blocker (the factory does not hold together as described), major (a material contradiction, gap or ambiguity a builder would trip on), minor (wording). Give a confidence from 0 to 100 and a concrete fix.

## Deposit

- Write `notes/retro/2026-10-factory-whole-review.md` in your worktree. Structure: summary (verdict in five lines: coherent, coherent with changes, or not coherent), findings (numbered, each with severity, confidence, section, evidence, fix), what you checked and found fine, sources.
- Plain language: the governor reads it. Avoid internal jargon (packet, slice, worktree, fidelity, owned paths).

## Worktree and git (hygiene from Wave 1)

- Your worktree: `/workspaces/2026-software-lab/.worktree-home/.cursor/worktrees/retro-whole-review`, on branch `review/wo-20261016-factory-wave1-retro-session-whole`. It is already created. Never use the primary checkout at `/workspaces/2026-software-lab` itself.
- Every shell command starts with `cd /workspaces/2026-software-lab/.worktree-home/.cursor/worktrees/retro-whole-review &&`. Before each commit, check that `git branch --show-current` prints the review branch; if it prints `main` or anything else, stop and report.
- Use file tools with absolute paths under your worktree for reading and writing.
- Never pass `required_permissions`. Never combine heredoc, echo or redirection with git in one command.
- Commit and push to your review branch only (`git push -u origin review/wo-20261016-factory-wave1-retro-session-whole`). The orchestrator copies the report onto the retro branch. If the push is refused, leave the commit in place and report.

## Owned paths (may edit)

- `notes/retro/2026-10-factory-whole-review.md` (in your worktree)

## Forbidden

- Every other file, including the file under review, the register, the funnel and this packet.
- Product and application code (`apps/`, `modules/`), `deploy/secrets/`, GitHub settings.
- Installing, running or signing up for anything; starting any Wave 1.5 work.

## Definition of done

- [ ] Report committed (and pushed if allowed) with all sections above.
- [ ] All five questions answered, each with evidence or "found fine".
- [ ] Stop. Do not ask the governor anything; the orchestrator presents the result.

## Governor locks (closed; do not reopen)

| Lock | Value |
|------|-------|
| Factory path | Spec Kit as the engine, GitHub Issues for work (decision `wave1-retro-factory-path`) |
| Register | Items 1 to 104 and P1 to P18 agreed; item 33 now lists six blocking checks |
| Appetite and shape | Must plus Should; probe, core, cutover, build-out, removal (funnel section 9) |
| Cutover | As early as convenient; no period of two ways of working |

## Fidelity (constitution §I)

| Lock | letter or intent | Notes |
|------|------------------|-------|
| Reviewer from a different model family | letter | GPT-5.6 Sol |
| Scope: logic, consistency, ambiguity only | letter | No estimates, no product value, no re-arguing locks |

## Stop and report if

- A file named in "Read first" is missing.
- Your shell shows the primary checkout or a branch other than your review branch.
- The hard stop arrives: commit what you have, marked partial.
