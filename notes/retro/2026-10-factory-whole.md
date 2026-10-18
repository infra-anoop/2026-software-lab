# The factory as one whole (end of Wave 1.5)

**Status: draft by the orchestrator (coach and architect), 2026-10-17, for a focused review of logic, consistency and ambiguity (stage 5, step 6).** Nothing here is built yet.

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
| Lane | How much process a piece of work gets: light, normal or full. Chosen when the work comes in |
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
| Factory code | Ours (Python, small) | Validates message formats, writes all records, generates briefs, runs the review controller, the reconciler, the watchdog and the scorecard |
| Role briefs and templates | Ours | What each worker and reviewer role is told; the spec, plan and tasks templates |
| Rulebooks | Ours | The constitution, `AGENTS.md` and the Cursor rules, rewritten to describe only this factory |

## 3. Who does what

| Actor | Does | Decides alone | Escalates to the governor |
|-------|------|---------------|---------------------------|
| Governor | Intent, decisions, rule approvals, acceptance of features | Everything on the escalation list (section 7) | — |
| Architect | Factory design; reviews the architecture of plans before the governor sees them; answers design questions from the sprint manager; runs retros | Design details inside agreed principles | Anything that changes scope, budget, architecture or rules |
| Sprint manager | Runs the wave: intent session, spec drafting with the governor, turning tasks into orders, watching status, handling exceptions | Order of work inside the approved plan | The escalation list |
| Engine | Runs every step in order; waits; retries within limits | Nothing: it follows the workflow and the state computed by code | Through gates and alerts |
| Workers | Build or write one step's output | How to do the step inside the brief | By reporting NEEDS_CONTEXT or BLOCKED |
| Reviewers | Review one artifact against its rubric | Their findings and severities | By marking a finding "needs the governor" |

The architect and the sprint manager share git as their surface. Each reads the other's records. When they disagree, the governor gets one decision request carrying both views.

Each conclusion reached in a chat session is recorded in git by that session. After cutover, chat sessions do not spawn workers or reviewers; any work with a wait or a handoff, including a review of a design note, goes through the engine (normally the light lane).

## 4. The flow

### 4a. Work comes in

1. Work enters as a GitHub issue, through one of two issue forms: an order, or a light change. The governor, the architect or the sprint manager may open one. Orders from a feature are created by code from its `tasks.md`.
2. The lane is set on the issue by a written rule: which files change, the size, and whether anything irreversible is touched. Code re-checks the lane against the actual changes when the pull request opens. Moving up a lane is allowed under the mission test; moving down needs the governor's yes.
3. Labelling the issue ready starts the engine through Actions.

### 4b. Normal lane (an order under an approved plan)

| # | Step | Who | Output, and how it is checked |
|---|------|-----|-------------------------------|
| 1 | Generate the brief from the order's tasks: references to the spec, plan, acceptance criteria and reviewer rubric; a named model | Code | Brief file, validated against its format |
| 2 | Build: tests first, then code | Worker | Commits on the order's branch; a report file. Code validates the report (one repair, then strict), checks there is a new commit and that tests pass |
| 3 | Open the pull request; enable GitHub auto-merge | Code, with the App token | Pull request linked to the issue; checks start |
| 4 | Review | Reviewers (cross-family seats from the roster for this stage and lane) | Verdict files: findings, plus two verdicts at code review (meets the spec; quality). Some acceptance scenarios are held back from the worker and run here by a fresh evaluator |
| 5 | Converge | Code | Open blocker or major findings with confidence 80 or more block. Low-confidence blockers are listed for the governor but do not block. A "needs the governor" mark stops the loop at once |
| 6 | Revise (if blocked) | Worker | Revision report: each finding fixed, rejected with reason, or needs the governor. Back to step 4, which checks only the fix against open findings. At most three rounds; then a gate |
| 7 | Accept | Code | Posts the review-accepted status (only the trusted job can) |
| 8 | Merge | GitHub | Auto-merge when the rules hold (section 8) |
| 9 | Close out | Code | Issue closed, status comment, step records complete |

### 4c. Light lane (notes, records, docs, config with no runtime effect)

The same as the normal lane, minus the plan and tasks behind it: the brief is generated from the issue itself. One worker; a cross-family review; merge on green checks and an accepted review. The irreversible-harm guards apply unchanged.

