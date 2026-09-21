# Packet: 2026-09-21-one-app-ship-tags

## Meta

| Field | Value |
|-------|-------|
| Packet id | `2026-09-21-one-app-ship-tags` |
| Status | done |
| Feature / spec | Lab cattle (one-app ship) — **not** a product feature; follow-on to `2026-09-20-ops-runtime-tags` |
| Branch | `packet/2026-09-21-one-app-ship-tags` |
| Agent mode | **background** |
| Spawn | `docs/agent-os/SPAWN_WORKER.md` + `_WORKER_PROMPT.md` |

## Goal

Agents can **verify → publish one app → pin Railway → smoke** from a Codespace via **git push of an annotated tag**, with ordinary git credentials. No `workflow_dispatch`, no PAT, no Codespace `actions:write`. Docs must make that the path agents reach for.

---

## Architecture (authoritative — implement this)

### Lifecycle (amend, do not collapse)

| Intent | Mechanism | Must not |
|--------|-----------|----------|
| Monorepo release (all `publish_container` / `deploy.enabled` apps) | `v*` + `ci-cd-pipeline.yml` | Run A23 sync; become the only ship path |
| **One-app ship** (this packet) | ops-style tag `ship/<app_id>/<environment>` + **new** `ship-one.yml` | Use `workflow_dispatch`; grant Codespace `actions:write`; fold into `ops-runtime.yml` (vault) |
| Secrets rotate | `sync/…` + `ops-runtime.yml` | Pin images |
| First-time footprint | `bootstrap/…` + `ops-runtime.yml` | Pin images |
| Human break-glass | Actions UI `workflow_dispatch` on leaf workflows | Agent happy path |

`v*` stays “release the lab.” `ship/…` stays “this one app, this env, this git SHA.”

### Why a new workflow (not `ops-runtime.yml`, not dispatch)

- **`ops-runtime.yml` holds vault OIDC + Railway create.** Ship must not inherit Infisical. Separate workflow, least privilege (`contents: read`, `packages: write` on ship; deploy/smoke as today).
- **`workflow_dispatch` is break-glass.** Default Codespace `ghu_*` cannot invoke it (`HTTP 403`). Do **not** “fix” that by granting `actions:write` (locked 2026-09-20; restated here).
- **`repository_dispatch` / extra PATs** have the same permission problem. Rejected.
- **Path-filtered `v*` or `v2-app-semver` tags** would overload release identity and still ship poorly. Rejected.

Pattern source: annotated tag push already proven for A23/A26 (`ops-runtime.yml` + `scripts/ops_runtime_tag.py`).

### Tag shape (strict)

```text
ship/<app_id>/<environment>
```

Examples: `ship/smart-writer-v2/production`, `ship/research-auditor/staging`.

- `environment` ∈ `{production, staging}`.
- `app_id` must be in `apps/registry.yaml` with **both** `ship.publish_container` and `deploy.enabled`.
- Railway YAML `deploy/railway/<environment>/<app_id>.yml` must exist (deploy job already fail-closes if missing).
- Secrets schema presence: reuse the same helper gate as sync/bootstrap (`validate_app_environment`) so staging without schema fails in the CLI, not as a mystery Actions error.
- No extra path segments. No `v*` overlap. Fail closed in helper + workflow parse.

Re-ship of the same app×env **replaces** the git tag (`--force`), same as sync/bootstrap. The **image identity is the git SHA**, not the tag name.

### Image identity (do not use the git tag as a GHCR tag)

`ship/smart-writer-v2/production` is **not** a legal/useful Docker tag (slashes). Today `ship-registry.yml` sets `TAG=$github.ref_name` when `ref_type==tag`. That is correct for `v1.2.3` and **wrong** for `ship/**`.

**Lock:**

1. Add optional `workflow_call` input `image_tag` to `ship-registry.yml`.
2. If `image_tag` is set, use it as the human-facing GHCR tag. Always still push `sha-<7>` and `latest` (existing behavior).
3. `ci-cd-pipeline.yml` does **not** pass `image_tag` → `v*` behavior unchanged.
4. `ship-one.yml` computes `sha-<7>` from `github.sha` and passes it as `image_tag` **and** as `deploy.yml` `tag`. Railway pins that digest. Never deploy `latest` from this path (avoids racing another ship of the same image name).

