# Harness changes agreed at the Wave 1 retro

A running register of harness changes the governor agrees during the Wave 1 retro (session started 2026-10-16, 23:00 PT). **Nothing here is implemented.** The plan, set by the governor:
1. Collect the changes here, theme by theme.
2. Look for off-the-shelf tools that cover most of them.
3. Then decide how to implement the rest.

The retro has no time limit (governor, 2026-10-17); it may run over several sessions. Wave 1.5 will be rescoped from its outcome.

Status values:
- **agreed**: you said yes;
- **proposed**: the orchestrator suggested it and you have not ruled on it yet;
- **draft**: under discussion; not yet aligned with you;
- **builds on**: names an existing part of the harness the change extends.

## Theme 1: Predictability

Principle (governor): cost saving comes from design that is correct the first time, not from fixing at the exit gate. Quality is paramount; doing mediocre work efficiently makes no sense. Budget and scope are both flexible: design to the budget, and don't cut late.

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 1 | **Estimate at intent time.** A statement of the wave's value, plus an estimate range (likely and pessimistic) in agent-hours. You make the go/no-go and cut calls then, while the investment is still low, knowing the estimate may be 50% off or more. Wave 1 is the first reference class | agreed | the intent session |
| 2 | **Architecture and buy-vs-build phase before plan approval.** It contains: a wide survey of off-the-shelf options; the major building blocks; the trust model; the irreversible choices, each decided on purpose; short experiments for the riskiest unknowns; and a review by a second model acting as staff engineer. It ends with a re-estimate. Its depth scales with the work, so small notes or records changes skip it | agreed | plan Architecture review |
| 3 | **One-level detailed design.** Each block's interfaces, APIs and data contracts are written down before building, and the rules that must always hold become automated checks | agreed (governor's addition) | the Wave 1 contract freeze |
| 4 | **Task estimates.** Each task is estimated in agent-hours plus expected review rounds, and the total is reconciled with the intent estimate. Tokens and dollars become the cost conversion once usage data exists. Tokens buy quality, so they are priced, never minimised blindly | agreed | `size_minutes` on orders |
| 5 | **Change control by the mission test.** Is this change required to strengthen the wave's core value? If yes, it comes in and the estimate is updated visibly. If it is only weakly related, it goes to the backlog. If unclear, it goes to you. Nothing is punted mechanically: punting load-bearing work stays in budget but ships a useless result | agreed | — |
| 6 | **Good-enough judgement.** Before fixing a review finding, judge its return on investment for the real context: a learning project with about 5 users, not 5 million. The reviewer rates likelihood and impact for that context. Unlikely corner cases are recorded, not fixed, and no elaborate test machinery is built to rule them out; fixing them breeds new bugs in the machinery and a vicious cycle. Wrong core behaviour is still fixed. A contested call comes to you | agreed (governor's addition) | the review-round budget; the harm-class table (agenda 5) |
| 7 | **Three-turn rule.** Anything unresolved after three turns (review rounds, fix attempts or debates) stops and comes to you for review. No fourth turn without you | agreed (governor's addition) | the review-round budget (constitution §J) |
| 8 | **Visibility.** A burn chart with scope, done and estimate lines, plus two quality-efficiency measures: first-pass acceptance and rework hours. It is for seeing, not a target | agreed | proposed `factory burndown` |
| 9 | **Drift signal triggers a re-plan, not a cut.** When the actual cost runs well past the estimate (for example 30%), the factory flags it and the response is a re-plan; the budget flexes with it | agreed | — |
| 10 | **Calibration.** Each retro compares estimates with actuals and updates the rules of thumb | agreed | — |

## Theme 2: Run reliability

**Status: draft, under discussion (reopened 2026-10-17).** Nothing in this theme is agreed unless its row says so.

Sources consulted: Anthropic, [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) (workflows vs agents), [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents), [multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) (durable execution, checkpoints, tracing, token cost of multi-agent); OpenAI, [Harness engineering](https://openai.com/index/harness-engineering/); the Kubernetes controller (reconciler) pattern; Google SRE practice on detection and game days.

### Principles

| # | Principle | Status |
|---|-----------|--------|
| P1 | **Reliable by design.** Design or buy a system that does not stall. Tests and checks confirm the design; they never stand in for it | draft (governor's point) |
| P2 | **Fix ladder.** Prefer the highest rung that works: (1) remove the cause through configuration or design; (2) route around the component; (3) recover automatically; (4) detect and report. A retry is a low rung, not a root-cause fix | draft (governor's point, ladder framing by the orchestrator) |
| P3 | **Work around during a sprint; root-cause and redesign after it.** A continuum, not a choice | draft (governor's point) |
| P4 | **Attack both sides:** prevent failures and recover from the ones that still happen | draft (governor's point) |

### A. Learn from Wave 1

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 11 | **Wave 1 failure inventory.** Every stall or failure in Wave 1, with evidence (bus timestamps, chat transcripts), its root cause, the rung of the fix ladder chosen, and the design change. Feeds the architecture phase (item 2) | draft | the retro facts (stage 2) |
| 12 | **Reliability properties are design requirements, not monitors.** Runs 8 hours unattended with your laptop closed; survives a codespace restart without losing work; no silent stall; every stall recovered or reported; you are interrupted only for decisions. Used to judge designs and platforms, and confirmed by a few deliberate trials (stop the codespace mid-order, kill an agent, close the laptop) | draft (refined by governor) | — |

### B. The control loop

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 13 | **Deterministic control loop.** Code runs the predictable pipeline. Models act only at judgment points; you act only at decision points | draft (governor's point) | the job board and the `factory` command |
| 14 | **Your laptop is not part of the machinery.** You watch and decide; you do not keep it alive | draft (governor's point) | — |
| 15 | **Control loop survey: where and in what form.** Where: codespace, GitHub Actions, cloud agents driven through the Cursor SDK, or a durable workflow engine. Form: a thin workflow file with the logic in Python, a state machine, a workflow engine, or agentic workflow definitions. Judged against item 12; the top pick is tried on one order. Part of item 2 | draft (governor: explore) | — |
| 16 | **Reconciler shape.** On every pass the loop reads the wanted state and the actual state from git and takes the next safe, repeatable step. A missed notice is harmless because the next pass sees it. Replaces the earlier acknowledgement idea | proposed | claim, verdict and handoff records |

### C. Roles and messages

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 17 | **Steady state: the orchestrator manages exceptions.** Day-to-day work is codified; judgment applies to corner cases, errors and violations | draft (governor's point) | — |
| 18 | **Bootstrap: streamline the orchestrator's role while the harness does not exist yet.** Open; under discussion | draft (open) | — |
| 19 | **Separate agents with typed messages.** Each agent role has defined input and output message formats, checked against policy at the boundary. A role is split out when its input and output fit a message and fresh context helps (review, triage, verification); tightly coupled work stays together | draft (governor's point, refined) | bus record schemas |

### D. Recover

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 20 | **Restart rule.** Up to two automatic restarts from the last checkpoint; a third failure stops and reports to you. Never automatic: merging, deleting work, changing settings | agreed | the three-turn rule (item 7) |
| 21 | **Checkpoint and resume.** A progress file per order and a commit at every green step, so a restart loses little | draft | push-after-green rule (PR #29) |
| 22 | **Deadlines on every claim.** Set from the task estimate (item 4); the loop uses them to spot dead work | draft | `factory claim` |
| 23 | **Run log.** Per agent: start, last push, activity and tokens where available. The data that root-cause work (item 11, principle P3) needs | draft | — |

### E. Telling you

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 24 | **Outside watchdog via GitHub.** When the factory goes quiet, something outside the codespace opens an issue or mentions you | draft | — |

### Future backlog (not this wave)

- Messaging connectors (WhatsApp, Telegram, Slack) for alerts and decisions. Governor: later sprint. Reachable from our own code even where the agent platform has no connector.
