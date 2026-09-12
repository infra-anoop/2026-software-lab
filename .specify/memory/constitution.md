# 2026 Software Lab Constitution

Non-negotiable principles for every feature and agent run in this monorepo.
Spec Kit phases (`/speckit-*`) and `AGENTS.md` must respect this document.
Product-unique choices belong in feature specs — **not** by reinventing process.

**Version**: 1.2.0 | **Ratified**: 2026-09-12 | **Last Amended**: 2026-09-12

## Core Principles

### I. Spec-Driven Development (NON-NEGOTIABLE)

Non-trivial work follows Spec Kit: **Specify → (Clarify) → Plan → Tasks → Implement**, with human gates at phase boundaries.
**Plan** means **Architecture + Phased delivery** (see overlay §E)—not tasks-by-another-name.
Do not implement from chat alone when the change is non-trivial.
Agents exchange context via **git artifacts** (specs, plans, tasks/packets, PRs) — not human copy/paste as the bus.

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

Prefer failing acceptance tests before implementation when practical.
Packet/task DoD must name commands/tests that prove done.
Do not claim “tests adequate” without listing which checks prove the DoD.
Honor locked decisions / won’t-dos in `notes/architect-backlog.md`.

### VI. Learning Journey over Premature Cheapness

This lab optimizes for **internalizing SOTA patterns**, not minimum ceremony for enterprise cost-cutting.
LangGraph and similar mainstream tools are acceptable when they fit the pipeline.
**Unwanted**: using a pattern solely because it is trendy, or solely because it is familiar when it is a misfit.
Learning/stack preferences must **not** be product Ubiquitous acceptance criteria that block a correct product.

## Lab process overlays (stable — do not re-argue per product)

These are **framework** rules. Customize product content inside them; do not debate whether they exist.

### A. Independent reviews before approve (product + process)

After a feature `spec.md` is drafted and before status → **Approved**:

1. **Product review (required for non-trivial features):** fresh session + `docs/agent-os/SPEC_REVIEW_PROMPT.md`. Finding IDs prefix **F**.
2. **Process / lab-vehicle review (optional, recommended for dogfood vehicles):** fresh session + `docs/agent-os/PROCESS_REVIEW_PROMPT.md`. Finding IDs prefix **R**.
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

### E. Plan = Architecture + Phased delivery (architecture is first-class)

`plan.md` is two mandatory parts (see `.specify/templates/overrides/plan.md`):

1. **Architecture** — building blocks, boundaries, data/persistence, APIs/contracts, UI surfaces, major deps/risks. Structure first; not a sprint list.
2. **Phased delivery** — high-level order toward that architecture (e.g. wireframe → API hookup → MVP), with exit criteria. Phases **reference** architecture; they do not replace it.

**Gate:** Do not run `/speckit-tasks` or implement until a human has approved both parts.  
Detailed work items belong in `tasks.md` (or optional packets), not as a substitute for Architecture.

## Stack constraints

- Python 3.12, PEP8, type hints on all signatures.
- Schema-first agents (Pydantic / PydanticAI-style structured outputs) where agents are used.
- Business logic out of infra/entrypoints.
- Codespaces: rebuild via Codespaces UI; do not “Reopen in Container” from Cursor here.
- Deployment: cattle manifests in git (`deploy/railway/`, workflows); no UI-only drift.

## Governance

1. This constitution supersedes informal chat habits when they conflict.
2. Amendments require editing this file, bumping **Version** / **Last Amended**, and a short note in `docs/agent-os/README.md`.
3. Feature specs may not waive I–V without an explicit architect-backlog decision.
4. `AGENTS.md` is the portable summary; `.specify/memory/constitution.md` is the Spec Kit source of process truth.
