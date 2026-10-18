# Top 10 Software Factories: An Analysis of Awesome Software Factories

Oct 10, 2026 · @Anoop Agarwal

## Revised answer for your situation

With Spec Kit fixed, the question is no longer "which factory" but "which vetted execution protocol sits under Spec Kit" — and, after your point 2d, the answer is Spec Kit's own workflow engine as a code-owned control plane, running Superpowers' packet and reviewer designs inside its agent steps, with Anthropic's published patterns as the rationale. All three of your problems (ad-hoc bus, looping reviews, runaway tokens) have explicit, tested answers in those two sources. None of the 181 Spec Kit community extensions is vetted: the catalog marks every one I checked `verified: false`, and all are single-author repos under 100 stars.

**What your clarifications changed.**

- **Spec Kit is fixed,** so OpenSpec, GSD Core and BMAD drop out: they are substitutes that want to own planning.
- **Newness now outweighs stars.** I dropped stars as a score input and judged "maturity" by who stands behind a pattern and whether they published evidence. That moves Anthropic's engineering posts up: they are not repos, so stars never counted them.
- **Orchestrators are deferred.** Multica, Vibe Kanban and OpenHands add parallelism, and parallelism is what multiplies token cost (2c).

**Revised shortlist: what to put under Spec Kit.**

