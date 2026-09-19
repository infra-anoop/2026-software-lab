# 2026 Software Lab Constitution

Non-negotiable principles for every feature and agent run in this monorepo.
Spec Kit phases (`/speckit-*`) and `AGENTS.md` must respect this document.
Product-unique choices belong in feature specs — **not** by reinventing process.

**Version**: 1.6.0 | **Ratified**: 2026-09-12 | **Last Amended**: 2026-09-19

## Core Principles

### I. Spec-Driven Development (NON-NEGOTIABLE)

Non-trivial work follows Spec Kit: **Specify → (Clarify) → Plan → Tasks → Implement**, with human gates at phase boundaries.
**Plan** means **Architecture + Phased delivery** (see overlay §E)—not tasks-by-another-name.
Do not implement from chat alone when the change is non-trivial.
Agents exchange context via **git artifacts** (specs, plans, tasks/packets, PRs) — not human copy/paste as the bus.
Independent reviews (F*/R*/P*/T*) are **spawned** from a git packet plus the named brief (`docs/agent-os/SPAWN_REVIEWER.md`). Do **not** ask the human to paste a brief into a new chat.

### II. Cattle-First Reproducibility

Nothing important lives only in a running container or UI console.
Declare environment (Nix/`flake.lock`), Python deps (per-app `uv.lock`), deploy manifests, and CI in git.
Prefer `nix develop` and `uv sync --locked`. No durable ad-hoc `pip install` / apt pets.

### III. Registry & App Boundaries

Applications exist only if listed in `apps/registry.yaml` (committed `apps/registry.json`).
Shared code goes in `modules/lab_shared` when used by more than one app.
New apps: register, then `uv run scripts/validate_app_registry.py --write-json`.

### IV. Secrets & Config Discipline

Secret **names** live in `deploy/secrets/schema.yaml` + typed Settings.
Secret **values** never commit; Infisical → runtime env (Pattern 2b).
No new ad-hoc `getenv` for durable knobs without schema/Settings.

### V. Test-First for Executable Work

For **executable apps** (registry applications with HTTP/jobs/UI), failing tests come **before** matching implementation. This is **not optional**.

- `/speckit-tasks` MUST emit contract-test and catalog-auto test tasks from `contracts/` auto-check hooks and `acceptance.md` rows with `how: auto`. Do not invent pytest for `how: human` rows.
- Tests MUST fail (red) before product code for that slice. Implementer agents must not write tests that only mirror code they are about to add.
- **Independent test review (T*):** after contract/catalog-auto tests exist, the implementer writes a review packet and **spawns** a reviewer (`docs/agent-os/SPAWN_REVIEWER.md` + `TEST_REVIEW_PROMPT.md`) before implementing that slice. Skip when the only work is scaffold with no such tests. Deposit `TEST_REVIEW.md`. Human adjudicates T* Debates; Nit/Later may be agent-adjudicated (§F). Do **not** ask the human to paste the brief.
- Packet/task DoD must name commands/tests that prove done. Do not claim “tests adequate” without listing which checks prove the DoD.
- Honor locked decisions / won’t-dos in `notes/architect-backlog.md`.

Upstream Spec Kit marks tests optional for generic/non-software features. **This lab overrides that** via `.specify/templates/overrides/tasks-template.md` and the `speckit-tasks` skill.
### VI. Learning Journey over Premature Cheapness

This lab optimizes for **internalizing SOTA patterns**, not minimum ceremony for enterprise cost-cutting.
LangGraph and similar mainstream tools are acceptable when they fit the pipeline.
**Unwanted**: using a pattern solely because it is trendy, or solely because it is familiar when it is a misfit.
Learning/stack preferences must **not** be product Ubiquitous acceptance criteria that block a correct product.

At **plan** time, make those preferences **visible as Architecture exploration**: see `docs/agent-os/STACK_POSTURE.md` and **hard authoring gates** in `docs/agent-os/PLAN_AUTHORING_GATES.md`.  
`research.md` MUST use the lab research shape (`docs/agent-os/research-template.md`): Decision / Rationale / Alternatives (≥1 non-sibling SOTA/managed/OSS or explicit defer) per major block — including **UI host** and **topology/secret custody**.  
**Sibling-app pattern reuse is not exploration.** Clean-room app id ≠ clean-room topology.  
`/speckit-plan` agents MUST ERROR (fix or escalate) if PLAN_AUTHORING_GATES fail — soft “reminders” are insufficient.  
Plan Architecture review (**P-***) stress-tests that exploration — it does **not** replace §A process review and does **not** invent product SCs for stack brands.

## Lab process overlays (stable — do not re-argue per product)

These are **framework** rules. Customize product content inside them; do not debate whether they exist.

### A. Independent reviews before approve (product + process)

After a feature `spec.md` is drafted and before status → **Approved**:

