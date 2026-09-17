# AGENTS.md

Cross-tool agent contract for this monorepo ([agents.md](https://agents.md/) standard).

**Process base:** [GitHub Spec Kit](https://github.com/github/spec-kit) (installed under `.specify/`).  
**Constitution (process truth):** `.specify/memory/constitution.md`  
**Human map:** `docs/agent-os/README.md`  
**Cursor:** `.cursor/rules/` + Spec Kit skills `.cursor/skills/speckit-*`

---

## Project

Cattle-first Python monorepo for durable POCs.

| Path | Role |
|------|------|
| `apps/<id>/` | Applications (registry-driven) |
| `modules/lab_shared/` | Shared libraries |
| `deploy/`, `db/`, `scripts/` | Infra / ops |
| `specs/` | Feature specs (Spec Kit) |
| `.specify/` | Spec Kit templates, scripts, constitution |
| `notes/packets/` | Optional long-run packets (lab overlay on tasks) |
| `notes/architect-backlog.md` | Locked decisions / won’t-dos |

Registry: `apps/registry.yaml` (+ committed `apps/registry.json`).

---

## Environment

- **Nix** for system tools: `nix develop` (see root `flake.nix`). Prefer Nix over ad-hoc `pip`/`apt`.
- **uv** per app: `cd apps/<id> && uv sync --locked`
- **Secrets**: never commit. Schema in `deploy/secrets/schema.yaml`; values in Infisical → runtime env.
- Codespaces: rebuild via Codespaces, not Cursor “Reopen in Container”.

### Golden commands

```bash
nix develop
cd apps/<id> && uv sync --locked
uv run pytest
uv run ruff check app/
nix flake check   # heavier; full matrix
```

HTTP app loop: `uv run uvicorn app.entrypoints.http:app --reload --host 0.0.0.0 --port 8080`

---

## Code conventions

- Python 3.12, PEP8, type hints on all function signatures.
- Schema-first agents: Pydantic models as `result_type`; `Agent(deps_type=...)` + `RunContext`.
- Keep business logic out of infra/entrypoints.
- New apps: register in `apps/registry.yaml`, regenerate JSON via `uv run scripts/validate_app_registry.py --write-json`.

---

## Workflow (Spec Kit + lab overlays)

```text
Constitution → Specify → [Clarify] → independent review → Plan → [Plan Architecture review] → Tasks → [failing tests + T* review] → Implement
```

| Phase | Artifact / skill | Notes |
|-------|------------------|--------|
| Constitution | `.specify/memory/constitution.md` | `/speckit-constitution` |
| Specify | `specs/<###-feature>/spec.md` | `/speckit-specify` (lab override template) |
| Spec review | Product **F-***; optional Process **R-*** | Before Approved |
| Plan | `plan.md` — **Architecture + Phased delivery** | `/speckit-plan` |
| Plan review | Architecture **P-*** (`PLAN_REVIEW_PROMPT.md` + `STACK_POSTURE.md`) | Arch-heavy incl. SOTA/alternatives; phasing-light; before plan approval |
| Tasks | `tasks.md` | `/speckit-tasks` — after plan approved; tests **required** for executable apps |
| Test review | **T-*** (`TEST_REVIEW_PROMPT.md`) | After red contract/catalog-auto tests; implementer writes a review packet and **spawns** the reviewer (`SPAWN_REVIEWER.md`) |
| Review packet | `notes/packets/<id>.md` | Required at F*/R*/P*/T* so the spawned reviewer has marching orders in git |
| Optional work packet | `notes/packets/<id>.md` | Long unattended implement DoD wrapper |
| Implement | Branch + PR | `/speckit-implement` — TDD order; T* Blockers resolved |

**Rules**

1. Do not implement from chat alone when the change is non-trivial — spec first.
2. Git artifacts are the bus (no human copy/paste router). Independent reviews (F*/R*/P*/T*) are **spawned** from a git packet (`docs/agent-os/SPAWN_REVIEWER.md`); do **not** ask the human to paste a brief.
3. Specs need **failable outcomes** + **acceptance catalog** (constitution §B–C).
4. Do not re-argue process per product; debate product-unique choices only.
5. Stop and escalate on missing decisions, invariant conflicts, or unmet DoD.
6. Human adjudicates Debates at spec and Architecture; progressive HITL may auto-accept Nit/Later later (§F).
7. `/speckit-plan` must satisfy `PLAN_AUTHORING_GATES.md` (fail closed) — sibling topology reuse without SOTA alternatives is an ERROR.
8. Executable apps: failing contract/catalog-auto tests before matching impl; T* review when those tests exist (constitution §V).

---

## Invariants (non-negotiable)

See constitution. Short list:

1. Cattle deploy — no UI-only Railway/config drift.
2. Secrets — schema + Settings; never commit values.
3. Registry — apps in `apps/registry.yaml` or they are not apps.
4. Locks — `uv.lock` / `flake.lock` committed.
5. Respect `notes/architect-backlog.md`.

---

## Human role

Governor, not router: approve specs/invariants, adjudicate review Debates (F*/R*/P*/T* at altitude), review PRs at decision altitude. Do **not** paste review briefs between agents. Downstream Nit/Later may be agent-adjudicated under explicit policy (constitution §F).

---

## Out of scope for agents unless the packet/task says so

- Force-push, rewriting git history, skipping hooks.
- Creating vault/runtime footprints without an explicit ops packet.
- Expanding scope beyond task/packet Out-of-scope.
