# Reliability: decisions and actions

The register for the Wave 1.5 reliability thread. One line per decision, one line per action. Reasoning lives in `2026-10-reliability-investigation.md`; locks live in `bus/decisions/`. Updated by the architect as decisions and actions change.

Status values: open, in progress, done, at build (waits for Layer 0 approval), later.

## Incident coverage

Each incident in the report (section 3) against what closes it. Updated 2026-10-21 23:50 PT: 8 of 11 decided; the rest wait on A1 and A8.

| # | Incident | Closed by | State |
|---|----------|-----------|-------|
| 1 | Codespace stops at 12 hours | Documented limit; batch work in Actions (D2); chunks restart from last push (D3) | decided |
| 2 | Codespace stops after 30 idle minutes | Batch work off the codespace (D2, D13); 240-minute codespace for interactive sessions (A2) | decided; A2 pending |
| 3 | Restart wiped working copies | Fixed in Wave 1; Actions machines are fresh | closed |
| 4 | Worker hung inside Cursor's runner | 60-minute hard limit; retry, then park (D3, D8) | decided |
| 5 | 10-minute step took 90 | Same as 4 | decided |
| 6 | Completion notices lost | Results through git and the issue; watcher (D9, D15) | decided |
| 7 | Permission prompts stalled agents | Run, refuse, or block and report (D10, D11); A1 trials: batch tools never wait | decided; P1 to P4 proposed |
| 8 | Codespace token cannot start workflows | Chunks dispatch each other inside Actions (report section 10) | decided |
| 9, 10 | Web-request approvals froze reviewers | As 7; unlisted web fetch refused at once in headless mode; editor prompts only in attended sessions (D10, D13, D14) | decided; P1 to P4 proposed |
| 11 | Package downloads timed out; hooks ran them per command | Layer 0 removes the hooks; Actions environment (A8) | open |

## Decisions

| ID | Decision | Date | Lock |
|----|----------|------|------|
| D1 | The reliability investigation and the rules inventory finish before Layer 0 builds anything; the architect leads both. | 10-20 | `wave15-reliability-rules-first` |
| D2 | GitHub Actions is the baseline host for unattended (batch) work. | 10-21 | `wave15-unattended-host` |
| D3 | Batch work is cut into chunks estimated at 30 minutes; each job has a hard 60-minute limit; estimates are tuned from measured times. | 10-21 | `wave15-unattended-host` |
| D4 | Spec Kit workflows stay the process; GitHub Actions triggers their steps. | 10-21 | `wave15-unattended-host` |
| D5 | Cursor and Copilot are both supported from day one, chosen per role by a setting (`AI_ENV`, default `cursor`), each as a command-line agent in the lab's own Actions job. Copilot's cloud agent is a later option. | 10-21 | `wave15-runner-and-chunks` |
| D6 | The allowed-commands policy is written once and generated into each tool's format. | 10-21 | `wave15-runner-and-chunks` |
| D7 | Chunk size is a factory requirement on the Spec Kit plan; every task carries an estimate of at most 30 minutes, checked by a warning-first check and judged by the reviewer; every step (specify, plan, review, implement) is a chunk; each chunk leaves the code working. | 10-21 | `wave15-runner-and-chunks` |
| D8 | On a 60-minute overrun: retry once from the last push; on a second overrun, park the task and continue with the next independent task; the sprint manager handles parked tasks (split, re-plan, escalate). | 10-21 | `wave15-runner-and-chunks` |
| D9 | The chunk design is agreed in principle: life cycle, failure responses, notifications through the work item's GitHub issue, a Cursor API key stored as a GitHub secret (report section 10). | 10-21 | `wave15-runner-and-chunks` |
| D10 | Every agent action is configured to run, be refused, or block the task and report; never to wait for an approval nobody sees. | 10-21 | `wave15-task-modes` |
| D11 | "Block and report" and "pause for the governor" are one mechanism: the task stops, posts its question on its issue, and resumes on the governor's answer. | 10-21 | `wave15-task-modes` |
| D12 | Every task is tagged interactive or batch, set by the sprint manager at planning from defaults (interactive: brainstorming, resolution sessions, intent and policy sessions, decision walkthroughs; batch: building, reviewing, inventories, research write-ups). | 10-21 | `wave15-task-modes` |
| D13 | Interactive tasks run in the codespace; batch tasks run in GitHub Actions. | 10-21 | `wave15-task-modes` |
| D14 | Subtasks spawned inside an interactive session run in the codespace while short and attended; a subtask that turns out long or unattended is promoted to a batch task. | 10-21 | `wave15-task-modes` |
| D15 | Interactive and batch tasks hand over through git only: interactive sessions end in decisions and artifacts that start batch tasks; a batch task needing a person creates an interactive task. | 10-21 | `wave15-task-modes` |
| D16 | Nothing is implemented in this phase; the session gathers decisions until the Layer 0 walkthrough is approved. | 10-21 | `wave15-runner-and-chunks` (notes) |

