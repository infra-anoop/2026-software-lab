# Wave 1.5 implementation approach

**Status: proposed (architect, 2026-10-19).** Sized by the sprint manager (section 4), and re-sized for the test-first shape (section 2.6); cross-family review done and triaged (section 9), with the work it added waiting for the sprint manager's re-size; then the governor's approval through a decision request. Until it is approved, the retro records stand unchanged.

This note says **how** Wave 1.5 is built. **What** is built does not change: the product shape stays the end-state description in `notes/retro/2026-10-factory-whole.md`, and the value statement and exit criteria stay those of `notes/retro/2026-10-wave1.5-funnel.md` section 9. Once approved, this note replaces the funnel's work-item list and phases (sections 8 and 9's phase table) as the plan of record for how to build. Every place where it varies from the product shape is listed in section 5 for the governor's approval; nothing varies silently.

## 1. Why this note exists

On 2026-10-19 the governor raised two concerns with the agreed Wave 1.5 plan (89 likely, 182 pessimistic agent-hours): the effort is high, and, more important, the work might not match what he expects, repeating Wave 1, where most of what was built had to be thrown away. In his words: "I don't want to build like I built Wave 1 - only to find myself in a position to throw away most of it."

The architect's diagnosis, which the governor accepted:
- **The plan built what can be bought.** Most of the hours went into our own machinery around the engine: saving a run's state between GitHub Actions jobs, resuming it, a restart controller, six message formats of our own and a review controller. The governor's expectation was "install, configure, add our policy layer, test that it is stitched together", with very little building.
- **The design grew on paper.** Each coherence review of the end-state description added a mechanism. Every addition was sound; together they describe a mature factory for a learning project of about five users. That is the Wave 1 pattern again, in a document instead of code.
- **The judgement came late.** The governor would first use the new factory after the Core phase, about half the budget in.

Governor's direction (chat, 2026-10-19, 19:35 to 20:32 PT): start from today's `main` (not rolled back), remove Wave 1's machinery, then build in layers (install, configure, policy, glue) with fewer intermediate tests; use Spec Kit workflows (a YAML file per job, run by Spec Kit's common Python runner, calling the Cursor or Copilot command-line agent); use the Superpowers packet set as shipped instead of designing our own formats; "for the most part, we are not planning to deviate from the overall product shape". He agreed to this note's form: a new note that replaces named parts of the retro records, one section per layer.

## 2. Six decisions that shape the build

### 2.1 Clean slate on today's `main`

Wave 1 was almost entirely additive: against the last commit before it (2026-09-21), it added about 56,000 lines in 538 files and deleted 36 lines. So its machinery can be removed in one change on today's `main`, without rewriting history or losing the non-factory work done since (CI fixes, database bootstrap tests, the Smart Writer V2 spec, the retro records). Git keeps the history. Layer 0 does this first, so Wave 1's rules stop applying at once (the governor: "I definitely don't want to run with wave 1 rules").

### 2.2 Build in layers, each judged by use

Install, then configure, then one end-to-end run with the parts as they come, then the policy layer, then only the glue the runs show is missing. Two refinements agreed with the governor:
- **One end-to-end run with defaults before designing the policy layer,** so the policy fits what the bought parts actually do instead of being designed on paper.
- **The policy layer is configuration and prose first** (Spec Kit templates, Superpowers prompts, workflow files, GitHub rulesets, code owners, role briefs). Code only where a rule that must hold cannot be expressed any other way.

Before each layer, the sprint manager writes a one-page walkthrough of what the governor will see and do on an ordinary day; the governor approves the experience, not a design. After each layer, the governor uses it on real work and decides: keep going, change course, or stop. Each layer has its own appetite (section 4); an overrun stops for a rethink instead of extending.

### 2.3 Fewer intermediate tests

- **Install and configure** are proved by running them, not by writing tests first.
- **Code we write** (glue, or a policy rule that has to be code) gets tests, written with it.
- **The whole** is proved by a few end-to-end runs of real issues, named in each layer's "done when".

### 2.4 Short workflows, cut where they would wait

Spec Kit workflows run inside a single GitHub Actions job. A paused Spec Kit run keeps its progress in a folder on the machine it ran on, and GitHub's machines are discarded when a job ends; making long paused runs survive that was the most expensive part of the old plan.

