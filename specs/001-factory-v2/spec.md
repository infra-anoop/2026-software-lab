# Feature Specification: Factory v2 — intent-faithful agent factory

**Feature Branch**: `001-factory-v2` (spec directory; work lands on `main` via PRs)

**Created**: 2026-10-03

**Status**: Approved (2026-10-03 — all review Blockers/Debates locked by governor or agent per review-locks table)

**Input**: Governor intent session 2026-10-03 → [`intent.yaml`](./intent.yaml) (49 intents, conflicts resolved). Sprint charter: [`notes/sprints/2026-10-sprint-02.md`](../../notes/sprints/2026-10-sprint-02.md).

**Framing (locked):** The software factory is the product. Smart Writer V2 is the workload that exercises it. **SNR = intent fidelity over autonomy time** — the longer agents run unattended, the more they drift; the factory exists to capture intent (including intent the governor cannot articulate upfront) and turn it into checks that stop drift mechanically.

**Intent traceability:** Every requirement and success criterion below cites the intent ids it serves. `intent.yaml` is the source of truth for intent; this spec is the source of truth for scope and scheduling.

## Actors

- **Governor** — the human lab owner. Sets intent, locks decisions, accepts outcomes. Wants to spend attention on product and process direction, not routing or bookkeeping.
- **Orchestrator** — the main agent session talking to the governor. Authors work orders, spawns workers and reviewers, triages results.
- **Worker** — a spawned agent executing one work order (local background or cloud).
- **Reviewer** — a spawned agent from a different model family, judging what machines cannot.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — See at a glance (Priority: P1)

As the governor, I can ask one question at any moment — "what is in flight, what is blocked, what is waiting on me?" — and get a correct answer without anyone having hand-maintained a status field.

**Why this priority**: Sprint 01 worked but the governor "couldn't tell" what was going on; status lived in five hand-synced places and produced bookkeeping commits. Every other story depends on a shared, trustworthy view of work state. (I-M4, I-M2, I-B4)

**Independent Test**: Create work orders in several lifecycle states (ready, claimed, in review, accepted, rejected, merged, blocked on governor). The board reports each correctly, and no file had a status field edited by hand.

**Acceptance Scenarios**:

1. **Given** a work order with no branch, **When** the board is viewed, **Then** it shows as ready.
2. **Given** a work order whose PR is open and checks are running, **When** the board is viewed, **Then** it shows as in review with check progress.
3. **Given** a work order blocked on a governor-owned decision, **When** the board is viewed, **Then** it appears under "waiting on governor" with the decision posed in plain language.
4. **Given** any bus message, **When** validated, **Then** it carries no hand-maintained status field (state is derived).

---

### User Story 2 — Hand off and trust the result (Priority: P1)

As the governor, I approve a work order, walk away for about an hour, and come back to a PR whose acceptance was decided by machine checks per intent, plus an independent reviewer for what machines cannot judge — not by the worker's own account.

**Why this priority**: This is the governor's ideal outcome (I-G2) and the core of the orchestrator/worker practice. (I-G2, I-B1, I-B2, I-P1, I-P3, I-X3, I-X4)

**Independent Test**: Issue a small work order; the worker produces one PR; the PR shows a per-intent result; the reviewer is recorded as a different model family; the worker's handoff lists deviations; the work order could not be issued while it depended on an open governor decision.

**Acceptance Scenarios**:

1. **Given** a work order, **When** it is issued, **Then** it declares goal, intent ids, owned paths, checks to run, locks it honors, estimated size within the autonomy horizon, and stop conditions — and is never edited afterwards (amendments are new messages).
2. **Given** a worker whose checks fail, **When** it tries to report done, **Then** it is prevented and continues or escalates.
3. **Given** ambiguity touching a governor-owned product/architecture decision, **When** the worker meets it, **Then** it stops and the governor is notified in real time as a blocker.
4. **Given** any other ambiguity, **When** the worker meets it, **Then** it takes the most conservative option and records a deviation in its handoff.
5. **Given** a work order that depends on an open governor decision, **When** issuing is attempted, **Then** it is refused.
6. **Given** the concurrency cap of workers already active, **When** another claim is attempted, **Then** it is refused; work without a claim cannot merge; an in-editor launch beyond the cap is warned about (governor waive 2026-10-03: "spawn refused" → "claim refused").
7. **Given** a completed PR, **When** it is reviewed, **Then** the verdict records a reviewer model family different from the author's.
8. **Given** a reviewer is spawned, **When** it starts, **Then** it receives only git artifacts (work order, diff, check results, intent ids) — never the author's conversation or narrative — and the verdict records the inputs it was given.