## Proposed decisions (awaiting the governor)

From action A1's trials (report section 11.1).

| ID | Proposed decision |
|----|-------------------|
| P1 | Batch runs never use `--force` (or Copilot's `--allow-all`); unlisted actions then stay refused. |
| P2 | The generated policy (D6) writes deny entries for files in absolute or `**/` form, and treats git-side checks (token, branch, changed paths, rulesets) as the boundary for writes. |
| P3 | Every chunk ends by writing a structured status: done, blocked with a question, or failed. The workflow acts on that status, not on the agent's prose; "blocked" triggers D11. |
| P4 | Agent program versions are pinned; the A1 cases become a conformance test rerun on every upgrade. |

## Actions

| ID | Action | Owner | Done when | Status | Depends on |
|----|--------|-------|-----------|--------|------------|
| A1 | **Research the permission blocks in each agent tool.** Tools: Cursor editor (chat-spawned agents), Cursor command-line agent (headless), Copilot command-line agent. Actions: shell command, file write, web request, external tools (MCP). Cases: allowed, refused, on neither list. | architect | A table where every cell is "runs", "refused" or "blocks and reports", each with evidence (documentation or a trial), plus the settings that remove every silent wait. The headless "on neither list" case is tested first. | done for Cursor (report section 11; 13 trial runs, none waited); Copilot by documentation only, trial at build (A12) | — |
| A2 | Create a new codespace with a 240-minute idle timeout (`gh codespace create --repo infra-anoop/2026-software-lab --idle-timeout 240m`), after saving the chat records and agent stores. | governor (architect gives exact steps) | The new codespace's idle timeout reads 240 through the API. | open | — |
| A3 | Fold the reliability findings and decisions D2 to D16 into the approach amendment (pull request #42): corrected Layer 0 list; the outside-reads reason corrected there and in `notes/wave1.5/sources/README.md`. | architect | The amendment cites this register and contains no stale reliability reason. | open | A1 |
| A4 | Open pull requests for the reliability report and the rules inventory. | architect | Both pull requests open with checks green. | open | — |
| A5 | One combined cross-family review: rules inventory, reliability report and register, approach amendment. | architect spawns a reviewer | A verdict in git; findings triaged; the governor's yes recorded. | open | A1, A3, A4 |
| A6 | Decide whether to require the governor's approval on rule paths now (a GitHub setting), before the policy session. | governor | Decision recorded; if yes, the setting read back through the API. | open | — |
| A7 | Size the Layer 0 additions and the reliability items; note that the rules inventory took 23 minutes against a 2 to 3 hour estimate. | sprint manager | Sizes recorded in the sprint manager's plan. | open | A3 |
| A8 | Discuss the next reliability item: the environment in Actions (cold installs, PyPI timeouts; caches and pinned downloads). | architect with governor | Decisions recorded here. | open | — |
| A9 | Delete the trial branch `trial/20261020-headless-agent` and the stopped reviewer's branch `review/wo-20261020-wave15-reliability-rules-first`. | architect | Both branches gone. | later | A5 |
| A10 | Policy session: keep, rewrite or drop each Wave 1 rule, starting from the rules inventory; reword "never `gh workflow run`" to "not from the codespace". | governor with architect | The interim rulebook is recorded. | later | tranche 1 |
| A11 | Store the Cursor API key and a Copilot-enabled token as GitHub secrets. | governor | Both secrets exist (names only in `deploy/secrets/schema.yaml` or the workflow docs). | at build | Layer 0 approval |
| A12 | Run the three proof trials: one chunk in Actions; a chain of three; deliberate kill and stall recovered by the watcher with an alert after the second failure. | architect | All three pass, recorded in the report. | at build | A11 |