So no workflow waits for the governor or for anything slow. Each place a run would wait becomes the boundary between two short workflows. Each workflow runs start to finish in one Actions job; Actions starts the next one when the event happens (a label, a pull request opening, a decision answered). Inside a workflow, code runs the steps and loops and calls the agents, as the governor wants. Between workflows, the state lives in GitHub: the issue, the pull request, labels and committed files. A crashed job is re-run; every step is written so repeating it does no harm.

Safe to repeat, by design, with bought parts and a few conventions rather than a reconciler:
- **One run per work item at a time.** Each workflow sets a GitHub Actions concurrency group keyed on the issue, so a second trigger for the same issue waits instead of running alongside.
- **The stage is a label.** The issue's stage label is the single record of where the work stands. Only the step that finishes a stage moves it, as its last action; a workflow started for a stage the label no longer shows exits without acting.
- **Read before write.** Every step that writes to GitHub first looks for its own earlier result and reuses it: the branch named from the issue number, the pull request found by that branch, comments carrying a hidden marker, labels set rather than toggled, statuses posted by name.
- **A dead job just ends.** Actions' job time limit ends it; the re-run finds whatever it had already written and carries on. No leases or attempt records.

The two cases this must survive (a duplicate trigger, and a job killed just after a write to GitHub) are trials in Layer 3, before anything builds on the path.

### 2.5 Superpowers' packet set, as shipped, with a thin lab profile