### Orchestrator: `.github/workflows/ship-one.yml`

```yaml
on:
  push:
    tags:
      - 'ship/**'
```

**Not** on `v*`, branch push, PR, or `workflow_dispatch`.

Jobs (sequential; stop on first failure):

1. **Parse + registry lookup** — extend helper `parse` / `--github-output` for kind `ship`; jq `apps/registry.json` for `nix_attr=container-<id>`, `oci.image_name`; fail if flags/YAML missing.
2. **Verify** — `uses: ./.github/workflows/verify-source.yml` (same Nix gate as `v*`). Cattle: do not skip because the agent “already ran pytest.”
3. **Ship** — `uses: ./.github/workflows/ship-registry.yml` with `app_id`, `nix_attr`, `image_name`, `image_tag=sha-<7>`; `secrets: inherit`; `packages: write`.
4. **Deploy** — `uses: ./.github/workflows/deploy.yml` with `app_id`, `environment` from tag, `tag=sha-<7>`; `secrets: inherit`.
5. **Smoke** — `uses: ./.github/workflows/smoke-test.yml` with `app_id`, `environment`.

Leaf workflows keep `workflow_dispatch` as **human** break-glass. Comments on those files must say: **preferred agent path is `ship/<app>/<env>` via `ship-one.yml`**, not `gh workflow run`.

### Helper: extend `scripts/ops_runtime_tag.py` (one CLI agents already know)

```bash
nix develop -c uv run scripts/ops_runtime_tag.py ship \
  --app-id smart-writer-v2 --environment production --push
```

- Add kind `ship` to parse/build/CLI (keep `sync` / `bootstrap` unchanged).
- `--dry-run` / `--push` / `--force` same as today.
- Printed Actions URL must point at **`ship-one.yml`**, not `ops-runtime.yml`.
- Never require `INFISICAL_TOKEN`, `RAILWAY_*`, PAT, or `actions:write`.

Do **not** put `ship` jobs in `ops-runtime.yml`.

### Master pipeline hygiene

`ci-cd-pipeline.yml` currently `on: push:` (all refs). `ship/**` / `sync/**` / `bootstrap/**` start empty skipped runs. Narrow tags to `v*` while keeping all branch pushes + PRs for verify. Do not change the `v*` all-apps matrix.

### Docs (this packet fails if agents would still choose dispatch)

**Happy path in agent-facing docs (Rank 1):** helper + `ship/` / `sync/` / `bootstrap/` tag push.

**Break-glass only (Rank 2, labeled as human UI):** Actions UI `workflow_dispatch`. Never show `gh workflow run` as the first command in READMEs, playbooks, or “Human ops” handoff blocks.

**Rewrite (not “also mention”):**

| File | Change |
|------|--------|
| `notes/codespace-a23-dispatch.md` | Retitle to agent **tag** playbook (provision + **ship**). Rank 1 = helper tags; Rank 2 = UI dispatch; Rank 3 = PAT (non-preferred). Keep filename so old links work. |
| `deploy/railway/README.md` | Replace “One-app ship: use workflow_dispatch”. New: `ship/…` helper; `v*` = all apps; dispatch = break-glass. |
| `apps/smart-writer-v2/README.md` | Replace commented `gh workflow run` with helper `ship` command. |
| `AGENTS.md` | Short table: verify on push; one-app ship = `ship/…`; lab release = `v*`; ops = `sync/` `bootstrap/`. |
| `notes/architect-backlog.md` | Lifecycle: code deploy = `v*` **or** `ship/<app>/<env>`. |
| Leaf workflow comments | `ship-registry.yml`, `deploy.yml`, `smoke-test.yml` — preferred agent path is `ship-one.yml`. |
| Historical packets | Banner at top of `2026-09-17-swv2-railway-bootstrap.md` and `2026-09-21-swv2-d5-one-service-ui.md`: **superseded for ship/deploy** — do not `gh workflow run`; use this packet’s helper. Leave the rest as history. |

