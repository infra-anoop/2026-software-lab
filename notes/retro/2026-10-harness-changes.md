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

**Status: agreed (governor, 2026-10-17 10:57 PT).**

Evidence: Wave 1 retro items D1, D5 to D8, D11, D17 to D19 in `notes/retro/2026-10-wave1-items.md`; 25 checks; 5 overrides in Wave 1, 3 of them on one check.

Sources consulted: OpenAI, [Harness engineering](https://openai.com/index/harness-engineering/) (few mechanically enforced invariants, fix-instructions in error messages, minimal blocking gates, continuous cleanup); Google Tricorder (analyzers kept under about 10% false positives or switched off); Anthropic, [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) (one default-fail contract judged by a fresh evaluator) and [Claude Code best practices](https://code.claude.com/docs/en/best-practices) (effort into the plan; don't let the model edit tests to pass); policy as code (one policy, many enforcement points); GitHub rulesets' evaluate mode; property-based testing; "make illegal states unrepresentable"; Ousterhout, *A Philosophy of Software Design* (deep modules).

### Principles

| # | Principle | Status |
|---|-----------|--------|
| P5 | **Fewer, stronger checks, derived from the design,** each written once and judged on its false-alarm record | agreed |
| P6 | **Learn from quality producers** (OpenAI, Google, Anthropic) and adopt where it fits a learning project | agreed (governor's point) |
| P7 | **Tilt toward correct by design.** Moving away from adding routine tests is half the change; the other half is design practices that prevent the defects in the first place | agreed (governor's point) |

### A. Adding a check, hook or test

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 25 | **Checks come from the design.** Each blocking check maps to an invariant in the one-level design (item 3) or a rule you set; anything else is a warning by default | agreed | the gate registry |
| 26 | **Relevance check.** Every proposed check, hook or test suite is judged on its economic return for a learning project with about 5 users: "two nines", not "six nines". Not relevant means backlog for triage, not built. Exception: irreversible harm (secrets, lost work, production data, changes to `main`) is always guarded | agreed (governor's point) | item 6 |
| 27 | **Consistency check.** Every proposal names the rule it enforces and the existing checks, hooks and tests it overlaps or conflicts with; overlaps are merged or the old one retired before the new one lands. Applies to checks, hooks, contract and acceptance tests, not to every unit test | agreed (governor's point, scoped) | — |
| 28 | **Each check carries its reason, severity (block or warn) and track record** (fires, overrides, false alarms) | agreed | `gates.yaml` |
| 29 | **New checks start as warnings** and become blocking after a clean run | agreed | — |

### B. Running and keeping checks

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 30 | **One implementation per rule,** called from every enforcement point (editor hook, `factory` command, CI). Hooks become thin callers | agreed | CI twins of hooks |
| 31 | **Structure over words.** Checks read structured records and typed messages (item 19), not prose; word lists only warn | agreed | record schemas |
| 32 | **False-alarm limit.** A check overridden three times in a wave is fixed or demoted, not overridden a fourth time | agreed | the three-turn rule (item 7) |
| 33 | **A small blocking set,** about seven: changes reach `main` only by PR; a reviewer accepted; tests green; changes stay within the order's files; records match their schemas; no secrets; choices brought to you are plain. Everything else warns | agreed | — |
| 34 | **No checks of checks.** The track record (item 28) is the only oversight; checks that only police other checks are retired | agreed | — |
| 35 | **Editor hooks only for irreversible harm** (committing or pushing to `main`); nudges move into CI or the control loop, where a false alarm does not interrupt you | agreed | `.cursor/hooks.json` |
| 36 | **A broken check never blocks its own fix:** a recorded governor bypass plus item 29 prevent deadlocks | agreed | override records |
| 37 | **Close the important holes first, by return on investment:** a reviewer's accept is required to merge now; claim and handoff honour amendments and overrides through item 30; the rest to backlog | agreed | — |
| 38 | **Audit all 25 checks:** keep, demote to warning, or retire, by items 25 to 28. Aim for fewer | agreed | — |
| 39 | **Continuous cleanup slot** for drift: duplicated code, stale branches, retired checks and tests | agreed | — |
| 40 | **Build or buy for checks** goes into the off-the-shelf survey; lean: our own Python for factory rules, bought tools for code-level analysis | agreed | item 2 |

### C. Correct by design

Items 2 (architecture phase, spikes, second-model review) and 3 (one-level design) already carry most of this; these add to them.

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 41 | **Requirements by example, with a held-back set.** The spec gives concrete examples for each requirement. The builder sees all requirements and most examples; a fresh evaluator runs a held-back share of acceptance scenarios. Every held-back scenario traces to a written requirement: hide test cases, never requirements | agreed (governor's idea, refined) | acceptance catalog |
| 42 | **Make wrong states impossible.** Typed records and messages, strict type checking, explicit state machines (for example the control loop's), so whole classes of defects cannot be written | agreed | Pydantic schemas |
| 43 | **Properties over examples.** Where a block has invariants, state them as property-based tests: one property replaces many example tests | agreed | — |
| 44 | **Architecture rules enforced by structure,** such as which layers may import which, rather than by review | agreed | — |
| 45 | **Exemplars.** One reference implementation per kind of block that agents copy | agreed | — |
| 46 | **Simplicity bias in design review:** the fewest blocks and interfaces that deliver the value | agreed | item 2 |
| 47 | **Trace rework to its cause.** Each rejection is classed as a design gap, a build slip or a check false alarm; the retro turns design gaps into design rules | agreed | items 8, 10 |

## Theme 4: How we work together

**Status: agreed (governor, 2026-10-17 11:35 PT), after two rounds of discussion.**

Evidence: rules spread over the constitution, `AGENTS.md`, `.cursorrules`, three Cursor rules, a dozen skills, `docs/agent-os/`, the architect backlog, the user's guide and the orchestrator's private notes; the constitution still describes packets, not orders (retro item B6); nine decisions waiting at Wave 1 close, one open since 10-07; the governor learned state by asking; a retro report without a stance; theme 2 recorded as agreed without explicit alignment; a long reply lost from the governor's chat when tool calls followed it; one session wearing coach, architect and sprint-manager hats. Not a defect (governor): Wave 1 growing from 94 to 110 tasks; scope change is a live event, and the response to it is what gets codified (theme 1, items 5, 8, 9).

Sources consulted: OpenAI, [Harness engineering](https://openai.com/index/harness-engineering/) (a short `AGENTS.md` as a map into a structured docs folder; knowledge the agent cannot see does not exist; a doc-gardening pass); Anthropic, [Claude Code best practices](https://code.claude.com/docs/en/best-practices) (short, pruned instruction file; hooks for must-happen rules), [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) (start simple; add agents only when they measurably help) and [multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) (orchestrator and short-lived workers on separable tasks); Cognition, "Don't Build Multi-Agents" (context loss between peer agents); architecture decision records; team working agreements revisited at retros.

### Principles

| # | Principle | Status |
|---|-----------|--------|
| P8 | **The working agreement is designed, written in one place, and revisited at each retro,** not accreted where convenient | agreed |
| P9 | **What is not in git does not exist.** A new session, a new agent or you can pick up from git alone. In git does not mean in an always-loaded rule file | agreed |
| P10 | **Roles are defined as a cast, not one at a time.** Split work by role (a factory manager and a coder); do not split the same work across parallel agents (one agent writing tests and another writing code for the same block) | agreed (governor's point) |
| P11 | **Codify how we respond to change, not the change.** Scope growth, failures and false alarms are live events; the response (re-estimate, restart rule, false-alarm limit) is what gets written down | agreed (governor's point) |
| P12 | **Every rulebook has a budget; what goes out matters as much as what comes in.** The pull to put top-of-mind rules into the constitution or `AGENTS.md` is resisted | agreed (governor's point) |
| P13 | **Prefer settled practice.** Where leading practitioners have iterated and settled on an approach, understand their reasoning and adopt it; our own experiments fill the gaps | agreed (governor's point) |

### A. The cast

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 48 | **One page lists the cast:** you, the coach and chief architect, the sprint manager, the control loop, workers and reviewers. Each with purpose, inputs, outputs, decision rights and escalation path. Checked against how leading teams organise human and agent roles (P13) | agreed | — |
| 49 | **Few standing agents, many short-lived ones.** Standing: the coach and the sprint manager. Short-lived: one worker or reviewer per order, fresh context, self-contained task. The same work is not split across parallel agents. Exception: acceptance scenarios come from the spec, independent of the builder (item 41) | agreed | item 19 |
| 50 | **The coach and chief architect is defined by boundaries and outputs, not tasks:** a free agenda (the problem of the day), clear decision rights (what it settles alone, what goes to you), and a disciplined record (decisions and state in git). Its own designs still get a second-model review | agreed (governor's point, refined) | item 2 |
| 51 | **Two conversations, three-way visibility.** You talk to the coach and to the sprint manager. Git is the shared surface: every conclusion reached in either chat is recorded there; each standing agent reads the other's records; when they disagree, the disagreement comes to you as one decision request carrying both views | agreed (decision `wave1-retro-front-door`, B) | — |
| 52 | **The sprint manager shrinks as the control loop grows:** a session in Wave 1.5; in steady state it handles exceptions only (item 17) | agreed | items 13, 17 |
| 53 | **The cast is reviewed at each retro;** Wave 1.5's split is an experiment (decisions `wave1-retro-bootstrap-role`, `wave1-retro-front-door`) | agreed | item 18 |

### B. Rulebooks

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 54 | **A size budget for always-loaded rule files:** `AGENTS.md` about 100 lines, the constitution capped. One in, one out: adding a rule means merging or removing one | agreed | — |
| 55 | **Rules live where they are needed.** Role pages and skills load only when relevant; always-loaded files hold only what every agent needs every time | agreed | skills |
| 56 | **A rule proposal passes the same tests as a new check** (items 26, 27): the failure it prevents, why it cannot be a mechanic or a role-page line, and what it replaces | agreed | items 26, 27 |
| 57 | **Must-happen rules become mechanics; guidance stays prose.** Rules the agents already follow without being told are deleted; removed rules are logged with the reason | agreed | item 35 |
| 58 | **The restructure only moves, merges and deletes;** it adds no new rules | agreed | — |
| 59 | **Nothing important lives only in private notes or chat.** The orchestrator's hard rules and state log move into git, on role pages and state notes, not into always-loaded files | agreed | orchestrator store |
| 60 | **Stale documents are fixed in the cleanup slot** (item 39), starting with the constitution's packet wording | agreed | retro item B6 |

### C. The interaction contract

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 61 | **Discussion in chat; decisions in git.** Choices that change scope, budget, architecture or rules go to a decision request. Confirmations inside an agreed process (like these theme lists) are given in chat and recorded in git | agreed | retro item B7 |
| 62 | **Nothing is recorded as agreed without your explicit yes** | agreed | — |
| 63 | **Every report takes a stance:** position, options, recommendation | agreed | — |
| 64 | **Status comes to you; you don't have to ask.** A short written update at milestones and on red, from the sprint manager and the run log (item 23) | agreed | items 8, 23 |
| 65 | **Decisions are batched and visible.** One list of open decisions with their age; anything open more than a week is raised again or closed; "later" decisions name their trigger | agreed | `factory board` |
| 66 | **One short escalation list:** missing decision, rule conflict, three turns, a substitute for something you locked, cost drift past the threshold | agreed | items 7, 9 |
| 67 | **The main content of a reply comes last,** after any tool calls, so it stays visible in your chat | agreed | — |

## Theme 5: Direction

**Status: agreed (governor, 2026-10-17 12:25 PT), after two rounds of discussion.**

Evidence: Wave 1 ran the factory only on itself; the workload (Smart Writer V2) was not touched; several stalls came from the factory checking its own unfinished parts; Wave 1 started from a buy decision (GitHub Spec Kit) and became build-heavy (job queue, 25 checks, editor guards, claims, status board, a large process layer); the planned Wave 2 (23 tasks) predates this register.

Sources consulted: OpenAI, [Harness engineering](https://openai.com/index/harness-engineering/) (the harness grew while shipping a real product); Anthropic, [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents); Team Topologies (platform as a product, thinnest viable platform); build what differentiates, buy the commodity (Wardley mapping); Shape Up (appetite, cool-down); SAFe capacity allocation; Martin Fowler, strangler fig migration; compiler bootstrapping; DORA delivery measures.

### Principles

| # | Principle | Status |
|---|-----------|--------|
| P14 | **The factory is the product, at least for a while.** Its first customer is real work: Smart Writer V2, then the governor's bigger projects | agreed (governor's point) |
| P15 | **Buy over build, for code and practices alike.** Ours is the culture layer on top; no reinventing | agreed (governor's point) |
| P16 | **A good-enough factory,** at proof-of-concept level; everything else to the backlog | agreed (governor's point) |
| P17 | **No piece of Wave 1 is kept by default.** Keeping needs a reason (guard against not-invented-here) | agreed (governor's point) |

### Changes

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 68 | **Three backlogs:** product, infrastructure, tooling | agreed (governor's point) | retro item A1 |
| 69 | **Each sprint names its primary type;** work of another type is small and named explicitly | agreed (decision `wave1-retro-sprint-type`, B) | retro item A2 |
| 70 | **Smart Writer V2 is built on the factory Wave 1.5 produces.** It is a conceptual test, not test cases; findings go to the tooling backlog | agreed (decision `wave1-retro-first-product-work`) | — |
| 71 | **The funnel after the retro:** dedupe; assign value and importance; set the appetite; scan off-the-shelf and open source; build only glue and missing pieces; draw the good-enough line; everything else to the backlog | agreed (governor's point) | items 1, 2, 5 |
| 72 | **The fork is decided consciously:** restart on a bought product, hybrid, or keep building. A time-boxed survey compares them against criteria agreed beforehand; the governor decides | agreed (governor's point) | item 2 |
| 73 | **Burden of proof on keeping.** A Wave 1 piece stays only if it captures our culture with no product equivalent, or leads current practice in a way that matters, and is cheap to maintain; otherwise it is replaced piece by piece without breaking the working factory | agreed | — |
| 74 | **A fresh agent from a different model family runs the survey,** because the orchestrator built Wave 1 and is biased toward keeping it | agreed | — |
| 75 | **Survey framed as differentiate versus commodity.** Keep ours: intent, decisions, independent review policy, checks from design, the cast. Buy: the control loop's runtime, agent hosting, the job queue, durable state, notifications, code analysis | agreed | items 2, 15, 40 |
| 76 | **A known-good factory runs the sprint;** the sprint never depends on the change it is building, whichever path the fork takes | agreed | item 36 |
| 77 | **Ambition stays a learning project for about 5 users;** productizing questions wait until the factory has built real work | agreed | item 6 |
| 78 | **Wave 1.5 is small:** the no-build habits are adopted at once; then the survey and the fork decision, and the Wave 1 failure inventory; then only glue and missing pieces | agreed | items 11, 71, 72 |
| 79 | **The planned Wave 2 is re-examined against this register** before any of it starts | agreed | — |
| 80 | **Cost is an operating control, not a selection criterion.** Model prices change too often to choose an architecture by; portability (at least two first-class runtimes, each with at least two model families) is the hedge. Every run records tokens and cost, has a cap, and uses a model chosen per step. Feeds the cost and measures discussion and the open token-usage decision | agreed (governor's point, 2026-10-17 13:43 PT) | items 23, 72 |

## Measures and guardrails (retro stage 4, discussion 2)

**Status: agreed (governor, 2026-10-17: items 82 to 85 and the measurement-cost rule at 14:24 PT; principle P18 and the scorecard at 14:36 PT).**

Evidence: Wave 1's cost was discovered from the plan tier, not from the factory; the token-usage request sat in git from Oct 7 without reaching the governor; the burn chart and run log were agreed but never built. The governor's usage export (Sep 8 to Oct 17) shows Wave 1 (Oct 3 to 7) used about 808M tokens, over three times all of September's pre-factory work, plus about $255 on-demand beyond the plan's included usage; 83% of Wave 1 tokens went to the builder model and 16% to the reviewer model. Review records show the three biggest orders needed 6 to 9 reviews each across their gates.

Sources consulted: DORA (lead time, change failure rate, rework rate); SPACE (no single activity measure; Goodhart's law); FinOps unit economics (cost per unit of value, tagged spend); OpenTelemetry semantic conventions for generative AI (standard token and cost fields); Anthropic, multi-agent research system (token use explains most quality variance); AI-SDLC's earned-autonomy bar (about 95% unattended completion).

| # | Principle | Status |
|---|-----------|--------|
| P18 | **Measurement follows the work; the work is never reshaped for measurement.** Batching tasks into one order for one agent stays the natural unit | agreed (governor's point) |

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 81 | **A scorecard read from machine data,** for seeing, not targets, reviewed each retro. **Measurement costs at most 1% of factory spend, is computed by code and never by a model, and the 1% is checked each retro.** Four units: **wave, feature, order** (a batch of tasks delegated to one agent) **and task.** Every number is measured at all four units; none is pre-judged useless at a level. Numbers: (1) **acceptance by pass**, the share accepted on pass 1, 2 or 3 or sent to the governor under the three-turn rule, split by gate (spec, plan, test, code review, governor acceptance), with the cause of each rework; (2) **lead time**; (3) **unattended rate**, finished with no stall and no interruption except decisions; (4) **cost by role** (builder, reviewer, orchestrator); (5) **estimate against actual**. Beside them, the burn chart. Each figure is labelled measured or estimated (for example, task cost is split from its order by time window). For task-level acceptance, reviewers note which task each finding concerns. Where it shows: inside the status the factory sends the governor, and as a full table at each retro | agreed (governor's points on units and coverage) | items 7, 8, 10, 47, 80 |
| 82 | **Telemetry by standard, bought.** Each agent run records model, tokens, cost, work item and role in the OpenTelemetry format, sent to a bought store (Logfire is already in the lab). No homemade token counters. Where a runtime exposes no per-run usage (Cursor on individual plans), the provider's usage export is joined by time and model | agreed | items 23, 80 |
| 83 | **Model routing by evidence.** Top-tier models by default; a step moves to a cheaper model only when the scorecard shows its first-pass acceptance holds. Each step's model is written in the workflow file | agreed | item 80 |
| 84 | **Runaway caps, not rationing.** Each run is capped at a generous multiple of its estimate; hitting a cap stops and reports under the restart rule | agreed | items 20, 80 |
| 85 | **Wave 1 baseline, once,** from git, the agent records and the governor's usage export (received 2026-10-17, kept out of git). First reference class for calibration | agreed | items 10, 11 |

## The lighter lane (retro stage 4, discussion 3)

**Status: agreed (governor, 2026-10-17 14:42 PT).**

Evidence: Wave 1 had one lane. Every change, whatever its risk, went through an order, a claim, a handoff, gates and an independent review; 8 of the 18 orders with review records were notes, records or guides. The fixed cost per change was high, which pushes toward unnatural batching or working around the process.

Sources consulted: ITIL change types (standard, normal, emergency); DoorDash Agentic Orchestrator profiles (Medium, Large, Moonshot, chosen at creation); AI-SDLC's routing by complexity; GitHub code owners and rulesets (review rules by path); Google's size-tuned code review.

| # | Change | Status | Builds on |
|---|--------|--------|-----------|
| 86 | **Three lanes, chosen when work comes in.** **Light:** notes, records, docs, and config with no runtime effect; no spec or plan; one agent; a review by another model family; merges on green checks and an accepted review. **Normal:** an order of tasks under an existing plan, with the usual reviews. **Full:** new features or anything that changes the architecture; the whole spec-to-review flow and the architecture phase (item 2) | agreed (governor: three lanes) | items 2, 6 |
| 87 | **The lane is decided by a written rule,** from which files change, the size, and whether anything irreversible is touched. Recorded on the work item. A change that grows moves up a lane under the mission test (item 5); moving down needs the governor's yes | agreed | item 5 |
| 88 | **Irreversible-harm guards apply in every lane** (item 26): pushes to main, secrets, deletions, settings. The light lane removes ceremony, not protection | agreed | items 26, 35 |
| 89 | **One workflow with a lane switch,** not three workflows. Scorecard numbers are split by lane too, to show whether the lanes sort work correctly | agreed | item 81 |
| 90 | **Every review is done by another model family,** in every lane. If a review happens, it is cross-family | agreed (governor's point) | item 74 |

### Future backlog (not this wave)

- An "extra light" lane with no review, created only if the scorecard data shows reviews add nothing for some kinds of change. Governor: not now.

## Parked for theme 3 (the factory's checks)

- The reply-end question check (`decision-in-chat`) treats any question mark as a decision asked in chat. In this retro it fired three times: twice fairly, once on a question the agreed format already covered. Its message, addressed to the agent, appears in the governor's chat as if he sent it. Example of a word-heuristic check producing false alarms. Covered by items 31 and 35.
