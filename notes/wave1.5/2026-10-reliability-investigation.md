# Reliability investigation: why runs hang, and what to change

**Status: first report, written by the architect, 2026-10-20 (decision `wave15-reliability-rules-first`).** It covers every hang and stall on record from Wave 1 and from 2026-10-19. Four short trials (section 5) confirm or reject the main hypotheses before the Layer 0 design is final. Not yet reviewed; the cross-family review covers this report together with the approach amendment ([pull request #42](https://github.com/infra-anoop/2026-software-lab/pull/42)).

**Decisions and actions:** one line each in [`2026-10-reliability-register.md`](./2026-10-reliability-register.md). This report holds the evidence and reasoning behind them.

## 1. Summary

1. **Most "Cursor disconnected" events were the codespace stopping, for two different reasons.**
   - **The 30-minute idle timeout (confirmed).** The governor changed the default on 2026-10-05, but a default applies only to codespaces created afterwards; this codespace still has 30 minutes, and an existing codespace's timeout cannot be changed. Fix: a new codespace created with a longer timeout.
   - **A stop at 12 hours of uptime (pattern seen four times; confirmed by GitHub's documentation on 2026-10-21).** "A codespace has a maximum lifetime of 12 hours, regardless of your idle timeout policy or settings. This limit applies even while you are actively using the codespace." No setting changes it.
2. **Yesterday's two reviewer freezes were web requests waiting for a click nobody saw (confirmed by trial on 2026-10-20).** On the Cursor version installed on 10-19, every web request from a spawned agent stops with a "Skip / Run" box on that agent's own card, with no "always allow" choice; three requests to three sites each needed their own click. Reads outside the worktree were not the cause. The rule added last night (no web requests) is the fix and should be enforced by configuration, not only by the brief; its second half (no reads outside the worktree) can be relaxed.
3. **One Wave 1 worker hung inside Cursor's agent runner.** It had finished its last command and simply never took its next step. Interrupting it hung too. This is a vendor fault we cannot remove; we can only detect it and restart from the last push.
4. **Completion notices were lost at least four times on 2026-10-07.** Cause unknown. Git already holds every result; nothing was reading it.
5. **The pattern behind all of these:** a chat-spawned agent depends on the governor's Cursor window, on the codespace staying up, and on someone seeing its card. Trials on 2026-10-20 settled the parts that can be settled. A headless command-line agent needs no card and no laptop (trials 3 and 4). But anything in the codespace stops 30 minutes after the governor's window goes away, however busy the agents are (trial 3), and 240 minutes is the most a new codespace allows. **Runs longer than about 4 hours unattended, such as overnight, cannot live in a codespace;** they need GitHub Actions or a cloud agent.

**Recommendation in one line:** remove the confirmed causes now (a new codespace with a 240-minute timeout; no web requests by spawned agents, enforced by configuration; Wave 1's network-dependent hooks gone); run spawned agents as headless command-line processes that a plain watcher script can see and restart; and treat GitHub Actions as the only home for overnight runs.

**Governor direction, 2026-10-21 (decision `wave15-unattended-host`, section 9):** GitHub Actions is the baseline host for all unattended work, on its own merits and not only to escape the codespace's limits. Unattended work is cut into chunks estimated at 30 minutes, under a hard limit of 60 minutes per job, so a chunk that takes twice its estimate still finishes; estimates are tuned from measured times. Spec Kit workflows remain the process; GitHub Actions starts their steps.

## 2. Sources

- The Wave 1 orchestrator's chat (2026-10-03 to 10-18) and its 59 spawned agents' records; the Wave 1 worker and reviewer chats; this architect chat and its four spawned reviewers (2026-10-19 and 20). Read in place; nothing raw is committed.
- `notes/retro/2026-10-wave1-agenda.md` sections 7, 8, 17 and 18 (the facts gathered on 2026-10-07).
- The machine: the Cursor server's log folders and installed versions, `uptime`, the agent configuration file (only its approval settings were read).
- The GitHub API for this codespace (idle timeout, machine, last use), and the `gh codespace` command's help.

## 3. Incidents

Times are Pacific. "Lost" is wall time the work stood still, not agent hours.

| # | When | What happened | Lost | Cause |
|---|------|---------------|------|-------|
| 1 | 10-04 night; 10-04 about 21:00; 10-05 19:30; 10-06 07:30 | The codespace stopped; the governor found Cursor disconnected and reconnected. The Wave 1 orchestrator lined up the restarts: each came at 12 hours 0 minutes of uptime. It ruled out memory (nothing killed) and the idle timeout (gaps of 3 to 6 minutes while the governor was active) | Re-orientation each time; work in flight after its last push (10-05: Stream B's final reports) | A stop at 12 hours of uptime. **Confirmed** on 2026-10-21: GitHub documents a 12-hour maximum lifetime for every codespace, even in active use (section 5, trial 2) |
| 2 | 10-06 17:55; 10-07 12:37 | The codespace stopped while the governor was away or the orchestrator was waiting | 10-07: part of a 90-minute standstill | The 30-minute idle timeout. **Confirmed:** the API shows 30 minutes today; the 10-05 change was to the default, which applies only to new codespaces; `gh codespace edit` cannot change it, only `gh codespace create --idle-timeout` |
| 3 | 10-04 night | A restart wiped the agents' working copies, which were under `/tmp` | Rebuilding the working copies | **Fixed** in Wave 1: working copies live under `/workspaces` |
| 4 | 10-05 21:35 to 10-06 00:13 | A worker pushed three commits, finished a commit-and-push command, and never took another step. No process running; its record not growing; no tokens used. Interrupting it hung for 11 minutes; the governor had to reload the window | About 2.5 hours | Inside Cursor's agent runner (between a finished command and the next model call). **Vendor fault, cause unknown** |
| 5 | 10-06 about 20:00 | A step expected to take 10 minutes took about 90; the governor moved it to the background by hand | About 80 minutes | Probably the same class as 4. **Unknown** |
| 6 | 10-07 11:50 to 13:27, and three more that day | Two reviewers finished; their completion notices never reached the orchestrator, which waited. The codespace stopped at 12:37 inside the gap (incident 2) | About 90 minutes, plus the stop | **Unknown.** Notices are delivered into the parent chat; nothing else watched the review branches |
| 7 | Before 10-05 | Agents stalled on permission prompts and on a sandbox-blocked command form while the governor was away | Hours, across several runs | Agents asked for elevated permissions. **Fixed** in Wave 1: spawned agents never ask; the allowed command form is written down |
| 8 | 2026-09-20 | The codespace's own token cannot start workflows; the sandbox sometimes refused GitHub's API | A session | Codespace token scope and sandbox network rules. **Handled** by the ship playbook (no `gh workflow run`) |
| 9 | 10-19 20:38 to 22:27 | Reviewer 1 sent six web requests at once (Spec Kit's site, the Superpowers repository and raw files, the GitHub blog, GitHub's documentation) and never continued | About 1 hour 50 minutes, plus a restart | See incident 10 |
| 10 | 10-19 22:32 to 23:10 | Reviewer 2 pushed its skeleton, fetched two pages (Spec Kit's site, GitHub) successfully, read a file outside its worktree successfully, then sent two more web requests (the GitHub blog, GitHub's documentation) and never continued. The governor saw a question on its card and answered it | About 40 minutes, a third reviewer, and the governor's attention | A web request waiting on an approval shown only on the agent's card. **Confirmed** by trial 1. Not the outside read |

| 11 | 10-20 08:48 to 09:25 | Downloads from the Python package index timed out twice (2 minutes each) when a new worktree set up the factory's environment; during trial 4, each git command waited about 60 seconds on Wave 1's shell-guard hook, which runs that same setup before every command | Minutes per command; a worker would stall on it | Wave 1's hooks depend on a network download at every command. **Removed by Layer 0** (the hooks go, a small standalone guard stays) |

Also in Wave 1, not a hang: long review loops that burned tokens. The three-round rule covers them.

## 4. What the evidence says

### 4.1 The codespace stops (incidents 1 to 3)

Every "Cursor disconnected" message examined lines up with a codespace restart (`uptime` and the server's log folders), so these are one family. Two causes are separable:
- **Idle stops** come 30 minutes after the governor's Cursor window goes away. Trial 3 showed that an agent running commands and pushing every 3 minutes does not count as activity, so no amount of agent work keeps the codespace up. The longest timeout GitHub allows is 240 minutes, so even a new codespace gives at most 4 unattended hours: enough for a meeting or an afternoon, not for a night.
- **12-hour stops** were seen four times at exactly 12 hours of uptime. The machine booted today at 06:12, so if the pattern holds it stops at about 18:12 today even while in use.

### 4.2 The reviewer freezes (incidents 9 and 10)

What the records show:
- Both freezes came right after a web request. In both, the requests that never returned included the GitHub blog and GitHub's documentation site.
- Reviewer 2's earlier requests to Spec Kit's site and GitHub returned; its read of a file outside the worktree returned. So neither "all web requests" nor "outside reads" freeze an agent.
- Between 10-04 and 10-17, six spawned agents made web searches or fetches (3 to 20 calls each), two of them fetching pages from GitHub's documentation site directly, and none froze. None fetched the GitHub blog directly; one searched it.
- A new Cursor version was installed on this machine at 18:33 on 10-19, about two hours before the first freeze. Both freezes ran on it.
- The agent configuration on this machine has approval mode "allowlist", with automatic acceptance of web searches off.

Two hypotheses fitted: (a) the new Cursor version asks approval for web requests from spawned agents, where the old one did not; (b) only a site not seen before raises an approval.

**Trial 1 result (2026-10-20, 08:56 to 09:05, governor watching the card): hypothesis (a).** A spawned agent fetched three pages one at a time: a GitHub documentation page Wave 1 agents had fetched without any prompt, `example.com`, and the GitHub blog's changelog. Each request stopped with "Fetching page ..." and two buttons, Skip and Run, on the agent's own card, and waited until the governor clicked Run. There is no "always allow" choice on the card, and approving one request did not cover the next. Nothing outside the card shows that the agent is waiting.

The cure: spawned agents make no web requests, and the spawning session commits dated copies of what they need (done since 10-19; the third reviewer finished in about 7 minutes this way). Because a brief can be ignored, Layer 0 should also remove the web tools from spawned agents' allowed tools where the configuration allows it.

Correction for the handover's operating rule 8: reading outside the worktree did not cause a freeze. That half of the rule can stay as hygiene (the primary checkout is off limits) but is not a reliability rule.

### 4.3 The hung worker and the lost notices (incidents 4 to 6)

Both happen inside Cursor, below anything we configure. A hung agent is silent and idle; a lost notice leaves a finished result unread. In both cases git already holds the truth: the last push of a hung agent, the verdict or handoff of a finished one. What was missing is something that reads git on a clock and acts.

### 4.4 The structural point

A spawned chat agent in this codespace needs four things nobody guarantees: the codespace up (incidents 1 and 2), the governor's Cursor window connected, every prompt seen (incidents 7, 9 and 10), and every notice delivered (incident 6). Rules have removed some causes. The rest can only be detected and recovered. Work that must run unattended for hours belongs off the laptop and outside the codespace's lifetime: in GitHub Actions (the approved design's path from Layer 3) or in Cursor's cloud agents.

## 5. Four trials before the design is final

Each takes minutes, and each can fail.

1. **Web request from a spawned agent. Done 2026-10-20: every request waits for a click (section 4.2).**
2. **The 12-hour stop. Closed without a trial on 2026-10-21:** GitHub documents a 12-hour maximum lifetime for every codespace, even in active use ([Understanding the codespace lifecycle](https://docs.github.com/en/codespaces/about-codespaces/understanding-the-codespace-lifecycle)). The same documentation defines activity as typing, mouse use, or terminal input or output ([Setting your timeout period](https://docs.github.com/en/codespaces/setting-your-user-preferences/setting-your-timeout-period-for-github-codespaces)), which agrees with trial 3.
3. **Laptop closed. Done 2026-10-20: the agent kept working, and the codespace stopped 30 minutes after the laptop closed anyway.** A headless agent pushed a heartbeat commit every 3 minutes (branch `trial/20261020-headless-agent`). The governor closed the laptop at about 09:26 and left it closed until the evening. Heartbeats 1 to 11 arrived on time, from 09:23:57 to 09:55:17; heartbeat 12, due at about 09:58, never came. On reconnecting, the machine had a new boot time and its temporary folder was empty. So the codespace stopped between 28 and 32 minutes after the laptop closed, while the agent was running commands and pushing every 3 minutes: **the idle timeout does not count an agent's work as activity.** A headless agent does not need the laptop; it does need the codespace, and the codespace stops 30 minutes after the governor's window goes away.
4. **A headless agent. Done 2026-10-20, passed.** The Cursor command-line agent (version 2026.10.19, installed in the home folder, signed in once by the governor) ran in a background process in its own worktree, with GPT-5.6 Sol and a committed allowed-commands file (`.cursor/cli.json` on branch `trial/20261020-headless-agent`). Unattended, it read this report, wrote a correct five-line summary, committed and pushed (`ddbf5d4`) in about 7.5 minutes. A `curl` command was refused at once ("Command blocked by permissions configuration") and a web fetch was refused at once ("Web fetch rejected"); neither waited for anyone. One finding: each git command took about 60 seconds, because the agent also runs the repository's editor hooks, and Wave 1's shell-guard hook first builds the factory's Python environment, which was slow to download this morning (incident 11).

## 6. Proposed design, by the fix ladder

**Remove the cause**
- **A new codespace with a 240-minute idle timeout** (the maximum), created by the governor: `gh codespace create --repo infra-anoop/2026-software-lab --idle-timeout 240m` or the equivalent in the Codespaces page. Before it, save what lives only on this machine: the chat records (the evidence for this report) and the agent stores. Closes incident 2.
- **No web requests by spawned agents;** the spawning session commits dated copies of outside sources. Closes incidents 9 and 10 (cause confirmed by trial 1). Already in force by brief; enforced by configuration in Layer 0 where possible.
- **No permission requests by spawned agents,** and each agent's allowed commands in a committed configuration file, so a command is allowed or refused, never left waiting. Closes incident 7 for the command-line agent as well.

**Route around**
- **Run spawned agents as command-line processes, not chat cards** (trial 4 passed). The orchestrator starts a worker or reviewer with the Cursor command-line agent: model pinned, allowed commands set, its output written to a log file, in its own worktree. A process has no card to wait on, a script can see whether it is alive, and the same agent is what the approved design runs in GitHub Actions, so this is Layer 1's install brought forward rather than new machinery.
- **Long unattended runs leave the codespace.** Trial 3 makes this a requirement, not a preference: overnight work goes to GitHub Actions, the approved design's path from Layer 3. Until then, unattended runs are limited to the codespace's timeout (about 4 hours with a new codespace), or go to a Cursor cloud agent for a trial.

**Recover automatically**
- **A watcher: a plain script loop, no AI** (the retro's heartbeat option B, now with teeth). Every 5 minutes while any agent runs, it checks each agent's branch and process: a start push within 10 minutes; a push before its deadline; a finished result (verdict or handoff) not yet picked up. A silent agent is stopped and restarted fresh from its last push, at most twice; a third silence is reported to the governor. A finished result is announced to the orchestrator through the watched terminal, so a lost notice no longer stalls anything. Never resume a hung agent: interrupting one hangs too (incident 4).
- **Deadlines from the estimate** on every agent run, and the restart rule (at most two) from the retro.

**Detect and report**
- **A scheduled GitHub workflow** that opens an issue mentioning the governor when an active branch has had no push for longer than its deadline, so a stopped codespace is reported even when nothing in it can run (the retro's option C). This is a small, early version of Layer 5's watchdog.

## 7. Proposed Layer 0 list

For the approach note's Layer 0 (section 2.7 of the amendment), subject to the trials:
1. The new codespace (governor), with chat records and agent stores saved first.
2. The spawned-agent rules: no web requests; no permission requests; a first push within 10 minutes and a push at every green step. Operating rule 8's reason corrected.
3. The Cursor command-line agent installed, with a committed allowed-commands file; spawned agents run as processes.
4. The watcher script, with restart from the last push (at most two) and announcement of finished results.
5. The scheduled silence alert in GitHub Actions.

Layer 0's reliability done-when then reads: an agent is silenced on purpose and restarted by the watcher without anyone clicking, and a third silence reaches the governor; a command outside the allowed list is refused with no prompt; a finished result is picked up with no completion notice; the codespace survives 3 hours of the governor being away.

## 8. What this report could not settle

- Why Cursor's runner hangs and loses notices; that is the vendor's to fix, and the watcher makes it survivable.
- Whether the Cursor command-line agent runs our chunks in GitHub Actions as it did in the codespace (the approved plan's Layer 2 unknown 1, now the baseline's first proof).
- Where, after section 9, the codespace watcher and the GitHub-side watcher each sit in Layers 0 to 3; for the Layer 0 walkthrough.
- Cursor cloud agents: the governor's 2026-10-20 experiment found they check the repository out onto Cursor's own machines and cannot use the codespace; a possible second host, not the baseline.

## 9. How others run unattended agents, and the direction taken (2026-10-21)

The governor asked for a benchmark against current practice before choosing where unattended work runs. Research on 2026-10-21, from primary documentation where possible:

- **Unattended agent factories are not built on Codespaces.** Comparisons position Codespaces as environments "for humans first", and the 12-hour lifetime rules out overnight work. One hobbyist design drives an agent inside a codespace over SSH from an always-on server, for single requests.
- **The common shape is a fresh machine per task:** the task arrives, a new machine copies the repository, the agent works, opens a pull request, and the machine is discarded; git and pull requests carry all state. GitHub's Copilot cloud agent runs on GitHub Actions ([About Copilot cloud agent](https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent)); Cursor documents its command-line agent in GitHub Actions ([Cursor CLI in GitHub Actions](https://cursor.com/docs/cli/github-actions)) and runs cloud agents on its own machines; Anthropic ships an official GitHub Action for Claude Code; OpenAI's Codex, Google's Jules and Devin each use a vendor machine per task.
- **The reasons are scale and safety, not time limits:** one machine per task in parallel; each task gets only the secrets and network it needs; setup is written down; any machine can die and the next resumes from git.
- **GitHub caps its own agent at one hour:** "Each Copilot cloud agent session has a maximum execution time of 59 minutes. This limit cannot be extended or bypassed… Break complex tasks into smaller, focused tasks." GitHub Actions jobs themselves may run 6 hours; the one-hour cap here is the lab's own choice, set as each job's time limit.
- **Long runs are many short sessions with a written handoff.** Anthropic's published harness ([Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)): each session starts fresh, reads a progress file and recent git history, does one feature, commits, updates the progress file; a separate evaluator judges the work. Durable-workflow tools take the same stance ("We assume the process will die", Temporal).
- **What does not fit a throwaway machine:** work needing a person, a service that must stay up, personal sign-ins, or several repositories at once. Leading products keep a long-lived environment for that alongside; here, the codespace.

Two of the comparison articles come from vendors of agent platforms, and details change monthly; the points above rest on GitHub's, Cursor's and Anthropic's own pages.

**Direction (governor, 2026-10-21, decision `wave15-unattended-host`):**
1. GitHub Actions is the baseline host for unattended work; the codespace is the workbench for conversation and supervised work.
2. Chunks are estimated at 30 minutes, with a hard 60-minute limit per job; estimates are tuned from measured times.
3. Spec Kit workflows stay the process; GitHub Actions triggers their steps, each step one or more chunks.

**Further direction (governor, 2026-10-21 10:20 PT, decision `wave15-runner-and-chunks`).** The session is gathering decisions; nothing is implemented yet.

4. **Copilot is designed in from day one, behind a switch.** A setting (for example `AI_ENV`, default `cursor`) chooses the agent per role, with one default and per-step overrides, so a builder can run on Cursor and its reviewer on Copilot. Because the workflow configuration, not the agent's own record, decides which tool runs the reviewer, cross-family review becomes a hard rule (the rules inventory found it is today checked only by self-declared model names). The switch selects Copilot's command-line agent inside the lab's own Actions job, the same shape as Cursor's, so the chunk steps, time limit, watcher and notifications stay identical; GitHub's Copilot cloud agent (assigned an issue, run on GitHub's terms with a 59-minute cap) stays a later option. The allowed-commands policy is written once and generated into each tool's format, so switching tools cannot loosen it. A Copilot-enabled token, stored like the Cursor key, comes at build time.
5. **Chunk size is a factory requirement fed into Spec Kit's plan.** The plan is shaped so work can be cut into thin pieces that are each testable; the task list carries each task's estimate, at most 30 minutes, with a simple check (starting as a warning) that every task has one and none is larger; the reviewer judges realism. Each chunk must also leave the code working and have its own done-check. Every step is a chunk, not only implementation: specify, plan and review can overrun too. Each chunk reports time used against its estimate; the sprint manager watches the ratio and tightens sizing guidance if tasks routinely run past about 1.5 times their estimate.
6. **The exception path is automatic first, then the sprint manager.** On a chunk that hits the 60-minute limit: retry once from its last push with a note; on a second overrun, park the task with a clear note and continue with the next task that does not depend on it; the sprint manager takes parked tasks in the morning (split, re-plan, or escalate to the governor). A night loses at most one task's progress, not the whole run. An overnight sprint-manager job in Actions that splits parked tasks is a later option.

Effects on sections 6 and 7, to settle in the Layer 0 walkthrough: the codespace watcher shrinks to daytime use, the long-term watcher is the scheduled GitHub workflow, and the 240-minute codespace protects supervised sessions rather than overnight runs.

## 10. The unattended chunk: design agreed in principle (2026-10-21)

The governor agreed this narrative at 10:16 PT ("all looks good to me, including notifications and cursor API key"). Design only; nothing is built.

**Life of a chunk**
1. **Start.** A trigger (a merged plan, the previous chunk finishing, a schedule) starts a job on a fresh GitHub machine with a 60-minute hard limit.
2. **Bearings.** Read the work item's progress note and recent git history; check the code works before changing anything (Anthropic's harness pattern).
3. **Work.** One task from the Spec Kit task list, estimated at 30 minutes; commit and push at each green step, so a kill loses minutes.
4. **Hand off.** Update the progress note (done, next, learned); comment on the work item's GitHub issue with time used against the estimate.
5. **Chain.** Start the next chunk, or hand over to review when the task list is done. GitHub does not let a job's built-in token start workflows through ordinary pushes (loop protection); an explicit workflow-start call is allowed, so chunk N starts chunk N+1 that way. The lab rule "never `gh workflow run`" (rules inventory R35) exists because the codespace's token cannot dispatch; it is reworded to "not from the codespace".

**Failures and responses**
| Failure | Response | Type |
|---------|----------|------|
| Chunk passes 60 minutes | GitHub kills it; one retry from the last push with a note; a second overrun parks the task (section 9 item 6) | hard |
| Agent hangs | The same time limit; hangs stop being a special case | hard |
| Cursor or Copilot service failure | Short retry | hard |
| Usage limit | Stop the chain; alert the governor | hard |
| Two chunks on one work item | GitHub's one-job-per-group setting; the second waits | hard |
| Runaway cost | Caps on chunks per work item per day and on concurrent jobs; "at most 3 agents" becomes configuration | hard |
| The chain goes silent (a job never started, a lost dispatch) | A scheduled watcher workflow every 15 minutes: an item in progress with no running job and no recent push is restarted, at most twice, then the governor is alerted | hard |
| Finished but wrong | Not a reliability failure; review catches it | (review) |

**Notifications.** Comments and mentions on the work item's GitHub issue, reaching the governor's phone through GitHub's notifications; no need to open the codespace to learn a run is stuck.

**Proof, in three trials that can fail** (at build time): one chunk in Actions (trial 4's equivalent); a chain of three chunks with no one touching anything; deliberate sabotage (one chunk killed midway, one made to stall) recovered by the watcher, with an alert after the second failure. All three need only a Cursor API key stored as a GitHub secret (governor action at build time).

## 11. Permission blocks in each agent tool (action A1): documentation pass, 2026-10-21

Read on 2026-10-21 at about 10:40 PT; the codespace then idle-stopped before anything was written (the session's own work died with it, an instance of decision D14's reason). Written up on 2026-10-21 at 23:45 PT. Trials still to run are marked.

| Tool and mode | Allowed | Refused | On neither list | Source |
|---------------|---------|---------|-----------------|--------|
| Cursor command-line agent, headless (`-p`) | Runs (trial 4) | Refused at once, no prompt (trial 4: `curl`, web fetch) | **Untested.** Documentation: a web fetch with no allow entry "prompts for approval"; print mode cannot prompt, so it may refuse, or may wait. File writes need `--force` or are only proposed | [CLI permissions](https://cursor.com/docs/cli/reference/permissions); trial 4 |
| Cursor editor, chat and spawned agents | Runs | No documented instant-refuse list; Auto-review's classifier can block, and Cursor may then show an approval prompt | **Waits for a click** unless the run mode is "Run Everything" (no prompts, no safety). Auto-review (the default) covers shell, external tools and web fetch; Allowlist runs only listed actions | [Run Modes](https://cursor.com/docs/agent/security/run-modes); [permissions.json](https://cursor.com/docs/reference/permissions); trial 1 |
| Copilot command-line agent, programmatic (`-p`) | Runs (`--allow-tool`) | Refused (`--deny-tool`, which beats any allow) | **Refused, no wait:** "Permission denied and could not request permission from user" (secondary source; to confirm). `--no-ask-user` also stops clarifying questions; a `permissionRequest` hook can allow or deny by script | [Copilot CLI](https://docs.github.com/en/copilot/concepts/copilot-surfaces/copilot-cli); a practitioner's write-up; Copilot CLI release notes |

Findings so far:
1. **Copilot's headless mode already fails closed:** anything not allowed is refused, never waited on. The target behavior, by default.
2. **Cursor's headless mode is the open cell.** Trials: a shell command, a web fetch and a file write on neither list, each with and without `--force`. If any waits, the fix is a complete deny-by-default list in the generated policy (decision D6).
3. **Cursor's editor has no zero-wait setting short of "Run Everything".** Prompts there are acceptable only because a person is present (decision D13). Inline subtasks must stay short and attended (D14), and must not make web requests unless the domain is allowlisted (unified domain allowlisting for web search and fetch, per Cursor's changelog).
4. **A fifth kind of block: the agent asking a question mid-task.** Copilot has a switch for it (`--no-ask-user`); Cursor's headless equivalent is unknown. Added to the table's action kinds for the trials.
5. **Policy files are "not a security boundary"** in Cursor's own words. The hard boundaries for batch work stay the job's token permissions, time limit and GitHub rulesets (rules inventory, architect's comment D).

### 11.1 Trials: Cursor command-line agent, headless, 2026-10-21 23:50 PT

Version 2026.10.19-6bbf2c4, model composer-2.5-fast (permission handling is the program's, not the model's), each case in its own folder with its own `.cursor/cli.json`, a 300-second timer (a run reaching it would mean "waits"). Thirteen runs; scripts, permission files and logs on branch `trial/20261020-headless-agent`, folder `notes/trials/a1/` (commit `4fa04ac`).

| Action | On the allow list | On the deny list | On neither list, no `--force` | On neither list, with `--force` |
|--------|-------------------|------------------|-------------------------------|---------------------------------|
| Shell command | runs | **refused**, also with `--force` ("Command blocked by permissions configuration") | **refused** ("Rejected") | **runs** |
| Web fetch | (not tested) | refused (trial 4) | **refused** ("Web fetch rejected: User Rejected") | **runs** |
| File write (editing tool) | runs, no `--force` needed | **refused only with an absolute or `**/`-prefixed pattern** ("Write permission denied … Blocked by permissions configuration"); the relative pattern `scratch/**` did not match, with or without `--force` (in a folder that is not a git repository) | **runs** | runs |
| Question to the user mid-task | n/a | n/a | the run **ends**, its final message being the question; nothing waits | (not tested) |

**No case waited.** Every run ended within 17 seconds.

Findings:
1. **The Cursor headless agent never waits;** "on neither list" means refused for shell and web fetch. Together with Copilot's documented behavior, both batch tools fail closed. Incidents 7, 9 and 10 cannot recur in batch work.
2. **`--force` turns "on neither list" into "allowed"** for shell and web fetch; only the deny list survives it. Batch runs do not use `--force`; writes do not need it.
3. **File writes are open by default.** The allow list does not fence them; only deny entries in absolute or `**/` form do. The real boundary for writes is on the git side: what a chunk may push (its token and branch), a changed-paths check, and the rulesets.
4. **A question ends the run.** "Block and report" (D11) needs no special machinery from the tool: the workflow must tell "finished" from "stopped to ask". That should come from a structured status the chunk writes (done, blocked with a question, failed), not from reading prose.
5. **Behavior is version-specific** (the relative write pattern is one surprise). The CLI version is pinned, and these cases become a conformance test rerun on every upgrade.

Not tested: external tools (no MCP servers configured); Copilot (no access yet; its documentation says unlisted tools are refused in programmatic mode).

## 12. The environment for batch chunks (incident 11, action A8), 2026-10-22

The problem has two halves. Reliability: a download timeout fails a chunk that did nothing wrong. Time: a cold install spends the 30-minute budget. Current CI shows both: the main check installs Nix from scratch on every run with no binary cache, and the architect backlog already records that the full test run downloads from PyPI and "can fail falsely" (O1).

Options considered: (1) retries, longer timeouts and caches keyed on lock files; (2) setup failures classified apart from work failures; (3) a ready-made image holding Nix and every dependency; (4) one environment definition shared by the codespace and Actions. The industry pattern is (3): Codespaces prebuilds, Copilot's setup steps, Ona's prebuilt environments. The lab already builds and publishes images to GitHub's registry for deploys.

Decided (D21 to D24): (3) as the baseline, made drift-proof by naming each image after a fingerprint of the lock files, so a stale image is never found rather than relying on anyone to rebuild it; (2) from the start, so an outage does not get good tasks parked; (1) protects the image build, now the only place a download can fail. A chunk whose task changes a lock file mid-run installs only the difference on top of the image. (4) is the direction, not a first step.

Unknown, settled at build: whether PyPI times out from GitHub's runners at all; the timeouts on record came from the codespace. If downloads are reliable there, the image still pays for itself in setup time.
