# Off-the-shelf factory survey

Desk research completed 2026-10-17. Scores use a 1–5 scale: 1 = poor, 3 = adequate with material glue or risk, 5 = strong fit now. A failed filter is not scored.

## Summary

1. Choose **Path A, Spec Kit native, with GitHub Issues as the queue**.
2. Upgrade Spec Kit, extend its workflow with overlays, and run it from plain GitHub Actions.
3. Use Cursor CLI for building, pinned to a non-OpenAI model, and Codex for independent review.
4. Keep the lab's intent, decision, and review policy; replace the home-grown queue, scheduler, and most checks.
5. Trial one real order before migration; Path A still lacks built-in watchdogs, automatic restart, and complete cost controls. [S1][S2][L1]

## Filters

The portability test is deliberately strict. “Many models” is not the same as “many runtimes”; a path needs two maintained runtime integrations, and both runtimes must offer at least two model families.

| Path | Portability | Tool cost | One-person operation | Result |
|---|---|---|---|---|
| **A. Spec Kit native** | **Pass.** Spec Kit itself maintains Cursor and Copilot integrations. Cursor CLI offers models from OpenAI, Anthropic, and Google; Copilot CLI offers OpenAI, Anthropic, and Google models. [S3][S4][S5] | **Pass.** Spec Kit is MIT-licensed. GitHub Actions and the already-paid agent subscriptions are the host and runtimes; model usage cost is outside this filter. [S6][L2] | **Pass.** It is a CLI with YAML workflows and files for state; there is no service or cluster to operate. [S1] | **Pass; score below.** |
| **B. AI-SDLC behind Spec Kit** | **Pass.** AI-SDLC maintains runners for Cursor and Copilot, as well as Codex and others. Cursor and Copilot each expose several model families. [S7][S4][S5] | **Pass.** The project is Apache-2.0 and its autonomous engine is available in the repository. [S8] | **Pass, narrowly.** It is a local/CI CLI rather than a cluster, but adds a second framework, TypeScript runtime, policies, state store, and release stream beside Spec Kit. [S8][S9] | **Pass; score below.** |
| **C. GitHub-native** | **Pass.** GitHub Agentic Workflows maintains Copilot and Pi engines; Copilot offers several model families and Pi can use Copilot, Anthropic, or OpenAI providers. Claude Code and Codex do not count toward the filter because each is tied to one vendor. [S10][S5] | **Pass.** `gh-aw` is MIT-licensed and runs as GitHub Actions. [S11] | **Pass.** Workflows compile to Actions; there is no separate server. [S11][S12] | **Pass; score below.** |
| **D. Keep building on Wave 1** | **Fail.** The implemented work-order schema allows only `local_subagent` and `cloud_agent`, both defined around Cursor in the plan; no second runtime adapter exists. [L3][L4] | Not scored. | Not scored. | **Fail; do not score further.** |

Path D fails even though Cursor itself offers several model families. The lock requires runtime portability, not only model choice inside one runtime.

## Criteria

### Scores

| Criterion | A. Spec Kit native | B. AI-SDLC | C. GitHub-native |
|---|---:|---:|---:|
| 1. Coverage | 4 | 5 | 3 |
| 2. Room for our culture | 5 | 3 | 4 |
| 3. Fit with our setup | 5 | 3 | 4 |
| 4. Maturity and momentum | 5 | 2 | 3 |
| 5. Lock-in and exit | 5 | 4 | 4 |
| 6. Effort to adopt | 4 | 2 | 3 |
| 7. Reliability by design | 3 | 4 | 3 |
| 8. Cost controls | 2 | 5 | 4 |
| **Total / 40** | **33** | **28** | **28** |

### Evidence for every score

