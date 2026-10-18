# Software factory landscape: the wide list (retro stage 4)

Working file for the off-the-shelf survey agreed in the Wave 1 retro (register items 2, 15, 40, 72 to 75). Step 1 of "widen, discuss, narrow": the governor and the orchestrator widen and discuss here; the first cut and the shortlist come next; a fresh reviewer from a different model family (GPT-5.6 Sol) then surveys the shortlist only.

**Status: survey brief agreed (2026-10-17, 13:43 PT).** See "Survey brief" near the end. Entries in the wide list are as described by their sources unless marked as checked.

Sources:
- [awesome-software-factories](https://github.com/varun1505/awesome-software-factories) (the governor's find; snapshot read 2026-10-17; the main source for the long list);
- the orchestrator's searches on 2026-10-05 and 2026-10-17 (AI-SDLC, Spec Kitty, Fishhawk, StrongDM, GitHub Agent HQ, Cursor cloud agents, agent SDKs).

## Two different scales

- **Levels (autonomy).** Dan Shapiro's five levels: how much the human still does, from "spicy autocomplete" to the "dark factory" where nobody writes or reads the code. Addy Osmani contrasts a **light factory** (human judgment stays upstream, in specs and architecture) with a dark one. We aim at about level 4, a light factory, borrowing one level-5 idea: validate against scenarios rather than review code.
- **Layers (architecture).** What a factory is made of. The orchestrator's ad hoc seven layers (2026-10-17) are replaced by an industry model, per principle P13 (prefer settled practice).

## Layer model adopted for this list

From Vaibhav Gupta and Dex Horthy ("Software Factory Design Patterns", 2026): compute, dev environment, harness, orchestration. Ona's Background Agents summit found the same primitives independently (sandboxes, context, triggers, fleet orchestration, governance). Two layers are added on top because our factory depends on them: the spec layer and gates.

| Layer | What it is | Ours in Wave 1 |
|-------|-----------|----------------|
| Compute and dev environment | Where an agent runs: a laptop, a codespace, a sandbox or cloud VM | Codespace; local Cursor agents |
| Harness | Everything around one agent run: tools, context, rules, hooks, the verify-and-retry loop | Cursor plus our rules, skills and hooks |
| Orchestration (workflow) | The flow across many agent runs: intake, plan, build, review, merge; agents are steps in it | The job queue (orders, claims, handoffs), the `factory` command, and the orchestrator chat session as scheduler |
| Spec layer | Turning intent into specs, plans and tasks | Spec Kit plus the intent session |
| Gates | What checks output before it ships | 25 checks, independent cross-family review |
| Governance and culture | Decisions, rules, roles, what the human owns | Constitution, decisions, the cast |

**Whole factories versus parts.** Some entries are whole factories you install; others are parts for one layer. That is the fork (item 72): restarting means adopting a whole factory; the hybrid means assembling parts around our governance layer.

## Ideas to read (practice, not products)

| Item | Why it matters to us |
|------|---------------------|
| StrongDM, [Software Factory](https://factory.strongdm.ai/) | Scenarios kept outside the codebase as a holdout set; "satisfaction" instead of green tests (item 41) |
| Dan Shapiro, five levels; Addy Osmani, "Software Factories, Light and Dark" | Calibrates ambition: light factory |
| Dex Horthy, "Why Software Factories Fail" | His lights-off factory degraded the codebase in three months; argues for heavier upfront planning with humans reading code |
| Victor Savkin (Nx), "Software factories are a workflow, not a product" | Factories work as custom workflows glued from existing tools rather than bought products |
| Gupta and Horthy, "Software Factory Design Patterns" | The layer model above, and buy-versus-build per layer |
| Noah Mitchem, "Nobody Has Actually Built a Software Factory" | 21 write-ups reviewed: mostly parallel agents on the process the company already had |
| Pieter Levels, "When I see people build a software factory" | The over-engineering critique; a useful check on us |
| Igor Ostrovsky, "Software Factories in September 2026" | Survey of the public write-ups |
| Stripe, "Minions"; Shopify, Roast | Blueprints of deterministic steps with agent steps inside |
| OpenAI, Symphony; Anthropic, harness articles | Vendor reference designs |

## Lead candidate for the orchestration layer: Spec Kit workflows (governor's pointer, 2026-10-17)

[Spec Kit workflows](https://github.github.com/spec-kit/reference/workflows.html): `specify workflow run` executes YAML workflows of steps: Spec Kit commands, agent prompts, shell commands, human gates, branches, loops, fan-out and fan-in. Runs persist state (`state.json`, `log.jsonl`) and resume from the exact step after a pause or failure. Overlays and slots let a project add, replace or remove steps of an installed workflow without editing it; custom step types are Python packages; `--json` gives machine-readable outcomes; a gate's verdict can be supplied as an input on resume.

**Finding:** this engine is already installed in our repo. Spec Kit 1.0.6, initialised 2026-09-12, ships the bundled "Full SDD Cycle" workflow in `.specify/workflows/speckit/`, with `cursor-agent` as the configured integration. Wave 1 built its own orchestration next to it without using or comparing it.

| Register item | What the engine offers | Gap or question |
|---------------|------------------------|-----------------|
| 13 deterministic control loop | The engine sequences steps; agents act only inside command and prompt steps | — |
| 19, 21 checkpoint and resume | Persisted run state; resume from the exact step | — |
| 23 run log | `log.jsonl` per run | Token use not recorded |
| 58 decisions in git; your gates | Gate steps pause; a verdict can be supplied on resume | Glue: turn a decision lock into a resume |
| P15, 54 to 58 culture on top, no forking | Overlays and slots on the base workflow | — |
| 19 typed messages | Step outputs, `--json`, `from_json` | — |
| 14 laptop not part of the machinery | A CLI, not a service | Needs a host, for example GitHub Actions: pause at a gate ends the job; your lock commit resumes it |
| Cross-family review | Integration and model per step | Verify that `cursor-agent` works in workflow command steps (the bundled workflow lists other integrations) and which second integration gives a different model family |
| 16, 22 reconciler, deadlines, watchdog | None | Glue |

## Reference designs from the governor's reading (not endorsements)

| Item | What to take from it | Fit |
|------|---------------------|-----|
| [Super Simple Software Factory](https://github.com/disler/super-simple-software-factory) | "Code owns sequencing, retries and acceptance; the agent owns only the work inside one bounded phase." Engineer, agent and code lanes; typed envelopes between phases; a failed gate re-prompts the same live session ("a correction costs one message") instead of a cold restart; every event in a SQLite trace | Version 1 runs agents only through the Pi CLI with separate provider API keys; a reference design, not a tool for us |
| [Factory 2.0](https://factory.com/news/software-factory) | Model independence with routing by cost and speed; autonomy as a gradual spectrum (skills, automations, long-running missions); every stage instrumented so the factory learns from itself | Enterprise product; ideas only |

## Whole factories (open source)

| Candidate | One line (from its source) | Notes for the first cut |
|-----------|---------------------------|-------------------------|
| [AI-SDLC](https://github.com/ai-sdlc-framework/ai-sdlc) | Spec Kit import, a gate that refuses undecided work, autonomous tick-loop orchestrator with checkpoint resume, advisory-to-mandatory gates, cross-tool reviewers, earned autonomy | Closest to our register; early alpha; orchestrator experimental |
| addyosmani/factory | Installs a factory operating model in a GitHub repo: issues as queue, scheduled agents triage, build, test, review, draft PRs | GitHub-native; Claude Code, Codex |
| DoorDash Agentic Orchestrator | Deterministic harness: gated phases research, design, plan, implement, review, publish | Matches our phase model |
| Optio | Tickets to merged PRs through a Kubernetes-style reconciliation control plane | Reconciler shape (item 16); supports Cursor |
| OpenAI Symphony | Open spec plus reference implementation; the issue tracker is the control plane | Reference design |
| Mastra Factory | Board from intake to done, each stage manual or auto; GitHub, Linear, Slack | Beta since September 2026 |
| Gas Town / Gas City | Yegge's orchestrator with supervisor roles and Beads as memory; Gas City is the SDK version | Heavy, parallel-swarm oriented |
| Super Simple Software Factory | Deterministic Python owns the workflow graph; agents are bounded nodes | Deterministic loop (item 13) |
| software-factory (nicolasmelo1) | Every rule written twice: prose and an enforced check, with a mutation test proving it fires | Culture match with themes 3 and 4 |
| great_cto | Pipeline of specialist agents; an independent model checks each stage; spending caps refuse | Supports Cursor |
| Anneal | Plan, review, implement, merge a spec unattended; two independent reviewers | — |
| Atomic | Engineering process as an explicit graph of stages, checks and approval gates | — |
| Miniforge | Policy-as-code governance over autonomous development | Clojure |
| Taskplane | "More light-factory than dark-factory"; transparency first | — |
| Squid | Claude Code plugin: spec to reviewed PR, five-agent pipeline, two human gates | Claude Code only |
| HAR | Open harness with isolated working copies and deterministic verification | Supports Cursor |
| Spec Kitty | PRD to specs, plans, tasks; each work package in its own working copy with review and acceptance gates | Named 2026-10-05 |
| Fishhawk | Plan, implement, review stages; policy limits, human approval gates, signed audit trail | Named 2026-10-05 |
| Odin | 11-phase spec-driven workflow, quality gates, human PR review | Every feature runs all 11 phases |
| Kilroy | Dan Shapiro's open implementation of the StrongDM factory | — |

## Orchestration and triggers (parts)

| Candidate | One line | Notes |
|-----------|----------|-------|
| GitHub Agentic Workflows (gh-aw) and Agentics | Markdown-plus-YAML agent workflows compiled to locked-down GitHub Actions | GitHub's own; control loop candidate (item 15) |
| Cursor cloud agents and SDK | Agents on cloud VMs, started from GitHub, Slack, Linear or the API; run our repo's hooks | Already in our stack |
| Claude Code Action; codex-action | Official GitHub Actions for running those agents on repository events | — |
| GitHub Agent HQ | Mission control for Copilot, Claude and Codex agents inside GitHub | Subscription tier to check against budget |
| another-orchestrator | LLM planner, then a deterministic state machine dispatches agents through YAML workflows | — |
| Sortie | Tracker tickets to isolated agent sessions with retries, stall detection, cleanup | Theme 2 recovery |
| Multica | Agents take issues like teammates and hand back for review | Supports Cursor |
| Bernstein | Deterministic, zero-LLM scheduler for many agents, signed audit chain | — |
| Durable engines: Temporal, DBOS, Inngest, Restate, LangGraph | Durable steps, retries, resume | Only if a whole factory or gh-aw leaves a gap |

## Control planes for many agents (parts)

amux, cezar, Orchestrator.inc, Agetor, Parallel Code, Conductor (paid, macOS), Claude Code agent teams. Mostly about running many agents at once; lower priority, since we split by role, not by parallel copies (principle P10).

## Spec layer (parts)

| Candidate | One line | Notes |
|-----------|----------|-------|
| GitHub Spec Kit | Spec, plan, tasks, code, with a constitution | Ours today |
| OpenSpec | Current truth in `specs/`, proposals in `changes/` | — |
| Kiro; cc-sdd | Requirements, design, tasks, steering; cc-sdd brings the Kiro style to Cursor and others | Kiro is a paid IDE |
| BMAD-METHOD | Analyst, PM and architect agents write PRDs and architecture; stories for builders | — |
| GSD Core | Discuss, plan, execute in waves, verify, ship; fresh context per phase | — |
| Superpowers; Compound Engineering plugin | Skills methodologies: brainstorm, plan, TDD, debug; plan-to-PR with a bounded repair loop | Compound Engineering supports Cursor |
| Agent OS (Builder Methods) | Injects codebase standards into spec writing | Same name as our `docs/agent-os/` |
| AWS AI-DLC Workflows | Workflow-steering rules for an AI-driven lifecycle | Supports Cursor |
| Beads; Backlog.md; Claude Task Master | Agent-friendly backlogs: git-backed issue graph; markdown tasks in the repo; PRD to task graph | Job queue candidates |

## Gates (parts)

| Candidate | One line | Notes |
|-----------|----------|-------|
| Bugbot | Cursor's PR reviewer | Already in our stack |
| oh-my-agent | Stop-hook gates and independent judges that re-verify completion claims | Supports Cursor |
| Harmonist | Hooks check every code-changing turn for required reviewers and other protocol rules | — |
| Cage | Gates on contract compatibility, invariant-linked tests, fresh review records | TypeScript |
| Foreman (thruwire) | Supervisor that independently judges whether requirements are met | — |
| Kodus; PR-Agent | Self-hosted, model-agnostic review agents | — |
| GitHub rulesets, code owners, secret scanning, Semgrep, reviewdog | Standard merge controls and linters | Commodity |

## Commercial (out unless a small personal plan exists)

Budget set by the governor: small personal subscriptions only, about $30 a month at most. Enterprise products are out: 8090, Factory.ai, Augment Cosmos, Blitzy, Warp Factories, GitLab Duo, Devin and similar. Personal tiers of Cursor (already paid), GitHub Copilot and Codex are checked against the budget in the survey.

## First cut (2026-10-17, proposed by the orchestrator, for discussion)

Filters: open source or within about $30 a month; works with Cursor and GitHub; actively maintained; fits a light factory. One filter added by the orchestrator: **the operating burden fits one person** (no cluster or hosted platform to run), from principle P16.

Facts checked for the cut (2026-10-17 searches):
- **Spec Kit workflows** can dispatch Cursor's agent command-line tool headlessly, with a model per step (spec-kit change #2631). Still to check: that our installed 1.0.6 has it (upgrade if not), and that a Cursor API key can be added under the secrets rules.
- **AI-SDLC**: Apache-2.0, created February 2026, about 400 stars, very active (orchestrator v0.35.0 released 2026-10-17). Cursor runs through its runner interface with a Cursor API key. The autonomous orchestrator is still experimental and off by default; its own bar for default-on is 95% unattended task completion. TypeScript.
- **addyosmani/factory**: MIT. Installs an operating model, not a service: GitHub Issues as the queue, committed policy and skills, a deterministic gates script, each run fresh for one stage. Clock and compute come from Claude Code cloud routines; a thin Codex adapter exists; no Cursor adapter.
- **Optio**: MIT, about 1,000 stars, a reconciliation control plane, but runs on Kubernetes with PostgreSQL and Redis.
- **Mastra Factory**: open source, but uses the Mastra platform for auth, database and sandboxes; beta.

### Shortlist: three paths, plus the baseline

| Path | What it is | Why it is on the list | Main risk |
|------|-----------|----------------------|-----------|
| A. Spec Kit native | Spec Kit workflows (already installed) with our overlays for the culture layer, Cursor's agent per step, hosted on GitHub Actions | No switching cost; GitHub-backed; covers the deterministic loop, resume and run log | Glue still needed: host trigger, decision-to-resume, watchdog |
| B. AI-SDLC on Spec Kit | Spec Kit in front; AI-SDLC's orchestrator, gates and cross-tool review behind | Closest to the whole register, including decisions and earned autonomy | Young; orchestrator experimental; a second tool and language to learn |
| C. Repo-native operating model | The addyosmani/factory pattern: issues as queue, policy plus skills plus a gates script, scheduled fresh runs, no service | Thinnest option; nothing to operate | Built for Claude Code; Cursor would need an adapter or a Claude subscription |
| D. Keep building on Wave 1 | Baseline for comparison | Works today | Not-invented-here; maintenance stays ours |

Runners-up, surveyed only if path B fails: Spec Kitty, Fishhawk.

### Parts every path still needs (narrow choice inside the survey)

| Part | Candidates |
|------|-----------|
| Host and trigger | Plain GitHub Actions; GitHub Agentic Workflows; Cursor cloud agents through the API |
| Reviewer from a different model family | Codex (codex-action); Copilot code review; Bugbot (same vendor as the builder; check its model family) |
| Work queue | GitHub Issues and Projects; Spec Kit task lists as they are; Beads |
| Merge controls | GitHub rulesets, code owners, secret scanning (commodity) |

### Cut, with reasons

| Cut | Reason |
|-----|--------|
| Optio | Kubernetes, PostgreSQL and Redis: operating burden |
| Roast | Ruby; Claude Code and Pi only; a scripting library |
| DoorDash Agentic Orchestrator | No Cursor; desktop-first. Kept as a reference design |
| Archon | No Cursor. Conditional: becomes path E if the Cursor filter relaxes |
| Mastra Factory | Depends on the Mastra platform; beta |
| Gas Town, Gas City, great_cto, control planes (amux, cezar and others) | Built for swarms of parallel agents; we split by role (P10) |
| Odin | Every feature runs all 11 phases; database-backed |
| Super Simple Software Factory, Kilroy | Pi-only agents; dark-factory aim. Kept as reference designs |
| Anneal, Atomic, Miniforge, Taskplane, Squid, HAR, another-orchestrator, Sortie, Multica, Bernstein | Smaller or Claude-only; their ideas are covered by the shortlist. Revisit only if all paths fail |
| Spec-layer alternatives (OpenSpec, Kiro, BMAD, GSD Core and others) | We are on Spec Kit, which is GitHub-backed; no sign that switching pays |
| Durable workflow engines | Spec Kit's run state or AI-SDLC's orchestrator covers durability for our scale |
| Commercial factories and enterprise tiers | Budget |

### Cross-check: the governor's earlier shortlist (2026-10-17)

The governor found six names shortlisted in an earlier AI discussion of workflow control planes. Checked the same day:

| Name | What it is | Agents it runs | Verdict |
|------|-----------|----------------|---------|
| Spec Kit workflows (GitHub) | YAML steps, Python step types, resumable state | Cursor's agent supported, plus others | Already path A |
| GitHub Agentic Workflows (GitHub, about 5,000 stars) | Markdown plus YAML compiled to locked-down GitHub Actions | Supported: Copilot (default), Claude Code, Codex, Gemini, Pi. Cursor only as an unsupported sample; custom engines removed in February 2026 | Stays a host candidate. Better fit as the home of the different-family reviewer than of the Cursor builder |
| Archon (Cole Medin, about 24,000 stars) | YAML graph of steps: shell steps, agent loops, human approval gates, an isolated working copy per run; triggered from the command line, web, GitHub, Slack, Telegram or Discord | Claude Code, Codex, Pi; no Cursor | Misfiled in the first cut as a spec-layer tool. The strongest engine of the six, but no Cursor. Conditional (see below) |
| Roast (Shopify, about 1,200 stars) | Ruby library chaining shell, chat and agent steps | Claude Code, Pi | Cut: Ruby, no Cursor, a scripting library rather than a factory |
| Agentic Orchestrator (DoorDash, about 100 stars) | Go state machine: knowledge base, clarify, research, design, roadmap, per-phase plan and build, final review, publish; plan critics in parallel; crash resume with bounded retries (3 in a row, 10 in total); desktop app plus local server | Claude Code, Codex, OpenCode; no Cursor | Missed in the first cut. Reference design for lifecycle, critics and the retry rule (compare register item 20). Desktop-first conflicts with item 14 |
| Super Simple Software Factory (IndyDevDan, about 1,000 stars) | Python owns the graph, retries and acceptance | Pi | Already a reference design |

**What the cross-check shows.**
1. All six follow one pattern: code owns the sequence, gates and retries; the agent does one bounded step. That confirms register item 13 from outside.
2. Spec Kit workflows is the only one that officially runs Cursor's agent. Every other engine assumes Claude Code, Codex, Copilot or Pi.
3. So "works with Cursor" is now the filter that decides the most. If it holds, path A stands almost alone among engines. If it relaxes (for example, a Claude or ChatGPT plan at about $20 a month), Archon becomes a serious path E, and the DoorDash orchestrator a weaker option.

**Open for discussion: the Cursor question.** Orchestrator's stance: keep Cursor as the agent runtime. It is already paid for, and it gives several model families under one subscription (the builder and the different-family reviewer both run through it). A second subscription would take most of the $30 budget only to change engines. The governor decides.

## Survey brief (agreed 2026-10-17, 13:43 PT; supersedes the first-cut shortlist above)

**What it decides:** which path to take at the fork (restart on a bought product, hybrid, or keep building), plus a keep, replace or adopt call for each Wave 1 piece. The governor decides; the survey recommends.

**Filters (pass or fail):**
1. **Portability.** The engine runs at least two agent runtimes, first-class and maintained by its own team (not a community or deprecated adapter). Each runtime offers at least two model families. Runtimes tied to one model vendor (Claude Code, Codex) do not count, because they remove cross-family review.
2. **Tool cost.** Open source, or a small personal subscription for the factory software itself. Enterprise products are out. Model usage cost is not a selection criterion: prices change too often, and portability is the hedge. The governor already pays for top-tier Cursor and may take a top Copilot plan.
3. **Operating burden fits one person.** No cluster or hosted platform to run.

**Criteria (judged, for candidates that pass):**
1. **Coverage:** the spec-driven flow (intent, spec, plan, tasks), independent review, decision records, orchestration and a control loop, and the theme 2 reliability properties.
2. **Room for our culture:** whether our layer (rules, review policy, plain-language decisions) sits on top without forking the product.
3. **Fit with our setup:** Cursor stays the home of the conversations (coach and sprint session); unattended steps run on whichever qualifying runtime the engine drives; GitHub and Codespaces.
4. **Maturity and momentum:** users, release pace, backing, churn risk, including a record of dropping integrations.
5. **Lock-in and exit:** whether our data stays in git or open formats.
6. **Effort to adopt:** the glue needed and the learning curve.
7. **Reliability by design:** whether it runs unattended, judged against the theme 2 properties.
8. **Cost controls:** whether it can record tokens and cost per run, cap a run, and choose a model per step (register item 80). Replaces the earlier "cost" criterion.

**Shortlist:**

| Path | What it is |
|------|-----------|
| A. Spec Kit native | Spec Kit workflows (installed) with our overlays; Cursor and Copilot both dispatchable per step with a model per step; GitHub Actions as host |
| B. AI-SDLC behind Spec Kit | Spec Kit for specs; AI-SDLC's orchestrator, gates and cross-tool review; Cursor, Copilot and Codex runners |
| C. GitHub-native | GitHub Issues as the queue, GitHub Agentic Workflows for scheduled locked-down runs (Copilot is its default engine), Copilot's cloud agent from issue to PR; the addyosmani/factory pattern without the Claude dependency. Also a candidate for the lighter lane |
| D. Keep building on Wave 1 | Baseline |

Blends are allowed (for example A with C's queue). Reference designs, not candidates: Archon (its Copilot adapter is deprecated), DoorDash Agentic Orchestrator, Super Simple Software Factory, StrongDM, Symphony.

**Parts, one pick each:** agent runtime (Cursor command line or cloud agents; Copilot command line or cloud agent); reviewer from a different model family (Copilot code review, Codex, Bugbot); host and trigger (plain GitHub Actions, GitHub Agentic Workflows, Cursor cloud agents through the API); work queue (GitHub Issues, Spec Kit task lists, Beads); merge controls (GitHub rulesets, code owners: commodity).

**Method:** desk research only by a fresh GPT-5.6 Sol reviewer working from a brief in git; claims cited to sources dated 2026; no installs or runs. The hands-on trial of the top pick is one real order early in Wave 1.5 (item 15).

**Output:** one comparison table (filters, then criteria, with evidence), a recommended path with the strongest argument against it, a keep, replace or adopt call for each Wave 1 piece, and the open questions only a trial can answer.

**Appetite:** to be set by the governor; placeholder about half a day of reviewer time.

## Next (widening, done)

1. The governor adds names and reacts.
2. First cut by quick filters: open source or within budget; works with Cursor and GitHub; maintained; fits a light factory.
3. Shortlist of two or three per layer that matters, whole factories first.
4. Survey of the shortlist by GPT-5.6 Sol against the agreed criteria.
