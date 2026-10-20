# Wave 1.5 sizing, layer by layer

**Status: the sprint manager's estimate (2026-10-19), for the layers in `notes/wave1.5/2026-10-implementation-approach.md`.** The governor read it in chat and asked for it to be recorded ("Go ahead and add the sizing", 21:03 PT). It is an input to the approach note's decision request, not a budget lock: the locked appetite (89 likely, 182 pessimistic agent-hours) stays the ceiling until the governor rules on the approach.

**Re-sized the same evening** for the test-first shape (approach note section 2.6 and section 5 row 10), which replaces the held-back scenarios. Changed: Layer 1 (plus 2 / 5.25), Layer 4 (plus 4.4 / 10), Layer 7 (minus 1.15 / 2.75). Layers 0, 2, 3, 5, 6 and 8 are unchanged; the in-step tests and type checker in Layer 3's build workflow are part of its existing brief.

All figures are agent-hours, likely / pessimistic, and **uncalibrated**: no Wave 1 baseline exists yet. The first real correction comes after Layer 3, when actual effort is compared with these figures and the remaining layers are re-estimated.

## How to read it

Each task is split the way the governor asked, in test-first order:
- **Design test:** writing the test, or, for install and configure work, defining the run that proves it.
- **Design code:** writing the code, configuration or prose.
- **Test-and-pass loop:** running it and fixing it until it passes. For workflow work every try is a real GitHub Actions run, measured in minutes.
- **Review:** the cross-family review and the fixes it asks for. Listed separately because review rounds were a large share of Wave 1's effort.

Tasks where agents of the new factory do the work (the proof runs, the workflow checker, the Smart Writer V2 change and feature) count as agent-hours too. Governor hours are shown separately.

## Summary

| Layer | Design test | Design code | Test-and-pass loop | Review | Total | Governor |
|-------|------:|------:|------:|------:|------:|------:|
| 0. Clean slate | 1 / 2 | 3.25 / 6.5 | 1.75 / 4.75 | 0.75 / 1.75 | **6.75 / 15** | 1 / 2 |
| 1. Install | 0.75 / 1 | 3 / 6 | 2.25 / 7.25 | 0.5 / 1.5 | **6.5 / 15.75** | 0.5 / 1 |
| 2. Configure, and answer the four unknowns | 0.7 / 1.5 | 2 / 4 | 3 / 9.25 | 0.5 / 1 | **6.2 / 15.75** | 0.5 / 1.5 |
| 3. First end-to-end run, with defaults | 1 / 2 | 3.25 / 6.5 | 2.75 / 7.5 | 0.75 / 1.75 | **7.75 / 17.75** | 0.5 / 1 |
| 4. Policy for changes (normal and light lanes) | 4.75 / 8.75 | 9 / 18.25 | 5.7 / 15.5 | 2.55 / 5.75 | **22 / 48.25** | 0.75 / 1.5 |
| 5. Running unattended | 1.85 / 3.5 | 2.5 / 5.75 | 3 / 8.25 | 0.65 / 1.75 | **8 / 19.25** | 0.5 / 1 |
| 6. Cost and quality numbers | 1.75 / 3 | 2.5 / 5.5 | 2 / 6 | 0.55 / 1.25 | **6.8 / 15.75** | 0.25 / 0.5 |
| 7. The design path for features (full lane) | 3.25 / 5.75 | 8.75 / 18.5 | 5 / 13.75 | 1.95 / 4.75 | **18.95 / 42.75** | 1.75 / 3.25 |
| 8. Finish | 0.25 / 0.5 | 5 / 11 | 1.1 / 3.25 | 0.7 / 1.5 | **7.05 / 16.25** | 1 / 2 |
| **Layers 0 to 8** | 15.3 / 28 | 39.25 / 82 | 26.55 / 75.5 | 8.9 / 21 | **90 / 206.5** | 6.75 / 13.75 |

Across all layers:

| Item | Agent-hours | Governor hours |
|------|------:|------:|
| One-page walkthrough before each of the nine layers | 2.5 / 4.5 | 1.5 / 2.5 |
| Sprint management: task lists per layer, status, re-estimate after Layer 3 | 3 / 6 | – |

