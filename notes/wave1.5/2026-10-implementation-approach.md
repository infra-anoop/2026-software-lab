# Wave 1.5 implementation approach

**Status: approved by the governor, 2026-10-19 (decision `wave15-implementation-approach`, option A); written by the architect, 2026-10-19.** Sized by the sprint manager (section 4) and re-sized twice; cross-family review done and triaged (section 9); the governor's funding calls in section 4. Tranche 1 (Layers 0 to 3) is committed. The retro records carry pointers to this note (section 6). **Amended 2026-10-20 (decision `wave15-reliability-rules-first`):** Wave 1's rules are inventoried and reviewed before Layer 0 removes anything, and unattended reliability comes first, with an investigation before Layer 0 and the early reliability pieces moved into Layer 0 (section 2.7, section 10). **Amended 2026-10-22 (reliability decisions D2 to D24, `notes/wave1.5/2026-10-reliability-register.md`):** GitHub Actions is the baseline host for unattended work, cut into 30-minute chunks under a 60-minute limit; every task is interactive or batch; batch agents fail closed and never wait; Copilot is designed in from day one behind a setting; batch chunks run in a ready-made image (section 11).

This note says **how** Wave 1.5 is built. **What** is built does not change: the product shape stays the end-state description in `notes/retro/2026-10-factory-whole.md`, and the value statement and exit criteria stay those of `notes/retro/2026-10-wave1.5-funnel.md` section 9. Once approved, this note replaces the funnel's work-item list and phases (sections 8 and 9's phase table) as the plan of record for how to build. Every place where it varies from the product shape is listed in section 5 for the governor's approval; nothing varies silently.

## 1. Why this note exists

On 2026-10-19 the governor raised two concerns with the agreed Wave 1.5 plan (89 likely, 182 pessimistic agent-hours): the effort is high, and, more important, the work might not match what he expects, repeating Wave 1, where most of what was built had to be thrown away. In his words: "I don't want to build like I built Wave 1 - only to find myself in a position to throw away most of it."

The architect's diagnosis, which the governor accepted:
- **The plan built what can be bought.** Most of the hours went into our own machinery around the engine: saving a run's state between GitHub Actions jobs, resuming it, a restart controller, six message formats of our own and a review controller. The governor's expectation was "install, configure, add our policy layer, test that it is stitched together", with very little building.
- **The design grew on paper.** Each coherence review of the end-state description added a mechanism. Every addition was sound; together they describe a mature factory for a learning project of about five users. That is the Wave 1 pattern again, in a document instead of code.
- **The judgement came late.** The governor would first use the new factory after the Core phase, about half the budget in.

Governor's direction (chat, 2026-10-19, 19:35 to 20:32 PT): start from today's `main` (not rolled back), remove Wave 1's machinery, then build in layers (install, configure, policy, glue) with fewer intermediate tests; use Spec Kit workflows (a YAML file per job, run by Spec Kit's common Python runner, calling the Cursor or Copilot command-line agent); use the Superpowers packet set as shipped instead of designing our own formats; "for the most part, we are not planning to deviate from the overall product shape". He agreed to this note's form: a new note that replaces named parts of the retro records, one section per layer.

## 2. Seven decisions that shape the build

### 2.1 Clean slate on today's `main`

Wave 1 was almost entirely additive: against the last commit before it (2026-09-21), it added about 56,000 lines in 538 files and deleted 36 lines. So its machinery can be removed in one change on today's `main`, without rewriting history or losing the non-factory work done since (CI fixes, database bootstrap tests, the Smart Writer V2 spec, the retro records). Git keeps the history. Layer 0 removes the machinery first.

Rules are treated differently from machinery (governor, 2026-10-20, recalibrating his earlier "I definitely don't want to run with wave 1 rules"): "I said we should keep what is good in Wave 1. And between the 'rules' and 'machinery' 'Rules' are likely to be more useful." So before Layer 0 removes anything, every Wave 1 rule is inventoried and reviewed with the governor (section 2.7). A rule is kept, rewritten or dropped with a recorded reason, in line with the retro's principle that nothing of Wave 1 is kept by default. The kept rules become the interim rulebook and the starting point of the policy layer. What goes is the machinery that enforced the rules (the queue, the claim and verdict records, the gates that only check those records), not the rules themselves.

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

