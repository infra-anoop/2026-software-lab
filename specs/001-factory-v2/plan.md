# Implementation Plan: Factory v2 — intent-fidelity gates, typed bus, derived board

**Branch**: `001-factory-v2` (work orders land on `main` via one branch + PR each) | **Date**: 2026-10-03 | **Spec**: [`spec.md`](./spec.md) (Approved)

**Input**: Feature specification `specs/001-factory-v2/spec.md`; intent [`intent.yaml`](./intent.yaml); research [`research.md`](./research.md); sprint charter [`notes/sprints/2026-10-sprint-02.md`](../../notes/sprints/2026-10-sprint-02.md).

**Lab rule (constitution §E):** Plan = **Architecture** + **Phased delivery**. No tasks or implement until both are human-approved after P* triage.

**Approval:** Architecture + Phased delivery approved by the governor 2026-10-03, after P* triage.

## Summary

Replace sprint-01's prose process (mutable packets, free-text status, the human as router) with code: one `factory` Python package that (1) defines the bus as immutable, schema-validated message files in git; (2) derives every work item's state from git, PR, and check reality and renders one markdown board; (3) runs drift gates in CI as required checks, mirrored by Cursor hooks; (4) records overrides, corrections, and run measurements so the scorecard and the religion-mining loop compute themselves. Wave 1 ships the P1 gates under bootstrap verdicts; P2 (architecture lints, rubric, mining loop, constitution 2.0, mutation) completes during Wave 2.

## Architecture *(mandatory — first-class)*

### System building blocks

- **UI / clients**: `factory status` markdown board (terminal + chat), the same board in the GitHub Actions job summary on every PR. No web UI (I-X5).
- **API / application services**: `factory` package (`scripts/factory/`, own uv project). Typer CLI plus a library used by hooks and CI. Subsystems:
  - `bus` — Pydantic message models, loader, append-only validation.
  - `lifecycle` — state derivation from git + GitHub REST.
  - `board` — rendering.
  - `gates` — registry, runner, override resolution, and one module per gate.
  - `intent` — traceability and coverage.
  - `metrics` — run records and scorecard.
  - `hooks` — Cursor hook entrypoints.
  - `github` — REST adapter, the only module that talks to GitHub (I-A4).
  - `config` — typed `factory.toml` loader (I-A3).
- **Orchestration / jobs**: **P1 lock — linear derived state machine** `issued → claimed → in_review → accepted | rejected → merged`, with `released` and overlays `stale` and `blocked_on_governor`; no workflow engine (migrate trigger in `research.md`). **Issuance never touches `main`:** the order is the first commit of `wo/<order-id>`; claims are atomic fast-forward pushes; decisions, corrections, and post-mortems travel in separate *bus PRs* (full sequence in [`data-model.md`](./data-model.md) § Lifecycle). Agents run as Cursor background subagents or cloud agents; the authoritative admission point is `factory claim` plus the merge check (cap 3); the editor spawn hook only warns (review P3, governor lock).
- **Data stores**: git only. `bus/` holds append-only YAML messages; `factory.toml` holds repo config; `scripts/factory/gates.yaml` is the gate registry; `scripts/factory/rubrics/patterns.yaml` is the pattern catalog (P2). No database.
- **External systems**: GitHub (git remote, REST API, Actions, branch protection, CODEOWNERS), Cursor (hooks, subagents, cloud agents), Semgrep CE / import-linter / mutmut (OSS CLIs in CI), and Bugbot (non-authoritative reviewer).

### Boundaries & responsibilities

| Block | Owns | Does not own |
|-------|------|--------------|
| `bus` | Message schemas, file layout, append-only rule, JSON Schema export | Lifecycle state (never stored) |
| `lifecycle` | State per order, derived from order files, branches, PRs, verdicts, decisions | Writing anything |
| `board` | Rendering sections: in flight, blocked, waiting on governor, overrides (counts per gate), ready queue | Data fetching (takes a lifecycle snapshot) |
| `gates` | Registry (id, class `drift`/`governor-only`, category, intents, hook twin); running gates against a PR; resolving overrides | Policy content (rules live in each gate module + registry) |
| `intent` | Presence and effective coverage over `specs/*/intent.yaml` + registry + catalogs | Writing intents |
| `metrics` | Run events → scorecard (drift, first-pass, decision points, governor minutes, overrides, rework) | Judging quality |
| `hooks` | Thin adapters from Cursor hook JSON to `gates` / `bus` calls; fast and offline | Any rule that has no CI twin |
| `github` | REST calls (PRs, checks, branches, open-PR creation) with `GITHUB_TOKEN` | Business decisions |
| CI workflow `factory-gates.yml` | Running every registered CI gate on `pull_request`; publishing the board summary | Deploys (unchanged pipelines) |