---

### User Story 3 — Machines catch the drift sprint 01 suffered (Priority: P1)

As the governor, every drift pattern I personally caught in sprint 01 is now caught by a machine before it reaches me: silent substitution of a named tool, required work parked as "Later", tests greened with fake data or test-only logic in production code, edits outside owned paths, jargon in decisions brought to me, and me acting as router.

**Why this priority**: These are observed failures, not hypotheticals — the strongest evidence of where intent leaks. (I-G1, I-B3, I-B4, I-B5, I-B6, I-B7, I-B8, I-A8, I-P2)

**Independent Test**: A suite of seeded-violation PRs — one per sprint-01 pattern — each is blocked by machine without governor involvement.

**Acceptance Scenarios**:

1. **Given** a PR whose new tests already pass on the base commit, **When** checks run, **Then** the PR is blocked (tests were not red first).
2. **Given** a PR that adds test-only branching to application code, **When** checks run, **Then** it is blocked.
3. **Given** a PR touching files outside its work order's owned paths, **When** checks run, **Then** it is blocked.
4. **Given** spec/plan/tasks text that parks required work ("Later", "optional", "deferred") without an Open Decision reference, **When** checks run, **Then** it is blocked.
5. **Given** a work order honoring a named lock, **When** it is issued without a fidelity declaration for that lock, **Then** it is refused.
6. **Given** a decision request to the governor containing task/finding ids or internal jargon, **When** validated, **Then** it is rejected before it reaches the governor.
7. **Given** an acceptance row marked automatic, **When** checks run, **Then** it must link to a real test or eval id, or the PR is blocked.
8. **Given** a work order that declares letter fidelity to a named lock, **When** its PR's output uses a different tool or host, or thinner behavior, than the lock names, **Then** the PR is blocked.

---

### User Story 4 — Hard gates without making the governor the unblocker (Priority: P1)

As the governor, gates bite, but when one is wrong the orchestrator can override it with a written reason; I see every override, and each gate's override count tells me which gates to tune or remove.

**Why this priority**: The governor's top pre-mortem risk is gates being too strict and agents stalling on them. (I-M1, I-P9, I-G5)

**Independent Test**: Trigger a drift gate; the orchestrator overrides it with a reason; the override appears on the board and in the per-gate count; an override without a reason is rejected; an orchestrator override of a governor-only gate is rejected; a gate registered as governor-only outside the four allowed categories is rejected.

**Acceptance Scenarios**:

1. **Given** a blocking drift gate, **When** the orchestrator overrides it with a reason, **Then** the PR proceeds and the override is surfaced to the governor and counted.
2. **Given** an override without a reason, **When** submitted, **Then** it is rejected.
3. **Given** a gate definition, **When** registered, **Then** it declares one of two classes: **drift** (blocks; orchestrator may override with a reason) or **governor-only** (blocks; only the governor may override) — and governor-only is allowed only for spend, secrets, irreversible operations, or governor-owned decisions.
4. **Given** a governor-only gate, **When** the orchestrator or a worker attempts an override, **Then** it is rejected.
5. **Given** an in-session editor hook, **When** registered, **Then** an equivalent repository-side check exists, so any agent tool meets the same gates.

---

### User Story 5 — Intent traceability (Priority: P1)

As the governor, every intent statement maps to a check or an explicit "governor judges this", the coverage is computed for me, and each PR shows which intents it was checked against.

**Why this priority**: Without traceability, intent capture is paperwork (pre-mortem risk) and drift cannot be attributed. (I-N1, I-P4)