**Chunks (2026-10-22, decisions D3, D7, D8, D19).** Each job runs one chunk: work estimated at 30 minutes under a hard 60-minute job limit, so a chunk that takes twice its estimate still finishes. Every step is a chunk, not only implementation (specify, plan and review can overrun too), and each leaves the code working. The chunk size is a factory requirement on the Spec Kit plan: every task carries an estimate of at most 30 minutes, checked by a warning-first check and judged by the reviewer. A chunk ends by writing a structured status (done, blocked with a question, failed); the workflow acts on that status, not on the agent's prose. On an overrun the chunk is retried once from its last push; a second overrun parks the task, the run continues with the next independent task, and the sprint manager takes parked tasks in the morning. The chunk's life cycle and failure table are in the reliability report, section 10.

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

### 2.7 Reliability first, and Wave 1's rules reviewed before anything is removed

Decided by the governor on 2026-10-20 (decision `wave15-reliability-rules-first`). Unattended long runs that are not flaky come before everything else: "We can't go anywhere if we can't do unattended long runs... First is that we can do long runs and they are not flaky, where we have to redo the work." On 2026-10-19 two reviewers froze in a row, which cost tokens, time and his attention. Meaningful work and token cost matter, but come second.

Two pieces of work finish before Layer 0 builds anything, and the Layer 0 walkthrough waits for them. The architect leads both, with a spawned worker gathering evidence; the sprint manager sizes and tracks them.

