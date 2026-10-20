# Architect handover (from the retro session, 2026-10-17)

**Status: final at retro close (2026-10-18, decision `wave1-retro-close`).** Written by the outgoing architect (the long-running orchestrator session that ran Wave 1 and its retro) for two fresh sessions: the new **architect** and the **Wave 1.5 sprint manager**. The governor agreed to the switch on 2026-10-17 (17:20 PT): this session had been summarised several times, and the switch tests principle P9 ("what is not in git does not exist").

Until the Wave 1.5 rulebook rewrite lands, this note carries the architect's role, state, the governor's working preferences and the operating rules that used to live only in private notes.

## 1. Who you are

**Architect** (also called the coach): a standing chat session that owns the factory's design direction. Defined by boundaries, not tasks (register item 50):
- **Free agenda:** the problem of the day, raised by the governor or found in the records.
- **Decides alone:** design details inside the agreed principles.
- **Brings to the governor:** anything that changes scope, budget, architecture or rules, as a decision request in git.
- **Records:** every conclusion and decision in git. Your own designs still get a second-model review.

Your standing jobs in Wave 1.5:
1. Read the sprint manager's plan architecture before it reaches the governor (alongside the cross-family plan review); hold it to the register, the funnel and the whole-factory file.
2. Answer design questions the sprint manager raises.
3. Keep the whole-factory file true as decisions land.
4. Run the next retro.

**Sprint manager:** a separate standing chat session that runs Wave 1.5 delivery: intent session, spec, plan, tasks, orders, status, exceptions. Starts with `.cursor/skills/lab-intent-session/SKILL.md`, then Spec Kit. Its plan's architecture and phasing need the governor's approval before any work starts.

You share git. Read each other's records. When you disagree, the governor gets one decision request carrying both views; he never relays messages.

## 2. Read first, in this order

1. This note.
2. `notes/retro/2026-10-factory-whole.md`: the factory as one whole at the end of Wave 1.5, and its review.
3. `notes/retro/2026-10-wave1.5-funnel.md`: the governor rulings (after section 5), section 8 (62 work items with estimates) and section 9 (the agreed Wave 1.5 shape).
4. `notes/retro/2026-10-harness-changes.md`: the register, items 1 to 104 and principles P1 to P18, all agreed.
5. `notes/retro/2026-10-factory-survey.md`: why Spec Kit, the parts, and the trial questions.
6. `bus/decisions/wave1-retro-*/`: the retro's decisions and locks.
7. `AGENTS.md` and `.specify/memory/constitution.md`: still describe Wave 1's process until the cutover rewrite.

## 3. State at handover

> **Update 2026-10-19:** the Wave 1.5 implementation approach is approved (decision `wave15-implementation-approach`; `notes/wave1.5/2026-10-implementation-approach.md`, sizing in `notes/wave1.5/2026-10-layer-sizing.md`). It replaces the phase plan below: clean slate on today's `main`, nine layers, three funding tranches (Layers 0 to 3 committed), a 1.5-times overrun stop. Next: the sprint manager's Layer 0 walkthrough for the governor's approval. The bullets below are the state at retro close.

- **Retro closed** (decision `wave1-retro-close`, governor 2026-10-18 00:56 PT). All six stages done. The whole-factory walk-through was reviewed by a second model family in three rounds (not coherent, not coherent, then coherent) and the governor read and agreed it. The retro's records reach `main` through the retro session's pull request.
- Decisions locked in the retro: bootstrap role, front door, sprint type, first product work, token usage, factory path (Spec Kit plus Issues), Wave 1.5 appetite (Must plus Should, about 89 to 182 agent-hours), retro close.
- The Wave 1 items list (`notes/retro/2026-10-wave1-items.md`) is closed with an outcome table; rows not traced there are traced in the failure inventory.
- **Wave 1 effort, rough:** about 808 million tokens over Oct 3 to 7 (usage export). No agent-hours were recorded; a rough reconstruction from commit activity (25 to 38 hours with an agent working, up to three agents plus the orchestrator in parallel) gives about 50 to 100 agent-hours. Unverified; the Wave 1 baseline (register item 85) replaces it. Wave 1.5's likely estimate is therefore about Wave 1's size, the pessimistic two to three times it.
- Roles: architect and sprint manager are separate sessions from the start of Wave 1.5 (governor, 2026-10-17).
- Housekeeping: about 60 Wave 1 working copies remain under `.worktree-home/.cursor/worktrees/`, plus merged remote branches (Wave 1 items list, D20). Harmless; clear them in Wave 1.5's removal phase. The retro's own review copies are already removed.
- Wave 1.5: shape agreed (probe, core, cutover, build-out, removal); first real order is the workflow checker; cutover as early as convenient, never two ways of working.
- Open decision `app-key-delivery`: likely closed when the GitHub App is set up in Wave 1.5 (the key becomes an Actions secret).
- Not yet built: everything in the register. The Wave 1 failure inventory and baseline are Wave 1.5 work; evidence in `notes/retro/2026-10-wave1-items.md` and `notes/retro/sources/orchestrator-notes-wave1/`.

## 4. How the governor works (observed in the retro)

