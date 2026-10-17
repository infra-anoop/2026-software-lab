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

**Status: agreed (governor, 2026-10-17 10:34 PT), after reopening the discussion that morning.**

Sources consulted: Anthropic, [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) (workflows vs agents), [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents), [multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) (durable execution, checkpoints, tracing, token cost of multi-agent); OpenAI, [Harness engineering](https://openai.com/index/harness-engineering/); the Kubernetes controller (reconciler) pattern; Google SRE practice on detection and game days.

### Principles

| # | Principle | Status |
|---|-----------|--------|
| P1 | **Reliable by design.** Design or buy a system that does not stall. Tests and checks confirm the design; they never stand in for it | agreed (governor's point) |
| P2 | **Fix ladder.** Prefer the highest rung that works: (1) remove the cause through configuration or design; (2) route around the component; (3) recover automatically; (4) detect and report. A retry is a low rung, not a root-cause fix | agreed (governor's point, ladder framing by the orchestrator) |
| P3 | **Work around during a sprint; root-cause and redesign after it.** A continuum, not a choice | agreed (governor's point) |
| P4 | **Attack both sides:** prevent failures and recover from the ones that still happen | agreed (governor's point) |

### A. Learn from Wave 1

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 11 | **Wave 1 failure inventory.** Every stall or failure in Wave 1, with evidence (bus timestamps, chat transcripts), its root cause, the rung of the fix ladder chosen, and the design change. Feeds the architecture phase (item 2) | agreed | the retro facts (stage 2) |
| 12 | **Reliability properties are design requirements, not monitors.** Runs 8 hours unattended with your laptop closed; survives a codespace restart without losing work; no silent stall; every stall recovered or reported; you are interrupted only for decisions. Used to judge designs and platforms, and confirmed by a few deliberate trials (stop the codespace mid-order, kill an agent, close the laptop). An outside watchdog stays as the bottom-rung safety net | agreed (refined by governor) | — |

### B. The control loop

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 13 | **Deterministic control loop.** Code runs the predictable pipeline. Models act only at judgment points; you act only at decision points | agreed (governor's point) | the job board and the `factory` command |
| 14 | **Your laptop is not part of the machinery.** You watch and decide; you do not keep it alive | agreed (governor's point) | — |
| 15 | **Control loop survey: where and in what form.** Where: codespace, GitHub Actions, cloud agents driven through the Cursor SDK, or a durable workflow engine. Form: a thin workflow file with the logic in Python, a state machine, a workflow engine, or agentic workflow definitions. Judged against item 12; the top pick is tried on one order. GitHub Actions is the trigger and scheduler, not the brain. Part of item 2 | agreed | — |
| 16 | **Reconciler shape.** On every pass the loop reads the wanted state and the actual state from git and takes the next safe, repeatable step. A missed notice is harmless because the next pass sees it. Replaces the earlier acknowledgement idea | agreed | claim, verdict and handoff records |

### C. Roles and messages

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 17 | **Steady state: the orchestrator manages exceptions.** Day-to-day work is codified; judgment applies to corner cases, errors and violations | agreed (governor's point) | — |
| 18 | **Bootstrap.** This session stays coach and architect; a separate session runs Wave 1.5, as an experiment. The first thing Wave 1.5 builds is a minimal control loop | agreed (decision `wave1-retro-bootstrap-role`, A) | — |
| 19 | **Separate agents with typed messages.** Each agent role has defined input and output message formats, checked against policy at the boundary. A role is split out when its input and output fit a message and fresh context helps (review, triage, verification); tightly coupled work stays together, because each split costs tokens and context | agreed (governor's point, refined) | bus record schemas |

### D. Recover

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 20 | **Restart rule.** Up to two automatic restarts from the last checkpoint; a third failure stops and reports to you. Never automatic: merging, deleting work, changing settings | agreed | the three-turn rule (item 7) |
| 21 | **Checkpoint and resume.** A progress file per order and a commit at every green step, so a restart loses little | agreed | push-after-green rule (PR #29) |
| 22 | **Deadlines on every claim.** Set from the task estimate (item 4); the loop uses them to spot dead work | agreed | `factory claim` |
| 23 | **Run log.** Per agent: start, last push, activity and tokens where available. The data that root-cause work (item 11, principle P3) needs | agreed | — |

### E. Telling you

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 24 | **Outside watchdog via GitHub.** When the factory goes quiet, something outside the codespace opens an issue or mentions you | agreed | — |

### Future backlog (not this wave)

- Messaging connectors (WhatsApp, Telegram, Slack) for alerts and decisions. Governor: later sprint. Reachable from our own code even where the agent platform has no connector.

## Theme 3: The factory's own checks

**Status: draft, under discussion (opened 2026-10-17).** Nothing in this theme is agreed unless its row says so.

Evidence: Wave 1 retro items D1, D5 to D8, D11, D17 to D19 in `notes/retro/2026-10-wave1-items.md`; 25 checks; 5 overrides in Wave 1, 3 of them on one check.

Sources consulted: OpenAI, [Harness engineering](https://openai.com/index/harness-engineering/) (few mechanically enforced invariants, fix-instructions in error messages, minimal blocking gates, continuous cleanup); Google Tricorder (analyzers kept under about 10% false positives or switched off); Anthropic, [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) (one default-fail contract judged by a fresh evaluator) and [Claude Code best practices](https://code.claude.com/docs/en/best-practices) (effort into the plan; don't let the model edit tests to pass); policy as code (one policy, many enforcement points); GitHub rulesets' evaluate mode; property-based testing; "make illegal states unrepresentable"; Ousterhout, *A Philosophy of Software Design* (deep modules).

### Principles

| # | Principle | Status |
|---|-----------|--------|
| P5 | **Fewer, stronger checks, derived from the design,** each written once and judged on its false-alarm record | draft |
| P6 | **Learn from quality producers** (OpenAI, Google, Anthropic) and adopt where it fits a learning project | draft (governor's point) |
| P7 | **Tilt toward correct by design.** Moving away from adding routine tests is half the change; the other half is design practices that prevent the defects in the first place | draft (governor's point) |

### A. Adding a check, hook or test

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 25 | **Checks come from the design.** Each blocking check maps to an invariant in the one-level design (item 3) or a rule you set; anything else is a warning by default | draft | the gate registry |
| 26 | **Relevance check.** Every proposed check, hook or test suite is judged on its economic return for a learning project with about 5 users: "two nines", not "six nines". Not relevant means backlog for triage, not built. Exception: irreversible harm (secrets, lost work, production data, changes to `main`) is always guarded | draft (governor's point) | item 6 |
| 27 | **Consistency check.** Every proposal names the rule it enforces and the existing checks, hooks and tests it overlaps or conflicts with; overlaps are merged or the old one retired before the new one lands. Applies to checks, hooks, contract and acceptance tests, not to every unit test | draft (governor's point, scoped) | — |
| 28 | **Each check carries its reason, severity (block or warn) and track record** (fires, overrides, false alarms) | draft | `gates.yaml` |
| 29 | **New checks start as warnings** and become blocking after a clean run | draft | — |

### B. Running and keeping checks

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 30 | **One implementation per rule,** called from every enforcement point (editor hook, `factory` command, CI). Hooks become thin callers | draft | CI twins of hooks |
| 31 | **Structure over words.** Checks read structured records and typed messages (item 19), not prose; word lists only warn | draft | record schemas |
| 32 | **False-alarm limit.** A check overridden three times in a wave is fixed or demoted, not overridden a fourth time | draft | the three-turn rule (item 7) |
| 33 | **A small blocking set,** about seven: changes reach `main` only by PR; a reviewer accepted; tests green; changes stay within the order's files; records match their schemas; no secrets; choices brought to you are plain. Everything else warns | draft | — |
| 34 | **No checks of checks.** The track record (item 28) is the only oversight; checks that only police other checks are retired | draft | — |
| 35 | **Editor hooks only for irreversible harm** (committing or pushing to `main`); nudges move into CI or the control loop, where a false alarm does not interrupt you | draft | `.cursor/hooks.json` |
| 36 | **A broken check never blocks its own fix:** a recorded governor bypass plus item 29 prevent deadlocks | draft | override records |
| 37 | **Close the important holes first, by return on investment:** a reviewer's accept is required to merge now; claim and handoff honour amendments and overrides through item 30; the rest to backlog | draft | — |
| 38 | **Audit all 25 checks:** keep, demote to warning, or retire, by items 25 to 28. Aim for fewer | draft | — |
| 39 | **Continuous cleanup slot** for drift: duplicated code, stale branches, retired checks and tests | draft | — |
| 40 | **Build or buy for checks** goes into the off-the-shelf survey; lean: our own Python for factory rules, bought tools for code-level analysis | draft | item 2 |

### C. Correct by design

Items 2 (architecture phase, spikes, second-model review) and 3 (one-level design) already carry most of this; these add to them.

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 41 | **Requirements by example, with a held-back set.** The spec gives concrete examples for each requirement. The builder sees all requirements and most examples; a fresh evaluator runs a held-back share of acceptance scenarios. Every held-back scenario traces to a written requirement: hide test cases, never requirements | draft (governor's idea, refined) | acceptance catalog |
| 42 | **Make wrong states impossible.** Typed records and messages, strict type checking, explicit state machines (for example the control loop's), so whole classes of defects cannot be written | draft | Pydantic schemas |
| 43 | **Properties over examples.** Where a block has invariants, state them as property-based tests: one property replaces many example tests | draft | — |
| 44 | **Architecture rules enforced by structure,** such as which layers may import which, rather than by review | draft | — |
| 45 | **Exemplars.** One reference implementation per kind of block that agents copy | draft | — |
| 46 | **Simplicity bias in design review:** the fewest blocks and interfaces that deliver the value | draft | item 2 |
| 47 | **Trace rework to its cause.** Each rejection is classed as a design gap, a build slip or a check false alarm; the retro turns design gaps into design rules | draft | items 8, 10 |

## Parked for theme 3 (the factory's checks)

- The reply-end question check (`decision-in-chat`) treats any question mark as a decision asked in chat. In this retro it fired three times: twice fairly, once on a question the agreed format already covered. Its message, addressed to the agent, appears in the governor's chat as if he sent it. Example of a word-heuristic check producing false alarms.