**Wave total: about 95.5 likely agent-hours (was 90 before the test-first shape); a realistic bad case of about 155 (likely times 1.6). The 217 sum of every pessimistic figure overstates the bad case, since not every task goes badly at once. Governor: about 8 to 16 hours.**

**The likely figure is now about 6.5 hours over the locked appetite's 89; the bad case stays under its 182.** The three remaining levers below recover about 4.

## What the numbers say

- **The effort is about the same as the retro's plan (89 likely); the risk is much lower.** The layered approach saves roughly 15 to 25 hours on the engine, formats and review machinery, but this bottom-up count also includes review rounds, the factory's own proof runs, the walkthroughs and sprint management, which the retro's estimate did not count separately. The gain is that the governor first judges the factory on real work after about 25 hours (Layers 0 to 3), instead of after 50 to 90, and can stop or redirect after every layer.
- **The test-first shape costs about 5 more hours to build and should cost less to run.** It removes one mechanism (the held-back store, minus 3 / 6.5) and adds several small ones: a fast build-step environment and a type checker for Smart Writer V2 (Layer 1), the example-id check, the tests-first verdict with a cause per finding, the way out for a wrong test, examples in the forms and first exemplars (Layer 4), and the feature's test review before code (Layer 7). The saving is per order once the factory runs: requirements arrive unambiguous, tests run inside the step instead of as Actions round trips, and review starts from a verdict on the tests. In Wave 1 one slice's tests went through seven review rounds and others reached four (Wave 1 orchestrator notes); if one round is saved per order, the 5 hours come back within this wave. That saving is expected, not measured, and is not booked in these figures; the review and loop columns of Layers 5 to 8 are re-estimated after Layer 4 shows whether it happens.
- **The bought parts are cheap; the policy is where the hours are.** Install, configure and the first run (Layers 1 to 3) are about 20 likely hours. The policy for changes (Layer 4, about 22) and the design path (Layer 7, about 19) carry the most, because the product shape asks for a lot of policy: lanes, decisions, the review loop, guards, the test-first checks, approval stops and feature acceptance. That is the part of the factory that is ours by design.
- **Writing is the biggest block; the loop is where the uncertainty is.** Design code is about 39 likely hours. The test-and-pass loop is about 27 likely, but its pessimistic figure is nearly three times that, because each try in Layers 1 to 3 and 5 is a real Actions run.
- **Design test is small on purpose** (about 15 hours): install and configure are proved by running them; only code we write gets tests.
- **Governor time is higher than the retro's 3 to 5 hours.** That is the price of judging after every layer and approving nine walkthroughs.

## Sprint manager's recommendations (for the architect and the governor)

1. **Re-align after an architecture lock waits for a run that needs it** (2 / 4.25); it was added to the design on paper. Readiness and feature acceptance stay: they are cheap, and acceptance is the governor's gate. *The held-back store, the other half of this recommendation, is resolved: the governor replaced it with the test-first shape.*
2. **Move "one record per agent step" from Layer 6 into Layer 3** (about 1.35 / 3.25), so the re-estimate after Layer 3 uses measured numbers rather than ones rebuilt from the usage export.
3. **Layer 0 sequencing:** the `main` ruleset must stop requiring the deleted checks at the same moment the deleting change merges; otherwise that change cannot pass. The sprint manager gives the governor the exact settings for that moment.
4. **Agent runs and Nix (a Layer 1 decision):** booting the full Nix environment in every agent run adds minutes to each try, and tries are where the loop cost lives. Agent runs may need only the agent command-line tools and uv. *Adopted: Layer 1 now has a fast build-step environment as a "done when", and the test-first shape makes it matter more, since tests run inside the step and small orders multiply the per-run start-up cost.*
5. **A ceiling on the Spec Kit risk:** if the current release's loop or approval steps misbehave, the fallback is a short script loop inside the same Actions job, about 2 to 4 hours, not a redesign.
6. **The way out for a wrong test needs a destination.** When the builder flags an example's test as wrong and stops, the example is spec content the governor approved, so the stop goes to the decision pause (the governor amends or keeps the example), not to an idle issue. Sized that way in Layer 4.
7. **Strict typing on new and changed code only.** No app runs a strict type checker today (Smart Writer and Research Auditor list mypy without settings; Smart Writer V2 has none). Turning strict mode on for whole apps would bury the first change under old errors; a baseline plus strict-on-touched-modules avoids that. Sized in Layer 1.
8. **Keep k at 3 by default and raise it per requirement, not globally.** Each extra example per requirement adds spec-writing time and governor reading time on every feature (ten requirements at k = 3 is thirty examples to approve). Raise k where the recorded causes of rework cluster on misread requirements; the cause field in Layer 4 makes that visible.
9. **Give the first Actions jobs a coarse time limit in Layer 3.** The inner loop is capped by time, but Layer 5's limits come later; a job-level limit from the first run stops a stuck loop from burning hours.