### 4d. Full lane (a new feature, or anything that changes the architecture)

1. **Intent** (chat): the sprint manager runs the intent session with the governor. Output: the feature's intent file, with the value statement and the estimate range.
2. **Spec** (chat): the sprint manager drafts the spec with the governor, including examples per requirement. Thinking happens in chat.
3. **Spec review** (engine): the review loop over the spec, with product seats. Gate: the governor approves the spec.
4. **Plan** (engine): a worker writes the plan, including the architecture and buy-vs-build section, the one-level design and the phasing. The held-back acceptance scenarios are written here, from the requirements, and kept out of the builders' briefs.
5. **Plan review** (engine): Spec Kit's consistency check first, then the review loop with architecture seats. The architect reads the result before the gate. Gate: the governor approves the architecture and phasing.
6. **Tasks** (engine): a worker writes the tasks with estimates; the consistency check runs again; code turns the tasks into orders.
7. Each order then runs the normal lane.
8. **Feature acceptance** (gate): the governor sees the spec, acceptance criteria and test names, not diffs.

## 5. Records: one home per fact

| Fact | Home | Written by |
|------|------|------------|
| Work and its state | GitHub Issues (labels: ready, claimed, blocked, done) | Code |
| Run state | Spec Kit's saved state, kept across Actions jobs (exact place set in the Wave 1.5 plan) | Engine |
| Decisions | `bus/decisions/<id>/request.yaml` and `lock.yaml` | Request: drafted by the engine's agent or a chat session, validated and committed by code. Lock: code, from the governor's answer |
| Reviews | Verdict and revision files in git, one per round (exact path set in the Wave 1.5 plan) | Drafted by the agents, validated and committed by code |
| Code and docs | Git, through pull requests | Workers commit on the order's branch inside their step; code pushes and opens the pull request |
| Step records | Logfire | Code |
| Rules | Rulebooks and role briefs in git | Through the light lane; rule paths need the governor's approval |

The message formats, defined once in Pydantic with generated JSON Schemas: **brief**; **report** (DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, BLOCKED); **review verdict**; **revision report**; **decision request and lock**; **status**. Agents write a named file or reply. Code validates at once, gives one repair attempt with the exact errors, then checks strictly. The engine branches only on state computed by code. Fields that code acts on are strict; judgment lives in bounded free text.

## 6. Done means checked

After every agent step, code verifies the outputs: a valid file, a new commit, tests passing. If something is missing, the step is retried with the reason, under the restart rule (section 10). Agents never wait for anything; the engine waits for checks and events. Every step has a time limit.

## 7. When the governor is involved

Only for:
1. a missing decision (scope, budget, architecture or rules);
2. a rule conflict;
3. three turns without resolution (review rounds, fix attempts, debates);
4. a proposed substitute for something the governor locked;
5. cost or effort drift past the threshold (about 30% over the estimate), which triggers a re-plan, not a cut;
6. the gates in section 4 (spec, plan, feature acceptance);
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

The scorecard, computed by code and never by a model, at four units (wave, feature, order, task):
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
| The finish bar, plan deltas and similar process documents | Folded into the templates and the workflow's gates, or removed in the rulebook rewrite | Gates and the consistency check |
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
- The exact path of review records, and the name of the small new command.
- How the governor's answer on a decision issue is read (comment wording or a reaction).
- Whether the normal lane has a separate test-review step before the build finishes, or reviews tests at code review only.
- The reviewer roster per stage and lane; the lane rule's thresholds; time limits, deadlines, watchdog interval and cap multiples.
- How the Cursor usage export reaches the factory (the governor's download, then a script).

## 15. Invariants (must always hold)

1. Agents and chat sessions draft files (briefs are the exception: code generates them); nothing they draft counts until code has validated it. Code alone pushes, opens pull requests, moves labels, posts statuses and writes locks.
2. Every review is by another model family; code refuses a seat in the author's family.
3. `main` changes only through a pull request with green checks and an accepted review; rule paths also need the governor.
4. Agents never wait; the engine waits.
5. The governor is reached only through decisions, gates, status and alerts, each in git or GitHub.
6. No fourth turn without the governor.
7. One way of working; one home per fact.
8. Secret values never enter git.
9. The sprint never depends on the change it is building.