**Independent Test**: Remove *all* mappings from one intent — the presence check fails. Separately, mark checks as planned-only — effective coverage drops and is reported.

**Acceptance Scenarios**:

1. **Given** the intent file, **When** checked, **Then** every intent has ≥1 mapped check (presence is a 100% invariant).
2. **Given** the intent file and current check registry, **When** coverage is computed, **Then** it reports the share of intents backed by an implemented, passing non-human check or an explicit governor-judged mapping (effective coverage).
3. **Given** a PR linked to a work order, **When** checks finish, **Then** results are reported per intent id.

---

### User Story 6 — Architecture religion enforced (Priority: P2)

As the governor, output that breaks my architectural patterns is caught — mechanically where possible (layering, typed config, typed agent outputs, adapters, descriptive names, scope) and by a reviewer whose rubric *is* my pattern catalog where not.

**Why this priority**: Architecture is the governor's strongest religion and "smells of breaking my patterns" is a rejection reason even when checks pass. P2 because the P1 stories catch the drift actually observed in sprint 01; these patterns mostly held. (I-A1..I-A11)

**Independent Test**: Seeded-violation PRs for each mechanical pattern are flagged; a reviewer run cites the pattern catalog by id.

**Acceptance Scenarios**:

1. **Given** changed code reading config outside typed Settings, **When** checks run, **Then** it is flagged.
2. **Given** a new agent without a typed output, **When** checks run, **Then** it is flagged.
3. **Given** changed code introducing generic identifiers or modules (e.g. `utils`, `helpers`, `data`, `result`), **When** checks run, **Then** they are flagged.
4. **Given** a PR introducing a new dependency or pattern, **When** checks run, **Then** it must reference a decision that weighed a non-sibling alternative.
5. **Given** any PR, **When** reviewed, **Then** the reviewer's rubric is the pattern catalog and findings cite pattern ids.

---

### User Story 7 — The religion-mining loop (Priority: P2)

As the governor, I don't have to write down my religion upfront. My corrections and rejections are recorded as I make them; a repeated correction triggers an immediate rule proposal; each sprint ends with a post-mortem that mines history and turns every correction into a proposed rule/check or an explicit no-op; I approve every rule change.

**Why this priority**: This is the factory's north star (I-N1) — intent capture as a loop. P2 only because it needs the bus (US1) and gates (US3/US4) to exist first; it must be live before sprint close. (I-N1, I-P5, I-P7, I-P8)

**Independent Test**: Record a correction that the orchestrator links to an earlier one; a rule proposal appears; the governor's batch shows the link for confirmation; attempt to close the sprint without a post-mortem dispositioning every correction — refused; a rule-file change without governor approval cannot merge.

**Acceptance Scenarios**:

1. **Given** a governor correction, **When** it happens, **Then** a correction record exists in git.
2. **Given** a correction the orchestrator links (when recording it) to an existing pattern id or prior correction, **When** recorded, **Then** a rule/check proposal is raised immediately, and the link appears in the governor's next decision batch for confirmation; a rejected link withdraws the proposal.
3. **Given** sprint close, **When** attempted, **Then** it requires a post-mortem that dispositions every correction and reviews overrides, reversed locks, and rework.
4. **Given** a change to factory rules or gates, **When** merged, **Then** governor approval is required.

---

### User Story 8 — Rules are code, context is lean (Priority: P2)

As the governor, the constitution and agent guidance shrink to what is not yet enforceable; every MUST/NEVER cites the check that enforces it; agents load deep rules only when a phase needs them.

**Why this priority**: Prose that nothing enforces is an anti-goal (I-X2) and always-loaded jargon dilutes every agent's context. (I-P6, I-X1, I-X2)

**Independent Test**: Add a MUST statement to a process doc without a check citation; the check fails.

**Acceptance Scenarios**:

1. **Given** process docs, **When** checked, **Then** every MUST/NEVER statement cites an enforcing check or is marked governor-judged.
2. **Given** the constitution, **When** this feature completes, **Then** it is version 2.0 and reflects the resolved conflicts (shared-code rule, ambiguity split, two-class fail-mode taxonomy, repeat-correction trigger).