1. **Product review (required for non-trivial features):** spawn per `docs/agent-os/SPAWN_REVIEWER.md` + `docs/agent-os/SPEC_REVIEW_PROMPT.md`. Finding IDs prefix **F**.
2. **Process / lab-vehicle review (optional, recommended for dogfood vehicles):** spawn per `SPAWN_REVIEWER.md` + `docs/agent-os/PROCESS_REVIEW_PROMPT.md`. Finding IDs prefix **R**.
3. Triage all findings as Blocker / Debate / Later / Nit. Record locks in the spec’s **Review locks** table; tag or note `product` vs `process` when helpful.
4. Edit the artifact as locks land. Human adjudicates Debates — reviewers are not automatic truth; opposing product vs process advice is expected and useful.
5. Do not re-merge the two roles into one vague “reviewer” brief.

### B. Failable outcomes (falsifiability)

Every feature spec MUST include **failable outcome classes** (Success Criteria / dedicated section):
statements an implementer can **fail**, not mood-only wins (“better than ChatGPT”, “feels polished”).
Aspirational quality (delight, prose beauty) may be labeled **aspirational** — it is not the only gate.

### C. Extensible acceptance catalog

Detailed check instances live in a **versioned acceptance catalog** beside the feature
(e.g. `specs/<feature>/acceptance.md`), **not** buried in prompts or orchestrator code.
Charter/spec keeps stable classes; the catalog grows from test runs (id, severity, preconditions, shall, how-checked).

### D. Background execution units

Spec Kit `tasks.md` is the default task breakdown.
For long unattended agent runs, optional lab **packets** (`notes/packets/`) may wrap one or more tasks with owned/forbidden paths and hard DoD — one packet ≈ one branch ≈ one PR when possible.
**Review packets** (`notes/packets/_REVIEW_TEMPLATE.md`) are required at F*/R*/P*/T* gates so a spawned reviewer can pick up marching orders from git (`SPAWN_REVIEWER.md`). They are not optional session notes.

### E. Plan = Architecture + Phased delivery (architecture is first-class)

`plan.md` is two mandatory parts (see `.specify/templates/overrides/plan.md`):

1. **Architecture** — building blocks, boundaries, data/persistence, APIs/contracts, UI surfaces, major deps/risks. Structure first; not a sprint list.
2. **Phased delivery** — high-level order toward that architecture (e.g. wireframe → API hookup → MVP), with exit criteria. Phases **reference** architecture; they do not replace it.

**Independent Architecture review (recommended for non-trivial / first-of-kind plans):** after `/speckit-plan` drafts the plan and **before** human plan approval / `/speckit-tasks`, spawn a reviewer per `docs/agent-os/SPAWN_REVIEWER.md` with `docs/agent-os/PLAN_REVIEW_PROMPT.md`. Finding IDs prefix **P**. Weight **Architecture heavy** (including **Learning / SOTA fit** per `STACK_POSTURE.md`), **Phasing light**. Do not re-run §A process review. Do not re-litigate F*/R* unless the plan contradicts them. Deposit report under the feature dir (e.g. `PLAN_REVIEW.md`); human adjudicates Blockers/Debates; record locks on the plan. Skip or shorten when Architecture is a thin follow-on to an already-reviewed shape. Do **not** ask the human to paste the brief.

**Gate:** Do not run `/speckit-tasks` or implement until a human has approved both Architecture and Phased delivery (after P* triage when review was run).  
Detailed work items belong in `tasks.md` (or optional packets), not as a substitute for Architecture.

### F. Progressive HITL (governor altitude)

Human adjudication is mandatory at **high-altitude** gates: spec Debates (F*/R*), plan Architecture Debates (P*), **Open Decisions** with `who: human` (§G), and test-suite findings that would lock **wrong product behavior** (T* tagged product — see below).

**Two pause types (do not conflate):**

| Type | Examples | Who resolves |
|------|----------|--------------|
| **Product lock** | Exact closed vocabulary labels, numeric spend caps, UX preference that changes shalls | Human (plain A/B or short list in chat) |
| **Process policy** | Test wording/SNR, duplicate coverage, Nit/Later, T* findings that do **not** change a product shall | Agent under explicit policy (accept / reject / edit tests); record in review file |

T* reviewers MUST tag each Debate as **product** or **process**. Only **product** Debates (and Blockers) require human adjudication before matching impl. **Process** Debates may be agent-adjudicated like Nit/Later, unless the implementer escalates.

**Human-facing language (NON-NEGOTIABLE in chat):** When speaking to the human, agents MUST use **product / risk / ops** vocabulary (what the user experiences, what could burn money, what needs a vault or account). Finding IDs (F*/R*/P*/T*), task IDs (T0xx), Open Decision ids (`D-*`), and internal mechanics belong in **git artifacts**. Chat Debates / Open Decisions are posed as **plain choices** (A vs B) with one-line stakes; the agent records the lock in the review file or Open Decisions table. Making the human comb `tasks.md` / `TEST_REVIEW.md` for intermediate terms is a **harness defect** — it recreates human-as-bottleneck.

After `tasks.md` is the approved breakdown, execution proceeds until the next **product** pause (§G Open Decision still `open` with `who: human`, product-tagged T* Debate/Blocker, or the MVP/checkpoint named in `tasks.md`). Do **not** ask the human what is next. Prefer **run until the next product lock** over “front-load every interaction then go dark,” except when a known batch of Open Decisions is already listed for the next checkpoint. Spawn T* per `SPAWN_REVIEWER.md`; after product Debates are recorded locked in `TEST_REVIEW.md`, resume. **Default implement path is packet + worker (§H)** — not the main chat session grinding every file.

