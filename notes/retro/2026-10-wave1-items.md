# Wave 1 retro: every item collected

**Status: closed at the retro close (2026-10-18, decision `wave1-retro-close`).** This list was the retro's input. The outcomes live in the register (`notes/retro/2026-10-harness-changes.md`), the Wave 1.5 funnel (`notes/retro/2026-10-wave1.5-funnel.md`) and the retro's decisions (`bus/decisions/wave1-retro-*/`). See "Retro outcome" at the end. The suggestions below are kept as they were written before the retro.

Prepared by the orchestrator on 2026-10-07 at 16:30 PT, for the governor's one-hour retro session. Your decision `wave1-scope` (option C) closed Wave 1's build work. This file is the single list. It points to `notes/retro/2026-10-wave1-agenda.md` (the agenda, with the detail) and to `docs/factory/USERS_GUIDE.md`. It does not mark Wave 1 as finished.

Each row has one suggestion:
- **1.5**: do it in Wave 1.5.
- **Backlog**: record it and schedule it in a future sprint.
- **Decide**: needs your answer in the session.
- **Done**: already handled; listed for completeness.

Every Wave 1.5 suggestion is tested the same way: would it have prevented a stall, a lost hour or an unplanned review round in Wave 1? Bold rows are the ones the orchestrator suggests for the session.

## A. Your own items

| # | Item | Where | Suggestion |
|---|------|-------|------------|
| A1 | A place to put deferred work (one backlog file per feature) and a grooming step at each sprint start | Agenda 3 | **1.5**: one file and a short grooming step; without it, items in this list have no home |
| A2 | Give each sprint one primary domain (harness, infrastructure or product), with a small allowance for the other two | Agenda 4 | Decide: adopt as a rule of thumb (no build) |
| A3 | When to insist on root cause and full tests, and when good enough is fine: the harm class decides | Agenda 5 | Decide: adopt the four-class table (no build) |
| A4 | Backlog numbers and a burndown that need no hand-written queries (`factory burndown`) | Agenda 6 | **1.5** |
| A5 | Monitoring and debugging agents: "is it stuck or working?" | Agenda 7 | **1.5**, as the heartbeat in A10 |
| A6 | Review every change you approved after the plan (15 changes) | Agenda 2 | Decide: the orchestrator recommends keeping all 15 |
| A7 | Build or adopt: compare other agentic delivery tools (AI-SDLC, Spec Kitty, Fishhawk) against the factory | Agenda 12 | Decide: before Wave 2, not in 1.5 |
| A8 | An effort estimate per phase at spec review (story points or tokens) | Agenda 13 | **1.5**: Wave 1 overran because it had no total estimate and nothing flagged the growth |
| A9 | Where effort and tokens went in Wave 1, one level down | Agenda 14 | Session, part 2. Token numbers need your usage export (open decision `wave1-token-usage`) |
| A10 | A 30-minute heartbeat with a short summary; its cost to the context window | Agenda 17 | **1.5**: option B, a plain command run by a background loop, with no AI and no context cost while all is green |
| A11 | Reliability beyond the heartbeat: (a) root-cause the codespace stops; (b) cloud agents; (c) a bigger machine; (d) keepalives; (e) a sturdier handshake with agents | Agenda 18 | **1.5**: (a), (e), and (d) if (a) confirms the idle timeout. (b) as a one-order pilot. (c) only if (a) points at resources |
| A12 | A Wave 1.5 before Wave 2, with the list decided together | Agenda 15 | Decide: as its own small feature, or as a new phase of this one (the orchestrator leans to the second) |
| A13 | The user's guide | `docs/factory/USERS_GUIDE.md` | Done: on main, two review passes |

## B. Decisions waiting for you

