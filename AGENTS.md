# AGENTS.md

Cross-tool agent contract for this monorepo ([agents.md](https://agents.md/) standard).
Cursor-specific overlays live in `.cursor/rules/` and `.cursor/skills/`.

Human map: `docs/agent-os/README.md`

---

## Project

Cattle-first Python monorepo for durable POCs.

| Path | Role |
|------|------|
| `apps/<id>/` | Applications (registry-driven) |
| `modules/lab_shared/` | Shared libraries |
| `deploy/`, `db/`, `scripts/` | Infra / ops |
| `specs/` | Feature specs (SDD source of truth) |
| `notes/packets/` | Executable work packets (agent bus) |
| `notes/architect-backlog.md` | Locked decisions / won’t-dos |

Registry of truth for apps: `apps/registry.yaml` (+ committed `apps/registry.json`).

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

## Workflow (Spec-Driven Development)

Standard four phases (GitHub Spec Kit / industry SDD). Humans gate each boundary.

```text
Specify → Plan → Tasks/Packets → Implement → Verify (CI/tests)
```

| Phase | Artifact | Owner |
|-------|----------|--------|
| Specify | `specs/<feature>/spec.md` | Human (+ session agent) |
| Plan | `specs/<feature>/plan.md` | Session agent; human approves |
| Tasks | `notes/packets/<id>.md` | Session agent; human launches |
| Implement | Branch + PR | Background / session agent |
| Verify | Tests + CI | Automatic; optional review agent |

**Rules**

1. Do not implement from chat alone when the change is non-trivial — write or update a spec first.
2. Agents exchange information via **git artifacts** (specs, packets, PRs). Do not rely on human copy/paste as the bus.
3. One packet = one branch = one PR when possible.
4. Stop and escalate on missing decisions, invariant conflicts, or DoD that cannot be met.

Templates: `specs/_TEMPLATE.md`, `notes/packets/_TEMPLATE.md`.

---

## Invariants (non-negotiable)

1. **Cattle deploy** — no UI-only Railway/config drift; declare in repo.
2. **Secrets** — names in `deploy/secrets/schema.yaml` + Settings; no new ad-hoc secret reads.
3. **Registry** — apps exist in `apps/registry.yaml` or they are not apps.
4. **Locks** — `uv.lock` / `flake.lock` stay committed; no floating installs for durable work.
5. **Respect locked decisions** in `notes/architect-backlog.md` (won’t-dos included).

---

## Testing expectations

- Prefer TDD for packet work: failing acceptance tests before implementation when practical.
- Run the smallest relevant suite before declaring done (`uv run pytest` in the touched app).
- Do not claim “tests adequate” without listing which tests prove the packet DoD.

---

## Human role

The human is **governor**, not router:

- Writes / approves specs and invariants.
- Reviews decisions and high-level patterns.
- Does not need to mediate agent-to-agent context if artifacts are updated.

---

## Out of scope for agents unless the packet says so

- Force-push, rewriting git history, skipping hooks.
- Creating vault/runtime footprints without an explicit ops packet.
- Expanding scope beyond the packet’s Out-of-scope section.
