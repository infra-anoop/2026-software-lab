# Work packet: inventory of Wave 1's rules

One background worker builds a complete list of the rules the lab's software factory ran on in Wave 1, so the governor and the architect can decide which to keep before any are removed. Reading and writing one document; no code, no rule changes.

## Meta

| Field | Value |
|-------|-------|
| Packet id | 2026-10-20-rules-inventory |
| Status | open |
| Order | `wo-20261020-wave15-rules-inventory` |
| Decision | `wave15-reliability-rules-first` (the governor, 2026-10-20) |
| Agent mode | spawned worker, background |
| Worker | Claude Opus 5.5 (high) |
| Appetite | Set by the sprint manager's sizing; hard stop at 1.5 times it. Commit and push a skeleton (headings only) within your first 10 minutes, then push after each source family is done, so progress shows in git |

## Why this exists

The governor decided to keep what is good in Wave 1: rules are likely more useful than machinery. The approved Wave 1.5 plan's Layer 0 removes Wave 1's machinery; before it does, every rule is listed and reviewed. A rule is kept, rewritten or dropped with a recorded reason, because nothing of Wave 1 is kept by default. The kept rules become the interim rulebook and the starting point of the policy layer. Your job is the list and a first recommendation; the architect checks it and the governor decides.

Read first: `notes/wave1.5/2026-10-implementation-approach.md` sections 2.1 and 2.7 and Layer 0 (on branch `wo/wo-20261020-wave15-reliability-rules-first`, already fetched; read it with `git show origin/wo/wo-20261020-wave15-reliability-rules-first:notes/wave1.5/2026-10-implementation-approach.md`), and `notes/retro/2026-10-harness-changes.md` principles P5, P12, P13 and P17.

## Sources (all in your worktree)

1. `.specify/memory/constitution.md`
2. `AGENTS.md` and `.cursorrules`
3. `.cursor/rules/*.mdc`
4. `docs/agent-os/*.md`
5. `scripts/factory/gates.yaml` (29 registered checks) and, for what each check really enforces, its code under `scripts/factory/src/factory/gates/`
6. `.cursor/hooks.json` and `.cursor/hooks/factory-hook.sh` (four hooks: spawn-guard, shell-guard, owned-path-warn, decision-in-chat)
7. `.github/CODEOWNERS` and the workflows under `.github/workflows/` (only the rules they enforce, such as required checks or trusted jobs)
8. `notes/retro/2026-10-architect-handover.md` section 5 (operating rules)
9. `notes/retro/sources/orchestrator-notes-wave1/HARD-RULES.md`
10. `notes/architect-backlog.md` (locked decisions and won't-dos)
11. The process skills under `.cursor/skills/` (`lab-kickoff`, `lab-intent-session`, and the `speckit-*` skills only where they add lab rules beyond stock Spec Kit)

## Job

Write `notes/wave1.5/2026-10-rules-inventory.md` with:

1. **Summary.** How many rules, from which sources, and the counts of your recommendations (keep, rewrite, drop, merge).
2. **The inventory, one row per rule.** Merge duplicates: the same rule stated in several sources is one row listing all of them. Columns:
   - an id (R1, R2, ...);
   - the rule in one plain sentence;
   - where it is stated (file and section);
   - how it is enforced today: prose only, a check (name it), a hook (name it), a GitHub setting, or by habit;
   - why it exists: the incident or reason, quoted or cited where the sources give one; "not stated" otherwise;
   - your recommendation: keep, rewrite (say how), drop, or merge into another row;
   - for keep or rewrite, where it would live: interim rulebook text, an automated check, configuration (for example an agent's allowed commands, a GitHub ruleset), or a role brief;
   - your reason, in one line.
3. **Machinery versus rules.** A short list of checks and hooks that enforce only Wave 1's own records (work orders, claims, verdict files, handoffs) rather than a rule about the work itself. Name the underlying rule, if any, that should survive without that machinery.
4. **Conflicts and gaps.** Rules that contradict each other, and rules the retro agreed (`notes/retro/2026-10-harness-changes.md`) that appear in no source.
5. **Candidates the approach note names** (section 2.7): change control by the mission test; new checks start as warnings; a relevance and consistency check on each proposed check; one backlog with grooming at each sprint start; one primary domain per sprint. Say for each whether a source already states it.

Recommend with these principles: fewer, stronger rules; a rule with no stated reason and no incident behind it is a candidate to drop; a rule that only feeds Wave 1's machinery is dropped unless the rule underneath it survives; prefer configuration or an automated check over prose where the rule must always hold; plain language. Do not decide; recommend. The governor decides.

## Deposit and git

- Your worktree: `/workspaces/2026-software-lab/.worktree-home/.cursor/worktrees/wave15-rules`, on branch `wo/wo-20261020-wave15-rules-inventory`. It is already created. Never use the primary checkout at `/workspaces/2026-software-lab` itself.
- Every shell command starts with `cd /workspaces/2026-software-lab/.worktree-home/.cursor/worktrees/wave15-rules &&`. Before each commit, check that `git branch --show-current` prints the branch above; if not, stop and report.
- Use file tools with absolute paths under your worktree. Never pass `required_permissions`. Never combine heredoc, echo or redirection with git in one command.
- **Make no web requests of any kind.** Everything you need is in git; a web request can wait on an approval nobody sees.
- Commit and push to your branch only (`git push origin wo/wo-20261020-wave15-rules-inventory`). If a push is refused, leave the commit and report.

## May edit

- `notes/wave1.5/2026-10-rules-inventory.md`

## Forbidden

- Every other file, including every rule file you are inventorying.
- Product and application code (`apps/`, `modules/`), `deploy/secrets/`, GitHub settings.
- Installing or running anything beyond `git`, `rg` and file reads.

## Definition of done

- [ ] Every source above read; every rule in them has a row or is merged into one.
- [ ] Every one of the 29 checks and four hooks appears, in the inventory or in the machinery list.
- [ ] Sections 1 to 5 present; pushed.
- [ ] Stop. Reply with the counts and the final commit sha. Do not ask the governor anything.

## Stop and report if

- A source is missing or unreadable.
- You find a secret value or personal data (report the file and line, never the value).