| Criterion | A. Spec Kit native | B. AI-SDLC | C. GitHub-native |
|---|---|---|---|
| **1. Coverage** | **4/5.** Workflows support commands, prompts, shell steps, gates, loops, fan-out/fan-in, stored outputs, exact-step resume, and append-only logs. The installed stock workflow covers only specify → plan → tasks → implement with two gates, so independent reviews, decision records, queue intake, and reliability glue must be added in an overlay. [S1][L2] | **5/5.** It has readiness gates, a dependency-driven control loop, isolated work, checkpoint resume, cross-runtime reviewers, attestations, and PR creation. That is the broadest direct match to the register. [S8][S9] | **3/5.** It provides triggers, sandboxing, safe outputs, audit logs, spending limits, and a work queue, but it is an automation substrate rather than a full intent/spec/plan/tasks lifecycle. Spec Kit remains necessary in front. [S12][S13] |
| **2. Room for our culture** | **5/5.** Overlays and slots alter installed workflows without editing the bundled workflow, and custom step types are supported. The existing constitution, skills, review briefs, and decision policy can remain project-owned. [S1][L5] | **3/5.** Policy, readiness, reviewers, attestations, and a fixed 0–13 pipeline overlap the lab's own governance. The framework is configurable, but reconciling two policy systems is likely to create duplication. [S8][S9][L5] | **4/5.** Markdown workflows, repository instructions, safe outputs, and ordinary GitHub records leave room for project policy. The lab must still build the links between Spec Kit gates, decisions, and workflow activation. [S11][S12] |
| **3. Fit with our setup** | **5/5.** Spec Kit is already installed, initialized for `cursor-agent`, and ships the workflow in this repository. It also maintains a Copilot integration and supports per-step integration/model settings. [L1][L2][S1][S3] | **3/5.** Cursor, Copilot, GitHub Issues, and CI are supported, but adoption adds a TypeScript framework and its own concepts behind the existing Python/Nix/Spec Kit setup. [S7][S8] | **4/5.** GitHub Issues, Actions, Codespaces, and Copilot fit directly; Cursor can remain the conversation home. However, `gh-aw` does not officially list Cursor among its stable built-in engines, so Cursor-driven build steps would sit beside it, not inside it. [S10][S11] |
| **4. Maturity and momentum** | **5/5.** GitHub backs Spec Kit; the repository has about 141,500 stars, and releases 1.1.0 through 1.2.1 landed during October 2026. [S6] | **2/5.** Activity is high, including v0.35.0 on 2026-10-17, but the project began in February 2026, has about 399 stars, labels its schema `v1alpha1`, and keeps the autonomous orchestrator experimental and off by default. [S8][S14] | **3/5.** GitHub backs it and releases are frequent, but it remains a technical preview on a 0.x line. It has also removed custom and Copilot SDK engines, evidence that integration churn is real. [S11][S15][S16] |
| **5. Lock-in and exit** | **5/5.** Definitions are YAML; state is JSON/JSONL; overlays are repository files; the engine is MIT-licensed. The lab can keep specs, decisions, and queue references in git. [S1][S6] | **4/5.** It is Apache-2.0 with formal schemas, isolated git checkouts, checkpoint commits, and repository configuration. Exit is possible, but AI-SDLC-specific policies, attestations, and state would need translation. [S8][S9] | **4/5.** Source workflows are Markdown and compiled output is standard Actions YAML; issues and PRs remain GitHub data accessible through APIs. The main lock-in is GitHub as control plane, already accepted by this lab. [S11][S17] |
| **6. Effort to adopt** | **4/5.** The engine and workflow are already present. Work remains to upgrade from installed 1.0.6, add the lab phases, connect issue intake and decision resumes, persist run state across Actions jobs, and add a watchdog. [L1][L2][S1] | **2/5.** It requires learning and configuring a second framework, runner registry, readiness policy, state, reviewer pipeline, and cost governance, then mapping those to current Spec Kit artifacts. [S7][S8][S18] | **3/5.** Queue and host are ready-made, but the lab must author compiled agentic workflows and bridge them to Spec Kit. Frequent 0.x releases and generated lock files add upgrade work. [S11][S15] |
| **7. Reliability by design** | **3/5.** State is saved after steps and a failed or paused run resumes exactly, but the documented engine does not provide an outside watchdog, deadlines, or automatic restart. Those remain thin project glue and must be tested in the trial. [S1][S19] | **4/5.** It emits checkpoint commits, detects recoverable work, resumes on later ticks, quarantines failures, and has chaos/soak machinery. The deduction is because the autonomous path remains experimental and default-off despite those mechanisms. [S9][S14] | **3/5.** GitHub supplies an independent host, schedules, logs, and durable memory patterns. However, `gh-aw` explicitly has no automatic retries; resume depends on a workflow author using cache, repository, or comment memory correctly. [S12][S13] |
| **8. Cost controls** | **2/5.** A model can be chosen per step, but first-party workflow documentation does not show token/cost capture or per-run caps; those appear in community extensions instead. Treat native caps as **unverified**. [S1][S19] | **5/5.** It records model calls by role/task/billing pool and supports token, time, and cost ceilings plus model routing. [S18] | **4/5.** It reports usage and audit data, supports per-run and daily AI-credit caps, and offers model/engine selection. Provider-side controls still matter, and it has no automatic retries. [S10][S12][S13] |