## Levers if the total should be lower

Each trims the product shape slightly; savings are likely / pessimistic agent-hours.

| Lever | Saves | Trade-off |
|-------|------:|-----------|
| Re-align after an architecture lock waits for the first such lock | 2 / 4.25 | Done by hand the first time it happens |
| Scorecard per issue first; four-unit roll-up later | 1 / 2.5 | Wave and feature views come later |
| User's guide folded into the cast page and rulebooks | 1 / 2 | One fewer document to keep true |

## Task by task

### Layer 0. Clean slate

Deleting is about 1 to 2 hours. The rest is the pieces we keep, stripping Wave 1 wording from about 20 kept skill, template and rule files, and the interim rulebook.

| Task | Design test | Design code | Test-and-pass loop | Review | Total |
|------|------:|------:|------:|------:|------:|
| Delete Wave 1 machinery (factory package, 25 of 29 checks, 3 hooks, 2 factory CI workflows, old process docs, deprecated skills) and fix what pointed at them | 0.25 / 0.5 | 0.75 / 1.5 | 0.5 / 1.5 | 0.5 / 1 | 2 / 4.5 |
| Archive old orders, packets, constitution and AGENTS.md | – | 0.25 / 0.5 | 0 / 0.25 | – | 0.25 / 0.75 |
| Kept pieces made standalone: decision format check, guard against pushing to main | 0.5 / 1 | 0.5 / 1 | 0.5 / 1 | – | 1.5 / 3 |
| Strip Wave 1 overlays (packets, finish bar, fidelity) from kept Spec Kit skills, templates and Cursor rules | 0 / 0.25 | 0.75 / 1.5 | 0.25 / 0.5 | – | 1 / 2.25 |
| One-page interim rulebook; AGENTS.md as a short map | – | 0.75 / 1.5 | 0.25 / 1 | 0.25 / 0.75 | 1.25 / 3.25 |
| Ruleset strings for the governor; a test pull request merges | 0.25 / 0.25 | 0.25 / 0.5 | 0.25 / 0.5 | – | 0.75 / 1.25 |
| **Layer total** | 1 / 2 | 3.25 / 6.5 | 1.75 / 4.75 | 0.75 / 1.75 | **6.75 / 15** |

Governor: 1 / 2 hours.

### Layer 1. Install

The loop is mostly waiting on real Actions runs; booting Nix in each run costs minutes.

| Task | Design test | Design code | Test-and-pass loop | Review | Total |
|------|------:|------:|------:|------:|------:|
| Spec Kit 1.0.6 to current release, keeping the lab's template overrides | 0.25 / 0.5 | 0.75 / 1.5 | 0.5 / 1.5 | 0.25 / 0.5 | 1.75 / 4 |
| Cursor and Copilot command-line agents in the Nix environment and in Actions | 0.25 / 0.25 | 0.75 / 1.5 | 0.75 / 2.5 | 0.25 / 0.5 | 2 / 4.75 |
| Build-step environment: an agent step runs an app's tests and the type checker in seconds (new: test-first shape) | 0.25 / 0.25 | 0.5 / 1 | 0.5 / 1.5 | 0 / 0.25 | 1.25 / 3 |
| Type checker for Smart Writer V2 (none today): strict on new and changed modules only, with a baseline (new) | – | 0.5 / 1 | 0.25 / 1 | 0 / 0.25 | 0.75 / 2.25 |
| Superpowers packet set copied in at a pinned version | – | 0.25 / 0.5 | 0 / 0.25 | – | 0.25 / 0.75 |
| GitHub App: refresh the existing setup steps; check its permissions once created | – | 0.25 / 0.5 | 0.25 / 0.5 | – | 0.5 / 1 |
| **Layer total** | 0.75 / 1 | 3 / 6 | 2.25 / 7.25 | 0.5 / 1.5 | **6.5 / 15.75** |

