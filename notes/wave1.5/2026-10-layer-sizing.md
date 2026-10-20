# Wave 1.5 sizing, layer by layer

**Status: the sprint manager's estimate (2026-10-19), for the layers in `notes/wave1.5/2026-10-implementation-approach.md`.** The governor read it in chat and asked for it to be recorded ("Go ahead and add the sizing", 21:03 PT). It is an input to the approach note's decision request, not a budget lock: the locked appetite (89 likely, 182 pessimistic agent-hours) stays the ceiling until the governor rules on the approach.

**Re-sized twice the same evening.**
1. For the test-first shape (approach note section 2.6 and section 5 row 10), which replaces the held-back scenarios: Layer 1 plus 2 / 5.25, Layer 4 plus 4.4 / 10, Layer 7 minus 1.15 / 2.75. Net plus 5.25 / 12.5.
2. For the cross-family review's triage (approach note section 9): plus about 10 / 26. Of that, the review's fixes are about 5.2 / 11.5 (safe repeat designed and proved in Layer 3, partly offset in Layer 5; the lab profile; the tests-and-stubs step; stronger example checks). Items restored from the retro's own plan are about 4.75 / 10.75 (the Wave 1 failure inventory, a reason and severity per kept check, each check's track record, the Wave 1 baseline, open decisions by age, the reviewer roster with the competition seat). The Spec Kit fallback is now counted in the pessimistic figures only (0 / 4). The per-step record moved from Layer 6 to Layer 3 at no change. Layers 1 and 8 are unchanged by the review.

All figures are agent-hours, likely / pessimistic, and **uncalibrated**: no Wave 1 baseline exists yet. The first real correction comes after Layer 3, when actual effort is compared with these figures and the remaining layers are re-estimated.

## How to read it

Each task is split the way the governor asked, in test-first order:
- **Design test:** writing the test, or, for install and configure work, defining the run that proves it.
- **Design code:** writing the code, configuration or prose.
- **Test-and-pass loop:** running it and fixing it until it passes. For workflow work every try is a real GitHub Actions run, measured in minutes.
- **Review:** the cross-family review and the fixes it asks for. Listed separately because review rounds were a large share of Wave 1's effort.

Tasks where agents of the new factory do the work (the proof runs, the workflow checker, the Smart Writer V2 change and feature) count as agent-hours too. Governor hours are shown separately. Task names mark what is new from the test-first shape, what grew or is new from the review, and what was restored from the retro plan.

## Summary

| Layer | Design test | Design code | Test-and-pass loop | Review | Total | Governor |
|-------|------:|------:|------:|------:|------:|------:|
| 0. Clean slate | 1 / 2 | 3.5 / 7 | 1.75 / 4.75 | 0.75 / 1.75 | **7 / 15.5** | 1 / 2 |
| 1. Install | 0.75 / 1 | 3 / 6 | 2.25 / 7.25 | 0.5 / 1.5 | **6.5 / 15.75** | 0.5 / 1 |
| 2. Configure, and answer the four unknowns | 0.7 / 2 | 2 / 6 | 3 / 10.25 | 0.5 / 1.5 | **6.2 / 19.75** | 0.5 / 1.5 |
| 3. First end-to-end run, with defaults | 2 / 3.75 | 5.5 / 11.25 | 4.25 / 12 | 1.35 / 3.25 | **13.1 / 30.25** | 0.5 / 1 |
| 4. Policy for changes (normal and light lanes) | 5.35 / 9.75 | 10.35 / 21 | 6.4 / 17.25 | 2.55 / 5.75 | **24.65 / 53.75** | 0.75 / 1.5 |
| 5. Running unattended | 1.6 / 3 | 2.25 / 5 | 2.75 / 7.25 | 0.4 / 1.5 | **7 / 16.75** | 0.5 / 1 |
| 6. Cost and quality numbers | 1.6 / 2.75 | 2.9 / 6.5 | 2 / 5.75 | 0.7 / 1.75 | **7.2 / 16.75** | 0.25 / 0.5 |
| 7. The design path for features (full lane) | 3.6 / 6.5 | 9.75 / 20.5 | 5.75 / 15.75 | 2.15 / 5.25 | **21.25 / 48** | 1.75 / 3.25 |
| 8. Finish | 0.25 / 0.5 | 5 / 11 | 1.1 / 3.25 | 0.7 / 1.5 | **7.05 / 16.25** | 1 / 2 |
| **Layers 0 to 8** | 16.85 / 31.25 | 44.25 / 94.25 | 29.25 / 83.5 | 9.6 / 23.75 | **99.95 / 232.75** | 6.75 / 13.75 |