## Parts

| Part | Pick | Why |
|---|---|---|
| **Agent runtime** | **Cursor CLI, pinned per step** | It is already used by the lab, works headlessly in CI, runs repository hooks, and offers multiple model families. Pinning avoids an opaque automatic family change and lets the review step deliberately use another family. [S3][S4][S20] |
| **Different-family reviewer** | **Codex, run as a bounded review step** | Codex gives a known OpenAI family. Pair it with a builder pinned to Anthropic, Google, or Cursor's Composer family. Do not use Copilot code review for this lock: it uses an undisclosed model mix and does not allow model switching. Bugbot now uses Composer 2.5, but may fall back when that model is blocked. [S21][S22] |
| **Host and trigger** | **Plain GitHub Actions** | It is independent of the governor's laptop, already in use, and keeps deterministic sequencing outside the agent. Use Actions to invoke Spec Kit workflows; do not make Actions itself the workflow brain. [S1][L4] |
| **Work queue** | **GitHub Issues** | Issues now expose sub-issues, dependencies, event history, assignees, labels, and Projects APIs. They are visible to the governor and every runtime without a second database or special sync. Beads is capable, but adds Dolt state plus explicit bootstrap/push/pull steps that are not justified at this scale. [S17][S23] |
| **Merge controls** | **GitHub rulesets plus CODEOWNERS** | Rulesets can require pull requests, status checks, and code-owner approval. Secret/code scanning can be added where the plan includes the needed GitHub entitlement; secret-scanning merge protection is still preview and must not be assumed available. [S24] |

Copilot CLI is the fallback runtime for portability, not the default builder. If the trial shows Cursor CLI cannot run unattended under Spec Kit without approval or session problems, switch the builder step to Copilot CLI before adding custom runtime code. Both integrations are maintained by Spec Kit. [S3][S5]

## Wave 1 pieces

“Keep” means the piece expresses lab-specific culture and remains useful. “Replace” means migrate its role to the selected product or a much thinner adapter. “Adopt” means an installed or available product capability becomes the primary mechanism.