Governor: 0.5 / 1 hours.

### Layer 2. Configure, and answer the four unknowns

Widest range relative to its size: each unknown is a real unattended run that either works quickly or needs several tries.

| Task | Design test | Design code | Test-and-pass loop | Review | Total |
|------|------:|------:|------:|------:|------:|
| Secrets, permissions, labels, first issue form, model per step | – | 0.5 / 1 | 0.25 / 0.75 | – | 0.75 / 1.75 |
| Unknown 1: Spec Kit step runs the Cursor agent unattended in Actions, pinned model | 0.25 / 0.5 | 0.5 / 1 | 1 / 3 | – | 1.75 / 4.5 |
| Unknown 2: the same with the Copilot agent | 0.1 / 0.25 | 0.25 / 0.5 | 0.75 / 2.5 | – | 1.1 / 3.25 |
| Unknown 3: a pull request opened with the App token starts its checks unaided | 0.1 / 0.25 | 0.25 / 0.5 | 0.5 / 1.5 | – | 0.85 / 2.25 |
| Unknown 4: usage per run visible, or joinable from the usage export | 0.25 / 0.5 | 0.25 / 0.5 | 0.5 / 1.5 | – | 1 / 2.5 |
| Record the four results; review | – | 0.25 / 0.5 | – | 0.5 / 1 | 0.75 / 1.5 |
| **Layer total** | 0.7 / 1.5 | 2 / 4 | 3 / 9.25 | 0.5 / 1 | **6.2 / 15.75** |

Governor: 0.5 / 1.5 hours.

### Layer 3. First end-to-end run, with defaults

Includes the factory's own agents building the workflow checker through the new path.

| Task | Design test | Design code | Test-and-pass loop | Review | Total |
|------|------:|------:|------:|------:|------:|
| Build workflow: labelled issue, brief, implementer, tests, commit and status check, pull request with the App token | 0.5 / 1 | 1.5 / 3 | 1.5 / 4 | 0.25 / 0.75 | 3.75 / 8.75 |
| Review workflow: review package, reviewer on another model family, verdict posted | 0.25 / 0.5 | 1 / 2 | 1 / 2.5 | 0.25 / 0.5 | 2.5 / 5.5 |
| First real order through it: the workflow checker | 0.25 / 0.5 | 0.5 / 1 | 0.25 / 1 | 0.25 / 0.5 | 1.25 / 3 |
| Gap list from the run | – | 0.25 / 0.5 | – | – | 0.25 / 0.5 |
| **Layer total** | 1 / 2 | 3.25 / 6.5 | 2.75 / 7.5 | 0.75 / 1.75 | **7.75 / 17.75** |

Governor: 0.5 / 1 hours.

### Layer 4. Policy for changes (normal and light lanes)

Now the largest layer: the test-first shape's guards land here (plus 4.4 / 10). This is the culture layer: it is ours by design, so it is where building legitimately happens.