Across all layers:

| Item | Agent-hours | Governor hours |
|------|------:|------:|
| One-page walkthrough before each of the nine layers | 2.5 / 4.5 | 1.5 / 2.5 |
| Sprint management: task lists per layer, status, re-estimate after Layer 3 | 3 / 6 | – |

**Wave total: about 105.5 likely agent-hours (90 at first sizing, 95.5 after the test-first shape); a realistic bad case of about 170 (likely times 1.6). The 243 sum of every pessimistic figure overstates the bad case, since not every task goes badly at once. Governor: about 8 to 16 hours.**

**Against the locked appetite: likely is about 16.5 over its 89; the realistic bad case stays under its 182; every task going badly is about 61 over.** All six levers below together recover about 6, to about 99. The appetite cannot be met with the whole product shape kept; that is a choice for the governor (see the end of "What the numbers say").

## What the numbers say

- **The first sizing's "about the same as 89" was flattering.** The retro's 89 was its must-have plus should-have band, and five of those should-have items, plus the must-have failure inventory, had dropped out of the layer note without a row; this sizing followed the note, so it left them out too. The cross-family review caught it. Restored, they cost about 4.75 likely, against roughly 6 in the retro's own plan, because Layer 6's usage-export join and the decision pause already carry most of the work.
- **The review's fixes are worth their 5 hours.** Each closes a gap that would have surfaced in the first runs: safe repeat was named but not designed (Wave 1's runs failed exactly there), the shipped formats are prompts that code cannot parse without a fixed profile, the full lane reviewed tests that no step wrote, and a skipped test would have passed the example check. The architect took the smallest fix each time and declined attempt records, leases, a state machine and provenance files; this sizing agrees with those refusals, since each would have rebuilt something the approach removed.
- **Layer 3 is now about 13 hours, so the first real judgement comes after about 33 hours (Layers 0 to 3), not 25.** It still comes well before the retro plan's 50 to 90, and it is now a better judgement: safe repeat and the per-step cost record are proved there, so the re-estimate after Layer 3 uses measured numbers.
- **The test-first shape costs about 5 more hours to build and should cost less to run.** It removes the held-back store and adds a fast build-step environment, a type checker for Smart Writer V2, the example checks, the tests-first verdict with a cause per finding, the way out for a wrong test, examples in the forms, first exemplars and the feature's test review. The saving is per order once the factory runs: requirements arrive unambiguous, tests run inside the step instead of as Actions round trips, and review starts from a verdict on the tests. In Wave 1 one slice's tests went through seven review rounds and others reached four (Wave 1 orchestrator notes); if one round is saved per order, the 5 hours come back within this wave. That saving is expected, not measured, and is not booked; the review and loop columns of Layers 5 to 8 are re-estimated after Layer 4 shows whether it happens.
- **The policy is where the hours are.** Layer 4 (about 25) and Layer 7 (about 21) carry the most, because the product shape asks for a lot of policy: lanes, decisions, the review loop, guards, the test-first checks, approval stops and feature acceptance. That is the part of the factory that is ours by design. Install and configure (Layers 1 and 2) stay under 13.
- **Writing is the biggest block; the loop is where the uncertainty is.** Design code is about 44 likely hours. The test-and-pass loop is about 29 likely, but its pessimistic figure is nearly three times that, because each try in Layers 1 to 3 and 5 is a real Actions run.
- **Governor time is higher than the retro's 3 to 5 hours.** That is the price of judging after every layer and approving nine walkthroughs.
- **The choice the numbers leave for the governor.** Keep the whole shape and set the appetite at about 105 likely (the 182 ceiling holds for the bad case); or take the levers and land near 99; or cut deeper, for instance moving the full lane (Layer 7, about 21) to a later wave, which breaks the retro's one-usable-whole requirement. The sprint manager's view: the bad case is the number that protects the governor, and it still fits under 182, so raising the likely appetite to about 105 is the honest option; take the re-align lever regardless.