| Wave 1 piece | Call | Reason |
|---|---|---|
| `bus/` orders | **Replace** with GitHub Issues plus a small issue form | Issues provide visible identity, dependencies, history, assignment, and API access. The current order schema duplicates a tracker and has already needed amendments to correct ownership and scope. [S17][L3][L6] |
| `bus/` amendments | **Replace** with issue edits/events and explicit decision records when the change is architectural | GitHub records issue events; keeping a second immutable amendment protocol adds translation work. Architecture decisions still stay in git. [S17][L5] |
| `bus/` claims | **Replace** with assignment plus a deterministic “ready/claimed” label transition | The current claim path failed to account for amendments in Wave 1. GitHub is the shared queue authority under this recommendation. [L6] |
| `bus/` handoffs | **Replace** with a pull-request template and workflow-produced run summary | The PR, checks, commits, and workflow log already carry most handoff facts; a separate manually authored file is duplicate state. [L3][S13] |
| `bus/` verdicts | **Keep**, but simplify their envelope | A review bound to exact git inputs, with reviewer family and accept/reject, captures the lab's independent-review policy and has no commodity equivalent that guarantees the same decision semantics. [L3][L5] |
| `bus/` decisions | **Keep** | Plain-language options, a recommendation, the governor's lock, and consequences are the culture layer. Git files also let Cursor conversations and unattended runs share the same conclusion. [L3][L5] |
| `factory` command | **Replace** | Spec Kit should own workflow state/resume; GitHub should own queue and PR state; Actions should own hosting. Retain only thin commands that validate lab-specific decision/review records if a normal check cannot call the library directly. [S1][S17] |
| `gates.yaml` and gate implementations | **Replace with a small audited set** | Keep only high-harm, lab-specific invariants: PR-only main changes, accepted independent review, green tests, owned-file boundaries, record schemas, secrets, and plain decision prompts. Move standard merge/security controls to GitHub and retire/demote the rest according to their false-alarm record. Wave 1 currently registers 25 checks and recorded repeated overrides and known holes. [L7][L8] |
| Editor hooks | **Replace with one irreversible-harm guard** | Keep a local guard against committing or pushing to `main`; move spawn, owned-path, and chat wording checks out of the editor path. The present hook set includes four hooks, and the wording hook already produced a false alarm. [L9][L8] |
| Constitution, `AGENTS.md`, role pages, rules, and skills | **Keep, then prune** | Intent, human decision rights, independent review, architecture review, and “git is the shared surface” are the differentiating layer. They should become overlays and role-specific guidance, not be copied into the engine or duplicated across always-loaded files. [L5][L8] |
| Factory v2 specification and acceptance history | **Keep as design history and migration requirements** | It records why trusted CI, review independence, and typed decisions exist. It should not remain the runtime contract for a replaced queue and scheduler. [L4][L10] |
| Factory v2 queue/lifecycle contracts | **Replace** | Their message types and derived lifecycle specify the home-grown queue being removed. Preserve only the decision and verdict schemas that survive the migration. [L3][L10] |
| Installed Spec Kit | **Adopt its workflow engine and upgrade it** | Version 1.0.6 and the bundled Full SDD Cycle are already committed, but the workflow is not overlaid with the lab's reviews, decision gates, reliability steps, or issue intake. Current upstream is 1.2.1. [L1][L2][S6] |

This is not “keep building” under another name. The custom Python scheduler, queue lifecycle, status derivation, and most gate machinery leave the critical path. The remaining custom code is the culture layer: decision/review records and a small number of invariants.

## Recommendation

Adopt **Path A as the control loop, blended with Path C's GitHub Issues queue**:

1. Upgrade Spec Kit and create an overlay that expresses intent → spec → independent review → plan → architecture review → tasks → test review → implementation → merge.
2. Trigger the overlay from plain GitHub Actions when a suitably labeled issue becomes ready.
3. Run build steps through Cursor CLI with an explicit model; run review through Codex with a different family.
4. Commit or upload Spec Kit run state after every completed step so a fresh Actions run can resume it.
5. Add only three reliability pieces around the engine: a deadline per issue, at most two automatic resumes, and an outside scheduled watchdog that opens or updates an issue on silence.
6. Replace the current queue and lifecycle gradually while the known-good Wave 1 process continues to run the migration.

This path wins because it has the strongest combination of maturity, cultural fit, low migration cost, open state, and exit options. Path B has more features, especially cost governance and recovery, but asks one person to operate and reconcile two process frameworks while its key autonomous mode is still experimental. Path C is an excellent host/queue/reviewer lane, but not a replacement for the lab's spec lifecycle. [S1][S8][S11]

### Strongest case against this recommendation

Path A may be too thin to satisfy the reliability goal. Its exact-step resume is real, but a workflow file and local state are not a reconciler: there is no documented native deadline, watchdog, automatic restart policy, or first-party cost ledger/cap. Running it on ephemeral Actions also requires the lab to design state persistence and safe resume correctly. That glue could regrow into another home-built factory. AI-SDLC already has checkpoint commits, recoverable-work detection, a dependency tick loop, cross-runtime review, and comprehensive usage controls; if one real-order trial exposes more than a few days of reliability glue, the recommendation should flip to Path B despite its youth. [S9][S14][S18][S19]

## Open questions for the trial

Only a real run can settle these:

