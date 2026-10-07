# Wave 1 retro — agenda and prep (Factory v2, sprint 02)

Prepared by the orchestrator on 2026-10-07 for the governor's retro session. It is a discussion document, not the formal retro record. The formal record is `bus/postmortems/wave1-retro.yaml`, written by `factory retro` (T068–T071) once the factory's GitHub App exists (T065). This file does not mark Wave 1 as finished.

Numbers come from git on `main` at `581ed18` unless stated otherwise.

## 1. Where Wave 1 stands

| Measure | Value |
|---------|-------|
| Tasks in `specs/001-factory-v2/tasks.md` | 110 lines: 74 done, 36 open |
| Open in Wave 1 | 13. Three only need ticking: T097 and T101 (work merged; ticked in a record order after the running orders merge) and T066, done apart from code-owner review (after T065). Three are in progress now (T036b, T105, T064). Then T066a, T049, your App setup (T065) and the retro tasks T068–T071 |
| Open in Wave 2 | 23 (US6–US8 and polish). Not started, per your instruction |
| Merged factory PRs | 12 integrated (#7, #8, #9, #20–#25, #27–#29): 11 merge commits plus #24, which landed as a single commit; probe PR #26 closed unmerged, as planned |
| Work orders | 8, all merged: 37 review verdicts, of which 23 were rejections; 35 order amendments; 3 overrides |
| Orders with a run-complete record | 2 of 8 (the first one landed this morning, #28) |
| Plan changes after approval | 6 rounds in `specs/001-factory-v2/PLAN_DELTA.md` |
| Time against the Wave 1 limit (SC-013) | First order 2026-10-03. Target 3 working days (today, 10-07), limit 5. The target will be missed. The limit (about Fri 2026-10-09) is reachable only if the App is set up quickly after T036b lands |

Since the snapshot: #30 merged at `a7c6341` (T064, per-intent results in `factory gate run`): 3 verdicts, 1 rejection, 1 amendment, with a run-complete record. That makes 9 orders and 3 run-complete records; T064 waits for the record order to be ticked.

**Burndown** (done / open at each merge to `main`):

| Merge | Done | Open |
|-------|------|------|
| 10-03 tasks written | 0 | 94 |
| 10-04 #9 contract freeze | 17 | 77 |
| 10-05 #20 Slice A | 39 | 57 |
| 10-05 #22 Slice B | 53 | 45 |
| 10-06 #21 Slice C | 72 | 37 |
| 10-06 #27 summary check | 73 | 37 |
| 10-07 #28 T103 close | 74 | 36 |

The total grew from 94 to 110 because review findings and your decisions added tasks (for example T036b, T094–T107). That growth is itself a G4 topic.

**Review cost per order** (verdicts, rejections first):

| Order | Verdicts | Rejected | Amendments |
|-------|----------|----------|------------|
| P0 contract freeze | 4 | 3 | 3 |
| Slice A | 9 | 6 | 9 |
| Slice B | 6 | 4 | 8 |
| Slice C | 8 | 6 | 9 |
| Status-board check (T102) | 5 | 3 | 5 |
| Summary check (T107) | 3 | 1 | 1 |
| T103 close, brief templates | 1 each | 0 | 0 |

The counts include test reviews, PR reviews and plan reviews. Slice A ran 7 test-review rounds before the round budget (constitution §J, PR #23) existed. Slices B and C each needed a fourth test-review round, which you approved under the budget. Every later order stayed within 3 rounds.

## 2. G6 — every change you approved after the plan was approved

For each change: what changed, why, what it costs, and my recommendation. Plain-language summary first; the record is in the file named.

| # | Date | Change | Why | Cost | Recommendation |
|---|------|--------|-----|------|----------------|
| 1 | 10-05 | **Review loop budget**: three review rounds, then accept-with-Later, cut scope or ask you (constitution 1.10, §J, PR #23) | Slice A ran 7 test-review rounds | Some test cases deferred | **Keep, and codify your refinement**: defer test cases, never bugs (agenda item 9) |
| 2 | 10-05 | **D5 trusted CI**: `main`'s gate code judges every PR; the PR's own code never runs with permission to post results (PLAN_DELTA round 1) | The Slice C review showed a PR could change the gates that judge it | Two workflows instead of one; a gate change only takes effect after merge | **Keep.** It is the trust root of the whole factory |
| 3 | 10-05 | **D6 probe, then pin**: freeze merges, prove the trusted results on a test PR, then require them (round 2) | A required factory result cannot exist before the gates exist | One evening of freeze | **Keep** as the pattern for any future trust-root change |
| 4 | 10-05 | **D7 red-first is "self-reported" in Wave 1**; a sealed run comes in Wave 2 (round 2) | The test job runs the PR's code, so it could fake its own red result | The proof of record is the reviewer's re-run until T104 | **Keep**; T104 stays Wave 2 |
| 5 | 10-05 | **D8 the agents' App cannot post statuses**; only CI does (round 2) | Agents must not be able to mark their own work green | None so far | **Keep** |
| 6 | 10-06 | **A repository ruleset, not classic branch protection** (round 4) | The codespace can read rulesets but not classic protection | The snapshot changed shape | **Keep** |
| 7 | 10-06 | **Code-owner review waits for the App** (round 4; an approved fidelity deviation) | You author the PRs today, and GitHub won't let you approve your own | Rule-path changes rely on your chat approval, not a GitHub approval | **Keep until T065**, then switch it on (already planned in T065) |
| 8 | 10-06 | **Status-board check blocks both cases** (T-ST3 option B) | A job waiting on you with no question recorded would look stuck | None | **Keep** |
| 9 | 10-06 | **D3/D4 locks taken off Slice C's order** (`drop_from_c`, slice-c amendment-09) | The lock check wanted their words in Slice C's code, but Slice C doesn't build them | None; they stay with the reviewer config and T065 | **Keep**; agenda item 10 asks whether lock words should be code tokens from the start |
| 10 | 10-06 | **Merge Slice C after those locks** (PR #21) | Unblock the D6 sequence | — | Done |
| 11 | 10-06 | **One required summary check, `factory/gates`**, instead of 25 per-gate checks (round 5, T107, PR #27) | You judged 25 pinned names "the extreme of hardcoding and very fragile" | One more status per PR | **Keep.** Adding a gate is now a code change, not a settings change |
| 12 | 10-06 | **Close the fake-green gap with the App** (round 5) | Any workflow in this repo running as GitHub Actions can post any status name | Open until T065 | **Keep**; design it with T065 (agenda item 11) |
| 13 | 10-06 | **Merge the summary check during the freeze** (PR #27) | The freeze otherwise had no way to end | A named exception to D6 | Done; the exception is recorded |
| 14 | 10-06 | **Pin `factory/gates` from GitHub Actions** (round 6). Two wrong attempts first: "Factory gates" (a job name that lands on `main`), then "factory gates" (never posted). I also wrongly concluded the pin was impossible and proposed a redesign, which you approved and I withdrew | Look-alike names in the GitHub screen | Your evening | **Keep the result.** The harness fix landed in PR #29: exact strings, which entry to pick, then an API read-back |
| 15 | 10-07 | **Worker and reviewer briefs name the factory's record steps** (PR #29) | Last night's orders failed their checks on missing claim, verdict and handoff records | None | **Keep** |

Changes I decided without asking you, for awareness: realistic shared test fixtures ("decision B", slice-b amendment-07 and slice-c amendment-08); fix-now calls on Slice B and C review findings; the strict-xfail fix for unbuilt commands (PR #21), which ended a `main` deadlock that the plan's wording "stays red" had caused.

## 3. G1 — sprint structure and grooming

**Problem.** Deferred work has no single home. Today it sits in `PLAN_DELTA.md` rows, review files, order amendments and my session notes. The deferral gate forces a pointer, and most pointers say `→ notes/sprints/2026-10-sprint-02.md`, which is a charter, not a backlog.

**Proposal.**
- One backlog file per feature (for example `specs/001-factory-v2/backlog.md`), plus `notes/architect-backlog.md` for lab-wide items. Every Later item gets one row: id, source, domain, size, harm if skipped.
- A grooming step at each sprint start: the orchestrator proposes, you accept, reject or schedule. That makes the step the "place to defer work to".
- The sprint charter names which backlog rows it takes.

## 4. G2 — domain-segregated sprints

Your clarification: "process" means the **harness** (the method and tooling agents follow), distinct from **infrastructure** (OS, Codespaces, GitHub) and **product** (the apps).

**My view: yes, with a cap.** Give each sprint one primary domain, plus a small enabling allowance for the other two (I suggest at most about 20% of tasks), because a product sprint always hits harness gaps. Wave 1 was harness-primary with heavy infrastructure (rulesets, workflows, codespace limits). That mix is why the D5–D8 and pinning work felt unplanned: it was infrastructure work hiding inside a harness sprint. A per-domain system prompt and context pack would follow naturally.

## 5. G3 — when we need purity, and when good enough is fine

**Proposal: let the harm class decide, not taste.**

| Class | Examples | Bar |
|-------|----------|-----|
| Trust root and security | gates, CI trust boundary, identity, secrets | Root cause, test first, independent review, no deferral of bugs |
| Data and decision integrity | bus records, lifecycle, board | Root cause and a regression test; missing extra test cases may defer |
| Tooling ergonomics | messages, CLI polish, docs | Fix when cheap; otherwise a backlog row |
| Product | apps | The product's own spec decides |

The rule from §J and your refinement stays: after three review rounds, defer **test cases**, never **bugs**.

## 6. G4 — backlog numbers and a burndown

Today these numbers needed hand-written git queries (section 1). **Proposal:** a deterministic `factory burndown` command. It counts done and open tasks per feature, sprint and wave from `tasks.md`, joins order states from the bus, and prints the table in section 1 at every merge, with no AI involved. Candidate for the first post-Wave-1 harness order.

## 7. G5 — monitoring and debugging agents

What happened in Wave 1:
- A worker hung silently and a resume also hung; you had to reload the window.
- Completion notices arrived hours late.
- Agents stalled on permission prompts and a sandbox-blocked Nix command form.
- The codespace stops about every 12 hours, and three Cursor disconnects cost re-orientation time.
- Some runs burned tokens on long review loops.

Fixes already in place: push after every green step; never resume a suspected hang, start fresh from the pushed head; no permission requests; the allowed Nix form (all in `docs/agent-os/SPAWN_WORKER.md` since PR #29).

**Proposal still open:** a heartbeat view. For each running agent, show the last pushed commit, transcript growth, wall time and the order's 60-minute budget, and alert after N quiet minutes. That would give a factual answer to "is it stuck or working?". It is also a candidate first post-Wave-1 harness order, next to `factory burndown`. You asked for a 30-minute heartbeat in Wave 1.5; the options and their context cost are in section 17.

## 8. Harness lessons found by running the factory on itself

| Lesson | Status |
|--------|--------|
| Briefs left out the record steps (claim, verdict, handoff) | Fixed, PR #29 |
| Look-alike names in GitHub screens | Fixed in the briefs, PR #29 |
| The orchestrator edited files in the main checkout before branching (caught before any commit), and once captured the Nix banner as a commit id (the merge call failed safely) | Retro: a pre-edit guard for the primary checkout; never capture `nix develop` output |
| `factory handoff` ignores recorded overrides while CI honors them | Backlog: align them |
| Workflows were invalid for a day (job-level `runner` context) and nothing caught it | Fixed with a regression test; backlog: add `actionlint` to CI |
| The plan said "Factory tests stays red" after the ruleset made it required | Fixed (strict xfail); retro: cross-check plan text against settings decisions |
| The deferral gate flags quoted governor text and review records | Overridden 3 times; backlog: skip review records |
| `red-first-proof` misjudges tests whose subject isn't code, and strict xfails | Overridden once; backlog |
| A failed PR gate run marks `main`'s commit red (the trusted job's own check) | Backlog (PLAN_DELTA round 6) |
| Wave 1 start date and `size_minutes` are reconstructed estimates | Correct by hand in the formal retro |
| Bootstrap orders don't name the sprint, so the sprint view showed 0 orders | Decide at retro |
| `factory claim` checks owned-path overlap against the original order and ignores amendments. Today that refused a claim it should have allowed. The harmful direction is an amendment that widens paths: two orders could then edit the same file | Backlog, Slice A owner: claim uses the amended order |
| Four orders this morning all listed `tasks.md`, so the overlap check (correctly) let only one claim | Retro: only orchestrator record orders own `tasks.md`; workers report completion in their handoff |
| 30 remote branches already merged into `581ed18` (`git branch -r --merged 581ed18`) are still kept | Housekeeping order |
| `gates/evidence.py` duplicates four helpers from `red_first.py` | Backlog |
| 10-07: two reviewers finished at about 11:50 PT, but their completion notices never reached the orchestrator. Nothing moved for about 90 minutes, until you asked "still working?" | Interim: the orchestrator checks review branches in git after about 30 quiet minutes. Wave 1.5 candidate: the heartbeat (section 17) |
| 10-07: a command mixing a file append with `git commit` ran inside the sandbox, which ignored the chosen worktree, so it committed on the primary checkout's local `main`. The push was refused, so nothing reached GitHub; the commit was removed | Interim: git commands run on their own, file edits use the editor tools. Wave 1.5 candidate: a guard that refuses commits on the primary checkout |

Earlier Later items (Slice A–C PR reviews: evidence `base_sha` binding, producer checkout origin, Nix fallback output, indexed `secrets['NAME']` detection, git read timeouts and bus blob size bounds, suite-wide timeout policy) are recorded in their review files and orders. They move into the backlog file at grooming (G1).

## 9–12. Decisions to take at the retro

9. **§J wording**: add "after three rounds, defer test cases, never bugs" to the constitution (a rule-path PR for your approval).
10. **Lock words**: should a letter lock's words be code tokens (such as `factory/gates`) from the start, so the lock check can find them? Prose locks caused `drop_from_c`.
11. **Fake-green gap**: post the required `factory/gates` under an identity only `main`'s trusted job can reach, designed with the App (T065).
12. **Build vs adopt** (your item from 10-05): compare AI-SDLC, Spec Kitty and Fishhawk against the factory's features, then adopt, borrow or keep each one, before any Wave 2 order. Prep not started; it needs a research worker once a slot frees up.

## 13–17. Your additions (2026-10-07 afternoon)

### 13. Effort estimates at spec review

**Your item:** spec review should include a definite step that estimates effort for each major phase, in story points or tokens.

**For discussion:**
- **Phases to estimate:** spec and reviews, plan and Architecture review, tasks and the finish bar, tests and test review, implementation and PR review, and the governor's own steps.
- **Unit.** Tokens can be measured, but only from Cursor's usage data, and they vary with the model. Story points are relative and need a reference task. The factory can already measure review rounds and wall time per order from the bus, so a mixed estimate is possible: story points per phase, plus expected review rounds.
- **Closing the loop:** each estimate is compared with the actual at the retro. That needs `factory burndown` (G4) and the effort data from section 14.
- **Where it lives:** the step would go in the spec review prompt and the spec template. Both are rule paths, so this needs a rule-path PR for your approval.

### 14. Where the effort and tokens went in Wave 1, one level down

**Your item:** spend retro time on where effort and tokens went, and why.

**What git can measure:**
- review rounds, rejections and amendments per order (section 1 has the totals);
- wall time between bus records: order to claim, claim to first verdict, and last verdict to merge;
- governor decision points and overrides;
- commits per order.

**What git cannot measure:**
- **Tokens.** The real numbers are in Cursor's usage data, and only you can export them. The stored agent transcripts leave out tool output, which is most of the tokens, so they are only a rough proxy.
- **Time lost** to disconnects, codespace stops and late notices. It can be reconstructed only partly, from gaps between commits.

**Proposed one-level split:**
- orchestration (main session);
- implementation workers;
- reviewers;
- rework after a rejection;
- infrastructure friction (sandbox, permissions, GitHub errors, lost notices);
- governor time.

For each, the session asks why. **Prep:** before the session, the orchestrator fills this split from git and the transcripts, and from your usage export if you can provide it.

### 15. A Wave 1.5 before Wave 2

**Your item:** a short Wave 1.5 between Wave 1 and Wave 2 to get a handle on unpredictability and unreliability. It would implement some of the lessons now, while most items move to future sprints. We decide the list together.

**Candidates from this agenda**, all aimed at how predictable or reliable a run is:
- the heartbeat (section 17);
- `factory burndown` (G4);
- the effort estimate step (section 13);
- `factory claim` using the amended order (section 8);
- `factory handoff` honouring recorded overrides;
- the deferral gate skipping review records;
- the primary-checkout commit guard;
- the `tasks.md` ownership rule;
- the brief rules for review branches and worktrees.

**Test for each candidate:** would it have prevented a stall, a lost hour or an unplanned review round in Wave 1? If not, it goes to the backlog (G1).

**How it fits the process** (decide at the session):
- **(A)** A small new feature, with its own short spec run through the full loop.
- **(B)** A plan-delta round that adds a Wave 1.5 phase to the current feature, reusing its spec and intents.

The orchestrator leans to B, because the items fix this feature's own tooling. Either way, Wave 2 starts only after Wave 1.5 exits.

### 16. A Factory user's guide before the session

**Your item:** a guide you can read and digest before the retro. It should cover the key principles and constructs, not the technical details.

**Status:** order `wo-20261007-factory-users-guide` is writing `docs/factory/USERS_GUIDE.md`. An independent reviewer then checks it against main. It explains the rules; the constitution, `AGENTS.md` and the factory spec stay the sources of the rules.

### 17. Heartbeat for reliable runs

**Your item:** in Wave 1.5, a heartbeat every 30 minutes that checks that the key elements are working and prints a very short summary. You asked about its cost to the context window, and whether there is a better way.

**Options:**
- **(A) The orchestrator wakes itself every 30 minutes** and checks.
  - **Context:** each wake-up adds, by estimate, 2,000 to 4,000 tokens to the orchestrator's context. That is about 50,000 to 100,000 over a 12-hour codespace day, which brings on summarisation sooner.
  - **Tokens:** each wake-up also re-reads the whole context, so it costs far more tokens than the check itself.
  - **Reliability:** it stops when the session hangs, which is exactly when it is needed.
- **(B) A plain `factory heartbeat` command run every 30 minutes by a background shell loop, with no AI.** It checks:
  - codespace time left;
  - GitHub reachable;
  - each active order's last push against its time budget;
  - each running agent's latest activity;
  - CI on open PRs;
  - review branches pushed but not yet picked up (today's 90-minute loss).

  It prints three to five lines and keeps a log. The orchestrator is told only when a line turns red, so the context cost is near zero while everything is fine.
- **(C) A scheduled GitHub workflow.** It runs even when the codespace is off, and could tell you directly that work has stopped. It cannot see local agents, so it complements B rather than replacing it.

**Orchestrator's lean:** B now, and C for "the codespace stopped" once the factory's GitHub App exists.