## Sprint manager's recommendations (for the architect and the governor)

1. **Re-align after an architecture lock waits for a run that needs it** (2 / 4.25); it was added to the design on paper. Readiness and feature acceptance stay: they are cheap, and acceptance is the governor's gate. *The held-back store, the other half of this recommendation, is resolved: the governor replaced it with the test-first shape. The re-align deferral is now listed as a choice for the governor (approach note section 7).*
2. **Move "one record per agent step" from Layer 6 into Layer 3** (about 1.35 / 3.25), so the re-estimate after Layer 3 uses measured numbers rather than ones rebuilt from the usage export. *Adopted.*
3. **Layer 0 sequencing:** the `main` ruleset must stop requiring the deleted checks at the same moment the deleting change merges; otherwise that change cannot pass. The sprint manager gives the governor the exact settings for that moment. *Adopted.*
4. **Agent runs and Nix (a Layer 1 decision):** booting the full Nix environment in every agent run adds minutes to each try, and tries are where the loop cost lives. Agent runs may need only the agent command-line tools and uv. *Adopted: Layer 1 has a fast build-step environment as a "done when"; keep test and type-checker output short (failures only), since reading output is the inner loop's token cost, and run nearby tests first and the full suite once at the end. The pull request's required check still runs the full suite.*
5. **A ceiling on the Spec Kit risk:** if the current release's loop or approval steps misbehave, the fallback is a short script loop inside the same Actions job, about 2 to 4 hours, not a redesign. *Adopted; counted in Layer 2's pessimistic figure only.*
6. **The way out for a wrong test needs a destination.** When the builder flags an example's test as wrong and stops, the example is spec content the governor approved, so the stop goes to the decision pause. *Adopted (approach note section 2.6 point 7).*
7. **Strict typing on new and changed code only.** No app runs a strict type checker today (Smart Writer and Research Auditor list mypy without settings; Smart Writer V2 has none). Turning strict mode on for whole apps would bury the first change under old errors; a baseline plus strict-on-touched-modules avoids that. Sized in Layer 1.
8. **Keep k at 3 by default and raise it per requirement, not globally.** Each extra example per requirement adds spec-writing time and governor reading time on every feature (ten requirements at k = 3 is thirty examples to approve). Raise k where the recorded causes of rework cluster on misread requirements.
9. **Give the first Actions jobs a coarse time limit in Layer 3.** The inner loop is capped by time, but Layer 5's limits come later; a job-level limit from the first run stops a stuck loop from burning hours. The safe-repeat design in Layer 3 relies on job time limits anyway.
10. **Write the failure inventory from the retro's sources, not from scratch.** The retro records and the Wave 1 orchestrator notes already describe how runs failed; the inventory is a short digest of them, which is why it is sized at 1 / 2.25 against the retro's 2 / 4.

## Levers if the total should be lower

Each trims the product shape slightly; savings are likely / pessimistic agent-hours.

| Lever | Saves | Trade-off |
|-------|------:|-----------|
| Re-align after an architecture lock waits for the first such lock | 2 / 4.25 | Done by hand the first time it happens |
| Scorecard per issue first; four-unit roll-up later | 1 / 2.5 | Wave and feature views come later |
| User's guide folded into the cast page and rulebooks | 1 / 2 | One fewer document to keep true |
| Competition seat waits for a product feature that needs it | 0.95 / 2 | The trial feature is reviewed without a competitor comparison |
| Checks' track record kept by hand at the retro, not computed | 0.75 / 1.75 | A retro chore instead of a number on the scorecard |
| Wave 1 baseline as one wave total, not per order | 0.5 / 1.25 | Less detail to compare the first Wave 1.5 orders against |

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
| One line of reason and severity per kept check (restored from the retro plan) | – | 0.25 / 0.5 | – | – | 0.25 / 0.5 |
| Ruleset strings for the governor, timed with the deleting merge; a test pull request merges | 0.25 / 0.25 | 0.25 / 0.5 | 0.25 / 0.5 | – | 0.75 / 1.25 |
| **Layer total** | 1 / 2 | 3.5 / 7 | 1.75 / 4.75 | 0.75 / 1.75 | **7 / 15.5** |

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
| Contingency: short script loop if Spec Kit's loop or approval steps misbehave (pessimistic only) | 0 / 0.5 | 0 / 2 | 0 / 1 | 0 / 0.5 | 0 / 4 |
| **Layer total** | 0.7 / 2 | 2 / 6 | 3 / 10.25 | 0.5 / 1.5 | **6.2 / 19.75** |