### Topology & runtime custody

The gate rule for this section applies to browser UI + protected API. There is neither, so it is filled for completeness:

- **Runtimes / hosts**: (1) the `factory` CLI in the Codespace, used by the orchestrator, workers, and hooks; (2) GitHub Actions `factory-gates.yml` on `pull_request`. No servers.
- **How UI calls API**: N/A (the CLI reads git and GitHub directly).
- **Secret custody**: `GITHUB_TOKEN` comes from the environment (Codespace for local, Actions-provided for CI). No spend keys. Under D4-A, the GitHub App private key lives in Infisical and the name goes in `deploy/secrets/schema.yaml`.
- **Cattle manifests**: `factory.toml`, `.github/workflows/factory-gates.yml`, `.cursor/hooks.json`, `.pre-commit-config.yaml`, `.github/CODEOWNERS`, `scripts/factory/gates.yaml`. Branch-protection required checks are a one-time ops step; a script snapshots them to `deploy/github/branch-protection.json` and a check compares it with the live settings (drift check = P3 per D1, so P1 records the snapshot only).

### Governor identity *(architecture decision — spec D4, `who: human`)*

Today the governor and every agent act as one GitHub account. So "only the governor may override" (FR-020) and "governor approval for rule changes" (FR-031) can be recorded but not enforced.

| Option | What changes | Services / secrets | Ops steps (governor) | Cost | Enforces FR-020 / FR-031 |
|--------|--------------|--------------------|----------------------|------|--------------------------|
| **A. Agents get their own identity (GitHub App)** — recommended | Agents push and open PRs as the App; the governor reviews and approves as themselves; CODEOWNERS + "require code-owner review" on rule paths; governor-only overrides = a governor PR review or approval-gated label check | 1 GitHub App; private key in Infisical; `factory` mints 1-hour installation tokens | Create the App (~20 min), install it on the repo, store the key, set branch protection | Free | **Yes** (GitHub-verified identity) |
| **B. Governor signs decisions** | Governor-only messages carry an SSH signature; gates verify against `allowed_signers` in git | None new; the key stays on the governor's own device (passphrase or hardware) | Set up a signing key outside the Codespace; Codespaces commit auto-signing stays off | Free | Yes for overrides and decisions; rule-path approval still needs A or trust |
| **C. Recorded only** | `actor: governor` field; board marks these actions **unverified**; post-mortem audits | None | None | Free | **No** (honor system) |

**Locked 2026-10-03: option A, set up during Wave 1.** Mechanics:
- The `identity` adapter starts in recorded-only mode. When the App is live, it switches to verified mode: a governor-only message counts only when the PR containing it has an approving review from the governor's account.
- Agents' git pushes and REST calls use 1-hour installation tokens minted by `factory` from the App key: a repo-local credential helper for git, and the `github` adapter for REST.
- Secret names `FACTORY_GITHUB_APP_ID` and `FACTORY_GITHUB_APP_PRIVATE_KEY` go in `deploy/secrets/schema.yaml` (Infisical, Codespace target).
- Branch protection on `main`: required factory checks, plus code-owner review on rule paths (`.github/CODEOWNERS`).

Until the App is live, the board marks governor-only actions **unverified**, and FR-020/FR-031 count as not yet enforced in effective coverage (SC-005b).

### Data & persistence

- Entities: [`data-model.md`](./data-model.md). The run identity is the **order id** (`wo-YYYYMMDD-<slug>`), which names the branch `wo/<order-id>` and the bus folder. Run measurements are append-only events (`claim`, `release`, `run-complete`), aggregated on read — no message is ever updated.
- Durable: every bus message (git). Ephemeral: lifecycle snapshots and the board (recomputed on read), gate run outputs (CI logs + job summary).

### APIs & contracts

- CLI commands and exit codes: [`contracts/cli.md`](./contracts/cli.md).
- Message schemas: [`contracts/messages.md`](./contracts/messages.md) (Pydantic → JSON Schema at `scripts/factory/schemas/`).
- Gate registry and CI check names: [`contracts/gates.md`](./contracts/gates.md).
- Hooks: [`contracts/hooks.md`](./contracts/hooks.md).

### UI surfaces

- `factory status [--json]`: the board. Same content in the PR job summary.
- `factory decisions`: the governor's batch, showing open decision requests in plain language (from `bus/decisions/*/request.yaml` without a lock).