1. Does installed-then-upgraded Spec Kit dispatch both Cursor CLI and Copilot CLI headlessly in this repository, with the selected models and existing Nix environment?
2. Can a workflow paused at a human decision end an Actions job, persist its state safely, and resume in a fresh job from the exact step?
3. What state must be committed to git versus stored as an Actions artifact, and how are concurrent or duplicate triggers made harmless?
4. Do Cursor hooks run in the selected headless mode exactly as documented, and can the unnecessary hooks be removed without losing a high-harm guard?
5. Can a Codex review step consume the lab's review brief, cite the reviewed SHA, produce the required verdict record, and remain isolated from the builder's context?
6. Can GitHub Issue dependencies, labels, and assignment express ready, claimed, blocked, and complete without races or a second status store?
7. After killing the run and starting a fresh job, does it lose less than one completed step and avoid repeating an irreversible action?
8. Can the watchdog distinguish quiet-but-working from stalled using only GitHub and committed run state?
9. Can usage from Cursor and Codex be normalized into one per-run token/cost record, and can the wrapper stop a run at a cap? Spec Kit-native support is **unverified**.
10. Does the overlay preserve all lab review and decision pauses without duplicating command-level extension hooks?
11. How much maintenance does an upgrade from Spec Kit 1.0.6 to 1.2.1 impose on local overrides and the installed workflow?
12. Is GitHub secret/code scanning merge protection available on this repository's plan? Entitlement is **unverified**.

## Sources

All web sources were accessed 2026-10-17. Dates in descriptions are publication or release dates where the source exposes them.

### Web