Governor: 0.5 / 1.5 hours.

### Layer 3. First end-to-end run, with defaults

Grew most in the review: safe repeat is now designed and proved here, the per-step record moved in from Layer 6, and the Wave 1 failure inventory is read before the safety design.

| Task | Design test | Design code | Test-and-pass loop | Review | Total |
|------|------:|------:|------:|------:|------:|
| Wave 1 failure inventory: a short document of how Wave 1's runs failed (restored; a must-have in the retro plan) | – | 0.75 / 1.75 | – | 0.25 / 0.5 | 1 / 2.25 |
| Build workflow: labelled issue, brief, implementer, tests, commit and status check, pull request with the App token | 0.5 / 1 | 1.5 / 3 | 1.5 / 4 | 0.25 / 0.75 | 3.75 / 8.75 |
| Review workflow: review package, reviewer on another model family, verdict posted | 0.25 / 0.5 | 1 / 2 | 1 / 2.5 | 0.25 / 0.5 | 2.5 / 5.5 |
| Safe-repeat conventions in both workflows: one run per issue, stage label moved last, read before write (new from review) | 0.5 / 0.75 | 0.75 / 1.5 | 0.5 / 1.5 | 0.25 / 0.5 | 2 / 4.25 |
| Two trials: duplicate trigger runs once; job killed after opening the pull request, re-run, no duplicates (new from review) | 0.25 / 0.5 | 0.25 / 0.5 | 0.5 / 1.5 | 0 / 0.25 | 1 / 2.75 |
| One record per agent step to Logfire (moved from Layer 6) | 0.25 / 0.5 | 0.5 / 1 | 0.5 / 1.5 | 0.1 / 0.25 | 1.35 / 3.25 |
| First real order through it: the workflow checker | 0.25 / 0.5 | 0.5 / 1 | 0.25 / 1 | 0.25 / 0.5 | 1.25 / 3 |
| Gap list from the run | – | 0.25 / 0.5 | – | – | 0.25 / 0.5 |
| **Layer total** | 2 / 3.75 | 5.5 / 11.25 | 4.25 / 12 | 1.35 / 3.25 | **13.1 / 30.25** |

Governor: 0.5 / 1 hours.

### Layer 4. Policy for changes (normal and light lanes)

The largest layer: the test-first shape's guards land here, and the review made the lab profile and the example checks firmer. This is the culture layer: it is ours by design, so it is where building legitimately happens.