---

### User Story 9 — Portable to my next repo (Priority: P3)

As the governor, the factory tooling runs in a fresh repo of mine with only configuration, not code edits. (I-G4)

**Why this priority**: Portability is intended but nothing in sprint 02 depends on a second repo. Design constraint applies now; the proof test is scheduled per **D1**.

**Independent Test**: The factory runs its core checks against a minimal fixture repository.

---

### Edge Cases

- A work order needs amending mid-run → a new amendment message supersedes it; the original is never edited.
- A worker's PR is rejected → the rejection is a correction record (feeds US7) and a new work order is issued; rework is counted.
- A gate produces a false positive repeatedly → override count rises; post-mortem decides tune/remove; the governor approves the change.
- Two work orders' owned paths overlap → they cannot run in parallel; the second waits.
- Checks pass but the governor rejects ("smells wrong") → recorded as a correction and counted against the drift metric.
- The bootstrap: factory gates are built before they exist → see FR-037 (bootstrap verdicts, retroactive gate runs, remediation before Wave 2).
- Existing sprint-01 packets → remain readable history; not migrated to the new message format.
- Legacy code (V1, Research Auditor) violating new architecture lints → checks apply to changed lines only; untouched legacy is not blocked.

## Requirements *(mandatory)*

### Functional Requirements

**Bus and visibility**

- **FR-001**: The factory MUST represent work as typed messages — work order, amendment, handoff, verdict, decision request/lock, correction, override — each validated against a schema. (I-B4, I-M2)
- **FR-002**: Messages MUST be immutable once issued; changes are new messages that reference the original. (I-M2)
- **FR-003**: Work state MUST be derived from repository, PR, and check reality — not from hand-maintained fields. (I-M2, I-M4)
- **FR-004**: The factory MUST provide one board answering in flight / blocked / waiting on governor, including governor decisions posed in plain language. (I-M4, I-B3)
- **FR-005**: One work order MUST map to one branch and one PR. (I-P1)

**Work orders, workers, reviewers**

- **FR-006**: A work order MUST declare goal, intent ids, owned paths, checks, honored locks with fidelity, size estimate within the autonomy horizon (1 hour this sprint), and stop conditions. (I-G2, I-B5)
- **FR-007**: Issuing a work order MUST be refused while it depends on an open governor-owned decision. (I-X3)
- **FR-008**: Claiming MUST be refused beyond the concurrency cap of **3** active workers, and a PR without a valid claim MUST NOT merge. In-editor launches beyond the cap MUST be warned about. (Governor waive 2026-10-03 of the "spawn refused" letter; launch broker not built this version.) (I-X4)
- **FR-009**: A worker MUST NOT be able to report done while its work order's checks fail. (I-G2)
- **FR-010**: Escalations MUST be classed: governor-owned product/architecture ambiguity = real-time blocker; all else = conservative choice + deviation recorded in the handoff. (I-B1, I-B2)
- **FR-011**: Acceptance MUST be decided from check results per intent plus a verdict from a reviewer of a different model family; worker self-reports MUST NOT count as evidence. (I-P3, I-G2)
- **FR-011a**: Reviewers MUST receive only git artifacts (work order, diff, check results, intent ids) and never the author's conversation or narrative; each verdict MUST record the inputs it was given. (I-P3)

**Drift gates (sprint-01 patterns)**

- **FR-012**: New or changed tests MUST be proven to fail on the base commit and pass on the PR head. (I-B7, I-P2)
- **FR-013**: Application code MUST NOT contain test-only branching (e.g. key sniffing, testing flags). (I-A8)
- **FR-014**: A PR MUST touch only its work order's owned paths. (I-B8, I-A8)
- **FR-015**: Spec/plan/tasks text MUST NOT park required work without an Open Decision reference. (I-B6)
- **FR-016**: Work orders MUST declare fidelity for every named lock they touch. (I-B5)
- **FR-017**: Decision requests to the governor MUST NOT contain task/finding ids or internal jargon. (I-B3)
- **FR-018**: Every acceptance-catalog row marked automatic MUST carry an evidence reference. The sentinel `planned` is allowed until the work order that implements the row; that work order's PR MUST NOT merge until the reference names an existing test or eval. (I-B7)
- **FR-019**: Changed code MUST meet a mutation-score threshold (**D2**). (I-B7)