| Task | Design test | Design code | Test-and-pass loop | Review | Total |
|------|------:|------:|------:|------:|------:|
| Role briefs and one shared reviewer rules page on Superpowers' prompts | 0.25 / 0.5 | 1 / 2 | 0.5 / 1 | 0.25 / 0.5 | 2 / 4 |
| Thin reader for the status reply and the verdict | 0.5 / 1 | 0.5 / 1 | 0.25 / 0.75 | 0.25 / 0.5 | 1.5 / 3.25 |
| Revision loop: Critical or Important blocks, three rounds then the governor, 'needs the governor' stops | 0.5 / 1 | 1 / 2 | 1 / 2.5 | 0.25 / 0.5 | 2.75 / 6 |
| Cross-family review enforced by code | 0.25 / 0.25 | 0.25 / 0.5 | 0.25 / 0.5 | 0 / 0.25 | 0.75 / 1.5 |
| Review-accepted status from the trusted job; auto-merge; ruleset strings | 0.25 / 0.5 | 0.5 / 1 | 0.5 / 1.5 | 0.25 / 0.5 | 1.5 / 3.5 |
| Decision pause as two workflows (request and issue; answer and lock) | 0.5 / 0.75 | 1 / 2 | 0.75 / 2 | 0.25 / 0.5 | 2.5 / 5.25 |
| Routing rule (light or normal; features wait), re-checked at the pull request | 0.5 / 1 | 0.5 / 1 | 0.25 / 1 | 0.25 / 0.5 | 1.5 / 3.5 |
| Guards: least privilege, files named on the issue, no secrets, recorded bypass | 0.5 / 1 | 1 / 2 | 0.5 / 1.5 | 0.25 / 0.5 | 2.25 / 5 |
| Issue forms for a change and a feature | – | 0.25 / 0.5 | 0.1 / 0.25 | – | 0.35 / 0.75 |
| Examples (k per requirement, a setting) in the issue form and spec template (new) | – | 0.25 / 0.5 | 0.1 / 0.25 | – | 0.35 / 0.75 |
| Example-id check: every example keeps its test (new) | 0.5 / 0.75 | 0.5 / 1 | 0.25 / 0.75 | 0.1 / 0.25 | 1.35 / 2.75 |
| Tests-against-spec verdict first in the code review; cause on each finding (new) | 0.25 / 0.5 | 0.5 / 1 | 0.25 / 0.75 | 0.1 / 0.25 | 1.1 / 2.5 |
| Way out for a wrong example test, routed to a decision (new) | 0.25 / 0.5 | 0.25 / 0.75 | 0.25 / 0.5 | 0 / 0.25 | 0.75 / 2 |
| First exemplars: pick and annotate existing code, one per kind of block (new) | – | 0.5 / 1 | 0 / 0.25 | 0.1 / 0.25 | 0.6 / 1.5 |
| Proof runs: normal change, light change, small Smart Writer V2 change, flawed change sent back, same-family reviewer refused, deleted example test sent back | 0.5 / 1 | 1 / 2 | 0.75 / 2 | 0.5 / 1 | 2.75 / 6 |
| **Layer total** | 4.75 / 8.75 | 9 / 18.25 | 5.7 / 15.5 | 2.55 / 5.75 | **22 / 48.25** |

Governor: 0.75 / 1.5 hours.

### Layer 5. Running unattended

The trials are cheap to write and expensive when they fail; that is the loop range.

| Task | Design test | Design code | Test-and-pass loop | Review | Total |
|------|------:|------:|------:|------:|------:|
| Time limits; re-run at most twice, then an alert issue | 0.25 / 0.5 | 0.5 / 1 | 0.5 / 1.5 | 0.1 / 0.25 | 1.35 / 3.25 |
| Scheduled watchdog that opens or updates an alert issue | 0.25 / 0.5 | 0.5 / 1 | 0.5 / 1 | 0.1 / 0.25 | 1.35 / 2.75 |
| Status comments at milestones and on red | 0.1 / 0.25 | 0.5 / 1 | 0.25 / 0.5 | 0.1 / 0.25 | 0.95 / 2 |
| Every step safe to repeat (no double push, comment, label or pull request) | 0.5 / 1 | 0.5 / 1.5 | 0.5 / 1.5 | 0.25 / 0.5 | 1.75 / 4.5 |
| Done means checked after every agent step | 0.25 / 0.5 | 0.25 / 0.75 | 0.25 / 0.75 | 0 / 0.25 | 0.75 / 2.25 |
| The three deliberate trials: kill a run, laptop closed, decision overnight | 0.5 / 0.75 | 0.25 / 0.5 | 1 / 3 | 0.1 / 0.25 | 1.85 / 4.5 |
| **Layer total** | 1.85 / 3.5 | 2.5 / 5.75 | 3 / 8.25 | 0.65 / 1.75 | **8 / 19.25** |

Governor: 0.5 / 1 hours.

### Layer 6. Cost and quality numbers

Recommendation 2 moves the first task into Layer 3 so real numbers exist from the first run.