1. **Reliability investigation (a side wave that reports back to this sprint).**
   - Covers every hang and stall on record. From Wave 1: the worker that hung silently and the resume that hung too; stalls on permission prompts and on a sandbox-blocked command form; completion notices lost or hours late; the codespace stopping about every 12 hours or at its 30-minute idle timeout; editor disconnects; long review loops. From 2026-10-19: the two reviewer freezes (both on web requests, each raising an approval prompt visible only on the agent's card; confirmed by trial on 2026-10-20; a read outside the worktree, first suspected, was not the cause).
   - For each: the evidence, the root cause or the best supported hypothesis, the rung of the fix ladder chosen (remove the cause, route around, recover automatically, detect and report), and the design change. Where no root cause is found, the design still has to make the case better.
   - Automatic recovery, for both kinds of agent. Agents spawned from chat sessions, which carry all work until Layer 3 and are what froze: a watcher that notices silence (no push past a deadline) and restarts the agent from its last push, at most twice, then reports to the governor, with no one clicking. Agents in GitHub Actions: their allowed commands configured up front, and time limits.
   - Output: a report in git, and the list of items moved into Layer 0 or into the layer that owns them.
2. **Rules inventory and review.**
   - Every Wave 1 rule, from the constitution, `AGENTS.md`, the Cursor rules, `docs/agent-os/`, the 29 registered checks, the four editor hooks, the handover's operating rules and the Wave 1 orchestrator's hard rules.
   - For each: what it says, the incident or reason behind it, and keep, rewrite or drop with the reason; for a kept rule, where it lives (rulebook text, an automated check, configuration, or a role brief).
   - The governor reviews the list. The kept rules become the interim rulebook in Layer 0, and the starting point of the policy layer.
   - Candidates from the retro to include: change control by the mission test (required for the wave's core value: in, with the estimate updated; weakly related: backlog; unclear: the governor); new checks start as warnings; each proposed check gets a relevance and consistency check; one backlog with a grooming step at each sprint start; one primary domain per sprint.

**The policy session.** After tranche 1 and before Layer 4, the architect and the governor hold a deep, lengthy session on the policy layer, starting from the kept rules and what Layers 0 to 3 showed. Layer 4's walkthrough waits for it.

## 3. The stack

| Job | Part | Bought or ours |
|-----|------|----------------|
| Conversations with the governor: architect, sprint manager, intent and spec drafting | Cursor chat sessions | Bought |
| Design method: spec, plan, tasks, consistency check, templates | Spec Kit | Bought |
| Engine inside a run: steps, loops, agent calls, model per step | Spec Kit workflows, upgraded from the installed 1.0.6 to the current release | Bought |
| Trigger between runs, host, schedules | GitHub Actions: the baseline host for all unattended (batch) work, on its own merits (D2) | Bought |
| Batch environment | A ready-made image with Nix and every dependency, named by a fingerprint of the lock files, in GitHub's registry (D21, D22) | Bought registry; the image build workflow is ours |
| Work queue and state between runs | GitHub Issues, labels, pull requests | Bought |
| Builder agent | Cursor command-line agent, model pinned per step | Bought |
| Second runtime | Copilot command-line agent, supported from day one in the same Actions job shape; a setting (`AI_ENV`, default `cursor`) chooses the agent per role, so a builder can run on Cursor and its reviewer on Copilot (D5). The allowed-commands policy is written once and generated into each tool's format (D6) | Bought |
| Packet formats and role prompts | Superpowers packet set, pinned version | Bought (open source) |
| Merge rules | GitHub rulesets and code owners | Bought |
| Robot identity for code that opens pull requests | GitHub App (created by the governor) | Bought |
| Run records | Logfire | Bought |
| Policy layer: rules, briefs, workflow files, decision format, thin reader, small scripts | This repository | Ours |

GitHub Agentic Workflows and Copilot's coding agent are not needed in this design. Copilot's coding agent runs its own agent loop, which is the pattern the governor wants code to replace; it stays a later option (D5).

## 4. The layers

Sizes are the sprint manager's (agent-hours, likely / pessimistic, uncalibrated), task by task in `notes/wave1.5/2026-10-layer-sizing.md`, with its recommendations. Across the layers: about 100 likely, plus about 5.5 for walkthroughs and sprint management, so about 105.5 for the wave; governor about 8 to 16 hours. The test-first shape added about 5 of those hours (Layers 1 and 4 gain its checks, Layer 7 loses the held-back store); its saving is in running orders, expected but not yet measured or booked. The cross-family review's triage (section 9) added about 10 more: about 5 for its fixes (safe repeat designed and proved in Layer 3, the lab profile, the tests-and-stubs step, the stronger example checks) and about 5 for items of the retro's own plan that this note had dropped (the failure inventory, each check's reason, severity and track record, the Wave 1 baseline, open decisions by age, the reviewer roster with the competition seat). The locked appetite (89 likely, 182 pessimistic agent-hours) stays the ceiling; it is not a target.

Three numbers, shown together because they tell different things:
- **Likely: about 105.5,** about 16.5 over the appetite's 89; all six levers in the sizing note together recover about 6.
- **Realistic bad case: about 170,** the likely figure times about 1.6, since not every task goes badly at once. Under the 182 ceiling.
- **Every task going badly: about 243,** the sum of each task's pessimistic figure, including the Spec Kit fallback. About 61 over the 182 ceiling.

The appetite's likely figure cannot be met with the whole product shape kept. After Layer 3 the sprint manager compares actual with estimate and re-estimates the remaining layers with that correction.

**Funding, decided by the governor (chat, 2026-10-19, about 23:45 PT).** The whole product shape is kept, and the wave is funded in three tranches, each committed only when the one before it is done:
- **Tranche 1: Layers 0 to 3,** about 33 likely (about 31 after the Copilot trim). Committed with this note's approval.
- **Tranche 2: Layers 4 to 6,** about 39 likely. Committed after Layer 3, on the sprint manager's re-estimate from measured numbers.
- **Tranche 3: Layers 7 and 8,** about 28 likely. Committed after Layer 6, the same way.

Walkthroughs and sprint management (about 5.5) run across all three. The provisional total is about 97 likely if every trim below is taken; the realistic bad case stays under the 182 ceiling.

**Added by the 2026-10-20 amendment (section 2.7), to tranche 1.** These are the architect's rough figures, not yet sized; the sprint manager sizes them before the work starts. Reliability investigation, about 6 likely / 12 pessimistic. Rules inventory, about 4 / 8, plus 1 to 2 hours of the governor's review. Layer 0's reliability pieces, about 3 / 6. Together about 13 likely, so tranche 1 becomes about 44 likely and the wave about 110 to 118.5. Layer 5 may shrink by what moves into Layer 0; the sprint manager re-sizes it at the tranche 2 gate. The governor accepted the cost of iterating on the design before building (2026-10-20).
- **Overrun rule:** a layer that passes 1.5 times its likely figure stops for a rethink with the governor; it does not quietly extend.
- **Trims:** the Copilot proof runs only if the Cursor agent fails in Layer 2 (taken 2026-10-19; reversed 2026-10-22 by decision D5, Copilot from day one, so its cost returns to tranche 1 and the sprint manager re-sizes it; section 5 row 13). The other seven trims in the sizing note (re-align waits for its first real use; scorecard per issue first; checks' track record by hand; Wave 1 baseline as one total; no separate hand-in command; user's guide folded into the cast page; competition seat waits) are decided at the tranche gates, with measured numbers. Until then they stay in scope.

| Layer | What the governor gets | Size (sprint manager) |
|-------|------------------------|-----------------------|
| Before 0 | The reliability report; Wave 1's rules reviewed, each kept, rewritten or dropped with a reason (section 2.7) | about 10 / 20 (architect, not yet sized) |
| 0. Clean slate | Wave 1's machinery gone; the kept rules as the interim rulebook; no approval prompt can block an agent; a watcher restarts a silent agent | 7 / 15.5, plus about 3 / 6 (not yet sized) |
| 1. Install | The bought parts present and pinned | 6.5 / 15.75 |
| 2. Configure | The parts wired together; the four unknowns that could change the stack answered | 6.2 / 19.75 |
| 3. First end-to-end run | An issue labelled, a reviewed pull request back, using the parts as they come | 13.1 / 30.25 |
| 4. Policy for changes | Our rules on every change: reviews, decisions, guards, the light and normal lanes | 24.65 / 53.75 |
| 5. Running unattended | Nothing to watch: time limits, re-runs, an alert on silence, status comments, the deliberate trials | 7 / 16.75 |
| 6. Cost and quality numbers | A record per run and the scorecard | 7.2 / 16.75 |
| 7. The design path for features | The full lane, proved on one real Smart Writer V2 feature | 21.25 / 48 |
| 8. Finish | Rulebooks and guide describing what runs; the end-state description matching reality | 7.05 / 16.25 |

**How work gets done before the new path can carry it (Layers 0 to 2).** The plain known-good way: a chat session starts a worker on a branch, the worker opens a pull request, a reviewer from another model family is started from the same session with a pointer to a note in git, and the change merges on green checks and an accepted review. That is safer than Wave 1's machinery and needs none of it. From Layer 3, the new path takes every piece of work it can handle.

**Interactive and batch work (2026-10-22, decisions D12 to D15).** Every task is tagged interactive or batch by the sprint manager at planning. Interactive by default: brainstorming, resolution sessions after a review, intent and policy sessions, decision walkthroughs. Batch by default: building, reviewing, inventories, research write-ups. Interactive tasks run in the codespace (now with the 240-minute idle timeout); batch tasks run in GitHub Actions. A subtask spawned inside an interactive session stays in the codespace only while it is short and attended; one that turns out long or unattended becomes a batch task. The two kinds hand over through git only. Until the Actions path exists, unattended work in the codespace must fit its window: 240 idle minutes at most, 12 hours of lifetime, and an agent's own activity does not count as use.

### Layer 0. Clean slate

**Purpose.** Stop running on Wave 1's machinery, keep its good rules, and make agent runs unattended-safe from the start. Starts only after the reliability report and the rules review (section 2.7).

**Contents.**
- Delete in one change: the `factory` package's queue, lifecycle, status board, metrics and command (`scripts/factory/`), the factory CI workflows (`factory-gates.yml`, `factory-pr-evidence.yml`), and the deprecated skills. Of the 29 registered checks and the four editor hooks, remove those the rules review drops or that only check Wave 1's records; a rule the review keeps survives as rulebook text, configuration, a brief or a small standalone check.
- Archive, not delete: `bus/orders/` and `notes/packets/` move to an archive folder; the current constitution, `AGENTS.md` and Wave 1's process documents in `docs/agent-os/` move there too, after the rules review has taken what it keeps from them.
- Keep: decisions in `bus/decisions/` with a small standalone check of their format; the guard against committing or pushing to `main`, as a small standalone script behind an editor hook; the lab's own checks (secrets schema, deploy settings, locked dependencies) in their existing CI jobs; the retro records; the Smart Writer V2 specs; the intent-session skill; the Spec Kit skills; and whatever else the rules review keeps. Each kept check gets one line stating its reason and severity.
- Write the interim rulebook from the rules the review kept, in force until Layer 8 replaces it. It holds at least: changes only through a branch and pull request, never to `main`; secrets never in git; the lab's invariants (Nix, uv, the app registry); every review by another model family; decisions in git with the governor's explicit yes; after three review rounds it comes to the governor; the short escalation list; the good-enough judgement for findings; change control by the mission test. It replaces the constitution file's content (Spec Kit reads that file), and `AGENTS.md` shrinks to a short map.
- Reliability pieces, from the reliability report (sections 7 and 9 to 12) and register decisions D10 to D20; their split between this layer and the Actions path is settled in the Layer 0 walkthrough:
  - **No approval prompt can block an agent (D10).** Every action is configured to run, be refused, or block the task and report; never to wait for an approval nobody sees. One allowed-commands policy, written once and generated into each tool's format (D6). Batch runs fail closed: a generous allow list, a short deny list, never the override flag (`--force`, Copilot's `--allow-all`); every refusal is logged and reviewed, and the allow list grows from that record (D17). File deny entries are written in absolute or `**/` form, and the boundary for writes is git-side: the job's token, its branch, a changed-paths check and the rulesets (D18). The agent programs' versions are pinned, and the permission trials of 2026-10-21 become a conformance test rerun on every upgrade (D20).
  - **Spawned agents make no web requests.** The spawning session commits dated copies of any outside source first (the cause of the 2026-10-19 freezes, confirmed by trial). Reads outside the worktree stay off limits as hygiene, not as a reliability rule. Each agent pushes a first version within 10 minutes and pushes again at every green step, so silence shows in git.
  - **A question ends the run, it does not hang it.** Each chunk ends with a structured status (D19); "blocked" posts the question on the work item's issue and resumes on the governor's answer, the same mechanism as the decision pause (D11). Chunk instructions say: decide and record the assumption; ask only what needs the governor.
  - **Interactive subtasks stay short and attended (D14).** Editor-spawned agents still show approval prompts; that is acceptable only because a person is present.
  - **A watcher for chat-spawned agents,** for daytime work in the codespace. When an agent's branch has had no push past its deadline, the watcher restarts it from its last push, at most twice, then reports to the governor. The long-term watcher is the scheduled GitHub workflow of Layer 5.
  - **Time limits** on every agent run.
  - The codespace with the 240-minute idle timeout, done on 2026-10-22 (register A2).
