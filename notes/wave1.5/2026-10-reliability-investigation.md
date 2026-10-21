# Reliability investigation: why runs hang, and what to change

**Status: first report, written by the architect, 2026-10-20 (decision `wave15-reliability-rules-first`).** It covers every hang and stall on record from Wave 1 and from 2026-10-19. Four short trials (section 5) confirm or reject the main hypotheses before the Layer 0 design is final. Not yet reviewed; the cross-family review covers this report together with the approach amendment ([pull request #42](https://github.com/infra-anoop/2026-software-lab/pull/42)).

## 1. Summary

1. **Most "Cursor disconnected" events were the codespace stopping, for two different reasons.**
   - **The 30-minute idle timeout (confirmed).** The governor changed the default on 2026-10-05, but a default applies only to codespaces created afterwards; this codespace still has 30 minutes, and an existing codespace's timeout cannot be changed. Fix: a new codespace created with a longer timeout.
   - **A stop at about 12 hours of uptime (pattern seen four times, cause unconfirmed).** A trial tonight confirms or rejects it.
2. **Yesterday's two reviewer freezes were web requests waiting for a click nobody saw (confirmed by trial on 2026-10-20).** On the Cursor version installed on 10-19, every web request from a spawned agent stops with a "Skip / Run" box on that agent's own card, with no "always allow" choice; three requests to three sites each needed their own click. Reads outside the worktree were not the cause. The rule added last night (no web requests) is the fix and should be enforced by configuration, not only by the brief; its second half (no reads outside the worktree) can be relaxed.
3. **One Wave 1 worker hung inside Cursor's agent runner.** It had finished its last command and simply never took its next step. Interrupting it hung too. This is a vendor fault we cannot remove; we can only detect it and restart from the last push.
4. **Completion notices were lost at least four times on 2026-10-07.** Cause unknown. Git already holds every result; nothing was reading it.
5. **The pattern behind all of these:** a chat-spawned agent depends on the governor's Cursor window, on the codespace staying up, and on someone seeing its card. Trials on 2026-10-20 settled the parts that can be settled. A headless command-line agent needs no card and no laptop (trials 3 and 4). But anything in the codespace stops 30 minutes after the governor's window goes away, however busy the agents are (trial 3), and 240 minutes is the most a new codespace allows. **Runs longer than about 4 hours unattended, such as overnight, cannot live in a codespace;** they need GitHub Actions or a cloud agent.

**Recommendation in one line:** remove the confirmed causes now (a new codespace with a 240-minute timeout; no web requests by spawned agents, enforced by configuration; Wave 1's network-dependent hooks gone); run spawned agents as headless command-line processes that a plain watcher script can see and restart; and treat GitHub Actions as the only home for overnight runs.

## 2. Sources

- The Wave 1 orchestrator's chat (2026-10-03 to 10-18) and its 59 spawned agents' records; the Wave 1 worker and reviewer chats; this architect chat and its four spawned reviewers (2026-10-19 and 20). Read in place; nothing raw is committed.
- `notes/retro/2026-10-wave1-agenda.md` sections 7, 8, 17 and 18 (the facts gathered on 2026-10-07).
- The machine: the Cursor server's log folders and installed versions, `uptime`, the agent configuration file (only its approval settings were read).
- The GitHub API for this codespace (idle timeout, machine, last use), and the `gh codespace` command's help.

## 3. Incidents

Times are Pacific. "Lost" is wall time the work stood still, not agent hours.

| # | When | What happened | Lost | Cause |
|---|------|---------------|------|-------|
| 1 | 10-04 night; 10-04 about 21:00; 10-05 19:30; 10-06 07:30 | The codespace stopped; the governor found Cursor disconnected and reconnected. The Wave 1 orchestrator lined up the restarts: each came at 12 hours 0 minutes of uptime. It ruled out memory (nothing killed) and the idle timeout (gaps of 3 to 6 minutes while the governor was active) | Re-orientation each time; work in flight after its last push (10-05: Stream B's final reports) | A stop at about 12 hours of uptime. GitHub's documentation does not describe one; one outside report does. **Unconfirmed** (trial 2) |
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
2. **The 12-hour stop.** Passive: on a day the codespace stays in use, note the boot time and check whether it restarts 12 hours later. Not observed on 2026-10-20, because trial 3 stopped the codespace at about 09:56; to be rerun.
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

- Why the codespace stops at about 12 hours (trial 2 confirms only whether it does).
- Why Cursor's runner hangs and loses notices; that is the vendor's to fix, and the watcher makes it survivable.
- Whether a Cursor cloud agent can run the lab's Nix and git commands; one trial review would tell.
