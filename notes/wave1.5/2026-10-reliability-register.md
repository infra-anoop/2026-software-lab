# Reliability: decisions and actions

The register for the Wave 1.5 reliability thread. One line per decision, one line per action. Reasoning lives in `2026-10-reliability-investigation.md`; locks live in `bus/decisions/`. Updated by the architect as decisions and actions change.

Status values: open, in progress, done, at build (waits for Layer 0 approval), later.

## Incident coverage

Each incident in the report (section 3) against what closes it. Updated 2026-10-22 00:22 PT: all 11 decided or closed.

| # | Incident | Closed by | State |
|---|----------|-----------|-------|
| 1 | Codespace stops at 12 hours | Documented limit; batch work in Actions (D2); chunks restart from last push (D3) | decided |
| 2 | Codespace stops after 30 idle minutes | Batch work off the codespace (D2, D13); 240-minute codespace for interactive sessions (A2) | decided; A2 done |
| 3 | Restart wiped working copies | Fixed in Wave 1; Actions machines are fresh | closed |
| 4 | Worker hung inside Cursor's runner | 60-minute hard limit; retry, then park (D3, D8) | decided |
| 5 | 10-minute step took 90 | Same as 4 | decided |
| 6 | Completion notices lost | Results through git and the issue; watcher (D9, D15) | decided |
| 7 | Permission prompts stalled agents | Run, refuse, or block and report (D10, D11); A1 trials: batch tools never wait; fail-closed policy (D17 to D20) | decided |
| 8 | Codespace token cannot start workflows | Chunks dispatch each other inside Actions (report section 10) | decided |
| 9, 10 | Web-request approvals froze reviewers | As 7; unlisted web fetch refused at once in headless mode; editor prompts only in attended sessions (D10, D13, D14, D17) | decided |
| 11 | Package downloads timed out; hooks ran them per command | Layer 0 removes the hooks; ready-made image named by lock-file fingerprint; setup failures retried apart from work (D21 to D24) | decided |

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
| D9 | The chunk design is agreed in principle: life cycle, failure responses, notifications through the work item's GitHub issue, a Cursor API key stored as a GitHub secret (report section 10). | 10-21 | `wave15-chunk-lifecycle` (recorded 10-22 after review finding 1) |
| D10 | Every agent action is configured to run, be refused, or block the task and report; never to wait for an approval nobody sees. | 10-21 | `wave15-task-modes` |
| D11 | "Block and report" and "pause for the governor" are one mechanism: the task stops, posts its question on its issue, and resumes on the governor's answer. | 10-21 | `wave15-task-modes` |
| D12 | Every task is tagged interactive or batch, set by the sprint manager at planning from defaults (interactive: brainstorming, resolution sessions, intent and policy sessions, decision walkthroughs; batch: building, reviewing, inventories, research write-ups). | 10-21 | `wave15-task-modes` |
| D13 | Interactive tasks run in the codespace; batch tasks run in GitHub Actions. | 10-21 | `wave15-task-modes` |
| D14 | Subtasks spawned inside an interactive session run in the codespace while short and attended; a subtask that turns out long or unattended is promoted to a batch task. | 10-21 | `wave15-task-modes` |
| D15 | Interactive and batch tasks hand over through git only: interactive sessions end in decisions and artifacts that start batch tasks; a batch task needing a person creates an interactive task. | 10-21 | `wave15-task-modes` |
| D16 | Nothing is implemented in this phase; the session gathers decisions until the Layer 0 walkthrough is approved. | 10-21 | `wave15-runner-and-chunks` (notes) |
| D17 | Batch runs start fail-closed: a generous allow list, a short deny list, no override flag (`--force`, Copilot's `--allow-all`). Every refusal is logged and reviewed; the allow list grows from that record; the override is reconsidered only if refusals prove frequent and costly. | 10-22 | `wave15-permission-policy` |
| D18 | The generated policy writes file deny entries in absolute or `**/` form; git-side checks (token, branch, changed paths, rulesets) are the boundary for writes. | 10-22 | `wave15-permission-policy` |
| D19 | Every chunk ends by writing a structured status: done, blocked with a question, or failed. The workflow acts on the status, not on the agent's prose; "blocked" triggers D11. Chunk instructions say: decide and record the assumption; ask only what needs the governor. | 10-22 | `wave15-permission-policy` |
| D20 | Agent program versions are pinned; the A1 trial cases become a conformance test rerun on every upgrade. | 10-22 | `wave15-permission-policy` |
| D21 | Batch chunks run inside a ready-made image holding Nix and every dependency; a chunk downloads nothing at start. | 10-22 | `wave15-batch-environment` |
| D22 | The image is named by a fingerprint of `flake.lock` and every `uv.lock`. A chunk uses only the image matching its own checkout; a merged lock-file change triggers a rebuild. A stale image is never used. | 10-22 | `wave15-batch-environment` |
| D23 | Setup failures are reported as "setup failed", retried on their own, and do not count toward the D8 retry; repeated setup failures alert the governor. | 10-22 | `wave15-batch-environment` |
| D24 | Image builds use retries, longer timeouts and caches keyed on lock files. A chunk whose task changes a lock file installs only the difference on top of the image. | 10-22 | `wave15-batch-environment` |

## Actions

| ID | Action | Owner | Done when | Status | Depends on |
|----|--------|-------|-----------|--------|------------|
| A1 | **Research the permission blocks in each agent tool.** Tools: Cursor editor (chat-spawned agents), Cursor command-line agent (headless), Copilot command-line agent. Actions: shell command, file write, web request, external tools (MCP). Cases: allowed, refused, on neither list. | architect | A table where every cell is "runs", "refused" or "blocks and reports", each with evidence (documentation or a trial), plus the settings that remove every silent wait. The headless "on neither list" case is tested first. | done for Cursor (report section 11; 13 trial runs, none waited); Copilot by documentation only, trial at build (A12) | — |
| A2 | Create a new codespace with a 240-minute idle timeout (`gh codespace create --repo infra-anoop/2026-software-lab --idle-timeout 240m`), after saving the chat records and agent stores. | governor (architect gives exact steps) | The new codespace's idle timeout reads 240 through the API. | done 10-22: new codespace reads 240 through the API; chat records and agent-store files restored from the backup | — |
| A3 | Fold the reliability findings and decisions D2 to D16 into the approach amendment (pull request #42): corrected Layer 0 list; the outside-reads reason corrected there and in `notes/wave1.5/sources/README.md`. | architect | The amendment cites this register and contains no stale reliability reason. | done 10-22: pull request #42, commit `930852e` (approach section 11 and in-place edits; `sources/README.md` corrected) | A1 |
| A4 | Open pull requests for the reliability report and the rules inventory. | architect | Both pull requests open with checks green. | open 10-22: pull requests #44 and #45 open. #45 green. #42 and #44 fail only Wave 1's order bookkeeping, done at merge after the governor's yes: a handoff on each, a claim on #44, and #42 merged first (#44 depends on its decision `wave15-reliability-rules-first`) | — |
| A5 | One combined cross-family review: rules inventory, reliability report and register, approach amendment. | architect spawns a reviewer | A verdict in git; findings triaged; the governor's yes recorded. | open 10-22: round 1 changes needed (one blocker, D9), all six findings accepted and fixed; round 2 accepts #42, #44 and #45 (report and triage in `notes/wave1.5/2026-10-reliability-rules-first-review.md`). Waiting for the governor's yes, including the wording of report section 10 (lock `wave15-chunk-lifecycle`) | A1, A3, A4 |
| A6 | Decide whether to require the governor's approval on rule paths now (a GitHub setting), before the policy session. | governor | Decision recorded; if yes, the setting read back through the API. | done 10-22: folded into the policy session (A10); not a separate decision. Until a bot identity opens pull requests, rule-file changes merge only after the governor's recorded yes | — |
| A7 | Size the Layer 0 additions and the reliability items; note that the rules inventory took 23 minutes against a 2 to 3 hour estimate. | sprint manager | Sizes recorded in the sprint manager's plan. | open 10-22: draft on `wo/wo-20261022-wave15-a7-sizing` (tranche 1 about 60 likely; the wave about 133, its bad case above the 182 ceiling); a budget decision for the governor follows | A3 |
| A8 | Discuss the next reliability item: the environment in Actions (cold installs, PyPI timeouts; caches and pinned downloads). | architect with governor | Decisions recorded here. | done (D21 to D24, report section 12) | — |
| A9 | Delete the trial branch `trial/20261020-headless-agent` and the stopped reviewer's branch `review/wo-20261020-wave15-reliability-rules-first`. | architect | Both branches gone. | later | A5 |
| A10 | Policy session: keep, rewrite or drop each Wave 1 rule, starting from the rules inventory; reword "never `gh workflow run`" to "not from the codespace"; decide when GitHub enforces the governor's approval on rule paths (from A6; workable only once a bot identity opens pull requests). | governor with architect | The interim rulebook is recorded. | later | tranche 1 |
| A11 | Store the Cursor API key and a Copilot-enabled token as GitHub secrets. | governor | Both secrets exist (names only in `deploy/secrets/schema.yaml` or the workflow docs). | at build | Layer 0 approval |
| A12 | Run the three proof trials: one chunk in Actions; a chain of three; deliberate kill and stall recovered by the watcher with an alert after the second failure. | architect | All three pass, recorded in the report. | at build | A11 |
| A13 | Measure from GitHub's runners: PyPI and Nix download failures, cold setup time, setup time with the image. | architect | Figures recorded in report section 12. | at build | Layer 0 approval |
| A14 | Consider one environment definition shared by the codespace and Actions. | architect | Proposal or a recorded "not now". | later | D21 built |