| Task | Design test | Design code | Test-and-pass loop | Review | Total |
|------|------:|------:|------:|------:|------:|
| One record per agent step to Logfire | 0.25 / 0.5 | 0.5 / 1 | 0.5 / 1.5 | 0.1 / 0.25 | 1.35 / 3.25 |
| Join the usage export where the runtime reports none, labelled estimated | 0.5 / 0.75 | 0.5 / 1 | 0.5 / 1.5 | 0.1 / 0.25 | 1.6 / 3.5 |
| Scorecard: five numbers at four units, by lane; drift signal; 1% check | 0.75 / 1.5 | 1 / 2.5 | 0.75 / 2 | 0.25 / 0.5 | 2.75 / 6.5 |
| Backfill earlier work from git and the usage export | 0.25 / 0.25 | 0.5 / 1 | 0.25 / 1 | 0.1 / 0.25 | 1.1 / 2.5 |
| **Layer total** | 1.75 / 3 | 2.5 / 5.5 | 2 / 6 | 0.55 / 1.25 | **6.8 / 15.75** |

Governor: 0.25 / 0.5 hours.

### Layer 7. The design path for features (full lane)

Now second-largest. The held-back scenarios are gone (minus 3 / 6.5); the feature's test review before code and types in the plan are added. Re-align remains a candidate to wait for evidence (recommendation 1).

| Task | Design test | Design code | Test-and-pass loop | Review | Total |
|------|------:|------:|------:|------:|------:|
| Templates: k examples per requirement (given, when, then), plan names data models and signatures, buy-vs-build, task estimates | – | 1.25 / 2.5 | 0.25 / 0.5 | 0.25 / 0.5 | 1.75 / 3.5 |
| Hand-in command for chat drafts | 0.5 / 0.75 | 0.5 / 1 | 0.25 / 0.75 | 0.1 / 0.25 | 1.35 / 2.75 |
| Stage workflows started by labels: spec review (examples included), plan, plan review, tasks | 0.5 / 1 | 2 / 4 | 1.5 / 4 | 0.25 / 0.75 | 4.25 / 9.75 |
| Feature test review before any code (new) | 0.25 / 0.5 | 0.5 / 1 | 0.5 / 1 | 0.1 / 0.25 | 1.35 / 2.75 |
| Readiness check; tasks become issues and sub-issues | 0.5 / 1 | 0.75 / 1.5 | 0.5 / 1.5 | 0.25 / 0.5 | 2 / 4.5 |
| Re-align after an architecture lock (candidate to defer) | 0.5 / 0.75 | 0.75 / 1.5 | 0.5 / 1.5 | 0.25 / 0.5 | 2 / 4.25 |
| Feature acceptance gate showing each example with its test result; a rejection becomes corrective tasks | 0.5 / 0.75 | 1 / 2 | 0.5 / 1.5 | 0.25 / 0.5 | 2.25 / 4.75 |
| Trial: one real Smart Writer V2 feature end to end | 0.5 / 1 | 2 / 5 | 1 / 3 | 0.5 / 1.5 | 4 / 10.5 |
| **Layer total** | 3.25 / 5.75 | 8.75 / 18.5 | 5 / 13.75 | 1.95 / 4.75 | **18.95 / 42.75** |

Governor: 1.75 / 3.25 hours (includes a quarter hour to read and approve the trial feature's examples).

### Layer 8. Finish

Mostly writing; the loop is the governor's review of the rule-path changes.

| Task | Design test | Design code | Test-and-pass loop | Review | Total |
|------|------:|------:|------:|------:|------:|
| Rulebooks rewritten to what runs, within size budgets | – | 1.5 / 3 | 0.5 / 1.5 | 0.25 / 0.5 | 2.25 / 5 |
| Role pages and the cast page | – | 0.75 / 1.5 | 0.1 / 0.25 | 0.1 / 0.25 | 0.95 / 2 |
| User's guide | – | 1.5 / 3 | 0.25 / 0.5 | 0.25 / 0.5 | 2 / 4 |
| Backlog labels; retro backlog items filed | – | 0.5 / 1.5 | 0 / 0.25 | – | 0.5 / 1.75 |
| Leftover removal; end-state description corrected | – | 0.5 / 1.5 | 0.25 / 0.5 | 0.1 / 0.25 | 0.85 / 2.25 |
| Exit-criteria record | 0.25 / 0.5 | 0.25 / 0.5 | 0 / 0.25 | – | 0.5 / 1.25 |
| **Layer total** | 0.25 / 0.5 | 5 / 11 | 1.1 / 3.25 | 0.7 / 1.5 | **7.05 / 16.25** |

Governor: 1 / 2 hours.