- **[S1]** GitHub Spec Kit, [Workflows](https://github.github.com/spec-kit/reference/workflows.html): workflow steps, overlays, gates, state, logs, resume, per-step runtime/model configuration.
- **[S2]** GitHub Spec Kit, [Reference overview](https://github.github.com/spec-kit/reference/overview.html): workflow scope and supported control-flow primitives.
- **[S3]** GitHub Spec Kit, [Integrations reference](https://github.com/github/spec-kit/blob/main/docs/reference/integrations.md) and [Cursor headless dispatch change #2631](https://github.com/github/spec-kit/commit/8e5643d4ffa4a4a053b163386459dc3f03c8b767): maintained Cursor/Copilot integrations and headless Cursor dispatch.
- **[S4]** Cursor, [CLI parameters](https://cursor.com/docs/cli/reference/parameters) and [CLI overview](https://cursor.com/docs/cli/overview): headless mode, model selection, resume, and available account models.
- **[S5]** GitHub, [Copilot CLI command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference) and [supported models](https://docs.github.com/en/copilot/reference/ai-models/supported-models): explicit model selection and model families.
- **[S6]** GitHub, [Spec Kit repository](https://github.com/github/spec-kit) and [releases](https://github.com/github/spec-kit/releases): MIT license, adoption, backing, and October 2026 release pace.
- **[S7]** AI-SDLC, [Agent runners](https://ai-sdlc.io/docs/api-reference/runners): maintained Cursor, Copilot, Codex, Claude, and other runners.
- **[S8]** AI-SDLC, [repository](https://github.com/ai-sdlc-framework/ai-sdlc): Apache-2.0, architecture, age, adoption, v1alpha1 status, and autonomous pipeline summary.
- **[S9]** AI-SDLC, [Autonomous orchestrator](https://ai-sdlc.io/docs/concepts/autonomous-orchestrator) and [resume commit](https://github.com/ai-sdlc-framework/ai-sdlc/commit/b063657f62c9082d5af795caba18a1e10ebde301): opt-in status, checkpoints, work recovery, and resume.
- **[S10]** GitHub Agentic Workflows, [engines reference](https://raw.githubusercontent.com/github/gh-aw/main/docs/src/content/docs/reference/engines.md): maintained engines, providers, model and run limits.
- **[S11]** GitHub, [Agentic Workflows technical preview announcement, 2026-02-13](https://github.blog/changelog/2026-02-13-github-agentic-workflows-are-now-in-technical-preview/) and [gh-aw repository](https://github.com/github/gh-aw): architecture, license, security defaults, and preview status.
- **[S12]** GitHub Agentic Workflows, [FAQ](https://github.github.com/gh-aw/reference/faq/) and [triggers](https://github.github.com/gh-aw/reference/triggers/): Actions hosting, schedules, cooldowns, limits, and lack of automatic retries.
- **[S13]** GitHub Agentic Workflows, [MemoryOps](https://github.github.com/gh-aw/patterns/memory-ops/) and [audit](https://github.github.com/gh-aw/reference/audit/): persistent memory patterns and run evidence.
- **[S14]** AI-SDLC, [releases](https://github.com/ai-sdlc-framework/ai-sdlc/releases) and [RFC-0015](https://github.com/ai-sdlc-framework/ai-sdlc/blob/main/spec/rfcs/RFC-0015-autonomous-pipeline-orchestrator.md): v0.35.0 on 2026-10-17, experimental flag, chaos/soak promotion evidence.
- **[S15]** GitHub Agentic Workflows, [releases](https://github.com/github/gh-aw/releases) and [release policy](https://github.github.com/gh-aw/reference/releases/): 0.x cadence, generated lock files, and pinning.
- **[S16]** GitHub Agentic Workflows, [v0.46.1](https://github.com/github/gh-aw/releases/tag/v0.46.1): removal of custom and Copilot SDK engines.
- **[S17]** GitHub, [sub-issues API](https://docs.github.com/en/rest/issues/sub-issues?apiVersion=2026-03-10), [issue dependencies API](https://docs.github.com/en/rest/issues/issue-dependencies), [Projects items API](https://docs.github.com/en/rest/projects/items?apiVersion=2026-03-10), and [issue events API](https://docs.github.com/en/rest/issues/events): queue capabilities and history.
- **[S18]** AI-SDLC, [Usage ledger and model routing](https://ai-sdlc.io/docs/concepts/usage-ledger-model-routing) and [cost governance](https://ai-sdlc.io/docs/tutorials/cost-governance): token/cost records, caps, and routing.
- **[S19]** GitHub Spec Kit, [community extensions](https://github.github.com/spec-kit/community/extensions.html): cost controls are available as community additions; no first-party watchdog/cost control was found.
- **[S20]** Cursor, [Cloud Agents](https://cursor.com/docs/cloud-agent) and [GitHub Actions](https://cursor.com/docs/cli/github-actions): hooks and unattended CLI execution.
- **[S21]** GitHub, [Copilot code review](https://docs.github.com/en/copilot/concepts/agent-capabilities/agent-powered-workflows-and-operations/code-review): undisclosed model mix and no model switching.
- **[S22]** Cursor, [Bugbot update, June 2026](https://cursor.com/blog/bugbot-updates-june-2026): Composer 2.5 default and fallback behavior.
- **[S23]** Beads, [introduction](https://beads.gascity.com/) and [sync setup](https://beads.gascity.com/getting-started/sync-setup): Dolt-backed queue and required synchronization.
- **[S24]** GitHub, [ruleset rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets) and [secret scanning merge protection](https://docs.github.com/en/code-security/how-tos/secure-your-secrets/prevent-future-leaks/block-merges-with-secrets): merge controls and entitlement/preview caveat.

### Repository

- **[L1]** `.specify/integration.json`: installed Spec Kit 1.0.6 and `cursor-agent` integration.
- **[L2]** `.specify/workflows/speckit/workflow.yml`: installed Full SDD Cycle workflow and its current steps.
- **[L3]** `scripts/factory/src/factory/bus/models.py`: message kinds, runtime vocabulary, decision and verdict schemas.
- **[L4]** `specs/001-factory-v2/plan.md`: current Cursor/GitHub/Python architecture and lifecycle.
- **[L5]** `.specify/memory/constitution.md` and `AGENTS.md`: lab-specific governance and review policy.
- **[L6]** `notes/retro/2026-10-wave1-items.md`: Wave 1 failures and repeated queue/check issues.
- **[L7]** `scripts/factory/gates.yaml`: current gate registry.
- **[L8]** `notes/retro/2026-10-harness-changes.md`: agreed principles, seven-gate target, false-alarm policy, and buy-over-build direction.
- **[L9]** `.cursor/hooks.json`: current four editor hooks.
- **[L10]** `specs/001-factory-v2/contracts/messages.md`: current queue/lifecycle record contract.
