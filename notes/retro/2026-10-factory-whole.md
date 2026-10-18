# The factory as one whole (end of Wave 1.5)

**Status: final at retro close (2026-10-18, decision `wave1-retro-close`); written by the orchestrator (coach and architect), 2026-10-17; focused review round 1 "not coherent" (2 blockers, 6 major, 1 minor), all nine findings fixed; round 2 "not coherent" (5 resolved, 4 partly; 1 new blocker, 3 major), all four fixed; round 3 "coherent" (all eight resolved, no new contradiction, nothing for the governor). Governor read the file and the review and agreed (2026-10-18 00:56 PT). Stage 5, step 6 done.**

Round 2 fixes: a trial state for switching a lane on (section 16); intake forms aligned with the funnel (funnel C1, C1.1); a worker turns rejected-feature reasons into tasks (4d step 11); the reviewer's flag and the author's "needs the governor" disposition kept as separate fields (4b step 6, section 5). Nothing here is built yet. Review: `notes/retro/2026-10-factory-whole-review.md`.

Round 1 fixes: a total routing rule, so unplanned runtime work lands in the normal lane (section 4a); a readiness step and a re-align step replacing the finish bar and plan deltas (4d steps 8 and 10); a code-owned hand-in from chat to the engine (4d step 3); custody rules for held-back scenarios (4e); feature acceptance before ship with a rejection path (4d step 11); a reviewer-owned "needs the governor" flag that stops the loop before revision (4b step 5, section 5); temporary rules between cutover and the light and full lanes (section 16); the scorecard split by lane (section 9); clearer wording on what agents draft and what code authors (section 5, invariant 1).

This describes the software factory as it should stand when Wave 1.5 ends: what Wave 1 keeps, what Wave 1.5 adds, and what is removed, read as one working system. It is the architect's design input to the Wave 1.5 sprint and the basis for the rewritten rulebooks and user's guide. Where this file and a source disagree, the source wins and this file is corrected.

Sources: the agreed register (`notes/retro/2026-10-harness-changes.md`, items 1 to 104, principles P1 to P18); the funnel and the Wave 1.5 shape (`notes/retro/2026-10-wave1.5-funnel.md`); the survey (`notes/retro/2026-10-factory-survey.md`); the decisions in `bus/decisions/wave1-retro-*` and `wave1-token-usage`.

## 1. Words used here (each defined once)