**Gate framework**

- **FR-020**: Every gate MUST be registered with one of two classes. **Drift** gates block merge; the orchestrator may override with a reason. **Governor-only** gates block merge; only the governor may override. Governor-only is allowed only for spend, secrets, irreversible operations, and governor-owned decisions. Overrides of either class are recorded and counted (FR-021). (I-P9, I-M1)
- **FR-021**: The orchestrator MUST be able to override a gate only with a written reason; every override MUST be surfaced to the governor and counted per gate. (I-M1)
- **FR-022**: Every in-session editor hook MUST have a repository-side equivalent check. (I-G5)

**Intent traceability**

- **FR-023**: Every intent MUST map to ≥1 check (presence — 100% invariant). Effective coverage MUST be computed and reported as the share of intents backed by an implemented, passing non-human check or an explicit governor-judged mapping. (I-N1, I-P4)
- **FR-024**: PR results MUST be reported per intent id. (I-P4)

**Architecture religion**

- **FR-025**: Changed code MUST be checked for: business logic outside entrypoints/infra layers; agents without typed outputs; config read outside typed Settings; vendor platform access outside adapters; generic identifiers and module names; shared-library modules without declared consumers. (I-A1..I-A5, I-A7, I-A8)
- **FR-026**: A PR introducing a new dependency or architectural pattern MUST reference a decision that weighed ≥1 non-sibling alternative. (I-A9)
- **FR-027**: Architecture-affecting decision requests MUST list concrete consequences per option (services, secret custody, ops steps, cost). (I-A10)
- **FR-028**: The reviewer rubric MUST be the pattern catalog; findings MUST cite pattern ids; the catalog MUST be versioned and grow via post-mortem. (I-A11)

**Religion-mining loop and rules-as-code**

- **FR-029**: Governor corrections and rejections MUST be recorded as correction messages; a repeated correction MUST trigger an immediate rule/check proposal. A correction is "repeated" when the orchestrator, while recording it, links it to an existing pattern id or prior correction; the governor confirms or rejects each link in the next decision batch. (I-P7)
- **FR-030**: Sprint close MUST require a post-mortem dispositioning every correction and reviewing overrides, reversed locks, and rework. (I-P7, I-P8)
- **FR-031**: Changes to factory rules and gates MUST require governor approval to merge. (I-P5)
- **FR-032**: Every MUST/NEVER in the governed process documents — the constitution, `AGENTS.md`, always-applied editor rules, and `docs/agent-os/` — MUST carry `[check: <id>]` or `[governor-judged]`. Other documents are out of scope for this gate. (I-P6, I-X2)
- **FR-033**: The constitution MUST move to 2.0, reflecting each conflict resolution in `intent.yaml`, with prose that became checks replaced by pointers. The constitution change MUST be its own work order with an independent verdict; each conflict resolution and each still-unenforceable invariant has its own acceptance row. (I-P6)
- **FR-034**: Always-applied agent guidance MUST contain only pointers and rules not yet enforceable; deep rules load per phase. (I-X2)

**Scorecard**

- **FR-035**: The factory MUST record per work order: wall time, governor interrupts/minutes, rework loops, first-pass acceptance, overrides, deviations, and cost — sufficient to compute the scorecard in `intent.yaml`. (I-G1, I-G2, I-G3, I-M2)

**Portability**

- **FR-036**: Factory core MUST NOT hardcode this repo's apps, paths, or providers; repo specifics come from configuration. (I-G4)

**Bootstrap**

- **FR-037**: Each Wave 1 PR (built before its gates exist) MUST carry a bootstrap verdict from an independent reviewer listing the manual equivalents run. Once the gates land, they MUST run retroactively on every Wave 1 PR; each failure becomes a remediation work order that must merge — or be overridden with a reason — before Wave 2 work orders are issued. (I-G1, I-M1)