**Grep contract (test or CI assertion):** agent-facing files above must contain `ops_runtime_tag.py ship` (or equivalent helper invocation) **before** any `gh workflow run` for ship/deploy, and must not call dispatch the happy path.

### Alternatives considered (non-sibling)

| Option | Why not |
|--------|---------|
| Codespace `actions:write` so `gh workflow run` works | Explicitly rejected 2026-09-20; makes agents succeed at the wrong API |
| `repository_dispatch` + PAT | Same token scope problem; extra secret |
| Encode app id into `v*` (`v1.2.3+smart-writer-v2`) | Breaks all-apps release identity; ugly matrix filters |
| GitHub Environment “one-app” UI | Not cattle; not agent-pushable without extra perms |
| Ship-only tag, deploy via dispatch | Leaves the original 403 for the half agents care about |

---

## Phased delivery

| Phase | Exit |
|-------|------|
| **0 — this packet** | Architecture + docs intent locked; implement unblocked |
| **1 — red contracts** | Helper parse tests for `ship/…`; workflow YAML tests (`ship-one.yml` tag-push only, no dispatch; `ship-registry` has `image_tag`; `ci-cd-pipeline` tags `v*` only); docs grep contract failing until rewrite |
| **2 — green path** | Helper + `ship-one.yml` + `image_tag` input + pipeline tag filter + comments |
| **3 — docs sweep** | Files in the table rewritten; historical banners; backlog Lifecycle |
| **4 — stop** | No live prod `--push` unless the human asks; packet handoff |

Phases 1–3 are **one PR**. Do not merge workflow without the docs sweep (otherwise agents keep dispatching).

---

## Context to read first

- This packet (Architecture above)
- `notes/packets/2026-09-20-ops-runtime-tags.md`
- `notes/codespace-a23-dispatch.md`
- `deploy/railway/README.md` (One-app ship + Ops tags)
- `.github/workflows/{ci-cd-pipeline,ship-registry,deploy,smoke-test,ops-runtime,verify-source}.yml`
- `scripts/ops_runtime_tag.py` + `scripts/test_ops_runtime_tag.py` + `scripts/test_bootstrap_workflows.py`
- `apps/registry.yaml`
- `notes/architect-backlog.md` Lifecycle / A23–A26

## Owned paths (may edit)

- `.github/workflows/ship-one.yml` (**new**)
- `.github/workflows/ship-registry.yml` (`image_tag` input + comments)
- `.github/workflows/ci-cd-pipeline.yml` (tag filter `v*` only; comments)
- `.github/workflows/{deploy,smoke-test}.yml` (comments only unless a pass-through is required)
- `scripts/ops_runtime_tag.py` + `scripts/test_ops_runtime_tag.py`
- `scripts/test_bootstrap_workflows.py` and/or new `scripts/test_ship_one_workflow.py`
- `notes/codespace-a23-dispatch.md`
- `deploy/railway/README.md`
- `apps/smart-writer-v2/README.md`
- `AGENTS.md` (short trigger table only)
- `notes/architect-backlog.md` (Lifecycle / closed-row wording)
- Historical packet banners listed above
- This packet (handoff)

## Forbidden paths (do not edit)

- Granting Codespace / `.devcontainer` `actions:write`
- Folding ship into `ops-runtime.yml` or A23 sync into `v*` / `ship-one.yml`
- Product app runtime code (`apps/*/app/**`) except the SWV2 README ship snippet
- Deleting leaf `workflow_dispatch` (break-glass stays)
- Live `--push` of `ship/…` to production from CI or this worker unless the human asks
- Changing the `v*` all-apps matrix semantics

## Parallelism

| Field | Value |
|-------|-------|
| `[P]` | no (one workflow + helper + docs; overlapping paths) |
| Disjoint from other in-flight? | docs overlap with SWV2 README — **serial vs product UI packets** |

## Definition of Done