### Major risks / non-goals for this architecture

- **Single identity until the GitHub App is live (D4-A)**: governor-only actions are marked unverified until then. Mitigation: unverified marking + audit; App setup is a Wave 1 ops step.
- **Decision requests asked in chat**: a question can still bypass the bus file. Mitigation: the `stop` hook warns when the session's last assistant turn asked the governor something and no new `bus/decisions/` request exists. Post-mortem routing count (SC-010).
- **Self-reported metrics**: governor minutes and agent cost are self-reported in decision locks and handoffs. Flagged as estimates on the scorecard.
- **Red-first false reds**: base collection errors from unrelated breakage. Mitigation: the gate distinguishes "new test fails as expected" from "base suite broken" and reports which; drift-class override available.
- **Existing `pytest scripts/` in verify-source** would collect `scripts/factory/tests` without factory deps. Fix: verify-source adds `--ignore=scripts/factory`; `factory-gates.yml` runs the factory's own tests.
- Non-goals: hosted board, a second state store, an orchestration engine, migrating sprint-01 packets.

## Phased delivery *(mandatory)*

| Phase | Wave | Goal | Architecture pieces touched | Exit criteria (failable) |
|-------|------|------|-----------------------------|--------------------------|
| **P0 — contracts glue** (orchestrator tiny glue, ≤ ½ day) | 1 | Freeze shared contracts so three workers can run in parallel | `bus` models, `config`, registry format, JSON Schema export, empty `factory-gates.yml`, seeded-violation fixture layout | `factory check schema` validates the sample messages; JSON Schemas generated; contract tests exist and are red for unimplemented commands |
| **P1 — Wave 1 core** (3 parallel slices, disjoint paths) | 1 | Bus + board, drift gates, gate framework live as required checks | **Slice A** (`bus`, `lifecycle`, `board`, `metrics`, `github`, `identity`, `claim`): status, order issue, claim/release, PR open, run events, scorecard, GitHub App token minting + identity adapter (verified mode once the App exists). **Slice B** (`gates/drift/*`): red-first, test-seam, owned-paths, deferral-needs-OD, catalog-linkage, pr-links-order, intent presence, fidelity + lock tokens, decision-request-no-ids, order-blocked-on-open-OD. **Slice C** (`gates` core, `hooks`, workflow): registry + two classes + overrides + counts, hook-twin check, cap, verdict family + isolation, bus immutability | SC-013: within 5 working days of the first order, every P1 check is implemented and passing; SC-002 seeded-violation suite 100% blocked; SC-001 board agrees with reality on the spot-check fixture; SC-004 override accounting |
| **P1b — bootstrap close** | 1→2 boundary | Prove the gates on the PRs that built them | `gates` retro runner | SC-012: every Wave 1 PR has a bootstrap verdict and retro results; each failure remediated or overridden before any Wave 2 order is issued |
| **P2 — religion + learning** (during Wave 2, ≤ 3 workers shared with the SWV2 lanes) | 2 | Architecture religion, mining loop, rules-as-code, identity | Semgrep + import-linter pack; pattern rubric; corrections + repeat links + post-mortem gate; CODEOWNERS / identity adapter per D4; process-rule-cites-check; **constitution 2.0 as its own order + independent verdict**; lean always-applied rules; system-path hook (the advisory `subagentStart` spawn-guard moved to P1 slice C because FR-008's editor warning is P1); mutation gate (SWV2 Models lane) | SC-005b ≥ 90% effective coverage; SC-006 rule citations 100%; SC-007 mining loop live; mutation gate at 70% on changed lines; all by sprint close |
| **P3 — portability** | sprint 03 (D1 waived) | Fixture-repo proof, live config drift, secret scan, one-service manifest | — | Out of this version |

**MVP definition**: an orchestrator can issue an order, claim it (refused beyond 3 or on an open governor decision), have a worker open a PR from `wo/<id>`, and see it move through the board purely from git/PR/check reality. Every sprint-01 drift seed is blocked in CI, and every override is reasoned and counted. Nothing in the bus was hand-edited.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Pydantic v2, Typer, httpx (GitHub REST), PyYAML, PyJWT[crypto] (GitHub App JWT), pytest; CI tools: Semgrep CE, import-linter, mutmut 3 (P2)

**Storage**: git files (`bus/`); no database

**Testing**: pytest unit tests per gate against **seeded fixture repos** (temporary git repos built in tests: base commit + violating head); contract tests for CLI exit codes and JSON output; one GitHub-adapter test against recorded responses; the seeded-violation suite *is* SC-002

**Target Platform**: Codespaces (Nix + uv) and GitHub Actions `ubuntu-latest`

**Project Type**: repo tooling — uv project at `scripts/factory/` (not a registry app: no deployable service)

**Performance Goals**: hooks < 300 ms (offline, no network); `factory status` < 5 s with network; full gate run < 5 min on CI excluding mutation

**Constraints**: no `workflow_dispatch` from agents; no `pip install`; changed-lines-only for legacy code; gh CLI absent → REST via httpx

**Scale/Scope**: 1 governor, ≤ 3 workers, ~3 apps, tens of orders per sprint

## Constitution Check

- [x] Architecture section complete (blocks, boundaries, data, contracts, UI surfaces)
- [x] Topology & runtime custody: no browser UI or protected API; filled anyway, with no servers and token custody stated
- [x] Phased delivery present with MVP and failable exit criteria
- [x] `research.md` alternatives per major block include non-sibling SOTA/managed/OSS options (GitHub Projects, Beads, Linear, Temporal/Inngest, Copilot agent, Cursor SDK, CodeRabbit, Semgrep/ast-grep/CodeQL, TDD-Guard, Doorstop)
- [x] Orchestrator P1 lock: linear derived state machine + named migrate trigger
- [x] Plan Architecture review (P*) triaged — locks table below; governor approved 2026-10-03
- [x] No tasks/implement started
- [x] Secrets / registry / cattle: no new secret values; factory is not a registry app (no service); all config in git manifests
- [x] Learning/stack prefs not smuggled as product gates
- [x] PLAN_AUTHORING_GATES rules 2–6 satisfied (rule 5 N/A with reason)
- [x] Governor decision **D4** locked: GitHub App agent identity during Wave 1 (ops HITL in the sprint charter)

## Project Structure

### Documentation (this feature)

```text
specs/001-factory-v2/
├── spec.md · intent.yaml · acceptance.md
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/{cli,messages,gates,hooks}.md
├── SPEC_REVIEW.md · PROCESS_REVIEW.md · PLAN_REVIEW.md (P*)
└── tasks.md (after plan approval)
```

### Source Code (repository root)

```text
factory.toml                       # repo-specific config (bus dir, app roots, rule paths, cap, horizon, families)
bus/                               # append-only messages (orders, decisions, corrections, runs)
scripts/factory/
├── pyproject.toml · uv.lock
├── gates.yaml                     # gate registry
├── rubrics/patterns.yaml          # P2 pattern catalog
├── semgrep/                       # P2 rule pack
├── schemas/                       # generated JSON Schema
├── src/factory/{bus,lifecycle,board,gates,intent,metrics,hooks,github,config,identity}/
└── tests/{unit,contract,seeds}/   # seeds = SC-002 fixtures
.github/workflows/factory-gates.yml
.cursor/hooks.json
.pre-commit-config.yaml
.github/CODEOWNERS                 # Wave 1 slice A, per D4-A
```

**Structure Decision**: one uv project under `scripts/` because it is repo tooling, not app runtime (so not `modules/lab_shared`) and not a deployable (so not `apps/`). The package boundary is clean enough to extract into its own repo in sprint 03.

## Plan review locks *(P\*, [`PLAN_REVIEW.md`](./PLAN_REVIEW.md))*

| ID | Status | Lock |
|----|--------|------|
| **P1** | locked (agent — contract defect) | Run record replaced by append-only `claim` / `release` / `run-complete` events; aggregates derived on read |
| **P2** | locked (agent — contract defect) | Issuance never touches `main`: order = first commit of `wo/<id>`; decisions/corrections/post-mortems via schema-gated bus PRs; FR-005 unchanged |
| **P3** | locked (governor 2026-10-03) | Cap bites at claim + merge (authoritative); editor hook advisory; spec FR-008 letter waived "spawn" → "claim" |
| **P4** | locked (governor 2026-10-03) | Git stays the lease authority: branch per order, atomic claim push, release events, stale flagging (data-model § Lifecycle) |
| **P5** | locked (governor 2026-10-03, spec D4) | GitHub App agent identity during Wave 1; unverified marking until live |
| **P6** | locked (governor 2026-10-03) | Red-first needs a real test failure; import errors count only for names the PR itself adds (research § Red-first) |
| **P7** | Later → tasks | Freeze executable interfaces + shared fixtures at P0; integration checkpoints; 3-day target vs 5-day max |
| **P8** | accepted | Strength: alternatives coverage — preserve rows |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New CI tool (Semgrep) | Five architecture rules with changed-lines baselines | Hand-written AST pack would need its own tests and diff logic per rule |