### Key Entities

- **Intent** — a stable-id statement of what the governor wants, with mapped checks (`intent.yaml`).
- **Work order** — immutable instruction to one worker: goal, intent ids, owned paths, checks, locks + fidelity, size, stop conditions.
- **Amendment** — supersedes part of a work order; references it.
- **Handoff** — worker's structured result: what changed, checks run, deviations, open questions.
- **Verdict** — one reviewer's or acceptance pass's findings with severity and tags; records reviewer model family.
- **Decision request / Decision lock** — a governor-owned question posed in plain language with options and consequences; its lock.
- **Correction** — a governor correction or rejection; links to what was corrected; may cite a prior equivalent correction.
- **Override** — a gate bypass with reason; links to gate and PR.
- **Gate** — a registered check with id, fail mode, category, and intents served.
- **Pattern** — an entry in the architecture pattern catalog (reviewer rubric).
- **Run events** — append-only per-work-order measurements (claim, release, run-complete) feeding the scorecard.
- **Post-mortem** — sprint-close artifact dispositioning corrections and reviewing overrides/reversals/rework.

## Success Criteria *(mandatory)*

### Failable outcome classes

- **SC-001 Visibility**: At any moment, one board answers in flight / blocked / waiting on governor, and in spot checks it agrees with repository/PR/check reality 100% of the time; zero hand-maintained status fields exist in bus messages. (US1)
- **SC-002 Seeded drift caught**: For each sprint-01 drift pattern (undeclared substitution, declared-but-violated lock, hidden deferral, fake-green tests, test seams in app code, out-of-scope edits, jargon to governor), a seeded-violation PR or message is blocked by machine — 100% of seeds, zero governor involvement. (US3)
- **SC-003 Hand-off integrity**: For every work order this sprint, the PR's acceptance shows per-intent check results and a different-family reviewer verdict; no work order was issued while depending on an open governor decision; no worker reported done with failing checks. (US2)
- **SC-004 Override visibility**: 100% of gate overrides carry a reason and appear on the board and in per-gate counts; zero overrides without a reason. (US4)
- **SC-005 Traceability**: (a) Presence: 100% of intents have ≥1 mapping; removing all mappings from any intent fails the check. (b) Effective coverage: by sprint close, ≥ 90% of intents are backed by an implemented, passing non-human check or an explicit governor-judged mapping. (US5)
- **SC-006 Rules as code**: 100% of MUST/NEVER statements in process docs cite an enforcing check or are marked governor-judged. (US8)
- **SC-007 Mining loop live**: By sprint close, every governor correction has a record; every repeated correction produced an immediate proposal; the sprint cannot close without a post-mortem dispositioning all corrections. (US7)
- **SC-008 No bookkeeping commits**: After Wave 1 lands, zero commits whose only change is recording status or SHAs in bus files. (US1)
- **SC-009 Scorecard measured**: By sprint close, drift, first-pass acceptance, decision points per feature, and governor minutes are computed from run records for every work order. (US2, US7)
- **SC-010 No routing**: Across the sprint, zero instances of the governor relaying content between agents or being asked what to do next (each instance the governor reports is recorded as a correction tagged routing). (I-B4)
- **SC-011 Capture budget**: Governor minutes spent on intent capture are recorded per feature; each feature is ≤ about 60 minutes. (I-M2)
- **SC-012 Bootstrap evidence**: Every Wave 1 PR has a bootstrap verdict and retroactive gate results; every retroactive failure is remediated or overridden with a reason before Wave 2 work orders are issued. (FR-037)
- **SC-013 Wave 1 time-box**: Wave 1 exits within 5 working days of its first work order (3 targeted, 2 slip) with every P1 check implemented and passing; start and exit dates come from run records. All P2 checks are implemented and passing by sprint close. (I-M3)

### Aspirational (judged at post-mortem — not sole pass/fail)

- Drift ≥ 95% of 1-hour unattended runs with no governor-found intent violation; first-pass acceptance ≥ 75% (targets in `intent.yaml`).
- The governor reports spending attention on product/process direction rather than routing.

### Acceptance catalog