- [x] `ship-one.yml` exists; `on.push.tags` is only `ship/**`; **no** `workflow_dispatch`
- [x] Helper accepts `ship`; rejects extra segments / unknown apps / missing flags; `--dry-run` prints tag + `ship-one.yml` URL; no live network required for tests
- [x] `ship-registry.yml` `workflow_call` has optional `image_tag`; `v*` caller unchanged
- [x] `ci-cd-pipeline.yml` does not start on `ship/**` / `sync/**` / `bootstrap/**` tags
- [x] Tests: extend `scripts/test_ops_runtime_tag.py` (and workflow YAML tests); `uv run pytest scripts/test_ops_runtime_tag.py scripts/test_bootstrap_workflows.py` (plus any new workflow test file) green
- [x] Docs sweep table done; agent-facing happy path is the helper, not `gh workflow run`
- [x] Historical bootstrap/D5 packets have supersede banners
- [x] Backlog Lifecycle: code deploy = `v*` **or** `ship/<app>/<env>`
- [x] Leaf workflow comments point at `ship-one.yml` as agent path; dispatch = UI break-glass
- [x] Commit(s) on `packet/2026-09-21-one-app-ship-tags`; handoff filled
- [x] **No** `.devcontainer` Actions write scope reintroduced

## Out of scope

- Preview/staging Railway for apps that lack `deploy/railway/staging/<app>.yml`
- Changing Infisical OIDC / Railway token layout
- Per-app verify (still full Nix `verify-source`)
- Auto-deleting historical `ship/` git tags in GitHub
- OpenTofu / `infra/*`

## Governor locks required

| Lock | Value |
|------|--------|
| Trigger | Annotated **`ship/<app>/<env>` git tag push** — not dispatch, not PAT |
| Codespace token | **No** `actions:write` (do not re-add) |
| `v*` | Unchanged **all-apps** release |
| One-app sequence | **verify → ship one → deploy one → smoke one** |
| Image pin | GHCR **`sha-<7>`** (not the git tag name, not `latest`) |
| Vault vs image | Ship workflow **must not** run A23 sync |
| Docs | Agent happy path = helper; `gh workflow run` / dispatch = human break-glass only |

## Fidelity (constitution §I — required)

| Lock | fidelity | How this packet honors it |
|------|----------|---------------------------|
| No Codespace `actions:write` | letter | Forbidden path; playbook Rank 1 remains git push |
| Tag-push one-app ship | letter | New `ship/**` workflow, not a dispatch wrapper |
| Docs retarget | letter | Rewrite happy-path docs in the same PR as the workflow |
| `v*` all-apps | letter | Matrix untouched; only ignore non-`v*` tags on that pipeline |

## Stop / escalate if

- Tempted to grant `actions:write` or document `gh workflow run` as Rank 1
- Tag grammar would need a free-form version segment (`ship/<app>/<env>/<semver>`) — escalate rather than invent
- `image_tag` cannot be added without breaking `v*` callers
- Docs sweep would be deferred to a follow-up PR

## Handoff notes (agent fills at end)

- What changed:
  - New `.github/workflows/ship-one.yml` (`push` tags `ship/**` only): parse → verify-source → ship-registry (`image_tag=sha-<7>`) → deploy.yml → smoke-test.yml.
  - `scripts/ops_runtime_tag.py` kind `ship`; `--dry-run` / `--push` / `--force` unchanged; Actions URL is `ship-one.yml`.
  - `ship-registry.yml` optional `image_tag` (v* caller does not pass it).
  - `ci-cd-pipeline.yml` `on.push.tags: v*` so ops/ship tags do not start empty matrix runs.
  - Docs: codespace playbook, railway README, SWV2 README, AGENTS.md, backlog Lifecycle, historical packet banners.
- Tests run: `nix develop -c uv run --with pytest --with 'pyyaml>=6' pytest -q scripts/test_ops_runtime_tag.py scripts/test_bootstrap_workflows.py scripts/test_ship_one_workflow.py` → **30 passed**.
- Open questions for human: none. No live `ship/… --push` from this packet.