| # | Question | Where | Suggestion |
|---|----------|-------|------------|
| B1 | Write "after three review rounds, defer test cases, never bugs" into the constitution | Agenda 9; guide question 1 | **Decide**: yes |
| B2 | Should lock wording be written as exact code names from the start, so the check can find them? | Agenda 10 | Decide: yes, for new locks |
| B3 | Close the fake-green gap: only `main`'s trusted job should be able to post the required factory result | Agenda 11 | Backlog: it needs the factory's GitHub App (A14) |
| B4 | May the orchestrator re-tag a reviewer's "product" debate as "process" if it tells you in the pull request? | Guide question 2 | **Decide** |
| B5 | Write down a worker's finishing order: handoff file, then review, then the handoff command | Guide question 3 | Decide: yes, in the spawn instructions |
| B6 | The constitution still describes packets, not orders and the bus: patch now, or wait for the Wave 2 rewrite? | Guide question 4 | Decide |
| B7 | Should every governor decision go through a decision request on the bus? | Guide question 5 | **Decide** |
| B8 | Token usage export | Bus `wave1-token-usage` | Decide: open since 10-07 |
| B9 | How the App's key reaches the codespace | Bus `app-key-delivery` | Waits for Wave 1.5 with the App (A14) |

## C. Moved out of Wave 1 by your scope decision

| # | Item | Suggestion |
|---|------|------------|
| A14 | The factory's GitHub App and the main-branch code-owner review (verified identity). Setup steps are written and reviewed | Decide: in 1.5, or later. It makes every change need your approving review on GitHub |
| C1 | The status board reads GitHub's own required checks | Backlog |
| C2 | The report-card tool (`factory retro`) and the success criterion it proves | 1.5 or backlog: decide with A4, since both read the same records |
| C3 | Check that every Wave 1 change has its review record | Backlog |
| C4 | Wave 1 exit dates computed by `factory scorecard` | Backlog |

## D. Problems found by running the factory on itself