| Word | Meaning |
|------|---------|
| Governor | The one human. Sets intent, makes decisions, approves rule changes. Watches; does not relay messages or keep anything running |
| Architect | A standing Cursor chat session (also called the coach). Owns the factory's design direction. Talks with the governor |
| Sprint manager | A standing Cursor chat session that runs one wave's delivery. Talks with the governor. Shrinks as the engine takes over routine work |
| Engine | The lab's Spec Kit workflow, run by GitHub Actions. Runs every step that involves waiting or a handoff |
| Worker | A short-lived agent the engine starts for one step (build, write, revise). Fresh context; runs headless through the Cursor CLI |
| Reviewer | A short-lived agent the engine starts to review one artifact. Always a different model family from the author |
| Wave | A sprint with a named primary type (product, infrastructure or tooling) |
| Feature | A spec folder under `specs/` with its spec, plan and tasks |
| Order | A batch of tasks handed to one worker. A GitHub issue; its tasks are sub-issues |
| Task | One unit of work inside an order |
| Lane | How much process a piece of work gets: light, normal or full. Chosen when the work comes in by the routing rule in section 4a; every piece of work lands in exactly one |
| Ship | Releasing merged work to production (the lab's existing ship command); separate from merging |
| Step | One action of the engine: an agent call, a code action, or a pause |
| Gate | A step where the engine pauses for the governor |
| Decision | A choice that belongs to the governor: scope, budget, architecture or rules. Asked as a request in git, answered as a lock in git |
| Review round | One pass of reviewers over an artifact, followed by the author's revision |
| Finding | One problem a reviewer raises: stable name, severity, confidence, file, section, task, cause, recommendation |
| Check | An automated test that runs on a pull request. Blocking or warning |
| Message format | One of about six fixed record shapes (section 5) that agents write and code validates |
| Scorecard | Numbers computed by code from run records (section 9) |

## 2. The parts

| Part | Bought or ours | What it does |
|------|----------------|--------------|
| Spec Kit 1.2.1 workflow engine | Bought (open source) | Runs the lab workflow: steps, gates, loops, fan-out, saved state, resume from the exact step |
| The lab workflow | Ours (one YAML file plus sub-workflows) | Encodes the three lanes, the stages, the review loop and the gates. One workflow with a lane switch |
| GitHub Issues | Bought | The work queue. Orders, tasks, labels for state, dependencies, history |
| GitHub Actions | Bought | Starts and resumes the engine on events (an issue labelled ready, a decision answered, a schedule). Holds no logic |
| Cursor CLI | Bought | Runs workers and reviewers headless, with a model named on every step |
| Copilot CLI | Bought | The second runtime, proven once, kept ready if Cursor fails |
| GitHub App | Bought (configured once by the governor) | The factory's robot identity. Its token lets code push, open pull requests, move labels and post statuses, and makes checks start without manual approval |
| Rulesets and CODEOWNERS | Bought | Merge rules on `main`; governor approval on rule paths |
| Logfire | Bought | Stores one record per step in the OpenTelemetry format |
| Factory code | Ours (Python, small) | Validates and persists what agents draft; authors every state change itself; generates briefs; runs the review controller, the readiness check, the reconciler, the watchdog and the scorecard |
| Role briefs and templates | Ours | What each worker and reviewer role is told; the spec, plan and tasks templates |
| Rulebooks | Ours | The constitution, `AGENTS.md` and the Cursor rules, rewritten to describe only this factory |

## 3. Who does what

| Actor | Does | Decides alone | Escalates to the governor |
|-------|------|---------------|---------------------------|
| Governor | Intent, decisions, rule approvals, acceptance of features | Everything on the escalation list (section 7) | — |
| Architect | Factory design; reviews the architecture of plans before the governor sees them; answers design questions from the sprint manager; runs retros | Design details inside agreed principles | Anything that changes scope, budget, architecture or rules |
| Sprint manager | Runs the wave: intent session, spec drafting with the governor and its hand-in to the engine, watching status, handling exceptions. Code, not the sprint manager, turns tasks into orders | Order of work inside the approved plan | The escalation list |
| Engine | Runs every step in order; waits; retries within limits | Nothing: it follows the workflow and the state computed by code | Through gates and alerts |
| Workers | Build or write one step's output | How to do the step inside the brief | By reporting NEEDS_CONTEXT or BLOCKED, or by the "needs the governor" disposition in a revision report |
| Reviewers | Review one artifact against its rubric | Their findings and severities | By marking a finding "needs the governor" |

The architect and the sprint manager share git as their surface. Each reads the other's records. When they disagree, the governor gets one decision request carrying both views.

Each conclusion reached in a chat session is recorded in git by that session. After cutover, chat sessions do not spawn workers or reviewers; any work with a wait or a handoff, including a review of a design note, goes through the engine (normally the light lane).

## 4. The flow

### 4a. Work comes in

1. Work enters as a GitHub issue, through one of three issue forms: a change (anything not yet planned), an order (created by code from a feature's `tasks.md`), or a new feature. The governor, the architect or the sprint manager may open a change or a feature.
2. **Routing rule** (total: every issue lands in exactly one lane), applied in this order:
   - **Full:** it adds a feature, or changes the architecture (new building blocks, interfaces between them, data contracts, dependencies or hosting).
   - **Light:** it changes only notes, records, docs, or config with no runtime effect.
   - **Normal:** everything else. That covers an order under an approved plan, and any runtime change that adds no feature and changes no architecture: a bug fix, a dependency repair, a small behaviour change. For a change, the issue itself is its one-task plan, linked to the feature it touches when one exists.
   The rule also weighs the size and whether anything irreversible is touched; its thresholds are set in the Wave 1.5 plan.
3. Code records the lane on the issue and re-checks it against the actual changes when the pull request opens. On a mismatch upward, the run stops, code moves the issue up a lane, restarts it there, and posts a status comment. Moving down a lane needs the governor's yes.
4. Labelling the issue ready starts the engine through Actions.

### 4b. Normal lane (an order under an approved plan, or an unplanned runtime change)

| # | Step | Who | Output, and how it is checked |
|---|------|-----|-------------------------------|
| 1 | Generate the brief from the order's tasks (or, for a change, from the issue): references to the spec, plan, acceptance criteria and reviewer rubric that apply; a named model | Code | Brief file, validated against its format |
| 2 | Build: tests first, then code | Worker | Commits on the order's branch; a report file. Code validates the report (one repair, then strict), checks there is a new commit and that tests pass |
| 3 | Open the pull request; enable GitHub auto-merge | Code, with the App token | Pull request linked to the issue; checks start |
| 4 | Review | Reviewers (cross-family seats from the roster for this stage and lane) | Verdict files: findings, plus two verdicts at code review (meets the spec; quality). For orders of a feature that has held-back scenarios, a fresh evaluator runs them here (section 4e) and reports failures as findings |
| 5 | Converge | Code | First, any finding a reviewer marked "needs the governor" stops the loop at once, before any revision: code opens a decision (section 7); the governor's lock is attached to the finding, and the loop resumes at step 6 with the lock as input. The author cannot remove the mark. Then: open blocker or major findings with confidence 80 or more block. Low-confidence blockers are listed for the governor but do not block |
| 6 | Revise (if blocked) | Worker | Revision report: each finding fixed, rejected with reason, or given the disposition "needs the governor" when the author cannot settle it (a field of the revision report, separate from the reviewer's flag); findings with a governor's lock follow the lock. Code treats the author's disposition as a stop, as in step 5. Back to step 4, which checks only the fix against open findings. At most three rounds; then a gate |
| 7 | Accept | Code | Posts the review-accepted status (only the trusted job can) |
| 8 | Merge | GitHub | Auto-merge when the rules hold (section 8) |
| 9 | Close out | Code | Issue closed, status comment, step records complete. For an order of a feature, the feature's progress is updated; the feature stays open until accepted (section 4d) |

### 4c. Light lane (notes, records, docs, config with no runtime effect)

The same as the normal lane, minus the plan and tasks behind it: the brief is generated from the issue itself. One worker; a cross-family review; merge on green checks and an accepted review. The irreversible-harm guards apply unchanged.

### 4d. Full lane (a new feature, or anything that changes the architecture)

1. **Intent** (chat): the sprint manager runs the intent session with the governor. Output: the feature's intent file, with the value statement and the estimate range.
2. **Spec** (chat): the sprint manager drafts the spec with the governor, including examples per requirement and any open decisions the spec depends on (each written as a decision request). Thinking happens in chat; the drafts are local files.
3. **Hand-in** (code): the sprint manager runs the factory's small command on the drafts. Code validates the intent and spec files, commits them to the feature's branch, pushes, and moves the feature issue to "spec ready". That event starts the engine for the feature. Nothing drafted in chat reaches the engine any other way.
4. **Spec review** (engine): the review loop over the spec, with product seats. Gate: the governor approves the spec.
5. **Plan** (engine): a worker writes the plan, including the architecture and buy-vs-build section, the one-level design and the phasing. A separate worker derives the held-back acceptance scenarios from the written requirements (section 4e).
6. **Plan review** (engine): Spec Kit's consistency check first, then the review loop with architecture seats. The architect reads the result before the gate. Gate: the governor approves the architecture and phasing.
7. **Tasks** (engine): a worker writes the tasks with estimates, each task naming any open decision it depends on; the consistency check runs again.
8. **Readiness** (code, fails closed): before any order is created, code lists the feature's decision requests without a lock. If any task depends on one, the engine pauses at a gate until it is locked; tasks that depend on none may proceed only if the plan says they are independent. Then code turns the tasks into orders.
9. Each order then runs the normal lane.
10. **Re-align after an architecture lock** (engine): when a lock arrives that changes the architecture (its request is marked as affecting architecture), orders not yet started are held. A worker amends the plan and tasks in place, the consistency check runs, and a review round checks only the amendment. Held orders are then re-created or released. Orders already merged are left alone unless the amendment names them, in which case code opens corrective orders.
11. **Feature acceptance** (gate, after the feature's orders merge and before the feature ships): the governor sees the spec, acceptance criteria, test names and the held-back results, not diffs. **Accept:** the feature is closed and may ship. **Reject:** the feature stays open and the governor's reasons become a decision lock. A worker maps each reason to amended or new tasks under the approved plan (if a reason changes the architecture, step 10 runs instead); the consistency check runs; code creates linked corrective orders from those tasks; acceptance is asked again when they merge.

### 4e. Held-back acceptance scenarios

- **Derived** by a dedicated worker from the written requirements at plan time; every scenario names the requirement it tests (hide test cases, never requirements).
- **Stored** where builder steps cannot read them: outside the repository the builders check out, readable only by the evaluator's step. A public manifest in the feature folder lists each scenario's name and requirement, without its content, so coverage stays inspectable. The exact store is chosen in the Wave 1.5 plan (section 14); keeping them only out of the brief does not count as held back.
- **Run** by a fresh evaluator during code review of each order that implements the requirements they cover.
- **Reported** as findings in the evaluator's verdict (cause: acceptance), so they enter the same convergence and revision loop. A failing scenario's requirement and the observed behaviour are given to the worker; once a scenario has failed and been shown, it is no longer counted as held back.
- **Results** for the whole feature are shown at feature acceptance.

## 5. Records: one home per fact

| Fact | Home | Written by |
|------|------|------------|
| Work and its state | GitHub Issues (labels: ready, claimed, blocked, done) | Code |
| Run state | Spec Kit's saved state, kept across Actions jobs (exact place set in the Wave 1.5 plan) | Engine |
| Decisions | `bus/decisions/<id>/request.yaml` and `lock.yaml`. A request names its feature and whether it affects scope, content or architecture; tasks name the decisions they depend on | Request: drafted by the engine's agent or a chat session, validated and committed by code. Lock: code, from the governor's answer |
| Feature state (open, accepted, rejected) | The feature's GitHub issue | Code, from the acceptance gate |
| Held-back scenarios | A store builder steps cannot read (section 4e); a public manifest in the feature folder | The dedicated worker drafts; code stores |
| Intent and spec drafts from chat | Local files until the hand-in; then the feature's branch | Chat session drafts; code validates, commits and pushes |
| Reviews | Verdict and revision files in git, one per round (exact path set in the Wave 1.5 plan) | Drafted by the agents, validated and committed by code |
| Code and docs | Git, through pull requests | Workers commit on the order's branch inside their step; code pushes and opens the pull request |
| Step records | Logfire | Code |
| Rules | Rulebooks and role briefs in git | Through the light lane; rule paths need the governor's approval |

The message formats, defined once in Pydantic with generated JSON Schemas: **brief**; **report** (DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, BLOCKED); **review verdict** (each finding carries a "needs the governor" flag that only a reviewer can set and no one but the governor's lock can clear); **revision report** (each finding fixed, rejected with reason, or "needs the governor", the author's own stop signal); **decision request and lock**; **status**. Convergence stops on either signal; only the governor's lock clears the reviewer's flag. Agents draft the payloads of reports, verdicts, revision reports and decision requests in a named file or reply; code validates and persists them. Code itself authors every state change: issue updates, labels, statuses, pushes, pull requests and locks. Code validates at once, gives one repair attempt with the exact errors, then checks strictly. The engine branches only on state computed by code. Fields that code acts on are strict; judgment lives in bounded free text.

## 6. Done means checked

After every agent step, code verifies the outputs: a valid file, a new commit, tests passing. If something is missing, the step is retried with the reason, under the restart rule (section 10). Agents never wait for anything; the engine waits for checks and events. Every step has a time limit.

## 7. When the governor is involved

Only for:
1. a missing decision (scope, budget, architecture or rules);
2. a rule conflict;
3. three turns without resolution (review rounds, fix attempts, debates);
4. a proposed substitute for something the governor locked;
5. cost or effort drift past the threshold (about 30% over the estimate), which triggers a re-plan, not a cut;
6. the gates in section 4 (spec, plan, readiness, feature acceptance);
7. a stall the factory could not recover (section 10).

How a decision works: the engine (or a chat session) writes the request in git: why it is asked, plain labelled options, a recommendation, what happens next. Code opens an issue that mentions the governor and links the request. The governor answers on that issue, or tells a chat session, which posts his words to the issue. Code writes the lock from the answer and the engine resumes. Requests are written in plain language; this is guidance for whoever writes them, and the request's required structure is enforced by its format. Open decisions are listed with their age; anything open more than a week is raised again or closed.

Status comes to the governor without asking: a short comment on the order at milestones and on red, with links to anything he needs to read, plus the scorecard summary.

## 8. Guards and checks

**Blocking (six):** changes reach `main` only by pull request; an accepted cross-family review; tests green; changes stay within the order's files; records match their formats; no secrets.

**Irreversible-harm guards, in every lane:** no direct commits or pushes to `main` (a local guard plus the ruleset); secrets never in git (names declared in the schema, values in Infisical or Actions secrets); no automatic merging outside the rules, deleting work or changing settings; least privilege for agent steps (no GitHub write access, only constrained values in shell commands).

**Rule paths** (constitution, `AGENTS.md`, Cursor rules, role briefs, the workflow, checks, CODEOWNERS) need the governor's approving review, through CODEOWNERS.

**Everything else warns.** New checks start as warnings and become blocking after a clean run. Each check names the rule it enforces and records its fires, overrides and false alarms. A check overridden three times in a wave is fixed or demoted. No check polices another check. A recorded governor bypass exists so a broken check never blocks its own fix. Lab invariants (secrets schema, deploy environment, locked dependencies) stay as they are.

## 9. Measurement

Each step writes one record to Logfire: model, role, work item (wave, feature, order, task), time, tokens and cost. Where the runtime reports no usage (Cursor on individual plans), tokens and cost are estimated by joining the governor's Cursor usage export on time window and model, and labelled estimated.

The scorecard, computed by code and never by a model, at four units (wave, feature, order, task) and split by lane (light, normal, full), so it also shows whether the lanes sort work correctly:
1. acceptance by pass (1, 2, 3, or sent to the governor), by gate, with the cause of each rework;
2. lead time;
3. unattended rate;
4. cost by role (builder, reviewer, orchestrator);
5. estimate against actual, with the drift signal.

Measurement costs at most 1% of factory spend, checked each retro. Numbers are for seeing, not targets. Measurement follows the work; the work is never reshaped for measurement. Each step's model is written in the workflow; a step moves to a cheaper model only when the scorecard shows its first-pass acceptance holds. Spend limits are enforced by the governor on the Cursor dashboard; the factory enforces time caps.

## 10. When things go wrong

| Failure | Response |
|---------|----------|
| A step exceeds its time limit, or its outputs fail the check | Retry from the last checkpoint with the reason. At most two automatic resumes; a third failure stops the run and raises an alert issue |
| A run is killed or the machine restarts | The next pass of the reconciler compares the wanted state with the actual state in git and GitHub and takes the next safe step. Every step is safe to repeat, so nothing is pushed, commented, labelled or opened twice |
| The factory goes quiet | A scheduled watchdog, outside the codespace, finds runs past their deadline or silent, and opens or updates an alert issue that mentions the governor |
| A review does not converge in three rounds | A gate: the governor decides |
| Never automatic | Merging outside the rules, deleting work, changing settings |

The governor's laptop is not part of the machinery: runs continue with it closed.

## 11. How the factory changes itself

- Changes to the factory are work like any other: they come in as issues and run in a lane. A change to rules or the workflow needs the governor's approval.
- The sprint never depends on the change it is building; each change runs on parts already proven. A broken engine change can be bypassed by the governor's recorded override.
- New rules and checks pass the same tests: the failure they prevent, the return for a learning project of about 5 users, the existing rules they overlap, and what they replace. Always-loaded rule files have a size budget: one in, one out.
- Recurring review findings become proposals to role briefs or checks at each retro, never appended to the constitution automatically.
- Each retro reviews the scorecard, the estimates against actuals, the checks' track records, the cast and the rulebooks. A cleanup slot each wave removes drift.

## 12. What Wave 1 left, and where each function went

| Wave 1 piece | Fate | Function now |
|--------------|------|--------------|
| Orders, amendments, claims, handoffs in `bus/orders/` | Removed (archived) | Issues and sub-issues; labels moved by code; pull request plus status comment |
| Review verdicts | Kept, simplified | The review verdict format |
| Decisions in `bus/decisions/` | Kept | The decision request and lock formats; the lock written by code |
| The `factory` command, status board, lifecycle and metrics | Removed | Spec Kit (state, resume), GitHub (queue, pull requests), the scorecard; a small new command for local use, named in the Wave 1.5 plan |
| 29 checks | 10 kept, merged or moved to rulesets; 4 warnings; 15 removed; 1 added (review accepted) | Section 8 |
| 4 editor hooks | 1 kept: the guard against committing or pushing to `main` | Nudges moved to the engine or CI, or dropped |
| Packets (briefs written by hand) | Removed | Briefs generated by code from the order's tasks |
| Spawning workers and reviewers from chat | Removed after cutover | The engine starts workers and reviewers |
| The finish bar (no implementing while governor decisions are open) | Removed as a document | The readiness step (section 4d, step 8), fed by decision requests that name their feature and the tasks that depend on them |
| Plan deltas (re-align the plan after an architecture-changing decision) | Removed as a document | The re-align step (section 4d, step 10) |
| Other process documents (plan-authoring gates, stack posture, review prompts) | Folded into the templates and role briefs in the rulebook rewrite | Templates, role briefs and the consistency check |
| Constitution, `AGENTS.md`, rules, skills, review prompts | Rewritten and pruned | Rulebooks describing only this factory; role briefs |
| Factory v2 spec and contracts | Kept as history | This file, the rulebooks and the user's guide |
| The orchestrator's private notes | Moved into git | Role pages and state notes |

## 13. Known gaps (in the backlogs, by choice)

- Cost per step on Cursor is estimated, and only as fresh as the governor's last usage export.
- Messaging connectors for alerts and decisions (WhatsApp, Telegram, Slack).
- An "extra light" lane without review, only if the scorecard shows reviews add nothing for some kinds of change.
- Burn chart, import-layer lint, exemplars.
- Pattern catalog and Semgrep rules; mutation testing; a sealed red-first run.
- The held-back acceptance set starts small.
- Copilot CLI is proven once, not exercised regularly.
- GitHub secret-scanning merge protection depends on the plan's entitlement (unverified).

## 14. Left to the Wave 1.5 plan (deliberately not decided here)

- Where run state is kept between Actions jobs (a git branch or an Actions artifact), and how duplicate triggers are made harmless.
- The store for held-back scenarios, within the rule in section 4e (for example a separate private repository readable only by the evaluator's step).
- The routing rule's size and irreversibility thresholds (section 4a).
- The exact path of review records, and the name of the small new command.
- How the governor's answer on a decision issue is read (comment wording or a reaction).
- Whether the normal lane has a separate test-review step before the build finishes, or reviews tests at code review only.
- The reviewer roster per stage and lane; the lane rule's thresholds; time limits, deadlines, watchdog interval and cap multiples.
- How the Cursor usage export reaches the factory (the governor's download, then a script).

## 15. Invariants (must always hold)

1. Agents and chat sessions draft payloads (reports, verdicts, revision reports, decision requests, intent and spec); nothing they draft counts until code has validated and persisted it. Code generates briefs and authors every state change: issue updates, labels, statuses, pushes, pull requests and locks. Workers commit only on their order's branch inside their step.
2. Every review is by another model family; code refuses a seat in the author's family.
3. `main` changes only through a pull request with green checks and an accepted review; rule paths also need the governor.
4. Agents never wait; the engine waits.
5. The governor is reached only through decisions, gates, status and alerts, each in git or GitHub.
6. No fourth turn without the governor.
7. One way of working; one home per fact.
8. Secret values never enter git.
9. The sprint never depends on the change it is building.
10. No order starts while a decision it depends on is open.

## 16. During Wave 1.5 (temporary rules, part of the one way of working)

The sections above describe the end state. Until the build-out finishes, these rules apply, and they are written into the cutover rulebooks so no older way creeps back:
- **Before cutover:** Wave 1's process runs Wave 1.5 (the known-good factory). The new path runs only the probe and the first real order.
- **From cutover, until the light lane is switched on:** light changes run in the normal lane as changes (the issue is the one-task plan). That is more process than they need, never less.
- **From cutover, until the full lane is switched on:** a new feature or architecture change is accepted as an issue and labelled as waiting for the full lane; it is not processed. Wave 1.5's own remaining work is orders under its approved plan, so it runs in the normal lane. No Smart Writer V2 feature starts before the full lane is on (register item 70).
- **Switching a lane on** goes through a trial state. Once a lane is built, code picks one eligible issue (a waiting feature for the full lane; a light change for the light lane), marks the lane "trial", and runs that issue end to end through it. If it passes, the lane is switched on, announced in a status comment and recorded in the rulebooks. If it fails, the lane stays off and the issue goes back to waiting (full) or to the normal lane (light); the failure is handled under the restart rule and the three-turn rule.