- Governor: update the `main` ruleset so it no longer requires the deleted factory checks, at the same moment the deleting change merges (before, the old checks block it; after, every pull request blocks), and keep "pull request required". Exact strings and timing come from the sprint manager.

**Done when.** `main` carries none of the removed machinery; every rule the review kept is in the interim rulebook or in the place the review named; CI is green with the kept checks; a test pull request merges under the new ruleset; the interim rulebook is the only always-loaded rule text besides the short map; the governor has approved the rule-path change. Reliability: a spawned agent asked to run a command outside its allowed list is refused and carries on, with no prompt; an agent deliberately silenced is restarted by the watcher from its last push, with no one clicking, and a third silence reaches the governor.

**Proof.** The test pull request, a green CI run, and the two reliability trials recorded in git. No new tests beyond the watcher's own.

### Layer 1. Install

**Purpose.** Every bought part present, at a pinned version, where it will run.

**Contents.** Spec Kit upgraded from 1.0.6 to the current release with the Cursor integration (Copilot's only if Layer 2 needs it), checking first whether the upgrade overwrites the lab's template overrides; the Cursor command-line agent available in the Nix environment and in Actions; the Superpowers packet set copied in at a pinned version; the GitHub App created by the governor. The Copilot command-line agent installed the same way, behind the `AI_ENV` setting (D5). The build step's environment, decided on 2026-10-22 (D21 to D24): a ready-made image holding Nix and every dependency, so a chunk downloads nothing at start and runs an app's tests and a strict type checker in seconds (section 2.6, point 5). The image is named by a fingerprint of `flake.lock` and every `uv.lock`; a chunk uses only the image matching its own checkout, and a merged lock-file change triggers a rebuild, so a stale image is never used. Image builds use retries, longer timeouts and caches keyed on the lock files; a chunk whose task changes a lock file installs only the difference on top of the image. Measure from GitHub's runners whether package downloads fail there, and setup time with and without the image (register A13).

**Done when.** Each part runs a trivial command in an Actions job and in the codespace, and its version is pinned in git; an agent step runs an app's tests and type checker inside its own job, in the image matching its checkout.

**Proof.** Running it. No tests.

### Layer 2. Configure, and answer the four unknowns

**Purpose.** Wire the parts together and settle early the unknowns that could change the stack.

**Contents.** Actions secrets for the Cursor key, a Copilot-enabled token (register A11) and the App key (this closes the open decision on how the App key is delivered); Spec Kit integration settings and a model per step; Actions permissions; the labels and a first issue form. The four unknowns:
1. A Spec Kit workflow step calls the Cursor command-line agent unattended in Actions, with a pinned model and the allowed-commands configuration from Layer 0. A command outside the list is refused at once, not left waiting for approval, tried deliberately. Then the three chunk trials (register A12): one chunk in Actions; a chain of three chunks with no one touching anything; one chunk killed midway and one made to stall, both recovered by the watcher, with an alert after the second failure.
2. The same with the Copilot command-line agent, selected by `AI_ENV` (D5). Its permission behavior, so far known only from documentation, is confirmed by the same trial cases.
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

**Purpose.** Our culture layer on every change, written as configuration and prose first. It starts from the rules kept in the rules review and from the policy session with the governor (section 2.7); its walkthrough waits for that session.

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

**Purpose.** The governor does not have to watch. Only what Layers 3 and 4 showed the bought parts do not already do. The early reliability pieces (allowed commands, spawned agents reading only git, the watcher for chat-spawned agents, time limits) are already in place from Layer 0; this layer extends them to the GitHub Actions path.

**Contents.** A time limit per step and per workflow; the chunk overrun rule (section 2.4: one retry from the last push, then park the task and continue); setup failures reported as "setup failed" and retried on their own, not counted as the task's retry, with repeated setup failures alerting the governor (D23); a failed workflow re-run at most twice, then an alert issue; caps on chunks per work item per day and on concurrent jobs; a scheduled watchdog that opens or updates an alert issue mentioning the governor when a run goes silent past its deadline; status comments on the issue at milestones and on red; "done means checked" (valid output, new commit, tests passing) after every agent step. Then the deliberate trials: kill a run mid-step, stop the codespace and close the laptop, leave a decision unanswered overnight.

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
| 5 | Removal and rulebook rewrite come last; a cutover moment after the Core phase (funnel section 9) | Wave 1's rules are reviewed first (section 2.7), then its machinery is removed (Layer 0); the kept rules run as the interim rulebook until Layer 8; no cutover moment because only one way of working ever runs | The governor wants Wave 1's good rules kept and its machinery gone (amended 2026-10-20); Wave 1 was almost entirely additive, so removal is cheap |
| 6 | "A known-good factory runs the sprint" meant Wave 1's process until cutover (register item 76) | The known-good way is plain GitHub plus Cursor: a worker on a branch, a pull request, a cross-family review, merge on green | Same principle; the governor judged Wave 1's process extremely wasteful |
| 7 | A probe, then a Core phase ending in one binding stop (funnel section 9) | The probe's four unknowns are Layer 2; the governor judges after every layer, each with its own appetite | Earlier and more frequent judgement |
| 8 | Switch the engine to AI-SDLC if the trial shows more than a few days of reliability glue (funnel section 4) | Any fail in Layer 2 or Layer 3 stops for the governor: fix, other runtime, or rethink the engine | The short-workflow design removes most of that glue; the decision stays the governor's |
| 9 | Exit criterion 3: the scorecard covers every Wave 1.5 order | Unchanged, with work done before Layer 6 covered from the usage export and git, labelled estimated | Makes the criterion achievable as written |
| 10 | A held-back set of acceptance scenarios: a separate worker derives them, a store builders cannot read, a fresh evaluator runs them at code review (section 4e; funnel C3.3; register item 41) | No held-back scenarios. The test-first shape of section 2.6 instead: k examples per requirement in the spec (3 by default), the builder writes the rest of the tests, the tests are reviewed against the spec (inside the code review for changes, before code for features), tests run inside the build step, small orders, types first, a way out for a wrong test, three rounds; plus an exemplar per kind of block and each finding's cause | The governor's aim was faster convergence, not secrecy; the builder writes its own tests, so there is nothing to hide from it; the examples are the independent tests. Saves the store, the evaluator and the governor's private-repository step |
| 11 | One lab workflow with a lane switch, plus sub-workflows (section 3; register item 89) | Several short workflows, each started by a GitHub event (an issue labelled, a pull request opened, a decision answered); the lane is a label each one reads | Follows from row 1: a single workflow would have to wait across events |
| 12 | Intake forms for a change, an order and a new feature (section 4a; funnel C1) | Forms for a change and a new feature only. Orders are created by code from a feature's tasks; ad hoc work enters as a change | No person writes an order by hand in this design |
| 13 | The second runtime (Copilot) proven once and kept ready (funnel, Copilot fallback) | Supported from day one in the same Actions job shape, chosen per role by `AI_ENV` (default `cursor`); proven in Layer 2 next to the Cursor agent. The 2026-10-19 trim ("only if the Cursor agent fails") is reversed | The governor, 2026-10-21 (D5): keeping both open is likely needed for the best experience; and because the workflow configuration, not the agent's own record, chooses the reviewer's tool, cross-family review becomes a hard rule |

## 6. What changes in the records when this note is approved

- `notes/retro/2026-10-wave1.5-funnel.md`: a pointer at the top of sections 8 and 9 saying this note replaces them as the plan of record for how to build.
- `notes/retro/2026-10-factory-whole.md`: a pointer under the status line naming the parts this note varies (section 5 above); the file otherwise stays the product shape, and Layer 8 corrects it to match what runs.
- `notes/retro/2026-10-harness-changes.md`: an "amended by" pointer on items 16 (reconciler), 21 (checkpoint and resume), 41 (held-back set), 76 (known-good factory), 92 (six formats), 94 (convergence rule) and 104 (design kit as the starting point).
- A new decision record amending `wave1-retro-factory-path`: Spec Kit stays the engine, run as short workflows; the Superpowers packet set is adopted as shipped.
- `notes/retro/2026-10-architect-handover.md`: the state section points here.

## 7. Open items for the governor (asked later, as plain choices)

- Approval of this note and its section 5 (decision request after sizing and review).
- The interim rulebook (Layer 0): a rule-path change needing his approving review.
- Settings only he can change: the ruleset update (Layer 0), the GitHub App and the Actions secrets including the Cursor key and a Copilot-enabled token (Layers 1 and 2), the merge rule requiring the review-accepted status (Layer 4).
- When GitHub enforces his approval on rule paths: decided in the policy session, workable only once a bot identity opens pull requests (register A6, folded into A10).
- Which Smart Writer V2 feature is the full-lane trial (Layer 7).
- At each tranche gate: commit the next tranche on the re-estimate, and decide the trims that fall in it (section 4).
- The rules review (section 2.7): keep, rewrite or drop for each Wave 1 rule.
- The reliability report (section 2.7): its design changes were decided with the governor on 2026-10-21 and 22 (D2 to D24, section 11); his yes on the report and this amendment after the combined review.
- The policy session after tranche 1 (section 2.7).
- Decided on 2026-10-20, recorded in section 2.7 and section 10: Wave 1's rules reviewed before anything is removed; reliability first, with the investigation and the rules review finishing before Layer 0 builds anything; the architect leads both.
- Decided on 2026-10-19 (about 23:45 PT), recorded in section 4: the whole shape kept, funded in three tranches; the 1.5-times overrun rule; the Copilot trim; the other trims decided at the gates.

## 8. Who does what

- **Architect:** owns this note and the product shape; leads the reliability investigation and the rules inventory, and holds the policy session with the governor (section 2.7); reads each layer's walkthrough and the plan for Layer 7 against them; keeps the end-state description true as decisions land.
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

## 10. Amendment of 2026-10-20: the governor's spot check

After approving this note, the governor asked the architect to check the design against his concerns, including those in the Wave 1 retro. He then recalibrated two points and chose the changes (chat, 2026-10-20, about 08:30 PT; decision `wave15-reliability-rules-first`):
- **Rules.** Keep what is good in Wave 1; rules are likely more useful than machinery. What prompted it, in the governor's words: "for PR41 we 'gamed' to meet the Wave1 rule, but it is temporary, since we will delete all of them in layer 0". His direction: collect and review all the rules, as the starting point of the policy layer. Now sections 2.1 and 2.7, Layer 0, row 5.
- **Reliability first.** Unattended runs that are not flaky come first. Investigate the root causes of the 2026-10-19 freezes and of Wave 1's hangs, and design automatic recovery even where no root cause is found. Reliability items such as the agents' allowed commands belong in Layer 0, not discovered in Layer 2. Now section 2.7, Layers 0, 2 and 5.
- **Policy.** "Very little building" is a weak spot for the policy layer, which still holds about 60 hours of our own code and prose. A deep, lengthy policy session comes after tranche 1, before Layer 4. Now section 2.7, Layer 4.
- **Cost and design growth.** Iterating on the design before building is accepted; it is cheaper now than after building.
- **Sequencing and ownership:** both pieces of section 2.7 finish before Layer 0 builds anything; the architect leads them; the note is amended now.

The architect's spot check of the governor's retro concerns against the approved design (sources: `notes/retro/2026-10-harness-changes.md` principles P1 to P18 and themes; `notes/retro/2026-10-wave1-items.md` sections A and B; `notes/retro/2026-10-wave1-agenda.md`):

| Concern | Before this amendment | Now |
|---------|-----------------------|-----|
| Three-turn rule; good-enough judgement; estimates and the drift signal; calibration | Covered (section 2.6, Layers 0, 4, 6; section 4) | Unchanged |
| Laptop not part of the machinery; outside watchdog; restart rule; run log; deliberate trials | Covered for the GitHub Actions path (Layers 3, 5) | Unchanged |
| Correct by design; fewer, stronger checks | Covered (section 2.6) | Unchanged |
| Git as the only record; decisions as requests; the governor not a router; one role per agent | Covered (sections 2.4, 3; Layer 4) | Unchanged |
| Fake-green gap: only trusted code marks a change accepted | Covered (Layer 4) | Unchanged |
| "Stuck or working" and the 30-minute heartbeat for agents spawned from chat, the case that froze on 2026-10-19 | Gap: only Actions runs were watched | The watcher in Layer 0, designed by the reliability investigation |
| Codespace stops and lost completion notices, never root-caused | Gap | In the reliability investigation |
| Approval prompts blocking unattended agents | Partly: found only by Layer 2's unknowns | Allowed commands configured in Layer 0 |
| Wave 1's rules | Mostly removed in Layer 0 | Inventoried and reviewed first; kept rules seed the policy layer |
| Change control by the mission test | Gap: not in the interim rulebook | In the interim rulebook (Layer 0) |
| New checks start as warnings; a relevance and consistency check on proposed checks; backlog grooming; one domain per sprint | Not written down | Candidates in the rules review and the policy session |

## 11. Amendment of 2026-10-22: the reliability decisions

The reliability investigation (section 2.7, item 1) ran with the governor on 2026-10-20 to 22. All 11 incidents on record are decided or closed. The one-line decisions and the actions are in `notes/wave1.5/2026-10-reliability-register.md`; the evidence and reasoning are in `notes/wave1.5/2026-10-reliability-investigation.md`; the locks are in `bus/decisions/` (`wave15-unattended-host`, `wave15-runner-and-chunks`, `wave15-task-modes`, `wave15-permission-policy`, `wave15-batch-environment`). Nothing is built in this phase (D16).

Where each decision lands in this note:

| Decisions | What | Where |
|-----------|------|-------|
| D2, D4 | GitHub Actions is the baseline host for unattended work, on its own merits; Spec Kit workflows stay the process and Actions triggers their steps | Section 3 |
| D3, D7, D8, D19 | Chunks of 30 minutes under a 60-minute job limit; chunk size as a requirement on the Spec Kit plan; the overrun rule; a structured status at the end of every chunk | Section 2.4; Layer 5 |
| D5, D6 | Copilot from day one behind `AI_ENV`; one allowed-commands policy generated per tool | Section 3; Layers 1 and 2; section 5 row 13; the trim in section 4 reversed |
| D9 | The chunk's life cycle, failure responses, notifications on the work item's issue, the Cursor key as a GitHub secret | Reliability report section 10; Layer 2 |
| D10, D11, D17, D18, D20 | Never wait: run, refuse, or block and report; fail-closed batch runs; file deny patterns; pinned agent versions and a conformance test | Layer 0 |
| D12 to D15 | Interactive and batch tasks; where each runs; promotion of a long subtask; handover through git | Section 4, before Layer 0 |
| D21 to D24 | The ready-made image named by the lock-file fingerprint; setup failures apart from work failures; sturdy image builds | Section 3; Layers 1 and 5 |

Corrected: the 2026-10-19 freezes were web requests waiting on an approval only the agent's card showed. Reads outside the worktree were not the cause (section 2.7; `notes/wave1.5/sources/README.md`).

**Cost.** Three decisions add work to tranche 1 that is not yet sized: Copilot from day one (the 2026-10-19 trim reversed), the image and its fingerprint-named builds, and the chunk machinery (structured status, overrun and setup-failure handling, caps). Some of Layer 5 moves earlier with them. The sprint manager sizes them with the other Layer 0 additions (register A7) before the Layer 0 walkthrough; the overrun rule of section 4 applies.

**Unchanged:** the product shape, the layers and their order, the three tranches, the test-first shape (section 2.6), the policy session before Layer 4.