| # | Problem | Suggestion |
|---|---------|------------|
| D1 | **No check requires the reviewer to have said "accept"**: a rejected change can pass CI; only the orchestrator's care stops the merge | **1.5** (rule path, your approval) |
| D2 | **Agents' completion notices got lost**, four times on 10-07; one loss cost about 90 minutes | **1.5**, through A10 and A11(e) |
| D3 | **Commands run in the sandbox ignored the chosen working folder**, so commits twice landed on the main checkout's local `main` (refused by GitHub, then removed) | **1.5**: a guard that refuses commits there |
| D4 | The orchestrator edited files in the main checkout before branching, and once captured setup output as a commit id | 1.5, with D3 |
| D5 | **The handoff command ignores recorded overrides while CI honours them**: it happened at least twice (PR #27, PR #33) | **1.5** |
| D6 | **Claiming an order checks the original order and ignores later amendments**: once a wrong refusal; the risky case is two orders editing one file | **1.5** |
| D7 | The deferral check flags quoted governor text and review records (overridden 3 times) | 1.5 |
| D8 | The red-first check misjudges tests whose subject isn't code, and expected failures | Backlog |
| D9 | A failed PR check run marks `main`'s commit red | Backlog |
| D10 | Workflows were invalid for a day and nothing caught it | Backlog: add a workflow linter to CI |
| D11 | Plan text contradicted a settings decision ("Factory tests stays red") and deadlocked `main` | Decide: cross-check plan text against settings decisions (habit, no build) |
| D12 | Orders don't name their sprint, so the sprint view showed none | Backlog |
| D13 | Wave 1's start date and the orders' time estimates are reconstructed | Backlog, with C4 |
| D14 | Several orders listed the task list as theirs, so only one could start | Done: only orchestrator record orders own it |
| D15 | Briefs left out the record steps; GitHub screens have look-alike names | Done (PR #29) |
| D16 | Workers hand-edited status fields in their packets (all three slice workers) | Done: the owned-paths check now catches it |
| D17 | No gate rejects a gate name that collides with a catalog row name | Backlog |
| D18 | A crashed CI rerun can leave a stale factory result; the gate name `gates` is not reserved | Backlog |
| D19 | One gate's code duplicates four helpers from another | Backlog |
| D20 | 30 merged remote branches and many review folders are still kept | Backlog: housekeeping |
| D21 | Per-gate results go only to the run report; a GitHub job summary needs a workflow change | Backlog |
| D22 | The orders' review rounds cost: 23 of 37 Wave 1 verdicts were rejections | Session, part 2 (A9) |
| D23 | Wave 1 had no total time budget; the orchestrator did not flag the growth from 94 to 110 tasks | Session: ties to A8 |

## E. Infrastructure friction (no action unless a pattern shows)

| # | Event | Suggestion |
|---|-------|------------|
| E1 | GitHub push errors for about 8 minutes on 10-07 morning; pull-request creation failed twice on 10-07 (REST worked) | Watch |
| E2 | Agents stalled on permission prompts and a blocked command form | Done: briefs forbid both (PR #29) |
| E3 | The command guard blocked a chained command (working as designed) | Watch |
| E4 | Earlier review findings marked for a later sprint (evidence binding, timeouts, size bounds and others) | Backlog: move into the backlog file at the first grooming (A1) |

## Suggested Wave 1.5 list (for you to cut)

A1 backlog file and grooming, A4 burndown, A8 estimate step, A10 heartbeat, A11 (a)(d)(e), D1 accept check, D3–D4 commit guard, D5 handoff and overrides, D6 claim and amendments, D7 deferral check. The orchestrator's rough size: 1.5 to 2 days, with a total estimate fixed up front (A8 applied to Wave 1.5 itself).

## Retro outcome (2026-10-18)

The retro went wider than this list: rather than patch Wave 1's machinery, it agreed a rebuilt factory on Spec Kit's workflow engine with GitHub Issues as the queue (decision `wave1-retro-factory-path`). No Wave 1 piece is kept by default. Every Wave 1 check, rule and record was binned in the funnel (sections 2 and 3 and its appendix) as habit, glue, bought, retire or done.

**The suggested Wave 1.5 list above is superseded** by the funnel's section 8 (62 work items with estimates) and section 9 (the agreed shape), within the appetite in decision `wave1-retro-wave15-appetite` (about 89 likely, 182 pessimistic agent-hours).

**The items that needed the governor's answer:**

| # | Outcome |
|---|---------|
| A1 | Three backlogs (product, infrastructure, tooling); register item 68 |
| A2 | Each sprint names its primary type; decision `wave1-retro-sprint-type`, register item 69 |
| A3 | Replaced by good-enough judgement for a learning project of about 5 users; register item 6 |
| A6 | Overtaken: Wave 1's plan and machinery are replaced, not carried forward |
| A7 | Done in the retro: factory survey and decision `wave1-retro-factory-path` |
| A8, D23 | Estimate at intent time and per task, in agent-hours; register items 1 and 4 |
| A9, D22, B8 | Token usage export received and locked (`wave1-token-usage`); the Wave 1 baseline is a Wave 1.5 work item (register item 85) |
| A12 | Wave 1.5 agreed as its own sprint, run by a new sprint manager session |
| A14, B3, B9 | The factory's GitHub App is a Wave 1.5 core item (funnel C10.1); `app-key-delivery` stays open until it is set up |
| B1 | Replaced: after three review rounds the item comes to the governor (funnel governor rulings) |
| B2 | Retired with the lock-word check (funnel section 3b) |
| B4 | Relabelling a reviewer's finding needs the governor; the product and process tags retire |
| B5 | Closed: the finishing order becomes code-owned procedure |
| B6 | Stale documents fixed in the cleanup slot, starting with the constitution; register item 60, Wave 1.5 cutover |
| B7 | Discussion in chat, decisions in git; register item 61 |
| D1, D5 to D8, D11, D17 to D19 | Covered by the checks theme and the 29-check audit (register theme 3, funnel section 3b) |
| D10 | The first real order of Wave 1.5: a workflow checker in CI |

Rows not listed carry over through the funnel's bins or the three backlogs. Tracing each remaining row to its new home is part of the Wave 1 failure inventory, a Wave 1.5 item (register item 11).