| Task | Design test | Design code | Test-and-pass loop | Review | Total |
|------|------:|------:|------:|------:|------:|
| Role briefs and one shared reviewer rules page on Superpowers' prompts | 0.25 / 0.5 | 1 / 2 | 0.5 / 1 | 0.25 / 0.5 | 2 / 4 |
| Lab profile over the unmodified prompts (parseable status reply and verdict, our four slots, own-test changes listed) and its reader; one repair, then fail (grew in review) | 0.75 / 1.5 | 1 / 2 | 0.5 / 1.25 | 0.25 / 0.5 | 2.5 / 5.25 |
| Revision loop: Critical or Important blocks, three rounds then the governor, 'needs the governor' stops | 0.5 / 1 | 1 / 2 | 1 / 2.5 | 0.25 / 0.5 | 2.75 / 6 |
| Reviewer roster for the light and normal lanes as configuration (restored from the retro plan) | 0.1 / 0.25 | 0.25 / 0.5 | 0.1 / 0.25 | – | 0.45 / 1 |
| Cross-family review enforced by code | 0.25 / 0.25 | 0.25 / 0.5 | 0.25 / 0.5 | 0 / 0.25 | 0.75 / 1.5 |
| Review-accepted status from the trusted job; auto-merge; ruleset strings | 0.25 / 0.5 | 0.5 / 1 | 0.5 / 1.5 | 0.25 / 0.5 | 1.5 / 3.5 |
| Decision pause as two workflows (request and issue; answer and lock); open decisions listed by age (age restored from the retro plan) | 0.5 / 0.75 | 1.25 / 2.5 | 0.85 / 2.25 | 0.25 / 0.5 | 2.85 / 6 |
| Routing rule (light or normal; features wait), re-checked at the pull request | 0.5 / 1 | 0.5 / 1 | 0.25 / 1 | 0.25 / 0.5 | 1.5 / 3.5 |
| Guards: least privilege, files named on the issue, no secrets, recorded bypass | 0.5 / 1 | 1 / 2 | 0.5 / 1.5 | 0.25 / 0.5 | 2.25 / 5 |
| Issue forms for a change and a feature | – | 0.25 / 0.5 | 0.1 / 0.25 | – | 0.35 / 0.75 |
| Examples (k per requirement, a setting, how each is proved) in the change form and spec template (test-first shape) | – | 0.35 / 0.75 | 0.1 / 0.25 | – | 0.45 / 1 |
| Example checks: every example proved by a test keeps it, none skipped or expected to fail (grew in review) | 0.75 / 1 | 0.75 / 1.5 | 0.25 / 1 | 0.1 / 0.25 | 1.85 / 3.75 |
| Tests-against-spec verdict first in the code review; cause on each finding (new) | 0.25 / 0.5 | 0.5 / 1 | 0.25 / 0.75 | 0.1 / 0.25 | 1.1 / 2.5 |
| Way out for a wrong example test, routed to a decision (new) | 0.25 / 0.5 | 0.25 / 0.75 | 0.25 / 0.5 | 0 / 0.25 | 0.75 / 2 |
| First exemplars: pick and annotate existing code, one per kind of block (new) | – | 0.5 / 1 | 0 / 0.25 | 0.1 / 0.25 | 0.6 / 1.5 |
| Proof runs: normal change, light change, small Smart Writer V2 change, flawed change sent back, same-family reviewer refused, deleted or skipped example test sent back | 0.5 / 1 | 1 / 2 | 1 / 2.5 | 0.5 / 1 | 3 / 6.5 |
| **Layer total** | 5.35 / 9.75 | 10.35 / 21 | 6.4 / 17.25 | 2.55 / 5.75 | **24.65 / 53.75** |

Governor: 0.75 / 1.5 hours.

### Layer 5. Running unattended

The trials are cheap to write and expensive when they fail; that is the loop range.

| Task | Design test | Design code | Test-and-pass loop | Review | Total |
|------|------:|------:|------:|------:|------:|
| Time limits; re-run at most twice, then an alert issue | 0.25 / 0.5 | 0.5 / 1 | 0.5 / 1.5 | 0.1 / 0.25 | 1.35 / 3.25 |
| Scheduled watchdog that opens or updates an alert issue | 0.25 / 0.5 | 0.5 / 1 | 0.5 / 1 | 0.1 / 0.25 | 1.35 / 2.75 |
| Status comments at milestones and on red | 0.1 / 0.25 | 0.5 / 1 | 0.25 / 0.5 | 0.1 / 0.25 | 0.95 / 2 |
| Safe repeat extended to the later workflows (conventions now built and proved in Layer 3; shrank) | 0.25 / 0.5 | 0.25 / 0.75 | 0.25 / 0.5 | 0 / 0.25 | 0.75 / 2 |
| Done means checked after every agent step | 0.25 / 0.5 | 0.25 / 0.75 | 0.25 / 0.75 | 0 / 0.25 | 0.75 / 2.25 |
| The three deliberate trials: kill a run, laptop closed, decision overnight | 0.5 / 0.75 | 0.25 / 0.5 | 1 / 3 | 0.1 / 0.25 | 1.85 / 4.5 |
| **Layer total** | 1.6 / 3 | 2.25 / 5 | 2.75 / 7.25 | 0.4 / 1.5 | **7 / 16.75** |