Downstream (routine unit tests, implement nits, PR nits, process-tagged T*), the lab **may** use agent review with **agentic adjudication** under explicit policy while still escalating Blockers and **product** Debates. Goal: reduce human-as-router without removing human judgment where structure, product bets, and **DoD tests** are set.

### H. Orchestrator / workers (default offload)

**Roles (NON-NEGOTIABLE bias):**

| Role | Responsibility |
|------|----------------|
| **Main session (orchestrator)** | Dialogue with the human at governor altitude; Open Decisions / product Debates; author packets; **spawn** reviewers and workers; triage results; tiny glue only (§H exception) |
| **Worker** | Real implement/ops work against a packet DoD (`docs/agent-os/SPAWN_WORKER.md`) |
| **Reviewer** | Independent F*/R*/P*/T* (`SPAWN_REVIEWER.md`) — never the same agent grading its own tests/spec |

**Default:** Non-trivial implement/ops → write/update `notes/packets/<id>.md` → spawn worker (**prefer background**) → main stays free for human dialogue. Do **not** wait for the human to ask “please delegate.”

**Parallelism:** `[P]` tasks with **disjoint** owned paths → harness **MUST** spawn parallel workers (or one worker with an explicit multi-path parallel DoD). Overlapping paths or missing `[P]` → serial. Do **not** ask the human whether parallelism is suitable when the graph is clear.

**Tiny-glue exception:** Main may edit without a worker only for short docs/lock/packet-meta/checkbox work (see `SPAWN_WORKER.md`). If unsure, spawn a worker.

**Anti-theater:** Orchestrator-only sessions that never land DoD in git are a harness defect. Workers produce; main verifies and talks to the human.

**Always-ready pool:** Not required. Spawn-on-demand with a fixed pointer prompt (`notes/packets/_WORKER_PROMPT.md`) is enough. Standing cloud/automation pools are optional later ops.

Open Decisions (§G) and progressive HITL (§F) still apply inside worker packets.

### G. Open Decisions (shape vs content — fail closed)

At **spec** time it is normal to lock **shape** (“closed property vocabulary,” “two intake axes”) while deferring **content** (exact labels, numeric caps). That deferral MUST NOT be silent prose (“non-final; expand at implementation”).

Every deferred interactive detail MUST appear in the feature spec’s **Open Decisions** table (template: `.specify/templates/overrides/spec.md`):

| Column | Meaning |
|--------|---------|
| id | Stable id (`D1`, `D2`, …) |
| shape_locked | What is already decided (testable shape) |
| content_open | What is still TBD |
| who | `human` \| `agent-policy` |
| before | Which story/phase/task class must not invent this (plain language OK) |
| status | `open` \| `locked` \| `waived` |

**Status meanings:** `open` = must ask before inventing content; `locked` = content recorded, implement may use it; `waived` = **deferred this cycle** (not forgotten). Before any work that depends on a `waived` row, the agent MUST reopen it to `open`, raise the topic again in product language, and get a lock (or confirm still deferred). Skipping that re-ask is a harness defect.

**Fail closed for implement / tasks:**

1. `/speckit-clarify` and `/speckit-specify`: when a list-like or numeric detail is wrong for PRD mood, **emit an Open Decision row** (do not drop the debt; do not invent the list).
2. `/speckit-tasks`: every `who: human` + `status: open` decision MUST produce at least one task tagged **`[HITL]`** (or `[OD:D#]`) that resolves it **before** dependent product work. Tasks that only need process policy use **`[POLICY]`** when useful.
3. `/speckit-implement` and packets: MUST NOT invent content for `who: human` opens. Stop, pose the Open Decision in **product language**, record the lock in the spec table, then resume. Inventing a seed list / caps / UX enum to “keep going” is a **harness defect** (unauthorized product authorship).
4. `who: agent-policy` opens may be resolved by the agent under written policy; still record the lock in the table (no silent defaults).
5. Product reviewers (F*) SHOULD flag “non-final / TBD content” without an Open Decision row as a **Debate** or **Blocker**.

Open Decisions are the bridge between high-altitude spec conversation and long autonomous execute stretches.

## Stack constraints

- Python 3.12, PEP8, type hints on all signatures.
- Schema-first agents (Pydantic / PydanticAI-style structured outputs) where agents are used.
- Business logic out of infra/entrypoints.
- Codespaces: rebuild via Codespaces UI; do not “Reopen in Container” from Cursor here.
- Deployment: cattle manifests in git (`deploy/railway/`, workflows); no UI-only drift.

## Governance

1. This constitution supersedes informal chat habits when they conflict.
2. Amendments require editing this file, bumping **Version** / **Last Amended**, and a short note in `docs/agent-os/README.md`.
3. Feature specs may not waive I–V or §G (Open Decisions fail-closed) without an explicit architect-backlog decision.
4. `AGENTS.md` is the portable summary; `.specify/memory/constitution.md` is the Spec Kit source of process truth.
