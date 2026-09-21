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

### Agent CI / ship (Codespace)

Ordinary git push. Do **not** `gh workflow run` (Codespace tokens cannot `workflow_dispatch`). Playbook: `notes/codespace-a23-dispatch.md`.

| Intent | Command |
|--------|---------|
| Verify | push a branch / open a PR |
| One-app ship + deploy + smoke | `nix develop -c uv run scripts/ops_runtime_tag.py ship --app-id <id> --environment production --push` |
| Lab-wide release (all apps) | `git tag vX.Y.Z && git push origin vX.Y.Z` |
| Secrets rotate | `… ops_runtime_tag.py sync --app-id <id> --environment production --push` |
| First-time Railway footprint | `… ops_runtime_tag.py bootstrap --app-id <id> --environment production --push` |

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
3. Specs need **failable outcomes** + **acceptance catalog** (constitution §B–C) + **Open Decisions** when shape≠content (§G). After tasks: **§G.2** finish-bar batch before implement. Architecture-affecting OD locks require **§G.1** before dependent implement.
4. Do not re-argue process per product; debate product-unique choices only.
5. Stop and escalate on missing decisions, invariant conflicts, unmet DoD, open `who: human` Open Decisions, incomplete §G.2 (`FINISH_BAR`), incomplete §G.1 after architecture-affecting locks, or **fidelity deltas** without recorded human waive (constitution §I). Do **not** ask what task is next. Do **not** invent deferred product content. Do **not** silently dilute named locks (“v0-class”, thinner SC, host swaps).
6. Human adjudicates product Debates (spec, Architecture, product-tagged T*) and human Open Decisions; after locks are recorded (and §G.2 / §G.1 done when required), work **resumes** (§F–G). Nit/Later and process-tagged T* may be agent-adjudicated.
7. `/speckit-plan` must satisfy `PLAN_AUTHORING_GATES.md` (fail closed) — sibling topology reuse without SOTA alternatives is an ERROR.
8. Executable apps: failing contract/catalog-auto tests before matching impl; **spawn** T* when those tests exist; after product locks, continue (constitution §V / §F).
9. **Orchestrator / workers (§H):** Main session dialogues and spawns; default implement/ops = packet + **background worker** (`SPAWN_WORKER.md`). `[P]` + disjoint paths → parallel workers automatically. Tiny-glue exception only.
10. **Fidelity (§I):** Packet Fidelity table required; disclose-or-stop before spawn if substituting a letter lock.

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

Governor, not router: approve specs/invariants, adjudicate review Debates and Open Decisions at **product/ops altitude**, review PRs at decision altitude. Adjudicate **fidelity waives** when agents propose substitutes for letter locks (constitution §I). Do **not** paste review briefs between agents. Do **not** need to memorize task IDs or finding IDs — agents translate into plain choices. Do **not** need to decide whether work can run in parallel — the harness uses `[P]` + owned paths. After you lock Debates/Open Decisions, agents resume without a new “keep going.” Downstream Nit/Later may be agent-adjudicated under explicit policy (constitution §F–H).

---

## Out of scope for agents unless the packet/task says so

- Force-push, rewriting git history, skipping hooks.
- Creating vault/runtime footprints without an explicit ops packet.
- Expanding scope beyond task/packet Out-of-scope.