Superpowers (version 7.0.0, MIT licence) ships no software kit for its formats, and needs none here. Its packet set is three prompt templates (implementer, task reviewer giving two verdicts with Critical, Important and Minor findings, re-review), three small shell scripts (pull one task's brief out of a plan; build the review package from the start and end commits; set up the working folder and progress log), and its conventions (a status reply under 15 lines with DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT or BLOCKED; a full report file; the reviewer distrusts the report and reads the change once). The scripts become shell steps and the prompts become agent steps in our workflows.

Its own loop (fix rounds, escalation, model choice run as a skill the agent follows) is not used between steps: code owns that, under the governor's principle that code runs the loop and agents do the work inside one step. Inside one agent step, Superpowers' discipline (tests first, self-review, the short status reply) applies as shipped.

Superpowers' formats are prompt templates in Markdown, not a machine schema, so the one small build is a **lab profile** over them. The upstream prompts and scripts stay unmodified at a pinned version. The profile is a short file appended to the prompts that fixes the exact parseable form of two things: the implementer's status reply and the reviewer's verdict block, with the content Superpowers defines (the four status words; the spec-compliance and quality verdicts; Critical, Important and Minor findings). Additions only where our rules need a slot Superpowers lacks, each tied to its rule: the reviewer's model family (every review by another family), a "needs the governor" mark on a finding, the tests-against-spec verdict and each finding's cause (section 2.6). A thin reader parses that form so code can decide the next step; malformed output gets one repair request, then fails the step. The profile and reader are ours to maintain, and sized as ours. Our decision request and lock format stays; Superpowers has no equivalent.

### 2.6 Tests first, shaped for fast convergence

The goal is code that is right on the first or second try. Secrecy is not a goal (governor, 2026-10-19: "Secrecy was never the goal. Faster convergence is the goal."), so there are no held-back test cases. Agreed with the governor on 2026-10-19:

1. **Examples in the spec.** For each requirement the spec writer gives k concrete examples in "given, when, then" form. k is a tunable setting: 3 by default (the main case, the boundary that matters most, the refusal or error case), at least 1, about 5 at most, and 1 for a light change; the spec writer chooses within that range, and the recorded causes tune the default. An invariant is stated once as a rule, not as more examples. The examples come from a different author than the builder, before any code, and the governor approves them with the spec: they are the independent tests. Each example says how it is proved: by a test (the usual case), or, where it cannot be automated, by the governor observing it, approved with the spec. For a change in the normal or light lane, the examples are in the issue, written through the change form.
2. **The builder writes the rest of the tests** from the spec and its examples. Every example becomes a test carrying the example's id. Its own tests check public behaviour, not internals; few and strong, relevant at two nines.
3. **Test review.** Normal and light lanes: inside the one code review, the reviewer first judges the tests against the spec (every example covered, the tests match the requirements) as its own verdict; if that verdict fails, the round fails before the code is judged. Full lane: after tasks, a builder writes and commits only the interface stubs and the failing tests for the feature; a separate test review judges that commit, and only an accepted verdict starts the implementation orders, because a wrong test there would spread across many orders.
4. **Types and interfaces before code.** In the full lane the plan names the data models and signatures; otherwise the builder writes them as stubs with the tests.
5. **The builder writes the code,** running the tests and a strict type checker inside its own step and trying again freely within the step's time limit. No GitHub Actions round trip per try.
6. **Small orders:** one behaviour, a handful of files, about an hour of agent work.
7. **A way out for a wrong test, and no quiet weakening.** The builder may not change or delete a test made from a spec example; it may flag it as wrong with its reason (Superpowers' `DONE_WITH_CONCERNS`) and stop, and since the governor approved the example, the flag goes to him through the decision pause. Code checks that every example proved by a test still has its test, and that none of those tests is skipped or marked as expected to fail. Changes to the builder's own tests after they were reviewed are listed with their reasons in its report, and the reviewer sees the diff.
8. **Three review rounds,** then the governor. The inner loop (run tests, fix, run again inside the step) is capped by time, not by a count.

Two architect additions, for the governor's approval with this note: **one exemplar per kind of block**, a reference implementation builders copy the shape of; and **the cause of each finding** recorded in the verdict (misread requirement, build slip, wrong test), so k and the other settings are tuned from evidence.

## 3. The stack

| Job | Part | Bought or ours |
|-----|------|----------------|
| Conversations with the governor: architect, sprint manager, intent and spec drafting | Cursor chat sessions | Bought |
| Design method: spec, plan, tasks, consistency check, templates | Spec Kit | Bought |
| Engine inside a run: steps, loops, agent calls, model per step | Spec Kit workflows, upgraded from the installed 1.0.6 to the current release | Bought |
| Trigger between runs, host, schedules | GitHub Actions | Bought |
| Work queue and state between runs | GitHub Issues, labels, pull requests | Bought |
| Builder agent | Cursor command-line agent, model pinned per step | Bought |
| Second runtime | Copilot command-line agent, proven once and kept ready | Bought |
| Packet formats and role prompts | Superpowers packet set, pinned version | Bought (open source) |
| Merge rules | GitHub rulesets and code owners | Bought |
| Robot identity for code that opens pull requests | GitHub App (created by the governor) | Bought |
| Run records | Logfire | Bought |
| Policy layer: rules, briefs, workflow files, decision format, thin reader, small scripts | This repository | Ours |

GitHub Agentic Workflows and Copilot's coding agent are not needed in this design. Copilot's coding agent runs its own agent loop, which is the pattern the governor wants code to replace.

## 4. The layers

Sizes are the sprint manager's (agent-hours, likely / pessimistic, uncalibrated), task by task in `notes/wave1.5/2026-10-layer-sizing.md`, with its recommendations. Across the layers: about 90 likely, plus about 5.5 for walkthroughs and sprint management, so about 95.5 for the wave; governor about 8 to 16 hours. The test-first shape added about 5 of those hours (Layers 1 and 4 gain its checks, Layer 7 loses the held-back store); its saving is in running orders, expected but not yet measured or booked. The locked appetite (89 likely, 182 pessimistic agent-hours) stays the ceiling; it is not a target.

Three numbers, shown together because they tell different things:
- **Likely: about 95.5,** about 6.5 over the appetite's 89; the levers in the sizing note recover about 4.
- **Realistic bad case: about 155,** the likely figure times about 1.6, since not every task goes badly at once. Under the 182 ceiling.
- **Every task going badly: about 217,** the sum of each task's pessimistic figure. About 35 over the 182 ceiling.

These do not yet include the work the cross-family review added (section 9): the safe-repeat conventions and trials, the full lane's tests-and-stubs step, the test-integrity checks and the restored product-shape items. The sprint manager re-sizes those before the decision request. After Layer 3 the sprint manager compares actual with estimate and re-estimates the remaining layers with that correction.

| Layer | What the governor gets | Size (sprint manager) |
|-------|------------------------|-----------------------|
| 0. Clean slate | Wave 1's machinery and rules gone; a one-page interim rulebook | 6.75 / 15 |
| 1. Install | The bought parts present and pinned | 6.5 / 15.75 |
| 2. Configure | The parts wired together; the four unknowns that could change the stack answered | 6.2 / 15.75 |
| 3. First end-to-end run | An issue labelled, a reviewed pull request back, using the parts as they come | 7.75 / 17.75 |
| 4. Policy for changes | Our rules on every change: reviews, decisions, guards, the light and normal lanes | 22 / 48.25 |
| 5. Running unattended | Nothing to watch: time limits, re-runs, an alert on silence, status comments, the deliberate trials | 8 / 19.25 |
| 6. Cost and quality numbers | A record per run and the scorecard | 6.8 / 15.75 |
| 7. The design path for features | The full lane, proved on one real Smart Writer V2 feature | 18.95 / 42.75 |
| 8. Finish | Rulebooks and guide describing what runs; the end-state description matching reality | 7.05 / 16.25 |

**How work gets done before the new path can carry it (Layers 0 to 2).** The plain known-good way: a chat session starts a worker on a branch, the worker opens a pull request, a reviewer from another model family is started from the same session with a pointer to a note in git, and the change merges on green checks and an accepted review. That is safer than Wave 1's machinery and needs none of it. From Layer 3, the new path takes every piece of work it can handle.

### Layer 0. Clean slate

**Purpose.** Stop running on Wave 1's machinery and rules, at once.

**Contents.**
- Delete in one change: the `factory` package's queue, lifecycle, status board, metrics and command (`scripts/factory/`), the 29 registered checks except the kept list below, three of the four editor hooks, the factory CI workflows (`factory-gates.yml`, `factory-pr-evidence.yml`), Wave 1's process documents in `docs/agent-os/`, and the deprecated skills.
- Archive, not delete: `bus/orders/` and `notes/packets/` move to an archive folder; the current constitution and `AGENTS.md` move there too.
- Keep: decisions in `bus/decisions/` with a small standalone check of their format; the guard against committing or pushing to `main`, as a small standalone script behind the one remaining editor hook; the lab's own checks (secrets schema, deploy settings, locked dependencies) in their existing CI jobs; the retro records; the Smart Writer V2 specs; the intent-session skill; the Spec Kit skills. Each kept check gets one line stating its reason and severity.
- Write the one-page interim rulebook, in force until Layer 8 replaces it: changes only through a branch and pull request, never to `main`; secrets never in git; the lab's invariants (Nix, uv, the app registry); every review by another model family; decisions in git with the governor's explicit yes; after three review rounds it comes to the governor; the short escalation list; the good-enough judgement for findings. It replaces the constitution file's content (Spec Kit reads that file), and `AGENTS.md` shrinks to a short map.
- Governor: update the `main` ruleset so it no longer requires the deleted factory checks, at the same moment the deleting change merges (before, the old checks block it; after, every pull request blocks), and keep "pull request required". Exact strings and timing come from the sprint manager.

**Done when.** `main` carries none of the removed machinery; CI is green with the kept checks; a test pull request merges under the new ruleset; the interim rulebook is the only always-loaded rule text besides the short map; the governor has approved the rule-path change.

**Proof.** The test pull request and a green CI run. No new tests.

### Layer 1. Install

**Purpose.** Every bought part present, at a pinned version, where it will run.

**Contents.** Spec Kit upgraded from 1.0.6 to the current release with the Cursor and Copilot integrations, checking first whether the upgrade overwrites the lab's template overrides; the Cursor and Copilot command-line agents available in the Nix environment and in Actions; the Superpowers packet set copied in at a pinned version; the GitHub App created by the governor. The build step's environment: it must run an app's tests and a strict type checker in seconds (section 2.6, point 5), so decide here whether agent steps need the full Nix environment or only the agent tools and uv.

**Done when.** Each part runs a trivial command in an Actions job and in the codespace, and its version is pinned in git; an agent step runs an app's tests and type checker inside its own job.

**Proof.** Running it. No tests.

### Layer 2. Configure, and answer the four unknowns

**Purpose.** Wire the parts together and settle early the unknowns that could change the stack.

**Contents.** Actions secrets for the Cursor key and the App key (this closes the open decision on how the App key is delivered); Spec Kit integration settings and a model per step; Actions permissions; the labels and a first issue form. The four unknowns:
1. A Spec Kit workflow step calls the Cursor command-line agent unattended in Actions, with a pinned model.
2. The same with the Copilot command-line agent (the second runtime). This likely needs a paid Copilot plan, which is the governor's call.
3. A pull request opened with the App's token starts its checks without anyone clicking approve.
4. Usage per run is visible, or can be joined from the governor's usage export.

**Done when.** Each unknown has a recorded pass or fail. Any fail stops for the governor, as a plain choice: fix it, move building to the other runtime, or rethink the engine. If Spec Kit's own loop or approval steps misbehave, the cheap fallback is a short script loop inside the same Actions job (about 2 to 4 hours), not a redesign.

**Proof.** The four runs, recorded in git.

### Layer 3. First end-to-end run, with defaults

**Purpose.** The core experience, as early as possible: an issue in, a reviewed pull request out. The policy layer is designed from what this run shows.

**Contents.**
- A build workflow, started when an issue is labelled ready: Superpowers' brief script, implementer prompt on the builder model (tests first, run inside its step as it works), the tests run again by a shell step, code checking there is a new commit and a valid status reply, then the pull request opened with the App token.
- A review workflow, started when the pull request opens: Superpowers' review package script, its task reviewer prompt on another model family, the verdict posted on the pull request.
- The safe-repeat conventions of section 2.4 (concurrency group, stage label, read before write) built into both workflows from the start.
- One record per agent step to Logfire (moved forward from Layer 6), so the re-estimate after this layer uses measured numbers.
- The Wave 1 failure inventory: a short document of how Wave 1's runs failed, read before the safety design here and in Layer 5.
- Merge by the governor's click at this layer; it becomes automatic in Layer 4.
- First real order: the workflow checker in CI (Wave 1 item D10), starting as a warning.

**Done when.** The workflow checker reaches `main` through these workflows with no message relayed by the governor; a duplicate trigger for the same issue runs once; a job killed just after it opened the pull request, then re-run, opens no second pull request and posts no duplicate comment; a list of the gaps the runs showed is in git, feeding Layers 4 and 5.

**Proof.** The run and the two trials.

### Layer 4. Policy for changes (normal and light lanes)

**Purpose.** Our culture layer on every change, written as configuration and prose first.

**Contents.**
- Role briefs: Superpowers' prompts plus one shared page of our reviewer rules (the good-enough judgement, distrust the report, what not to flag, the "needs the governor" mark for anything about what the user sees or about scope).
- The thin reader (section 2.5). Code decides from it: a failed tests-against-spec verdict or open Critical or Important findings send the change back for revision; after three rounds it goes to the governor; a "needs the governor" mark stops the loop at once and opens a decision.
- The test-first shape for changes (section 2.6): examples in the change form and spec template (k as a setting, how each example is proved), the example checks (each test present, none skipped or expected to fail), the way out for a wrong test, the tests-against-spec verdict first in the code review, each finding's cause, and the first exemplars.
- The reviewer roster for the light and normal lanes (which seats, which model families) as configuration; cross-family review enforced by code: a reviewer seat in the builder's model family is refused.
- The review-accepted status, posted only by the trusted job; GitHub auto-merge; the ruleset requiring that status (the governor applies it).
- The decision pause as two workflows: one writes the request in git and opens an issue mentioning the governor; his answer on that issue starts the next, which writes the lock and continues. Open decisions are visible as a list with their age (a label on the decision issues, oldest first).
- The routing rule (light or normal; a feature or an architecture change waits for Layer 7), recorded on the issue and re-checked when the pull request opens. The light lane is the same workflows with the brief taken from the issue itself.
- Guards in every lane: least privilege for agent steps; changes stay within the files the issue names; no secrets; a recorded governor bypass so a broken check never blocks its own fix.
- Issue forms for a change and for a new feature (the feature form waits for Layer 7).
- Second job through the path: a small real Smart Writer V2 change, such as a bug fix or a behaviour change. Not a feature, so it fits the rule that no Smart Writer V2 feature starts before the design path is on.

**Done when.** A normal change and a light change both merge with no governor action other than a decision; a deliberately flawed change is sent back and does not merge; a same-family reviewer is refused; a change that deletes an example's test is sent back.

**Proof.** Those runs, plus tests for the thin reader, the routing rule and the example-id check (code we wrote).

### Layer 5. Running unattended

**Purpose.** The governor does not have to watch. Only what Layers 3 and 4 showed the bought parts do not already do.

**Contents.** A time limit per step and per workflow; a failed workflow re-run at most twice, then an alert issue; a scheduled watchdog that opens or updates an alert issue mentioning the governor when a run goes silent past its deadline; status comments on the issue at milestones and on red; "done means checked" (valid output, new commit, tests passing) after every agent step. Then the deliberate trials: kill a run mid-step, stop the codespace and close the laptop, leave a decision unanswered overnight.

**Done when.** The trials pass: a killed run, re-run, repeats no push, comment, label or pull request and loses at most the step it was in; work continues with the laptop closed; an answer the next morning starts the next workflow; a stall raises the watchdog's alert. (Exit criterion 2.)

**Proof.** The trials, recorded in git.

### Layer 6. Cost and quality numbers

**Purpose.** The governor sees cost and quality for every piece of work.

**Contents.** The per-step record started in Layer 3 completed (model, role, work item, time, tokens, cost), taken from the runtime where it reports usage and estimated from the governor's usage export where it does not, labelled estimated; the Wave 1 baseline, once, from git and the usage export; each kept check's track record (how often it fired and was right); the scorecard computed by code (acceptance by pass, lead time, unattended rate, cost by role, estimate against actual) at wave, feature, order and task, split by lane; the drift signal past about 30% over estimate; the 1% measurement-cost check. Work done before this layer is covered from the usage export and git, labelled estimated.

**Done when.** The scorecard shows its five numbers for every Wave 1.5 piece of work, each labelled measured or estimated. (Exit criterion 3.)

**Proof.** The scorecard itself, plus tests for the code that computes it.

### Layer 7. The design path for features (full lane)

**Purpose.** Bigger work goes through spec, plan and the governor's approval before building, so Smart Writer V2 can start on the factory.

**Contents.**
- Intent and spec drafted in chat (Cursor) with the governor; a small hand-in command validates and commits the drafts and labels the feature issue "spec ready".
- Short workflows for each stage, each started by a label: spec review (product seats, including whether the examples match the requirements); plan (Spec Kit's plan, naming the data models and signatures); plan review (Spec Kit's consistency check first, then architecture seats; the architect reads the result); tasks (with estimates, and the consistency check again); then the tests-and-stubs step and its test review before any implementation (section 2.6, point 3). The reviewer roster per stage (product seats, architecture seats, the competition seat for product features) as configuration. The governor's approvals of the spec and of the plan's architecture and phasing are labels that start the next workflow.
- Readiness: before orders are created, code lists the feature's unanswered decisions; a task that depends on one waits. Then the tasks become issues with sub-issues (Spec Kit's tasks-to-issues command), and each runs the normal lane.
- Re-align after a decision that changes the architecture: orders not started are held, the plan and tasks are amended in place, the consistency check runs, and a review round checks only the amendment.
- Feature acceptance: the governor sees the spec, its examples with their test results, acceptance criteria and test names, not diffs; accept closes the feature, reject turns his reasons into corrective tasks.
- Trial: one real Smart Writer V2 feature, chosen with the governor, end to end through the lane.

**Done when.** That feature passes feature acceptance through the lane, and the full lane is switched on.

**Proof.** The trial feature, plus tests for the hand-in command and the readiness check.

### Layer 8. Finish

**Purpose.** One way of working, described as it actually runs.

**Contents.** The rulebooks (constitution, `AGENTS.md`, Cursor rules) rewritten to describe what runs, replacing the interim rulebook, within the agreed size budgets; role pages and the cast page; the user's guide; the three backlog labels and the retro's backlog items filed; anything of Wave 1 still left removed; the end-state description corrected wherever it differs from what runs; the material for the next retro.

**Done when.** All five exit criteria are checked and recorded: at least one piece of work per lane merged by the new path with no governor action other than decisions; the trials passed; the scorecard covers every Wave 1.5 piece of work; nothing of the old queue remains and the rulebooks describe only the new factory; actual effort inside the estimate range or a re-plan raised visibly.

**Proof.** The exit-criteria record.

## 5. Differences from the product shape (for the governor's approval)

Each row is a variation from `notes/retro/2026-10-factory-whole.md` or the funnel. Approving this note approves these rows; anything not listed here follows the product shape.

| # | Product shape says | This approach | Why |
|---|--------------------|---------------|-----|
| 1 | Spec Kit's saved run state is kept across Actions jobs; a minimal reconciler takes the next safe step after a restart (sections 5, 10) | No run pauses across jobs. State between workflows lives in GitHub (issue, pull request, labels, commits). A crashed workflow is re-run from its start; every step is safe to repeat through the conventions of section 2.4 (one run per work item, the stage as a label, read before write), proved by trials in Layer 3 | Removes the most expensive building; same outcome for the governor: runs continue with the laptop closed, nothing irreversible repeats, silence raises an alert |
| 2 | About six message formats of our own, in Pydantic (section 5) | Superpowers' prompts and scripts unmodified at a pinned version, plus a thin lab profile fixing the parseable form of the status reply and verdict (with our four added slots) and a reader for it; our decision request and lock format kept; status comments as plain text | A format reviewed and revised by others instead of new design and new mistakes |
| 3 | Convergence: open blocker or major findings with confidence 80 or more block; low-confidence blockers listed for the governor (section 4b) | Superpowers' severities decide: open Critical or Important findings block; Minor does not. No confidence score unless real runs show the need | Keeps the shipped format; confidence scoring was our own addition |
| 4 | Review controller built from the design kit (funnel C9) | The review loop is a Spec Kit workflow loop using Superpowers' reviewer and re-review prompts | Bought engine; no separate controller |
| 5 | Removal and rulebook rewrite come last; a cutover moment after the Core phase (funnel section 9) | Wave 1's machinery and rules are removed first (Layer 0); an interim rulebook runs until Layer 8; no cutover moment because only one way of working ever runs | The governor does not want to run on Wave 1's rules; Wave 1 only added files, so removal is cheap |
| 6 | "A known-good factory runs the sprint" meant Wave 1's process until cutover (register item 76) | The known-good way is plain GitHub plus Cursor: a worker on a branch, a pull request, a cross-family review, merge on green | Same principle; the governor judged Wave 1's process extremely wasteful |
| 7 | A probe, then a Core phase ending in one binding stop (funnel section 9) | The probe's four unknowns are Layer 2; the governor judges after every layer, each with its own appetite | Earlier and more frequent judgement |
| 8 | Switch the engine to AI-SDLC if the trial shows more than a few days of reliability glue (funnel section 4) | Any fail in Layer 2 or Layer 3 stops for the governor: fix, other runtime, or rethink the engine | The short-workflow design removes most of that glue; the decision stays the governor's |
| 9 | Exit criterion 3: the scorecard covers every Wave 1.5 order | Unchanged, with work done before Layer 6 covered from the usage export and git, labelled estimated | Makes the criterion achievable as written |
| 10 | A held-back set of acceptance scenarios: a separate worker derives them, a store builders cannot read, a fresh evaluator runs them at code review (section 4e; funnel C3.3; register item 41) | No held-back scenarios. The test-first shape of section 2.6 instead: k examples per requirement in the spec (3 by default), the builder writes the rest of the tests, the tests are reviewed against the spec (inside the code review for changes, before code for features), tests run inside the build step, small orders, types first, a way out for a wrong test, three rounds; plus an exemplar per kind of block and each finding's cause | The governor's aim was faster convergence, not secrecy; the builder writes its own tests, so there is nothing to hide from it; the examples are the independent tests. Saves the store, the evaluator and the governor's private-repository step |
| 11 | One lab workflow with a lane switch, plus sub-workflows (section 3; register item 89) | Several short workflows, each started by a GitHub event (an issue labelled, a pull request opened, a decision answered); the lane is a label each one reads | Follows from row 1: a single workflow would have to wait across events |
| 12 | Intake forms for a change, an order and a new feature (section 4a; funnel C1) | Forms for a change and a new feature only. Orders are created by code from a feature's tasks; ad hoc work enters as a change | No person writes an order by hand in this design |

## 6. What changes in the records when this note is approved

- `notes/retro/2026-10-wave1.5-funnel.md`: a pointer at the top of sections 8 and 9 saying this note replaces them as the plan of record for how to build.
- `notes/retro/2026-10-factory-whole.md`: a pointer under the status line naming the parts this note varies (section 5 above); the file otherwise stays the product shape, and Layer 8 corrects it to match what runs.
- `notes/retro/2026-10-harness-changes.md`: an "amended by" pointer on items 16 (reconciler), 21 (checkpoint and resume), 41 (held-back set), 76 (known-good factory), 92 (six formats), 94 (convergence rule) and 104 (design kit as the starting point).
- A new decision record amending `wave1-retro-factory-path`: Spec Kit stays the engine, run as short workflows; the Superpowers packet set is adopted as shipped.
- `notes/retro/2026-10-architect-handover.md`: the state section points here.

## 7. Open items for the governor (asked later, as plain choices)

- Approval of this note and its section 5 (decision request after sizing and review).
- The interim rulebook (Layer 0): a rule-path change needing his approving review.
- Settings only he can change: the ruleset update (Layer 0), the GitHub App and the Actions secrets (Layers 1 and 2), the merge rule requiring the review-accepted status (Layer 4).
- Whether to buy a Copilot plan for the second runtime (Layer 2).
- Which Smart Writer V2 feature is the full-lane trial (Layer 7).
- Whether the re-align step in Layer 7 (amending plan and tasks after an architecture decision, about 2 to 4 hours) waits until a real run needs it, as the sprint manager recommends.
- How to read the cost picture: the likely figure is about 6.5 over the appetite, and the every-task-goes-badly figure about 35 over its ceiling (section 4).

## 8. Who does what

- **Architect:** owns this note and the product shape; reads each layer's walkthrough and the plan for Layer 7 against them; keeps the end-state description true as decisions land.
- **Sprint manager:** sizes each layer; writes each layer's walkthrough and task list; runs delivery and status; decides how much of the intent session and Spec Kit spec it still needs for Wave 1.5 itself (the architect's suggestion: this note serves as the plan's architecture and phasing, so a short intent record and per-layer task lists are enough).
- **Governor:** approves this note, each walkthrough, and the decisions and settings above; judges each layer by using it.

## 9. Cross-family review and triage

Reviewer: GPT-5.6 Sol, 2026-10-19 (`notes/wave1.5/2026-10-implementation-approach-review.md`, reviewer commit 7ae7196). Verdict: sound with changes; no blockers, six major, one minor. Triaged by the architect with a simplicity bias: accept the gap, take the smallest fix that closes it, and do not re-grow what this note removed.

| # | Finding | Severity | Triage | Where |
|---|---------|----------|--------|-------|
| 1 | Safe repeat is named but not designed: duplicate or concurrent triggers, a job killed after a write | major | Accepted in part. Added a concurrency group per work item, the stage as a label moved last, read before write, and the two trials in Layer 3. Not taken: attempt records, leases and a state machine, which would rebuild the reconciler row 1 removes | 2.4; Layer 3; row 1 |
| 2 | Superpowers' formats are prompts, not a machine schema | major | Accepted. A thin lab profile over unmodified prompts fixes the parseable form; one repair, then fail; sized as ours | 2.5; row 2 |
| 3 | The full lane reviews tests before code, but no step writes them | major | Accepted. A tests-and-stubs step after tasks; only an accepted test review starts implementation. Normal-lane examples come through the change form | 2.6 points 1 and 3; Layer 7 |
| 4 | An example id alone does not protect what a test checks | major | Accepted in part. Each example says how it is proved; code rejects skipped or expected-to-fail example tests; a flag on an example's test goes to the governor; changes to the builder's own tests carry reasons in its report. Not taken: separate provenance records and structured reason files, since the report and the diff already carry them | 2.6 points 1 and 7; Layer 4 |
| 5 | Product-shape items dropped without a row | major | Accepted. Restored: the failure inventory (Layer 3), reason and severity per kept check (Layer 0) and track record (Layer 6), open decisions with age (Layer 4), the Wave 1 baseline (Layer 6), the reviewer roster with the competition seat (Layers 4 and 7). New rows 11 (several event-started workflows) and 12 (no order form) | Layers 0, 3, 4, 6, 7; rows 11, 12 |
| 6 | The cost picture hides the every-task-goes-badly total | major | Accepted. Section 4 shows likely, realistic bad case and every-task-goes-badly together, with the 35 hours over the ceiling stated; the sprint manager re-sizes the added work. The sprint manager's recommendation to move the per-step record into Layer 3 is adopted | 4; Layer 3; 7 |
| 7 | "Wave 1 only added things" overstates the diff | minor | Accepted: "almost entirely additive" | 2.1 |

Also adopted from the sprint manager's sizing recommendations: the ruleset change timed with the deleting merge (Layer 0) and the script-loop fallback if Spec Kit's loop misbehaves (Layer 2). The re-align deferral is a choice for the governor (section 7).
