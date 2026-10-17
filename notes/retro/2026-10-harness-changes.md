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

**Status: draft, reopened 2026-10-17.** The orchestrator recorded these as agreed on 2026-10-17 at 00:43 PT without the governor's explicit alignment; they stay draft until the discussion finishes.

Principle (governor): attack both sides. Prevent failures by root-causing the error-prone parts and getting onto a platform that is not flaky and just runs. Recover automatically when failures still happen. With little hard data, root causes come from shared experience and from industry practice.

Sources consulted: Anthropic, [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) (workflows vs agents), [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents), [multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) (durable execution, checkpoints, tracing); OpenAI, [Harness engineering](https://openai.com/index/harness-engineering/).

### A. Prevent: root causes and a stable platform

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 11 | **Deterministic control loop.** Code runs the predictable pipeline (order, build, review, triage, handoff, PR, merge). Models act only at judgment points: build, review, triage proposals. You act only at decision points. The chat session stops being the scheduler | draft (governor's point) | the job board and the `factory` command |
| 12 | **Your laptop is not part of the machinery.** The factory runs where it does not depend on your laptop or the chat window (codespace, cloud agents or CI). You watch and decide; you do not keep it alive | draft (governor's point) | — |
| 13 | **A platform that just runs.** The off-the-shelf survey judges the candidates (Cursor SDK and cloud agents, a durable workflow engine, GitHub Actions) first on whether they run unattended for a full day, then pilots one order | draft | — |
| 14 | **Root cause from experience and data.** Record stop and restart times from now on. Fix the known causes: the 30-minute idle timeout, laptop dependence, sandbox quirks. Write each environment quirk down once, and turn known traps into guards, for example refusing commits on the main checkout | draft | `HARD-RULES` notes; the shell-guard hook |
| 15 | **Git is the record; notices are only hints.** Every agent writes its start, progress and finish to git; nothing waits on a completion notice | draft | claim, verdict and handoff records |

### B. Recover: assume failure

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 16 | **Leases.** Every claim and spawned agent gets a deadline from its task estimate (item 4). A missed deadline means presumed dead: restart fresh from the last push, never resume a hung session | draft | `factory claim` |
| 17 | **Supervisor** inside the deterministic loop: checks leases, CI, machine time and unacknowledged results; writes a short line every 30 minutes; interrupts only on red, so it costs almost no context. Replaces the 30-minute heartbeat idea | draft | agenda 17, option B |
| 18 | **Acknowledgements.** The orchestrator records that it picked up each finished result; the supervisor flags any it has not | draft | — |
| 19 | **Checkpoint and resume.** A progress file per order, a commit at every green step, and a stop hook as backstop, so any agent restarts from its last commit (Anthropic's long-running harness pattern) | draft | push-after-green rule (PR #29) |
| 20 | **Liveness you can see.** A one-screen status on demand, plus an outside watchdog that tells you when the factory went quiet, even with the codespace off | draft | `factory board` |
| 21 | **Tracing.** Per agent: start, last push, activity and tokens where available, so "busy-looping or idle?" always has an answer | draft | — |
