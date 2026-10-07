# Factory user's guide

**For:** the governor, the one human who owns this software factory.
**Purpose:** explain the factory's principles and building blocks in plain language, so you can read it in one sitting before the Wave 1 retro.
**Accurate to:** `main` at `a2f782c` (2026-10-07, after PR #32).
**Not a rule source.** Rules live in the constitution (`.specify/memory/constitution.md`, version 1.10.0), `AGENTS.md`, and the factory feature in `specs/001-factory-v2/`. This guide explains those files and adds no rules. Where they disagree or leave a gap, the guide says so in the last section.

Throughout, a **Not built yet** note marks anything that is designed in the spec or plan but not on `main` today, and names the task or wave that owns it.

---

## 1. What the factory is, in one page

The factory is a set of habits, files and checks that lets AI agents do real software work for long stretches without you watching, while staying faithful to what you meant.

**The factory is the product; Smart Writer is the workload.** This framing is locked in the factory spec. Smart Writer V2 is the application that exercises the factory: real work, run through it, to find out whether it holds.

**The measure is intent fidelity over time.** The spec calls it SNR: the longer agents run unattended, the more they drift. The factory captures your intent, including intent you could not write down in advance, and turns it into checks that stop drift mechanically, instead of relying on agents' promises or your attention.

**Git is the bus.** Every instruction, result, review and decision is a file committed to the repository. Agents do not pass context to each other through chat, and they never ask you to copy text from one agent to another. If it is not in git, it did not happen.

**State is derived, never hand-written.** No file holds a "status: done" field. Whether a piece of work is ready, in progress, in review, accepted or merged is computed from git, pull requests and check results. A board (`factory status`) shows the computed view.

**You are a governor, not a router.** You set intent, lock decisions, approve plans, and judge outcomes. You are not asked to relay messages, pick the next task, decide what can run in parallel, or learn task numbers. Agents should ask you only real decisions, in product language, as plain choices. The orchestrator plans, workers build, reviewers from another model family judge, and machine checks decide whether a change may merge (section 3).

---

## 2. Principles

Each principle below says what it is, why it exists, and what it costs. All of them come from the constitution, `AGENTS.md` or the factory spec.

### Spec first

**What.** Non-trivial work follows GitHub Spec Kit's order: specify, clarify, plan, tasks, implement. A plan has two mandatory parts, Architecture and Phased delivery. You approve the spec, then the plan, before any task list is written or any code starts.
**Why.** Work built from chat drifts, and nobody can later check it against anything.
**Cost.** Up-front time. This sprint's charter budgets about a day (Wave 0) for intent, specs, plans and their reviews before any code.

### Failable outcomes and the acceptance catalog

**What.** Success criteria must be statements an implementer can visibly fail ("the board agrees with reality 100% of the time in spot checks"), not moods ("feels polished"); aspirational goals are labelled as such. The detailed checks live in a versioned acceptance catalog beside the spec (`acceptance.md`), and every row marked automatic must point to a real test.
**Why.** You can only stop drift you can detect.
**Cost.** Failable criteria are harder to write, and the catalog must keep step with the tests.

### Tests before code, with an independent test review

**What.** For executable work, the tests that prove a behaviour are written first and must fail ("be red") before the code that makes them pass. Then a separate reviewer judges the tests before implementation starts. This is the **T\* review**.
**Why.** In sprint 01 you caught tests that were "greened" with fake data, or that merely mirrored the code they were meant to judge.
**Cost.** At least one extra review round per slice of work, often two or more.
**Today.** The gate `red-first-proof` checks for red-then-green, but in Wave 1 its evidence comes from a job that runs the pull request's own code, so it is labelled "self-reported" and the reviewer's re-run is the proof of record. **Not built yet:** a sealed run that cannot be faked (task T104), and a gate that blocks code commits before the test review accepts (FR-012b); both are Wave 2.

### Different model families review each other

**What.** A reviewer must come from a different model family than the author. You locked GPT (OpenAI) as the default reviewer family; authors are Claude. The reviewer sees only git artifacts (the order, the diff, check results, intent ids), never the author's conversation, and the verdict records exactly which files it read.
**Why.** A model grading its own work, or reading the author's narrative, tends to agree with it.
**Cost.** Two model providers, and review latency on every order.

### Machine checks over promises: intents and gates

**What.** Every statement of your intent has an id and maps to at least one check, or to an explicit "the governor judges this". Checks that run on pull requests are **gates**. A worker's own account of its work never counts as evidence.
**Why.** Prose rules that nothing enforces get ignored, and the longer the run, the more they are ignored.
**Cost.** Gates are code that must be built, tested and tuned. A wrong gate blocks good work; the override mechanism (section 4) exists for that.

### Cattle, not pets

**What.** Nothing important lives only in a running container or a settings screen. Environments (Nix, `uv` lock files), deploy manifests and CI are declared in git. The GitHub branch rules, which must be set in a screen, are snapshotted to a file that a gate checks.
**Why.** A factory you cannot rebuild from git cannot be trusted or moved to another repository.
**Cost.** Extra steps for anything done in a web console.

### Fidelity to named locks

**What.** When a decision names a specific tool, host, number or label, agents must honour it to the letter by default. If an agent wants to use a substitute (a different host, a thinner version, an "-class" approximation), it must disclose the swap and get your explicit waiver before spawning work, or stop. This is "disclose or stop". A lock can be marked `intent` instead of `letter` when you lock it, meaning the outcome matters more than the exact wording.
**Why.** In sprint 01, named choices were silently replaced by lookalikes.
**Cost.** Some stops that feel pedantic. Wave 1 showed a second cost: when a lock is written as prose, the machine check cannot find its words in the code (retro agenda item 10).

### Progressive human-in-the-loop

**What.** You are asked at high-altitude points: spec debates, plan architecture debates, Open Decisions that belong to you, and test-review findings that would lock in wrong product behaviour. Lower-level questions (test wording, duplicate coverage, nits) are settled by agents under written policy and recorded.
**Why.** Asking you everything recreates the human-as-bottleneck problem. Asking you nothing lets agents author your product.
**Cost.** The line between "product" and "process" is a judgement call, made first by the reviewer's tag and then by the orchestrator's triage. You see those calls after the fact, in review files and pull request bodies.

### The three-review-round rule

**What.** Each artifact under review (a test set, a plan change, a pull request) gets a budget. Rounds 1 and 2 use the normal bar. In round 3 a finding may block only if it states a concrete harm: a security or credential exposure, data loss, behaviour that breaks a locked requirement, or a broken `main`. Everything else is recorded as "Later". After round 3 the orchestrator must accept with recorded Later items, cut scope, or ask you; a fourth round needs your explicit yes. Every blocking finding must also name its root cause, and the fix addresses that cause once.
**Why.** Slice A ran seven test-review rounds before this rule existed (constitution 1.10, PR #23).
**Cost.** Some test cases are deferred. Your refinement, "defer test cases, never bugs", is recorded in the retro agenda but is **not yet in the constitution**; adding it is retro decision 9.

---

## 3. Roles

| Role | Who | Decides | Is not asked to |
|------|-----|---------|-----------------|
| Governor | You | Intent, spec and plan approval, product and architecture debates, your Open Decisions, waivers of named locks, approval of changes to rule files, acceptance of outcomes | Route content between agents, pick the next task, judge parallelism, read task lists to understand a question |
| Orchestrator | The main agent session you chat with | Writes work orders and amendments, spawns workers and reviewers, triages findings, settles process questions, may override a drift gate with a written reason, merges its pull requests on green | Write bulk code itself (only small doc or bookkeeping edits), invent content for your open decisions |
| Worker | A spawned agent, local background or cloud | How to meet one order's definition of done, inside its owned paths; on ambiguity you do not own, the most conservative option, recorded as a deviation | Expand scope, edit outside owned paths, substitute named locks, ask you what is next |
| Reviewer | A spawned agent from another model family | Accept or reject, with findings and severities | Write product code, read the author's conversation |

Two kinds of ambiguity get different treatment (spec FR-010). If a worker meets a question that belongs to you (product or architecture), it stops and you are told as a blocker. Anything else, it takes the most conservative choice and lists it under "deviations" in its handoff.

---

## 4. Constructs: a glossary

Terms are grouped by topic. Each has a short real or realistic example.

### Planning artifacts

- **Feature.** A unit of scope with its own folder, such as `specs/001-factory-v2/`.
- **Spec** (`spec.md`). User stories, requirements, success criteria, Open Decisions, review locks. Example: user story 1, "See at a glance".
- **Plan** (`plan.md`). Architecture, then phased delivery with exit criteria. Example: one `factory` Python package, git as the only data store, two CI workflows.
- **Tasks** (`tasks.md`). The numbered, dependency-ordered work list. Example: task T064, "per-intent PR results".
- **Contracts** (`contracts/`). The frozen interfaces between pieces: command-line behaviour, message shapes, gate registry, editor hooks.

### Time

- **Sprint.** A chartered stretch of work with goals, a scorecard and waves. The charter is `notes/sprints/2026-10-sprint-02.md`.
- **Wave.** A stage inside a sprint with a failable exit. Wave 0 was intent and specs. Wave 1 is the factory skeleton: P1 gates live as required checks, then the gates replayed over the pull requests that built them. Wave 2 is Smart Writer V2 under the gates, alongside the factory's P2 work. Wave 3 is calibration and retro. **Wave 1 is not finished.** No Wave 2 order may be issued until the retro replay is complete (tasks.md, Phase 9).

### Intent

- **Intent** (`intent.yaml`). A stable-id statement of what you want, captured in an intent session before the spec. The factory has 49 (goals, agent behaviour, architecture, process and ops "religion", pre-mortem guardrails, anti-goals), plus four resolved conflicts and scorecard targets. Example: I-G2, "the governor hands off a work order, walks away for the autonomy horizon, and returns to a PR accepted without rework."
- **Check mapping.** Each intent lists its checks by kind (CI gate, hook, lint, schema, metric, review, human), each marked as existing or planned. **Presence** (every intent has at least one mapping) is a 100% rule, enforced by the gate `factory-check-intent`. **Effective coverage** (the share of intents backed by a real, passing, non-human check, or by an explicit governor-judged mapping) must reach 90% by sprint close; until then it is report-only.

### Gates

- **Gate.** A registered check, listed in `scripts/factory/gates.yaml` with an id, the intents it serves, and a class. About 25 gates run on every pull request; four editor hooks mirror some of them. Example: `diff-within-owned-paths` blocks a pull request that touches files outside its order's owned paths.
- **Gate class.** **Drift** gates block, and the orchestrator may override them with a written reason. **Governor-only** gates block, and only you may override them; this class is allowed only for spend, secrets, irreversible operations and your own decisions. Today's governor-only gates guard open governor decisions, override records, the `main` branch rules, and the secrets schema.
- **Override.** A bus record that bypasses one failing gate on one pull request, with a reason. Every override is counted per gate and shown on the board, so a gate that is often overridden is a candidate to tune or remove. Example: Slice C's override of the deferral-word gate, because the flagged lines were verbatim quotes of yours that should not be reworded.
- **Editor hook.** A fast, advisory mirror of a gate inside Cursor. Each hook must have a CI twin, because CI is authoritative and any agent tool must meet the same gates. Example: `shell-guard` refuses `git commit` on `main` and `pip install`.
- **Trusted base.** Gates that judge a pull request run from `main`'s code, never the pull request's own code; the pull request is only data to inspect (your lock D5). So a pull request that changes a gate is judged by the old gate, and its change applies to later pull requests.

### Decisions and locks

- **Open Decision.** A row in the spec's Open Decisions table for something whose shape is decided but whose content is not (for example, "mutation score is a gate" with the threshold open). Each row says who decides (`human` or `agent-policy`), what must not be built before it, and its status: `open`, `locked`, or `waived` (meaning out of this product version, not "do it another day"). Example: D2, locked at 70%.
- **Lock.** A recorded decision. When locking, the row is classed **content-only** (fills in a number or label) or **architecture-affecting** (changes how the system is built), and given a fidelity of **letter** (the default) or **intent**.
- **Plan delta** (`PLAN_DELTA.md`). After an architecture-affecting lock: amend the plan, contracts and tasks in place, record what changed, and check consistency before dependent work. The factory plan has had six rounds, mostly on CI trust and the `main` branch rules.
- **Finish bar** (`FINISH_BAR.md`). A one-time batch before the first implementation: every open decision and parked finish item is listed, and you lock or truly waive each. The factory's reads "Implement unblocked: yes".
- **Deferral-word rule.** In `specs/` and `notes/sprints/`, words that park work (such as "later", "optional", "deferred", "TBD") must sit on the same line as an Open Decision id, a pointer to an existing file or phase, or a governor-judged marker. A gate (`deferral-words-need-od`) enforces it. This guide's folder is outside its scope.

### Work orders and the bus

- **Work order.** An immutable instruction to one worker, in `bus/orders/<order-id>/order.yaml`. It declares a goal, the intents served, **owned paths** (the only files the worker may touch), the gates to run, any named locks with their fidelity, a size within the 60-minute autonomy horizon, and stop conditions. One order is one branch (`wo/<order-id>`), one pull request. The order is the branch's first commit, so issuing work never touches `main`.
- **Bus records.** Every later event is a new file beside the order; nothing is ever edited.
  - **Claim**: a worker takes the order. Refused at three active workers, on owned-path overlap with another active order, or while the order depends on one of your open decisions.
  - **Amendment**: the orchestrator changes part of an order, for example a ruling on a worker's question.
  - **Verdict**: one review round's decision, findings, reviewer family, and the files it read.
  - **Handoff**: what changed, checks run (informational only), deviations, open questions.
  - **Run-complete**: wall time, your interrupts, deviation count, cost estimate.
  - **Override** (see Gates) and **release** (frees a claim when work is abandoned, superseded or blocked).
- **Decision requests, corrections and post-mortems** go in their own small "bus PRs" (`bus/decisions/`, `bus/corrections/`, `bus/postmortems/`). A **correction** records a time you corrected an agent; one is on `main` today.
- **Concurrency cap.** At most three active workers (your lock), because review bandwidth, not compute, is the limit. The cap is enforced at claim time and again at merge; the editor launch hook only logs.

### Reviews

- **Review rounds.** F (spec, product), R (spec, process), P (plan architecture), T (tests), and PR (implementation) reviews. Each round is a verdict file; finding ids carry the prefix of their review.
- **Finding severities.** **Blocker** (must be fixed), **Debate** (a real choice; you adjudicate product debates, agents may settle process ones), **Later** (recorded for the retro, not dropped), **Nit** (small). Each finding is also tagged product, process or architecture.
- **Bootstrap verdict.** Wave 1 built the gates that would govern it, so every Wave 1 pull request carries a reviewer's verdict listing the manual equivalents run (red-first shown by hand, owned paths checked by hand).

### Credentials by role

- **CI's trusted job** holds the only token allowed to post `factory/*` results. **CI's untrusted job** runs the pull request's own tests with read-only access and no secrets.
- **Agents today** push and open pull requests through the Codespace token, which acts as your GitHub account. So the factory cannot yet tell your actions from an agent's: governor-only actions are marked "unverified", and code-owner review on rule files is off, because GitHub will not let you approve a pull request your own account opened.
- **Not built yet: the factory GitHub App** (task T065, a setup step for you, about 20 minutes, plus token wiring in T036b). Agents will then act as the App with one-hour tokens, with no permission to post statuses (your lock D8). The factory switches to "verified" identity mode, and code-owner review on rule files is switched on.

---

## 5. The life of a change

The example is order `wo-20261007-factory-per-intent`, which added per-intent results to the gate report (PR #30). Times are UTC on 2026-10-07. Points where you are involved are marked **[You]**.

1. **Intent, spec, plan, tasks.** Two intents motivate it: I-G2 (hand off and trust the result) and I-P4 (results traceable to intents). The spec requires results per intent (FR-024), the plan places it in the gate runner, and task T064 names the work. **[You]** You stated the intents in the Wave 0 session, approved the spec and plan on 2026-10-03, and locked the finish bar.
2. **Order (16:00).** The orchestrator writes the order as the first commit of branch `wo/wo-20261007-factory-per-intent`: goal, two intents, nine owned paths, ten gates, no named locks, 60 minutes, and four stop conditions (for example, "any change to the posted commit statuses or the workflows"). Before the claim, it drops `tasks.md` from the owned paths because another active order owns that file.
3. **Claim (16:00:30).** A Claude worker claims it: fewer than three workers are active and no owned paths overlap.
4. **Tests first, and a stop.** The worker writes failing tests and stops on three scope questions. At 16:20 the orchestrator answers them in amendment 01: results go in the `factory gate run` report, not a separate GitHub summary file; an intent's gates come from the gate registry; and an intent kept passing only by an override is "overridden", never "held". None was your decision, so you were not interrupted.
5. **Test review, round 1 (16:24).** A GPT reviewer rejects: one Blocker (the test fixture could not tell the right source of intent ids from the wrong one, so a wrong implementation could pass), two Debates and a Nit. The reviewer tagged both Debates "product". The orchestrator judged them to be about a command's output shape, settled them as process, recorded why in the test review file, and listed the call in the pull request for you.
6. **Test review, round 2 (16:35).** Accepted with no findings.
7. **Implementation and PR review (17:00).** The worker makes the tests pass; a second GPT review of the whole change accepts with no findings.
8. **Handoff (17:05) and run-complete (17:06).** Two deviations: `tasks.md` is not ticked (not an owned path), and one owned file needed no change. Wall time 66 minutes, zero interrupts to you.
9. **Pull request and gates.** PR #30's body names the order, the change, the review rounds and local results. CI's trusted job runs `main`'s gates and posts the required `factory/gates` result.
10. **Merge.** **[You]** The change touches gate code, a rule path, so it needs your approval. Until the App exists, that approval is given in chat rather than as a GitHub review. It merged at `a7c6341`.
11. **Bookkeeping.** The orchestrator ticks T064 in `tasks.md` in a later record order.

Across the run you were asked one thing: approval to merge a rule-path change. Everything else was settled from git.

---

## 6. What you will see, and how to read it

### Pull request bodies

Each work pull request links its order (the gate `pr-links-order` requires it). In practice the orchestrator writes a short body: what changed in plain terms, the review rounds and their results, local test and gate results, any calls made on your behalf (such as re-tagged debates), and whether it needs your approval because it touches rule paths.

Read for three things: does the goal match what you wanted; were any of your decisions settled for you; does it need your approval.

### Gate results

- **The required result** is one commit status, `factory/gates`. It is green only if every gate in `main`'s registry ran and passed or was overridden. The `main` branch rules also require `Factory tests` and `Verify Source / verify`. All three are pinned to GitHub Actions as their source, so a result posted by any other account does not count.
- **Per-gate results** (`factory/<gate-id>`) are posted too, for diagnosis. They are not individually required; adding a gate is a code change, not a settings change.
- **The per-intent report** comes from `factory gate run`, in the CI job log and in the command's own output. For each intent, it lists the gates serving it and gives one word:
  - **held**: every gate serving the intent passed;
  - **broken**: at least one gate serving it failed;
  - **overridden**: none failed, but at least one passed only by override.
  An intent that is "overridden" was not proven; it was waved through with a recorded reason.
- **Red-first results** in Wave 1 start with "self-reported:". The reviewer's re-run is the real proof.

### The board: `factory status`

The board is computed on demand from git, pull requests and checks. Its sections are:

- **In flight**: claimed, in review, or accepted and not yet merged, with check progress. An order claimed with no pull request and no commit for more than three times its size is flagged stale.
- **Blocked**: orders whose latest review rejected them, waiting for rework.
- **Waiting on you**: orders blocked on one of your decisions, with the question in plain language.
- **Ready**: issued, unclaimed, not blocked.
- **Overrides per gate**: the counts that tell you which gates to tune.
- **Unverified governor actions**: actions recorded as yours that the factory cannot yet prove were yours (until the App is live).

`factory decisions` lists open decision requests from the bus, and `factory scorecard` computes the scorecard from run records.

### AskQuestion prompts

When the orchestrator needs a decision, it asks in Cursor's AskQuestion tool, in batches. The kickoff skill sets the form: two to four plain options per question, the recommended option first and labelled "(Recommended)", the stakes of each option, and for architecture choices the concrete consequences (services, where secrets live, ops steps, cost). No task ids, finding ids or internal jargon. If you have to open `tasks.md` to understand a question, the constitution counts that as a harness defect.

---

## 7. Limits and known rough edges today

This section reports what the Wave 1 retro agenda found, without proposing fixes.

**Designed but not built.**
- The factory's GitHub App (T065) and its token wiring (T036b, in progress at the time of writing). Until both land, the factory has a single identity, governor-only actions are "unverified", and approval of rule-path changes relies on your chat approval rather than a GitHub approval.
- The retro tooling (`factory retro`, T068–T071) that replays `main`'s gates over every Wave 1 pull request and records remediations. Wave 1 cannot formally close without it, and the formal retro record waits for it.
- The lifecycle reading the non-factory required checks from GitHub (T066a).
- All of Wave 2: architecture lints and the pattern catalog (user story 6); the correction-mining loop with `factory correction new` and `factory sprint close` (user story 7); rules-as-code, constitution 2.0 and lean always-loaded guidance (user story 8); the mutation gate at 70%; the sealed red-first run; and the tests-reviewed-before-code gate.
- Portability to another repository, live settings drift detection, secret scanning and the one-service-per-app check are out of this version (sprint 03, D1).

**Known gaps in what is built.**
- Red-first evidence is self-reported in Wave 1.
- Any workflow in this repository running as GitHub Actions can post any status name, so the source pin alone does not close fake-green results; that gap stays open until it is designed with the App.
- A failed pull request gate run marks `main`'s commit red, through the trusted job's own check.
- `factory claim` checks owned-path overlap against the original order and ignores amendments, which once refused a valid claim and could let a widened order overlap another.
- `factory handoff` ignores recorded overrides while CI honours them.
- The deferral-word gate flags quoted governor text and review records (overridden three times); `red-first-proof` misjudges tests whose subject is not code (overridden once).
- `bus/decisions/` is empty: your decisions so far were asked in chat and recorded in the spec, plan delta and task files, not as bus decision requests.
- Run-complete records exist for only the most recent orders; the Wave 1 start date and order sizes are reconstructed estimates.

**Harness lessons from running the factory on itself.**
- Early briefs omitted the claim, verdict and handoff steps, and look-alike names in GitHub's screens cost you an evening. Both are now covered in the spawn docs (PR #29).
- Agents hung silently, completion notices arrived hours late, agents stalled on permission prompts, the Codespace stops about every 12 hours, and editor disconnects cost re-orientation time.
- Review is the main cost: across the first eight orders, 23 of 37 verdicts were rejections, and the task list grew from 94 to 110 lines.
- Wave 1 missed its three-day target; its five-day limit falls around 2026-10-09.

---

## 8. Where to look

| Question | File |
|----------|------|
| What are the process rules? | `.specify/memory/constitution.md` (canonical), `AGENTS.md` (portable summary) |
| How is the lab's agent process laid out? | `docs/agent-os/README.md` |
| How are workers and reviewers spawned, and what must their briefs say? | `docs/agent-os/SPAWN_WORKER.md`, `docs/agent-os/SPAWN_REVIEWER.md` |
| What did I say I want? | `specs/001-factory-v2/intent.yaml` |
| What is in scope, and which decisions are open or locked? | `specs/001-factory-v2/spec.md` (Open Decisions, Review locks) |
| How is the factory built? | `specs/001-factory-v2/plan.md`, `data-model.md` |
| What changed after the plan was approved? | `specs/001-factory-v2/PLAN_DELTA.md` |
| Exact command, message and gate behaviour | `specs/001-factory-v2/contracts/` |
| What is done and what is open? | `specs/001-factory-v2/tasks.md` |
| Which checks prove each success criterion? | `specs/001-factory-v2/acceptance.md` |
| Was the finish bar locked? | `specs/001-factory-v2/FINISH_BAR.md` |
| Which gates exist, and their class? | `scripts/factory/gates.yaml` |
| Repo settings for the factory (cap, horizon, families, identity mode) | `factory.toml` |
| One order's full story | `bus/orders/<order-id>/` |
| The sprint and its waves | `notes/sprints/2026-10-sprint-02.md` |
| How Wave 1 went | `notes/retro/2026-10-wave1-agenda.md` |
| Locked lab-wide decisions and won't-dos | `notes/architect-backlog.md` |
| The `main` branch rules as last snapshotted | `deploy/github/branch-protection.json` |

---

## Open questions for the governor

These are gaps or tensions between the sources, found while writing. The guide does not resolve them.

1. **"Defer test cases, never bugs."** It is applied in practice but is not in the constitution, whose round-3 rule is phrased as a harm bar. The guide presents it as your refinement, pending retro decision 9.
2. **Re-tagging a reviewer's "product" debate.** In the per-intent order, the reviewer tagged two debates "product" and the orchestrator settled them as process, disclosing the call in the pull request. The constitution says reviewers must tag debates and only product debates need you; it does not say whether the orchestrator may change a reviewer's tag.
3. **When a worker runs `factory handoff`.** The worker spawn doc says to run it when the work is done, but the command refuses while any gate fails, and the review-verdict gates cannot pass until a reviewer has read the handoff. In practice the handoff file comes first, then review, then the command. No source states that order.
4. **Two vocabularies for work units.** The constitution still describes worker units as lab packets (`notes/packets/`) and never mentions work orders or the bus; the factory spec and the spawn docs use orders. Constitution 2.0 (task T088, Wave 2) is the item that reconciles them.
5. **Where your decisions are recorded.** The plan routes governor questions through bus decision requests (`bus/decisions/`, listed by `factory decisions`), but every decision to date was asked in chat and recorded in the spec, plan delta or task files. It is unclear whether bus decision requests are expected in Wave 1, or whether the current practice is accepted.