- **Discuss, align, then record.** Nothing is recorded as agreed without his explicit yes. Confirmations inside an agreed process are given in chat and recorded in git; scope, budget, architecture and rules decisions go to a decision request.
- **For each topic:** take a stance on the root cause, give options and leading-practice benchmarks, then propose. Disagree openly; you are the architect, take only what makes sense.
- **Plain language.** No internal ids or jargon in chat. When he asks to unpack a phrase, explain it from first principles. Lead with the outcome; keep the main content last in a reply, after any tool calls.
- **Values:** quality first; good enough for a learning project of about 5 users; buy over build; no Wave 1 piece kept by default; coherence over a small scope; measurement never reshapes the work; fewer, simpler checks (he dislikes eagerly created checks); cost is an operating control, not a selection criterion (he sets spend limits on the Cursor dashboard).
- **Links:** his file explorer shows `main`. Give GitHub links to files on a branch when he must read them.
- **Question marks:** the editor hook `decision-in-chat` fires on any question mark in a reply and shows its message as if he sent it. Until it is removed, avoid question marks in chat; put real decisions in `bus/decisions/<id>/request.yaml`; decline its false alarms briefly.
- **Time:** no rush; he prefers depth and explicit alignment.

## 5. Operating rules (moved from private notes; still in force until the rulebook rewrite)

**Git and shell**
1. Never put a heredoc, `echo >` or any redirection in the same shell command as git: such commands run sandboxed, and the sandbox ignores the working directory, so they land on the primary checkout's `main` (incidents on 2026-10-07).
2. Edit files with the editor tools; run git in its own command, in the worktree, and check `git log --oneline -1` afterwards.
3. Never work or check out in the primary checkout `/workspaces/2026-software-lab`; use worktrees under `.worktree-home/.cursor/worktrees/`.
4. Every change goes through a branch and a pull request; never commit or push to `main`. No force-push, history rewrite or skipped hooks.
5. Never capture `nix develop` output into a variable; its banner pollutes it.
6. `gh` commands: `nix develop /workspaces/2026-software-lab -c gh ...`. Open pull requests through the REST API with `-F body=@<file>`; merge with `gh api -X PUT repos/infra-anoop/2026-software-lab/pulls/<n>/merge -f merge_method=merge -f sha=<sha>`. Never `gh workflow run`.
7. Records check: `nix develop /workspaces/2026-software-lab -c bash -c 'cd scripts/factory && uv run --locked factory check schema'`. Decision ids allow letters, digits, `-` and `_` only.

**Agents**
8. Workers run on Claude Opus 5.5 (high); reviewers on GPT-5.6 Sol (medium); at most 3 agents at once. Spawned agents never pass `required_permissions` and never use the primary checkout. Spawned agents make no web requests and read no files outside their worktree: either can raise an approval prompt that shows only on the agent's own card, and the agent waits silently (two reviews stalled this way on 2026-10-19). The spawning session fetches outside sources first and commits dated copies for the agent to read. Have spawned agents push a first version within 10 minutes, so a stall shows in git. Completion notices can be lost: check the review branch in git after about 30 quiet minutes.
9. On a usage limit, stop and tell the governor.

**Secrets and data**
10. Never print or log tokens or passwords. Secret names go in `deploy/secrets/schema.yaml`; values never in git. GitHub settings, rulesets and Infisical are the governor's: give him exact strings.
11. The governor's Cursor usage export (`downloads/usage-events-*.csv`, git-ignored) carries his email on every row: never commit it; print only aggregates.
12. Do not read the terminal where the governor generated passwords; use `ps -eo pcpu,etime,comm`, not a full process list; never use the governor's browser session or credentials.
13. Off limits: the `smart-writer-prod` and `research-auditor-prod` Supabase projects and the `public` tables in `2026-software-lab`; no Railway or vault changes without an explicit ops order.

**Process (until cutover)**
14. Each change has an order in `bus/orders/<id>/`; widen its files by an amendment with `supersedes: [owned_paths]`. Rule paths (constitution, `AGENTS.md`, `.cursor/rules/`, `docs/agent-os/`, the factory's checks and rubrics, workflows, CODEOWNERS) need the governor's approving review.
15. Independent reviews: write a review note under `notes/packets/`, create the reviewer's worktree, and start the reviewer with a pointer to the note, never a pasted brief.
16. Do not start Wave 1.5 work before its plan is approved. Do not land `bus/postmortems/wave1-retro.yaml`.

## 6. Session channel: each session reads the other's chat (adopted 2026-10-19)

The governor adopted this on 2026-10-19 (19:06 PT to the architect, "I like this channel"; 19:12 PT to the sprint manager, "Lets adopt it"), so he does not repeat himself between the two sessions.

- **Where.** Cursor writes each chat's live transcript to `~/.cursor/projects/workspaces-2026-software-lab/agent-transcripts/<chat-id>/<chat-id>.jsonl` in the codespace. It holds the governor's messages and the session's replies and tool calls, not tool output.
- **Who is who.** Architect: chat `1c20d7e6-e6a4-4327-bc5b-ff7879f06151`. Sprint manager: chat `47a3626f-fcf9-4bfb-b2e4-57423a199602`. A session that replaces either one adds its chat id here.
- **Habit.** Before replying to the governor, read the other session's new turns since your last read. To see only the conversation (the governor's messages and replies without tool calls):

  ```bash
  jq -r 'select(.role=="user" or (.role=="assistant" and ([.message.content[].type]|index("tool_use")|not))) | "### \(.role)\n" + ([.message.content[]|select(.type=="text")|.text]|join("\n"))' <transcript>.jsonl
  ```
- **Limits.** Transcripts live only in this codespace and are lost if it is deleted or rebuilt; never commit them (they can carry personal data). They are a broadcast, not a record: every conclusion still goes into git. A session sees the other's news on its own next turn.
- **Direct messages** between the sessions (GitHub issues) are for later, when needed.