Check instances: [`acceptance.md`](./acceptance.md). Grows from runs; seeded-violation fixtures are first-class rows.

## Check scheduling *(finish bar for this version)*

Ranking rule: **P1** = catches a drift pattern observed in sprint 01, or is foundational for other gates; **P2** = governor's stated religion not yet observed failing, or the mining loop; **P3** = intended but nothing in sprint 02 depends on it. **Wave 1 exits on P1** (SC-013); P1 and P2 together are this version's finish bar at sprint close. P3 rows are out of this version (**D1**).

| Priority | Wave | Checks (refs in `intent.yaml`) |
|----------|------|--------------------------------|
| **P1** | 1 | Bus schema + derived board (`bus.*`, `message.*`, `factory-status-test`, `order.size-cap`); gate registry + fail-mode category + override (`gate.fail-mode-category`, `message.override`, `overrides-per-gate`); hook-has-ci-twin; intent traceability (`factory-check-intent`); red-first proof; test-seam ban; diff-within-owned-paths; deferral-words-need-od; order-fidelity-declared + lock letter tokens; decision-request-no-ids; catalog-test-linkage; pr-links-order; order-blocked-on-open-human-od; spawn-concurrency-cap; verdict reviewer-family-differs; run records + scorecard metrics |
| **P2** | 1 (stretch) → 2 | Architecture lint pack (import-layers, agent-has-output-type, banned-getenv-outside-config, vendor-imports-only-in-adapters, generic-identifier-ban, lab-shared-declares-consumers); pattern-catalog reviewer rubric (`rubric.patterns`, `rubric.fidelity`, `rubric.undeclared-decisions`); new-dependency-needs-decision-ref; research-decision-has-nonsibling-alt; od.arch-options-have-consequences; od.plain-options; correction records + repeated-corrections; sprint-close-requires-postmortem; codeowners-governor-on-rule-paths; process-rule-cites-check; constitution 2.0 + lean always-applied guidance; block-system-path-edits hook |
| **P2** | 2 (Models lane) | mutation-changed-lines (threshold **D2**) |
| **P3** | out of this version — sprint 03 (**D1** waived) | factory-fixture-repo-test (portability proof); one-service-per-app-manifest; live-config-drift-check; secret-scan |

Existing checks reused as-is: validate-secrets-schema, validate-deploy-env, uv-sync-locked.

## Open Decisions *(constitution §G)*

| id | shape_locked | content_open | who | before | status | arch_impact | fidelity |
|----|--------------|--------------|-----|--------|--------|-------------|----------|
| **D1** | P3 rows are intended but not needed by sprint 02 work | Confirm P3 rows are out of this version (scheduled next sprint), or pull any in | human | Before tasks | **waived** (2026-10-03) — all four P3 rows out of this version; scheduled for sprint 03 | content-only | letter |
| **D2** | Changed-code mutation score is a gate (FR-019) | Threshold (share of mutants killed on changed lines) | human | Before the mutation gate blocks | **locked** (2026-10-03) — **70%** of mutants killed on changed lines; tune at post-mortem from override counts | content-only | letter |
| **D3** | Reviewers come from a different model family than the author (FR-011) | Which family reviews by default | human | Before the first spawned review of this spec | **locked** (2026-10-03) — **GPT (OpenAI)** reviews by default; author family is Claude | content-only | letter |

| **D4** | Governor-only gates (FR-020) and rule-change approval (FR-031) need the governor to be distinguishable from agents; today both act as one GitHub account | Mechanism: separate agent identity (GitHub App) / governor-signed decisions / recorded-only — consequences in plan Architecture "Governor identity" | human | Before P2 governor-only enforcement work (P0/P1 ship recorded-only behind an adapter) | **locked** (2026-10-03) — **agents get their own GitHub App identity, set up during Wave 1**; governor-only actions show as unverified until the App is live | **arch** (identity, secret custody, ops steps) | letter |

**Rules:** see constitution §G. Do not invent `content_open` while `open`.

## Review locks *(mandatory before Approved)*