Governor: 0.5 / 1 hours.

### Layer 6. Cost and quality numbers

The per-step record moved to Layer 3; the Wave 1 baseline and each check's track record are restored from the retro plan.

| Task | Design test | Design code | Test-and-pass loop | Review | Total |
|------|------:|------:|------:|------:|------:|
| Join the usage export where the runtime reports none, labelled estimated | 0.5 / 0.75 | 0.5 / 1 | 0.5 / 1.5 | 0.1 / 0.25 | 1.6 / 3.5 |
| Wave 1 baseline, once, from git and the usage export (restored from the retro plan) | – | 0.5 / 1.25 | 0.25 / 0.75 | 0.25 / 0.5 | 1 / 2.5 |
| Track record per kept check: how often it fired, from Actions history; whether it was right is judged at the retro (restored) | 0.1 / 0.25 | 0.4 / 0.75 | 0.25 / 0.5 | 0 / 0.25 | 0.75 / 1.75 |
| Scorecard: five numbers at four units, by lane; drift signal; 1% check | 0.75 / 1.5 | 1 / 2.5 | 0.75 / 2 | 0.25 / 0.5 | 2.75 / 6.5 |
| Backfill earlier work from git and the usage export | 0.25 / 0.25 | 0.5 / 1 | 0.25 / 1 | 0.1 / 0.25 | 1.1 / 2.5 |
| **Layer total** | 1.6 / 2.75 | 2.9 / 6.5 | 2 / 5.75 | 0.7 / 1.75 | **7.2 / 16.75** |

Governor: 0.25 / 0.5 hours.

### Layer 7. The design path for features (full lane)

Second-largest. The held-back scenarios are gone; the review added a step that writes the stubs and failing tests the feature's test review judges, and the roster with the competition seat is restored. Re-align remains a candidate to wait for evidence.

| Task | Design test | Design code | Test-and-pass loop | Review | Total |
|------|------:|------:|------:|------:|------:|
| Templates: k examples per requirement (given, when, then), plan names data models and signatures, buy-vs-build, task estimates | – | 1.25 / 2.5 | 0.25 / 0.5 | 0.25 / 0.5 | 1.75 / 3.5 |
| Hand-in command for chat drafts | 0.5 / 0.75 | 0.5 / 1 | 0.25 / 0.75 | 0.1 / 0.25 | 1.35 / 2.75 |
| Stage workflows started by labels: spec review (examples included), plan, plan review, tasks | 0.5 / 1 | 2 / 4 | 1.5 / 4 | 0.25 / 0.75 | 4.25 / 9.75 |
| Tests-and-stubs step after tasks, then its test review; implementation orders start only on acceptance (grew in review) | 0.5 / 1 | 1 / 2 | 1 / 2.5 | 0.2 / 0.5 | 2.7 / 6 |
| Reviewer roster per stage, with the competition seat for product features (restored from the retro plan) | 0.1 / 0.25 | 0.5 / 1 | 0.25 / 0.5 | 0.1 / 0.25 | 0.95 / 2 |
| Readiness check; tasks become issues and sub-issues | 0.5 / 1 | 0.75 / 1.5 | 0.5 / 1.5 | 0.25 / 0.5 | 2 / 4.5 |
| Re-align after an architecture lock (candidate to defer) | 0.5 / 0.75 | 0.75 / 1.5 | 0.5 / 1.5 | 0.25 / 0.5 | 2 / 4.25 |
| Feature acceptance gate showing each example with its test result; a rejection becomes corrective tasks | 0.5 / 0.75 | 1 / 2 | 0.5 / 1.5 | 0.25 / 0.5 | 2.25 / 4.75 |
| Trial: one real Smart Writer V2 feature end to end | 0.5 / 1 | 2 / 5 | 1 / 3 | 0.5 / 1.5 | 4 / 10.5 |
| **Layer total** | 3.6 / 6.5 | 9.75 / 20.5 | 5.75 / 15.75 | 2.15 / 5.25 | **21.25 / 48** |

Governor: 1.75 / 3.25 hours.

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
