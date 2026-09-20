# 2026 Software Lab Constitution

Non-negotiable principles for every feature and agent run in this monorepo.
Spec Kit phases (`/speckit-*`) and `AGENTS.md` must respect this document.
Product-unique choices belong in feature specs — **not** by reinventing process.

**Version**: 1.8.0 | **Ratified**: 2026-09-12 | **Last Amended**: 2026-09-20

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
| arch_impact | Set when locking: `content-only` \| `architecture-affecting` (drives §G.1); omit while `open` |

**Status meanings:**
- `open` = content still TBD; must ask before inventing; **still required for product finish** until locked or explicitly `waived`
- `locked` = content recorded; implement may use it
- `waived` = **out of this product version** (won’t-do for this feature’s finish bar) — not “do later today.” Parking work for a later session while it remains required → keep **`open`** (or pause the agent run); do **not** use `waived`

Before implementing any `open` `who: human` row, raise it in product language and lock (or confirm `waived` = drop from this version). Skipping that is a harness defect.

**Fail closed for implement / tasks:**

1. `/speckit-clarify` and `/speckit-specify`: when a list-like or numeric detail is wrong for PRD mood, **emit an Open Decision row** (do not drop the debt; do not invent the list).
2. `/speckit-tasks`: every `who: human` + `status: open` decision MUST produce at least one task tagged **`[HITL]`** (or `[OD:D#]`) that resolves it **before** dependent product work. Tasks that only need process policy use **`[POLICY]`** when useful.
3. `/speckit-implement` and packets: MUST NOT invent content for `who: human` opens. Stop, pose the Open Decision in **product language**, record the lock in the spec table, then resume. Inventing a seed list / caps / UX enum to “keep going” is a **harness defect** (unauthorized product authorship). After architecture-affecting locks, complete **§G.1** before dependent implement.
4. `who: agent-policy` opens may be resolved by the agent under written policy; still record the lock in the table (no silent defaults).
5. Product reviewers (F*) SHOULD flag “non-final / TBD content” without an Open Decision row as a **Debate** or **Blocker**.
6. Column **`arch_impact`** (optional but recommended): `content-only` \| `architecture-affecting` — set when locking (§G.1).

Open Decisions are the bridge between high-altitude spec conversation and long autonomous execute stretches.

#### G.1 Architecture delta reconcile (after OD lock — NON-NEGOTIABLE)

Locking an Open Decision is **not** enough when the lock changes how the system is built. Spec Kit stock under-specifies evolution; this lab fails closed.

**When any `who: human` row becomes `locked` or `waived`, classify it** (record on the row or in the feature `PLAN_DELTA.md`):

| Class | Meaning | Examples |
|-------|---------|----------|
| **content-only** | Fills numbers/enums/labels/ops into already-locked Architecture shape | Spend-cap integers; vault “yes seed”; citation in Settings when Settings already planned; explicit regenerate control already in contract |
| **architecture-affecting** | Changes topology, hosts, required subsystems, entities/fields, or pipeline stages | New scored quality loop; UI design-tool vs deploy-host split; upload storage model; new job snapshot metrics that imply new entities |

**If the batch includes any architecture-affecting lock, before dependent implement/packets:**

1. **Amend in place** (do **not** create a new feature directory solely for OD fills; do **not** re-run stock plan setup that **replaces** `plan.md` with an empty template):
   - `plan.md` Architecture (+ Phasing exit criteria if needed)
   - `data-model.md` and `contracts/` when entities/APIs change
   - `research.md` Decision rows that were overturned
   - `tasks.md` — append/adjust; do not renumber completed task IDs
2. **Deposit** `PLAN_DELTA.md` in the feature dir (or an **Amendments** checklist section that points to the same content) with: locks classified, artifacts touched, remaining gaps, and whether a delta **P\*** review is warranted.
3. **Run** `/speckit-analyze` (cross-artifact consistency) and record the result in `PLAN_DELTA.md` (pass / gaps filed as tasks).
4. **Independent P\*** (spawn) **only if** the delta reopens topology or SOTA/host forks — or the human asks. Not a greenfield re-plan.
5. **Gate:** Do **not** spawn implement/ops workers whose DoD depends on those locks until steps 1–3 are done for the architecture-affecting subset.

**Content-only locks:** update the Open Decisions table + dependent Settings/task text; no `PLAN_DELTA` gate required (still may note them in an existing delta if one is open).

**Human chat:** one product-altitude line — “Architecture delta reconcile required / done” — not three synonymous soft phrases.

#### G.2 Finish-bar lock batch (before first implement — NON-NEGOTIABLE)

Open Decisions and plan “Later/deferred” parking are easy to skip until late dogfood. This lab requires a **governor lock batch** after tasks (and analyze), **before** unattended execute.

**When:** After `tasks.md` exists for the feature, and **before** the first implement/ops worker (or main-session product implement) for that feature.

**Steps:**

1. **Run** `/speckit-analyze` (if not already run for this tasks revision). Map CRITICAL underspec / deferred-finish findings into the inventory below.
2. **Deposit** `FINISH_BAR.md` in the feature dir (template: `docs/agent-os/FINISH_BAR_TEMPLATE.md`) with an **inventory** of:
   - Every Open Decision with `status: open` and `who: human`
   - Every plan/tasks phrase that parks finish work (`deferred`, `Later`, `P7`, `optional`, `out of MVP`, similar) that still affects the feature’s **stated finish / dogfood / MVP-complete** bar
   - Each row: already an OD id **or** must be promoted to a new OD (no silent plan-only deferral on the finish bar)
3. **Human batch** (product language): lock or **true-waive** (`waived` = out of this product version) every inventory row. Set `arch_impact` on lock.
4. **Then:**
   - If any lock in the batch is **architecture-affecting** → complete **§G.1** before implement
   - Else → implement may start
5. **Gate:** Do **not** spawn implement/ops workers while any finish-bar inventory row is unresolved, or while `FINISH_BAR.md` is missing / `Implement unblocked: no`.

**Exceptions (narrow):**

- Tiny-glue / docs-only packets that touch no product behavior
- A packet whose Out-of-scope explicitly excludes all unfinished finish-bar rows
- Re-entry: if §G.2 already completed, only **new** ODs / new finish deferrals opened later require a **delta** addendum in `FINISH_BAR.md` (not a full reset)

**Human chat:** one product-altitude line — “Finish-bar lock batch required / done.”

**Relation:** §G = define/lock rows · §G.2 = batch before first execute · §G.1 = reconcile after architecture-affecting locks.

## Stack constraints

- Python 3.12, PEP8, type hints on all signatures.
- Schema-first agents (Pydantic / PydanticAI-style structured outputs) where agents are used.
- Business logic out of infra/entrypoints.
- Codespaces: rebuild via Codespaces UI; do not “Reopen in Container” from Cursor here.
- Deployment: cattle manifests in git (`deploy/railway/`, workflows); no UI-only drift.

## Governance

1. This constitution supersedes informal chat habits when they conflict.
2. Amendments require editing this file, bumping **Version** / **Last Amended**, and a short note in `docs/agent-os/README.md`.
3. Feature specs may not waive I–V or §G / §G.1 / §G.2 (Open Decisions, Architecture delta, Finish-bar batch) without an explicit architect-backlog decision.
4. `AGENTS.md` is the portable summary; `.specify/memory/constitution.md` is the Spec Kit source of process truth.