Briefs: product [`SPEC_REVIEW_PROMPT.md`](../../docs/agent-os/SPEC_REVIEW_PROMPT.md) (**F-***); process [`PROCESS_REVIEW_PROMPT.md`](../../docs/agent-os/PROCESS_REVIEW_PROMPT.md) (**R-***). For this feature the factory *is* the product, so the product reviewer judges factory value for the governor; the process reviewer judges whether the factory improves on its own process.

Reports: [`SPEC_REVIEW.md`](./SPEC_REVIEW.md) (F1–F10), [`PROCESS_REVIEW.md`](./PROCESS_REVIEW.md) (R1–R8). Reviewer family: GPT (D3).

| ID | Status | Lock |
|----|--------|------|
| **F1 + R1** | locked (governor 2026-10-03) | Two classes: drift gates block, orchestrator may override with reason; governor-only gates (spend, secrets, irreversible, governor decisions) block, only governor overrides — US4, FR-020 |
| **F2** | locked (governor 2026-10-03) | Cap = 3 active workers — FR-008 |
| **F3** | locked (agent — restores intent letter) | Reviewer isolation added: US2 #8, FR-011a, acceptance `handoff.reviewer_isolated` |
| **F4** | locked (agent) | Finish evidence added for no-routing (SC-010), capture budget (SC-011), Wave 1 time-box (SC-013) |
| **F5** | locked (governor 2026-10-03) | Every seed blocks; jargon decision requests rejected before reaching governor; declared-lock substitution seed added — US3 #6/#8, SC-002 |
| **F6 + R6** | locked (governor 2026-10-03) | Wave 1 exits on P1 (3 days + ≤2 slip); P2 required by sprint close — SC-013, check scheduling |
| **F7** | locked (governor 2026-10-03) | Orchestrator links repeats when recording; governor confirms links in batch — US7 #2, FR-029 |
| **F8** | locked (agent, process) | FR-032 bounded to governed documents; accepted forms `[check: <id>]` / `[governor-judged]` |
| **F9** | Later → plan | Bus transport alternatives stay in plan Architecture |
| **F10 + R5** | locked (agent) | Catalog gains `evidence` column; FR-018 lifecycle: `planned` until the implementing work order, real id before its PR merges |
| **R2** | locked (agent, process) | Traceability split: 100% presence invariant + ≥90% effective coverage (implemented & passing, or governor-judged) by sprint close — SC-005, FR-023, US5 |
| **R3** | locked (agent, process) | Constitution 2.0 is its own work order with independent verdict; acceptance rows per conflict resolution + preserved invariants (FR-033) |
| **R4** | locked (agent, process) | Bootstrap verdicts + retroactive gates + remediation before Wave 2 (FR-037, SC-012) |
| **R7** | Later → plan | Group stories into observe → enforce → learn slices with explicit dependencies |
| **R8** | accepted | Strength: framing, intent traceability, seeded fixtures — preserve |

**Status may become Approved only after Blockers are resolved or explicitly accepted.**

## Assumptions

- Single governor; hobbyist-scale repo; 3 apps today.
- Git + PRs + CI remain the medium; final bus transport (plain files vs issue tracker vs git-native agent tracker) is a **plan Architecture** decision with alternatives and independent review (sprint charter lock).
- Spec Kit remains the base framework; overlays become code under a factory tool so the base stays swappable.
- Cursor is the primary agent tool; repository-side checks are authoritative (I-G5).
- Branch protection and governor-approval rules are set once by the governor (Codespace tokens cannot set them) — ops HITL in the charter.
- Model families for reviewers are selectable per spawned agent without a new vault secret; runtime judges inside apps (feature 002) need their own provider key.
- Governor time budget for intent capture ≈ 60 minutes per feature (I-M2).
- Wave 1 targets 3 days and may slip at most 2 (I-M3).

## Out of scope (this version)

- Smart Writer V2 product changes (feature `002`), except as the workload that exercises the factory.
- A dashboard/UI for the board (I-X5).
- Packaging the factory for engineers other than the governor (I-G4 scope).
- Migrating sprint-01 packets to the new message format.
- P3 rows, subject to **D1**.