| # | Source | Backed by | Date | Role under Spec Kit | Solves |
| --- | --- | --- | --- | --- | --- |
| 1 | [Superpowers subagent-driven development](https://github.com/obra/superpowers) | Prime Radiant | Oct 2025, revised through Oct 2026 | Prompt and packet designs (briefs, status contract, two-verdict reviewer) run inside Spec Kit workflow steps; its skill-driven loop is replaced by code (see 2d) | 2a, 2b, 2c |
| 2 | [Harness design for long-running apps](https://anthropic.com/engineering/harness-design-long-running-apps) | Anthropic | Mar 2026 | Planner / generator / evaluator; sprint contracts agreed before code | 2b |
| 3 | [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) | Anthropic | Jun 2025, updated Jan 2026 | Delegation contract; artifacts on disk, references in messages; token data | 2a, 2c |
| 4 | Claude Code [code-review plugin](https://github.com/anthropics/claude-code) | Anthropic | Current | PR-level parallel reviewers with a confidence filter | 2b |
| 5 | [Compound Engineering](https://github.com/EveryInc/compound-engineering-plugin) | Every | Oct 2025, active | Turns recurring review findings into written rules | 2b, 2c |
| 6 | [GitHub Agentic Workflows](https://github.com/github/gh-aw) | GitHub | Aug 2025, active | Validated "safe outputs" bus for unattended runs | 2a |

**On a Spec Kit ↔ Superpowers bridge.** Three community bridges exist: [speckit-superpowers-bridge](https://github.com/lihan3238/speckit-superpowers-bridge) (48 stars, v1.3.0, updated Sep 29, verified for Codex and Claude Code only), [superspec](https://github.com/WangX0111/superspec) (78 stars) and [superb](https://github.com/RbBtSn0w/spec-kit-extensions) (33 stars). Treat them as reading, not dependencies; the first is the most current.

## 2a. The bus and the packet

The teams with published evidence converged on no message bus at all: the git repo is the bus, packets are files on disk, and agents pass each other short status lines plus file paths. Anthropic found that letting subagents write results to external storage and hand back lightweight references avoids a "game of telephone" and cuts the tokens spent copying outputs through the coordinator. Superpowers applies the same idea to coding with a fixed set of packet files.

**The vetted packet set (Superpowers subagent-driven development).**

| Packet | Written by | Read by | Contents |
| --- | --- | --- | --- |
| Task brief | Orchestrator (a script extracts it from the plan) | Implementer, reviewer | The task text verbatim; exact values, signatures and test cases live only here |
| Dispatch prompt | Orchestrator | Implementer | Where the task fits, the brief path, interfaces from earlier tasks, rulings on ambiguities, report path and report contract |
| Report file | Implementer | Reviewer, orchestrator | What changed, covering tests, TDD evidence, concerns |
| Status reply | Implementer | Orchestrator | One of DONE, DONE\_WITH\_CONCERNS, NEEDS\_CONTEXT, BLOCKED, plus commits, one-line test summary, concerns; under 15 lines |
| Review package | Script, from recorded base and head commits | Reviewer | Commit list, diff stat and full diff with context, in one file read once |
| Ledger | Orchestrator | Every later session | Append-only progress and rulings, so work resumes after context compaction |

Anthropic's delegation rule fills in the dispatch prompt: every subagent needs an objective, an output format, guidance on tools and sources, and clear task boundaries. Without them, its agents duplicated work and left gaps.

**Mapping onto Spec Kit.** Spec Kit already writes the durable artifacts: constitution, `spec.md`, `plan.md`, `tasks.md`. Make each entry in `tasks.md` the source of a task brief; nothing else in your current bus needs to survive.

**Why not a formal agent protocol.** A2A is the vetted wire protocol for agent-to-agent messages: v1.0 shipped in 2026 under the Linux Foundation, and more than 150 organisations back it. It is designed for opaque agents across vendors and networks that do not share state. Your agents share one repo, so A2A would add envelopes and infrastructure without solving your problem.

## 2b. Reviews that are insightful and converge

Reviews loop when the reviewer and the builder judge against different criteria, so the fix is upstream: agree what "done" means before code exists, give both agents the same rubric, and make every later round smaller than the last. Anthropic and Superpowers each publish a version of this, and they agree.

**Seed the criteria before the build.**

- **Sprint contract (Anthropic, Mar 2026).** Before each chunk of work, the evaluator negotiates explicit, testable success criteria with the generator. In Spec Kit terms, the acceptance criteria in `spec.md` and the rules in your constitution are that contract.
- **Same rubric for both sides.** Anthropic wrote four grading criteria and gave them to the generator and the evaluator alike, and calibrated the evaluator with few-shot examples and scores.
- **A separate, skeptical judge.** Anthropic found that tuning a standalone evaluator to be skeptical was far easier than making a generator grade itself honestly.

**What goes in the reviewer's packet (Superpowers task reviewer).**

- **Inputs:** the task brief, the global constraints that bind the task, the implementer's report, and the review-package diff file.
- **Two verdicts, one pass:** spec compliance (nothing more, nothing less than requested) and code quality.
- **Distrust by default:** the implementer's report is treated as unverified claims, and a stated rationale such as "kept it simple per YAGNI" never lowers a finding's severity.
- **Bounded investigation:** read the diff once; look outside it only to check a named risk, and say which; do not re-run the full suite; never spawn extra reviewers.

**Make each round smaller.**

- **Scoped re-review:** later rounds check only the fix diff against the open findings, on a cheaper model.
- **Escalate instead of repeat:** rounds 1–3 resume the same implementer; rounds 4–5 use a fresh implementer on a stronger model; after that, each open finding is adjudicated and the ruling written to the ledger. This is a decision procedure, not a cap.
- **Filter noise at merge:** Anthropic's code-review plugin runs four parallel reviewers (two for written-rule compliance, one for bugs, one for git history) and drops any finding scored below 80 of 100 confidence.

**Stop the same finding from coming back.** Compound Engineering adds a "capture what you learned" step after review. Put recurring findings into the constitution, so the next brief carries them and the next build avoids them. Anthropic's plugin then checks compliance with those written rules directly.

## 2c. Token-efficient exchange

The biggest token lever is structural, not a cap: Anthropic measured agents at about 4× the tokens of a chat and multi-agent systems at about 15×, and warns that most coding tasks are less parallelizable than research. So use subagents to keep contexts clean, not to run many agents at once, and make every message between them small.

| Practice | What it means in your setup | Source |
| --- | --- | --- |
| Pass references, not payloads | Agents exchange file paths and status lines; diffs and reports stay on disk | Anthropic research system |
| Short return contract | Implementer replies in under 15 lines; detail lives in the report file | Superpowers |
| Name a model on every dispatch | An omitted model silently inherits the session's, usually the most expensive | Superpowers |
| Route by task, not by habit | 1–2 file mechanical task → cheap model; multi-file integration → standard; architecture → most capable; reviewer sized to the diff's risk | Superpowers |
| Count turns, not token price | Cheapest models often take 2–3× the turns on multi-step work, costing more overall; default to mid-tier | Superpowers |
| Batch tiny tasks | Several trivial tasks go to one subagent with one brief and one review | Superpowers |
| Reviewers read once | One diff file, no codebase crawl, no full-suite re-runs, no sub-reviewers | Superpowers |
| Scale effort explicitly | Write rules into the orchestrator: how many agents and tool calls for small, medium, large work | Anthropic research system |
| Choose the cheaper mode when tasks are small | Superpowers' inline mode costs one context plus one final review, versus a fresh context per task and per review | Superpowers |
| Measure before tuning | Anthropic built tracing to see why agents failed; you need per-run cost at minimum | Anthropic research system |

The last row is the gap in vetted tooling. Spec Kit has community cost and token extensions ([token-budget](https://github.com/tinesoft/spec-kit-token-budget), [token-analyzer](https://github.com/coderandhiker/spec-kit-token-analyzer), [cost](https://github.com/Quratulain-bilal/spec-kit-cost)), but each has under 10 stars and one author. Your model provider's usage dashboard is the trustworthy baseline; the list's Uber field report credits model routing and context work with a 34% cost cut, though I did not open that report.

## 2d. Code owns the loop

Under your 2d criterion the top pick changes: Spec Kit now ships its own workflow engine, so the control plane can live in code inside the tool you have already chosen. Superpowers drops from "execution protocol" to "source of prompt and packet designs", because its loop — fix rounds, escalation, model routing — lives in a skill the agent reads and follows, which is exactly the pattern you want to avoid.

**The principle has well-known backing.** HumanLayer's 12-Factor Agents (Dex Horthy) lists "own your control flow", "own your context window" and "small, focused agents" as factors. Super Simple Software Factory states it most plainly: code owns sequencing, retries and acceptance; the agent owns only the work inside one bounded phase. Archon's README makes the same split — deterministic nodes for bash, tests and git; AI only where it adds value. The curated list describes Stripe's Minions the same way: a blueprint of deterministic and agentic nodes.

**Spec Kit workflows, briefly.** `specify workflow run` executes a YAML workflow and persists its state, so a failed or paused run resumes where it stopped. Step types include `shell`, `gate` (human approval), `if`, `switch`, `while`, `do-while`, `fan-out` / `fan-in` with a concurrency limit, and nested `workflow` calls; only `command` and `prompt` steps spend tokens. Each agent step can name its integration and model, and the integrations include `cursor-agent`, `claude`, `codex` and `copilot`. The changelog shows active hardening, including a fix so an interrupted gate prompt cannot approve the gate.

**What moves to code, what keeps tokens.**

| Concern | In code (no tokens) | In an agent step (tokens) |
| --- | --- | --- |
| Phase order and transitions | Workflow steps, `if` / `switch` | — |
| Tests, lint, types, build | `shell` steps; exit code decides | — |
| Fix-round loop and escalation | `do-while` with a round counter; stronger `model` from round 4 | — |
| Task briefs and review packages | Shell scripts extract the task and write the diff file | — |
| Model routing | Per-step `model` field | — |
| Parallelism | `fan-out` with a concurrency cap, `fan-in` | — |
| Human approval | `gate` step | — |
| Writing the code | — | Implementer step, fed one brief |
| Judging spec compliance and quality | — | One reviewer pass using Superpowers' reviewer prompt |
| Adjudicating a stuck finding | — | Strongest model, only when the loop exhausts |

**Ranked for 2d: code-owned orchestration you could use.**

| # | Project | Backer | Stars | Created / last push | Control plane | Agents | Fit with Spec Kit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | [Spec Kit workflows](https://github.com/github/spec-kit) | GitHub | Part of Spec Kit | Active Oct 2026 | YAML, Python step types, resumable state | Spec Kit integrations incl. Cursor | Native |
| 2 | [GitHub Agentic Workflows](https://github.com/github/gh-aw) | GitHub | 5k | Aug 2025 / Oct 11 | Markdown + YAML compiled to Actions | Copilot, Claude Code, Codex, Gemini, Pi | Unattended review and CI gates on PRs |
| 3 | [Archon](https://github.com/coleam00/Archon) | Cole Medin | 24k | Feb 2025 / Oct 10 | YAML DAG: bash nodes, AI loops, approval gates, worktrees | Requires Claude Code | Separate engine wrapping Spec Kit commands |
| 4 | [Roast](https://github.com/Shopify/roast) | Shopify | 1.2k | Apr 2025 / Oct 10 | Ruby DSL mixing `cmd`, `agent`, `chat`, `map` | Claude Code, Pi | A library to script around Spec Kit |
| 5 | [Agentic Orchestrator](https://github.com/doordash-oss/agentic-orchestrator) | DoorDash | 112 | May 2026 / Oct 10 | Deterministic gated phases, desktop app + server | Claude, Codex, OpenCode | Owns planning, so it competes with Spec Kit |
| 6 | [Super Simple Software Factory](https://github.com/disler/super-simple-software-factory) | IndyDevDan | 961 | Aug 2026 / Aug 4 | Python owns the graph, retries and acceptance | Pi via OpenRouter | Reference design to read |

Spec Kit workflows rank first on your criteria: newest, backed by GitHub, and no second tool to adopt. Its weakness is youth — I found no published field report of anyone running a review loop with it. Archon is the most mature standalone alternative, but it requires Claude Code.

## Next steps and open questions

Replace your ad-hoc bus with Superpowers' packet set on one Spec Kit feature, and compare cost and review rounds against your last run. That single experiment tests all three fixes at once.

- [ ] Pick a small feature you already ran with your current setup, so you have a baseline for cost and review rounds.
- [ ] Run Spec Kit through `/speckit-tasks`, then write one Spec Kit workflow that loops over the tasks: a shell step builds each brief, an implementer step writes the code, shell steps run the tests, a reviewer step uses Superpowers' reviewer prompt, and a `do-while` handles fix rounds.
- [ ] Move the feature's acceptance criteria into the constitution or spec as the shared review rubric before implementing.
- [ ] Set an explicit model per role: cheap for mechanical tasks, mid-tier default, strongest only for design and round 4–5 fixes.
- [ ] Record per-run cost and review rounds, and compare with the baseline.
- [ ] After the run, write recurring review findings into the constitution.

**Open questions I could not verify.**

- **Does Spec Kit's per-step model field work with the cursor-agent integration?** The workflow docs show a model field on agent steps; I did not verify that cursor-agent honours it. If Cursor cannot do it, run this experiment in Claude Code, which you have through Vertex AI at work but would need separately for personal use.
- **Does `tasks.md` feed a workflow loop directly?** A shell step has to turn it into a list for a loop or fan-out; I found no published example of this, and no field report of a review loop built on Spec Kit workflows. If the engine proves too young, Archon is the fallback, at the cost of requiring Claude Code.

## Original ranking (general view, before your clarifications)

Start with **Superpowers** for execution discipline and **GitHub Spec Kit** for specs; add an orchestrator only after that pair works on one real project. The list's \~250 entries mostly sit at the orchestration and infrastructure layers, but the projects that most improve code quality for a solo builder are the methodology layer, and those are also the most mature by every measure I could check.

Ranked by weighted score (method and weights in the next section):

1. **Superpowers** (Prime Radiant / Jesse Vincent) — TDD-enforcing skills methodology, 16 harnesses including Cursor. Score 97.
2. **GitHub Spec Kit** (GitHub) — spec → plan → tasks → implement, constitution per project, broadest agent support. Score 84.
3. **Compound Engineering plugin** (Every) — plan/build/review loop that writes down what each change taught. Score 80.
4. **GitHub Agentic Workflows (gh-aw)** (GitHub) — sandboxed agent runs on GitHub Actions with validated outputs. Score 79.
5. **GSD Core** (open-gsd) — discuss/plan/execute/verify/ship loop with fresh-context parallel waves. Score 78.
6. **OpenSpec** (Fission-AI) — lightweight, brownfield-friendly change proposals. Score 77.
7. **OpenHands** — the oldest, most-used self-hosted agent platform; runs any ACP agent. Score 73.
8. **Multica** — a board where agents take issues like teammates; Cursor, Claude Code, Codex and more. Score 73.
9. **Vibe Kanban** (now community-run) — easiest parallel-agent kanban, but its company shut down. Score 72.
10. **BMAD Method** — the oldest persona-based agile method (analyst, PM, architect, scrum master). Score 68.

Two things change how to read this list. First, #2, #5, #6 and #10 are **substitutes** — each wants to own your planning step, so pick one. Second, you vibe-code without reading files, which is the exact setup that sank Dex Horthy's lights-off factory after three months; the gates in #1 and #4 matter more for you than any orchestrator.

## How I analysed the list

I shortlisted 52 of the list's entries, pulled live GitHub data for all 52 on 2026-10-10, read the READMEs of the leaders, and scored each on five weighted criteria. Shortlisting dropped single-purpose infrastructure (sandboxes, worktree tools), paid products, and anything the list marks unmaintained.

**The list mixes layers that are not comparable.** Dex Horthy and Vaibhav Gupta describe a factory as four layers: compute, dev environment, harness, orchestration. The list adds a spec layer and review gates on top. A sandbox and a methodology cannot be ranked against each other, so I ranked across layers by one question: how much does adopting this improve the quality of what a solo builder ships?

| Layer | What it does | Top-10 picks here |
| --- | --- | --- |
| Spec / backlog | Turns intent into specs and tasks | Spec Kit, OpenSpec, GSD Core, BMAD |
| Harness / methodology | Disciplines how one agent works: TDD, review, verify | Superpowers, Compound Engineering |
| Event-to-PR pipeline | Runs agents on issues or events, unattended | gh-aw, OpenHands |
| Orchestration / kanban | Runs many agents in parallel, one place to review | Multica, Vibe Kanban |
| Isolation / compute | Worktrees, containers, microVMs | None ranked; your Codespaces already covers this |

**Criteria and weights (1a + 1b).** Each criterion is scored 1–5, then weighted to a 100-point total.

| Criterion | Weight | What I looked at |
| --- | --- | --- |
| Maturity (1b1) | 25 | Stars and forks on a log scale, organisational backing, docs depth, release discipline |
| Adoptability (1b3) | 25 | Install effort, runs in Cursor / Codespaces, learning curve, cost to run |
| Quality machinery | 20 | Built-in TDD, independent review, verification gates — your stated "guards and adversaries" goal |
| Newness (1b2) | 15 | Created date, last push, whether it reflects 2026 practice |
| Multi-pattern (1b4) | 15 | Number of agent backends; composable vs. one fixed workflow |

**Caveats on the evidence.**

- Stars are a weak signal in this field. Superpowers has 297k stars, more than OpenHands after two extra years; star counts here track social-media reach as much as use. I used them on a log scale and never alone.
- Scores for adoptability and quality machinery are my judgment from READMEs, not hands-on testing. I have not run these tools.
- The curated list itself is young: 3 stars, 5 commits, one curator. It is a good map, but inclusion is not endorsement.
- GitHub's API reports BMAD's and Multica's licenses as unrecognised. BMAD's README says MIT; Multica describes itself as source-available, so check its terms before building on it.

## Scorecard

Superpowers leads by 13 points; places 3 to 6 sit within 3 points of each other, so treat them as a tier, not a strict order. Stars, created and last-push dates are GitHub data as of 2026-10-10; the five criterion scores (1–5) are my judgment. Weights: Maturity 25, Adoptability 25, Quality 20, Newness 15, Multi-pattern 15.

| # | Project | Backer | Stars | Created | Last push | Mat. | Adopt. | Quality | New | Multi | Score /100 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | [Superpowers](https://github.com/obra/superpowers) | Prime Radiant | 297k | Oct 2025 | Oct 10 | 5 | 5 | 5 | 4 | 5 | 97 |
| 2 | [Spec Kit](https://github.com/github/spec-kit) | GitHub | 141k | Aug 2025 | Oct 10 | 5 | 4 | 3 | 4 | 5 | 84 |
| 3 | [Compound Engineering](https://github.com/EveryInc/compound-engineering-plugin) | Every | 25k | Oct 2025 | Oct 10 | 4 | 4 | 4 | 4 | 4 | 80 |
| 4 | [gh-aw](https://github.com/github/gh-aw) | GitHub | 5k | Aug 2025 | Oct 11 | 4 | 3 | 5 | 4 | 4 | 79 |
| 5 | [GSD Core](https://github.com/open-gsd/gsd-core) | open-gsd | 10k | May 2026 | Oct 10 | 3 | 4 | 4 | 5 | 4 | 78 |
| 6 | [OpenSpec](https://github.com/Fission-AI/OpenSpec) | Fission-AI | 72k | Aug 2025 | Oct 9 | 4 | 5 | 2 | 4 | 4 | 77 |
| 7 | [OpenHands](https://github.com/OpenHands/OpenHands) | OpenHands org | 91k | Mar 2024 | Oct 11 | 5 | 3 | 3 | 3 | 4 | 73 |
| 8 | [Multica](https://github.com/multica-ai/multica) | Multica | 52k | Jan 2026 | Oct 11 | 4 | 3 | 2 | 5 | 5 | 73 |
| 9 | [Vibe Kanban](https://github.com/BloopAI/vibe-kanban) | Community (Bloop closed) | 28k | Jun 2025 | Sep 19 | 3 | 5 | 2 | 3 | 5 | 72 |
| 10 | [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD) | BMad Code | 54k | Apr 2025 | Oct 10 | 4 | 3 | 3 | 3 | 4 | 68 |

GSD Core's 10k stars understate it: it is the successor to the archived Get Shit Done (64k stars), so its lineage is more mature than its repo. OpenHands and Multica tie at 73; OpenHands ranks higher because you weighted maturity first.

## The top 10, one by one

### 1. Superpowers — the methodology to learn first

- **What it is:** a skills framework that makes the agent brainstorm a spec with you, write a bite-sized plan, then run one fresh subagent per task with red/green TDD and a two-stage review (spec compliance, then code quality). It deletes code written before its test.
- **Why #1:** the only top-10 entry scoring 5 on both quality machinery and reach. It installs from the official Claude Code, Codex, Cursor and Grok marketplaces, plus 12 other harnesses. Built by Jesse Vincent's company Prime Radiant, which offers commercial support.
- **Cons:** subagent-per-task review is token-hungry; the cheaper `executing-plans` mode trades away per-task review. The maintainers generally do not accept new skill contributions, so its direction is theirs.
- **Second-order:** its brainstorming step overlaps Spec Kit's specify step. If you run both, let Spec Kit own the spec and Superpowers own execution.

### 2. GitHub Spec Kit — the spec layer you already chose

- **What it is:** a constitution once per project, then specify → plan → tasks → implement → converge per feature, plus optional bug-fix and idea-assessment processes.
- **Why #2:** the strongest organisational backing in the list (GitHub), 141k stars, and the broadest agent support (the list says 30+ agents).
- **Cons:** it shapes what gets built, not how carefully. Execution discipline (TDD, independent review) is thin unless you add it.
- **Second-order:** a GitHub-owned spec format is likely to stay compatible with Copilot and Codespaces, which you use at work.

### 3. Compound Engineering plugin — the learning loop

- **What it is:** 36 skills around brainstorm → plan → build → review → capture what you learned. Its `/lfg` command runs plan, execute, simplify, review, browser-test, commit, PR and CI-watch with a bounded repair loop.
- **Why #3:** a company (Every) that uses it daily, 14 agent hosts including Cursor, and a distinctive idea: lessons from each change are written into the repo so the next change starts smarter.
- **Cons:** a full-loop framework like Superpowers; running both doubles the rules your agent juggles. Not yet in Codex's built-in marketplace.
- **Second-order:** the capture step is the cheapest defence against an agent repeating a mistake, which matters more when you do not read the code.

### 4. GitHub Agentic Workflows (gh-aw) — the safest unattended loop

- **What it is:** Markdown plus YAML workflows that compile to locked-down GitHub Actions. Agent jobs are read-only and sandboxed by default; writes go through validated "safe outputs." Engines: Copilot, Claude Code, Codex, Gemini, Pi.
- **Why #4:** a first step into background agents with guardrails designed in, running on GitHub's cloud next to your Codespaces. Pair it with GitHub Next's [Agentics](https://github.com/githubnext/agentics) sample workflows (CI coach, reviewers).
- **Cons:** no Cursor engine; Actions minutes and model calls both cost money; the workflow format is a small DSL to learn.
- **Second-order:** it moves agent runs into an auditable log, which is what a "guard" should look like.

### 5. GSD Core — the newest complete loop

- **What it is:** discuss → plan → execute in parallel waves → verify → ship, each executor starting with a clean 200k-token context. One `npx` installer for Claude Code, Codex, Copilot, Cursor, Windsurf and more.
- **Why #5:** the strongest 2026 design in the spec layer, built around context bloat, the failure mode of long sessions.
- **Cons:** the original GSD was archived and succeeded by this project in May 2026; that handover is a governance risk. Rapid versioning (1.7.0 now) also means churn.
- **Second-order:** a substitute for Spec Kit, not an add-on. Try it if Spec Kit's planning feels heavy.

### 6. OpenSpec — the lightest spec framework

- **What it is:** `specs/` holds current truth, `changes/` holds proposals; each change gets a proposal, specs, design and tasks, driven by commands like `/opsx:propose` and `/opsx:apply`.
- **Why #6:** the easiest to adopt in the list, built for existing code, 72k stars.
- **Cons:** almost no verification of its own; you supply the tests and the review.
- **Second-order:** the best pick if your hobby projects are mostly changes to existing code rather than new builds.

### 7. OpenHands — the mature platform

- **What it is:** a self-hosted control centre for coding agents with a GitHub resolver (label an issue, get a PR). Runs its own agent or Claude Code, Codex, Gemini, Pi, OpenCode, or any ACP agent — locally, in Docker, on VMs or in the cloud.
- **Why #7:** the oldest project in the top 10 (March 2024), 91k stars, steady activity.
- **Cons:** a platform, not a method; it adds infrastructure before it adds quality.
- **Second-order:** a good choice when you want agents running while your laptop is off, without committing to GitHub Actions.

### 8. Multica — the board where agents are teammates

- **What it is:** assign an issue to an agent as you would a colleague; it reports progress and hands back for review. Supports Claude Code, Codex, Cursor, Copilot, Kimi, OpenCode, with per-run cost analytics.
- **Why #8:** newest of the top 10 (January 2026), 52k stars, and the closest match to a human-in-the-loop light factory.
- **Cons:** source-available rather than standard open source; 1,850 open issues signal fast growth and rough edges. You run its server.
- **Second-order:** per-run cost tracking serves your dollar- and token-efficiency goal better than any other orchestrator here.

### 9. Vibe Kanban — the easiest parallel agents

- **What it is:** a kanban board where each card runs an agent in its own worktree, with built-in diff review and PR creation. Nine backends including Cursor and Copilot.
- **Why #9:** the gentlest way to feel what parallel agents are like.
- **Cons:** Bloop, the company behind it, shut down; it is community-maintained and last pushed September 19. Maturity risk is real.
- **Second-order:** fine for learning; do not build long-term habits on it.

### 10. BMAD Method — the original agile-agent method

- **What it is:** planning agents (analyst, PM, architect) write PRDs and architecture, a scrum-master agent writes stories, implementation agents build them. Add-ons include BMad Loop (unattended epics) and a Test Architect.
- **Why #10:** the oldest method in the top 10 (April 2025), large community, right-sized planning paths.
- **Cons:** the most ceremony per change; its persona model reflects 2025 thinking more than 2026 harness design.
- **Second-order:** worth reading even if you never adopt it — its role split explains why newer frameworks separate planning from building.

## Notable exclusions

Several of the list's most-starred projects missed the top 10 because they bind you to one agent, aim at lights-off operation, or are slowing down. Gas Town and Symphony are the two worth studying anyway.

| Project | Stars | Why it is not in the top 10 |
| --- | --- | --- |
| [gstack](https://github.com/garrytan/gstack) | 136k | Garry Tan's personal Claude Code setup; requires Claude Code, so it is one religion, and you prefer Cursor |
| [Paperclip](https://github.com/paperclipai/paperclip) | 100k | Aims at "zero-human companies" — the dark-factory end; 5,877 open issues |
| [Ruflo (Claude Flow)](https://github.com/ruvnet/ruflo) | 74k | Swarm-first and heavy; single maintainer; 1,057 open issues |
| [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) | 40k | Claude Code only |
| [Gas Town](https://github.com/gastownhall/gastown) + [Beads](https://github.com/gastownhall/beads) | 18k + 28k | Scored 59: the reference design for running 20–30 agents, but the steepest learning curve and highest running cost. Study it; adopt later |
| [OpenAI Symphony](https://github.com/openai/symphony) | 28k | Scored 64: OpenAI calls it an engineering preview for trusted environments. Read the spec for the "tracker as control plane" idea |
| [Claude Task Master](https://github.com/eyaltoledano/claude-task-master) | 28k | Last push April 2026; momentum has moved to spec frameworks |
| [snarktank/ralph](https://github.com/snarktank/ralph) | 22k | Marked unmaintained. Learn the Ralph loop from Anthropic's official ralph-wiggum Claude Code plugin instead |
| [Claude Code PM (ccpm)](https://github.com/automazeio/ccpm) | 8k | Claude Code only; last push March 2026 |
| [Mastra Factory](https://github.com/mastra-ai/softwarefactory-template) | 54 | Promising, with Mastra's own field results, but in beta only since September 2026 |

Paid products (Factory.ai, Devin, Warp, Augment Cosmos) were out of scope; the list marks them 💰 and most cannot be self-hosted.

## Adoption path for your setup

Climb one layer at a time and move up only when the gate is met; every stage runs in Cursor with Opus 5.5 inside Codespaces, so nothing forces a tool switch. The order follows the field reports' common lesson: the teams that succeeded kept humans on specs and review (a light factory), while Horthy's no-review factory degraded within three months.

1. **Methodology (weeks 1–3).** Install Superpowers from Cursor's plugin marketplace and build one small project end to end. *Gate:* you can predict what the agent will do next, and test coverage comes for free.
2. **Specs (weeks 3–6).** Add a Spec Kit constitution and run specify → plan → tasks for the next feature; hand the tasks to Superpowers for execution. I have not seen this pairing documented, so if the two fight over planning, keep one. *Gate:* a feature ships from a spec you wrote in under an hour.
3. **Guards and adversaries (weeks 6–8).** Make CI the back pressure: tests, lint and type checks must pass before merge. Add one gh-aw review workflow that uses a different model family from your builder, so the reviewer does not share the builder's blind spots. *Gate:* the reviewer catches something real.
4. **Parallelism (after week 8).** Run 2–3 agents at once with Multica (for its per-run cost view) or Vibe Kanban (for simplicity). *Gate:* parallel output is not lower quality than serial output.
5. **Study, do not run, the dark factory.** Read Gas Town and Symphony as reference designs for what comes next.

Because you rarely read code, make your review step reading the spec and the test names, not the diff. That keeps your judgment upstream, where Addy Osmani's light-factory model puts it, at a fraction of the reading effort.

## Sources

Repository statistics come from the GitHub search API, queried on 2026-10-10 for all 52 shortlisted repos. Project descriptions come from the READMEs below, read the same day. Claims about Horthy, Osmani and the four-layer model are taken from the curated list's own summaries; I did not open those essays or podcasts.

- [Awesome Software Factories](https://github.com/varun1505/awesome-software-factories) — the source list, layers, field reports and essay summaries
- READMEs: [Superpowers](https://github.com/obra/superpowers), [Spec Kit](https://github.com/github/spec-kit), [Compound Engineering](https://github.com/EveryInc/compound-engineering-plugin), [gh-aw](https://github.com/github/gh-aw), [GSD Core](https://github.com/open-gsd/gsd-core), [OpenSpec](https://github.com/Fission-AI/OpenSpec), [OpenHands](https://github.com/OpenHands/OpenHands), [Multica](https://github.com/multica-ai/multica), [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD), [Gas Town](https://github.com/gastownhall/gastown), [gstack](https://github.com/garrytan/gstack), [Symphony](https://github.com/openai/symphony)
- Vibe Kanban's status (company shut down, community-maintained) is from the curated list; its README was not opened.

**Added for the drill-down (read 2026-10-10):**

- Anthropic, [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) — token multiples, delegation contract, filesystem artifacts
- Anthropic, [Harness design for long-running application development](https://anthropic.com/engineering/harness-design-long-running-apps) — read via search excerpts and [InfoQ's coverage](https://infoq.com/news/2026/04/anthropic-three-agent-harness-ai/), not the full post
- Superpowers `skills/subagent-driven-development`: SKILL.md, implementer prompt and task-reviewer prompt, fetched from the [repo](https://github.com/obra/superpowers)
- Claude Code code-review plugin README, `plugins/code-review` in the [claude-code repo](https://github.com/anthropics/claude-code)
- Spec Kit `extensions/catalog.community.json` (181 entries) from the [Spec Kit repo](https://github.com/github/spec-kit); extension stars from the GitHub search API
- Linux Foundation, [A2A passes 150 organizations](https://linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations-lands-in-major-cloud-platforms-and-sees-enterprise-production-use-in-first-year), April 2026

**Added for 2d (read 2026-10-10):**

- Spec Kit `docs/reference/workflows.md`, `docs/reference/integrations.md` and `CHANGELOG.md` in the [Spec Kit repo](https://github.com/github/spec-kit)
- [12-Factor Agents](https://github.com/humanlayer/12-factor-agents) README (HumanLayer)
- READMEs: [Archon](https://github.com/coleam00/Archon), [Roast](https://github.com/Shopify/roast), [Agentic Orchestrator](https://github.com/doordash-oss/agentic-orchestrator), [Super Simple Software Factory](https://github.com/disler/super-simple-software-factory), [Mastra Factory](https://github.com/mastra-ai/softwarefactory-template)
- Stripe's Minions description is from the curated list's summary; I did not open Stripe's post
