# Implementation Plan: Factory v2 — intent-fidelity gates, typed bus, derived board

**Branch**: `001-factory-v2` (work orders land on `main` via one branch + PR each) | **Date**: 2026-10-03 | **Spec**: [`spec.md`](./spec.md) (Approved)

**Input**: Feature specification `specs/001-factory-v2/spec.md`; intent [`intent.yaml`](./intent.yaml); research [`research.md`](./research.md); sprint charter [`notes/sprints/2026-10-sprint-02.md`](../../notes/sprints/2026-10-sprint-02.md).

**Lab rule (constitution §E):** Plan = **Architecture** + **Phased delivery**. No tasks or implement until both are human-approved after P* triage.

**Approval:** Architecture + Phased delivery approved by the governor 2026-10-03, after P* triage.

**Amended in place 2026-10-05 (constitution §G.1):** spec **D5** (trusted-base CI, governor lock after PR review PR-C1) changes the CI topology and trust boundary — § CI topology and trust boundary, Boundaries, Topology & runtime custody, Major risks, Phased delivery P1/P1b exits. Delta record: [`PLAN_DELTA.md`](./PLAN_DELTA.md). Round 2 the same day, after the delta P* review (`PLAN_REVIEW.md` § Delta review — D5): governor locks **D6** (probe, then pin), **D7** (red-first self-reported in Wave 1, sealed trusted run in Wave 2), **D8** (agents' App has no `statuses: write`); agent-adopted P9 (status source pinning) and P12 (artifact provenance, cache isolation).

## Summary

Replace sprint-01's prose process (mutable packets, free-text status, the human as router) with code: one `factory` Python package that (1) defines the bus as immutable, schema-validated message files in git; (2) derives every work item's state from git, PR, and check reality and renders one markdown board; (3) runs drift gates in CI as required checks — judged by the base branch's gate code, with the PR head treated only as data (D5) — mirrored by Cursor hooks; (4) records overrides, corrections, and run measurements so the scorecard and the religion-mining loop compute themselves. Wave 1 ships the P1 gates under bootstrap verdicts; P2 (architecture lints, rubric, mining loop, constitution 2.0, mutation) completes during Wave 2.

## Architecture *(mandatory — first-class)*

### System building blocks

- **UI / clients**: `factory status` markdown board (terminal + chat), the same board in the GitHub Actions job summary of the trusted gates run for every PR, linked from each `factory/*` status (D5). No web UI (I-X5).
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
| CI workflow `factory-pr-evidence.yml` (read-only, `pull_request`) | Running the PR head's own factory tests; producing execution evidence (red-first) as an untrusted artifact | Any status write; judging the PR (D5) |
| CI workflow `factory-gates.yml` (trusted, `workflow_run`) | Running every registered CI gate from `main`'s code over the PR head as data; posting `factory/<gate-id>` statuses; publishing the board summary | Executing any PR-head code; deploys (unchanged pipelines) |

### Topology & runtime custody

The gate rule for this section applies to browser UI + protected API. There is neither, so it is filled for completeness:

- **Runtimes / hosts**: (1) the `factory` CLI in the Codespace, used by the orchestrator, workers, and hooks; (2) GitHub Actions: the read-only `factory-pr-evidence.yml` on `pull_request` and the trusted `factory-gates.yml` on `workflow_run` (§ CI topology and trust boundary, D5). No servers.
- **How UI calls API**: N/A (the CLI reads git and GitHub directly).
- **Secret custody**: `GITHUB_TOKEN` comes from the environment (Codespace for local, Actions-provided for CI). In CI, `statuses: write` exists only in the trusted `factory-gates` job, which runs `main`'s code and never executes PR-head code (D5). No other identity holds `statuses: write`: not the agents' App (D8), and not any token the factory mints (P9). No spend keys. Under D4-A, the GitHub App private key lives in Infisical and the name goes in `deploy/secrets/schema.yaml`.
- **Cattle manifests**: `factory.toml`, `.github/workflows/factory-pr-evidence.yml`, `.github/workflows/factory-gates.yml`, `.cursor/hooks.json`, `.pre-commit-config.yaml`, `.github/CODEOWNERS`, `scripts/factory/gates.yaml`. Branch-protection required checks are a one-time ops step; a script snapshots them to `deploy/github/branch-protection.json` and a check compares it with the live settings (drift check = P3 per D1, so P1 records the snapshot only).

### CI topology and trust boundary *(architecture decision — spec D5, locked 2026-10-05)*

`factory/*` statuses decide merges, so whatever can write them is the factory's trust root. The first Slice C design ran PR-head code (`uv sync` + `factory gate run` from the head checkout) in a job holding `statuses: write`, so a PR could rewrite its own judge or take the token (PR review PR-C1). D5 splits CI into an untrusted half and a trusted half:

| | `factory-pr-evidence.yml` — **untrusted** | `factory-gates.yml` — **trusted** |
|---|---|---|
| Trigger | `pull_request` | `workflow_run` on "Factory PR evidence" `completed` (any conclusion). GitHub runs this workflow file from the default branch |
| Permissions | `contents: read` only, set at workflow level; no secrets; cannot post `factory/*` statuses | `contents: read`, `pull-requests: read`, `actions: read` (artifact download), `statuses: write` |
| Code that runs | The PR head's own factory test suite (`factory-tests`), and `main`'s red-first harness executing the head's new and changed tests (`red-first-evidence`) | Only `main`'s code: the checkout is the default branch, and `uv sync --locked` uses `main`'s `scripts/factory` lock |
| Head treated as | Executed code (tests) | Data only: head commits fetched as git objects (no checkout, no worktree), read through `git show` / `git archive` into a temp dir; the head's bus messages, `gates.yaml`, hooks and tests are inspected, never executed or imported |
| Output | Its own job checks (`Factory tests`, required by name at T066) + artifact `factory-evidence` (an untrusted evidence bundle) | One commit status `factory/<gate-id>` per registered CI gate on the PR head SHA, posted as GitHub Actions, the only source branch protection accepts (P9). The `red-first-proof` description says "self-reported" in Wave 1 (D7). The board goes in the run's job summary, linked from every status |

**Rules (contract: [`contracts/gates.md`](./contracts/gates.md) § CI topology and trust boundary).**

- **Trusted base.** `main`'s registry (`scripts/factory/gates.yaml` in the trusted checkout) decides which gates run and which entrypoints they call. The head's registry is data: `gate.fail-mode-category` and `hook-has-ci-twin` validate it (T-C2 unchanged), but it never selects or loads code. Overrides are read from the head's bus as data and resolved by `main`'s code.
- **Execution-derived evidence (D7).** A gate that needs head code executed (today only `red-first-proof`) splits in two:
  - **Wave 1:** the untrusted workflow runs the tests and writes the evidence bundle. The trusted gate validates the bundle as data (schema, bound to the run's head SHA, every test in it lies in a test file the diff adds or changes, every such file accounted for) and judges from it. A missing, malformed or mismatched bundle fails the gate closed. The binding prevents mix-ups, not fabrication: head test code could forge its own outcomes. So the result is **self-reported**, the status description and contracts say so, and the independent T* reviewer's re-run is the proof of record for FR-012 (delta P* P10).
  - **Wave 2:** a **sealed trusted run** replaces the bundle. `main`'s harness runs head tests in a locked-down sandbox with no credentials: `persist-credentials: false`, a separate user or container, a read-only head tree, and outcomes recorded by the parent, never by head code. Shape per P19 (confirmation round 2, adopted verbatim): "move the sealed runner and runner-owned outcome capture to a separate job with no status-write permission, then have the privileged publisher validate that exact job/run result without executing head code." The status-writing job never runs head code, not even sandboxed. A Wave 2 P* confirmation of this design gates T104's implementation.
- **Existing validators.** The existing validators (`validate-secrets-schema`, `validate-deploy-env`) run `main`'s scripts against the exported head tree; they parse with `ast`/YAML and import nothing from it.
- **Identity of the PR comes from GitHub, never from the artifact.** The trusted job takes the PR number and head SHA from the `workflow_run` event payload, confirms them through REST, and posts statuses only to that SHA, only when it is still the PR's head (otherwise it posts nothing; the newer run judges the newer head).
- **Effect of gate changes.** Because `workflow_run` always runs `main`'s workflow file and the trusted job only runs `main`'s code, a PR that edits a gate, the registry, the runner or either workflow is judged by `main`'s current gates. Its new gates take effect for PRs judged after it merges.
- **Artifact provenance and a clean privileged environment (P12).** The trusted job downloads `factory-evidence` only from the exact triggering run (`github.event.workflow_run.id`), only from this repository, and only by the exact artifact name, into a fresh directory outside the checkout. It rejects zero or several matches and refuses a run whose head repository is not this one. It runs on a fresh GitHub-hosted runner and never restores a cache the PR workflow can write: no `actions/cache`, no `setup-uv`/`setup-python` cache restore.
- **Status source (P9, D8).** Branch protection requires every `factory/*` context with the GitHub Actions integration as its expected source. The snapshot `deploy/github/branch-protection.json` records that integration/app id per context, and `branch-protection-require-pr` asserts it. Non-CI identities the factory controls never get `statuses: write`: the agents' App (D8) and any token the factory mints. The Codespace user token can still post statuses. Pinning is what makes such a status, or a same-named check run from any other source, unable to satisfy the requirement.
- **Bootstrap (D6: probe, then pin).** Until Slice C merges, `main` has no runner and no trusted workflow, so no `factory/*` statuses are posted for C's own PR (or for any earlier Wave 1 PR). The sequence:
  1. C merges on its FR-037 bootstrap verdict plus governor approval.
  2. Merges freeze. A non-merging probe PR obtains trusted `factory/*` statuses, so GitHub Actions is now a known source for every context.
  3. The governor requires every `factory/*` context with GitHub Actions pinned as expected source.
  4. The live rule is read back and verified against the snapshot.
  5. Only then do other merges reopen. No merge happens between steps 1 and 4.

  Phase 9 retro replays `main`'s gates over the Wave 1 PRs as data.
- **Banned.** `pull_request_target` combined with checkout or execution of head code, anywhere in `.github/workflows/`. Cache restore in the trusted workflow. Artifact download by pattern or from any run other than the triggering one. Only `github.event.workflow_run.id`, the head SHA and the PR number reach shell steps, and only through `env:` (branch names and titles never do).

Alternatives (single job with `statuses: write`, `pull_request_target` with a base checkout, rulesets-required workflows, a hosted GitHub App bot): [`research.md`](./research.md) § Topology & runtime custody.

### Governor identity *(architecture decision — spec D4, `who: human`)*

Today the governor and every agent act as one GitHub account. So "only the governor may override" (FR-020) and "governor approval for rule changes" (FR-031) can be recorded but not enforced.

| Option | What changes | Services / secrets | Ops steps (governor) | Cost | Enforces FR-020 / FR-031 |
|--------|--------------|--------------------|----------------------|------|--------------------------|
| **A. Agents get their own identity (GitHub App)** — recommended | Agents push and open PRs as the App; the governor reviews and approves as themselves; CODEOWNERS + "require code-owner review" on rule paths; governor-only overrides = a governor PR review or approval-gated label check | 1 GitHub App; private key in Infisical; `factory` mints 1-hour installation tokens | Create the App (~20 min), install it on the repo, store the key, set branch protection | Free | **Yes** (GitHub-verified identity) |
| **B. Governor signs decisions** | Governor-only messages carry an SSH signature; gates verify against `allowed_signers` in git | None new; the key stays on the governor's own device (passphrase or hardware) | Set up a signing key outside the Codespace; Codespaces commit auto-signing stays off | Free | Yes for overrides and decisions; rule-path approval still needs A or trust |
| **C. Recorded only** | `actor: governor` field; board marks these actions **unverified**; post-mortem audits | None | None | Free | **No** (honor system) |

**Locked 2026-10-03: option A, set up during Wave 1.** Mechanics:
- The `identity` adapter starts in recorded-only mode. When the App is live, it switches to verified mode: a governor-only message counts only when the PR containing it has an approving review from the governor's account.
- Agents' git pushes and REST calls use 1-hour installation tokens minted by `factory` from the App key: a repo-local credential helper for git, and the `github` adapter for REST. The App has **no `statuses: write`** (D8, 2026-10-05): only CI posts `factory/*` statuses.
- Secret names `FACTORY_GITHUB_APP_ID` and `FACTORY_GITHUB_APP_PRIVATE_KEY` go in `deploy/secrets/schema.yaml` (Infisical, Codespace target).
- Branch protection on `main`: required factory checks, plus code-owner review on rule paths (`.github/CODEOWNERS`).

Until the App is live, the board marks governor-only actions **unverified**, and FR-020/FR-031 count as not yet enforced in effective coverage (SC-005b).

### Data & persistence

- Entities: [`data-model.md`](./data-model.md). The run identity is the **order id** (`wo-YYYYMMDD-<slug>`), which names the branch `wo/<order-id>` and the bus folder. Run measurements are append-only events (`claim`, `release`, `run-complete`), aggregated on read — no message is ever updated.
- Durable: every bus message (git). Ephemeral: lifecycle snapshots and the board (recomputed on read), gate run outputs (CI logs + job summary), and the `factory-evidence` artifact (untrusted input to the trusted job, D5).

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
- **Existing `pytest scripts/` in verify-source** would collect `scripts/factory/tests` without factory deps. Fix: verify-source adds `--ignore=scripts/factory`; `factory-pr-evidence.yml` runs the factory's own tests (read-only, D5).
- **Red-first is self-reported in Wave 1 (D7)**: its outcomes come from a job that executes head tests, so test code in the diff could tamper with the harness and forge its own outcomes. Accepted for Wave 1, and stated in the status description. The T* reviewer's independent re-run is the proof of record; the bundle binding and fail-closed rules catch mix-ups; no status write is reachable from that job. Closed in Wave 2 by the sealed trusted run (T104).
- **Sealed run (D7, Wave 2)**: closed in shape by P19. The sealed runner and its parent-owned outcome capture run in a separate job with no status-write permission, so head code never shares a job with the status token (D5 kept to the letter). Residual: the publisher must treat the sealed job's result as hostile data and bind it to that exact job/run. T104's tests prove this, and a Wave 2 P* confirmation of the design comes before T104 is implemented.
- **`factory/*` statuses posted outside CI**: closed by source pinning (P9) and D8. Residual: a mis-set branch-protection rule; `branch-protection-require-pr` asserts the pinned source in the snapshot, and T103 verifies the live rule (live drift detection is P3 → sprint 03 per D1).
- **Bootstrap window (D5/D6)**: Slice C's own PR is not machine-judged by trusted gates. Mitigation: bootstrap verdict + governor approval, a merge freeze until the probe PR has proven trusted statuses and the pinned rule is verified live, then Phase 9 retro replays `main`'s gates over C.
- Non-goals: hosted board, a second state store, an orchestration engine, migrating sprint-01 packets.

## Phased delivery *(mandatory)*

| Phase | Wave | Goal | Architecture pieces touched | Exit criteria (failable) |
|-------|------|------|-----------------------------|--------------------------|
| **P0 — contracts glue** (orchestrator tiny glue, ≤ ½ day) | 1 | Freeze shared contracts so three workers can run in parallel | `bus` models, `config`, registry format, JSON Schema export, empty `factory-gates.yml`, seeded-violation fixture layout | `factory check schema` validates the sample messages; JSON Schemas generated; contract tests exist and are red for unimplemented commands |
| **P1 — Wave 1 core** (3 parallel slices, disjoint paths) | 1 | Bus + board, drift gates, gate framework live as required checks | **Slice A** (`bus`, `lifecycle`, `board`, `metrics`, `github`, `identity`, `claim`): status, order issue, claim/release, PR open, run events, scorecard, GitHub App token minting + identity adapter (verified mode once the App exists). **Slice B** (`gates/drift/*`): red-first, test-seam, owned-paths, deferral-needs-OD, catalog-linkage, pr-links-order, intent presence, fidelity + lock tokens, decision-request-no-ids, order-blocked-on-open-OD. **Slice C** (`gates` core, `hooks`, workflow): registry + two classes + overrides + counts, hook-twin check, cap, verdict family + isolation, bus immutability | SC-013: within 5 working days of the first order, every P1 check is implemented and passing; SC-002 seeded-violation suite 100% blocked; SC-001 board agrees with reality on the spot-check fixture; SC-004 override accounting; **D5/D6:** Slice C merges on the bootstrap path, then merges freeze. A non-merging probe PR receives one `factory/<gate-id>` status per P1 gate from the trusted `workflow_run` job running `main`'s code, and a probe edit that makes a gate always pass is still failed by `main`'s gate. Branch protection then requires every `factory/*` context pinned to GitHub Actions. The live rule is read back and matches the snapshot. Only then do merges reopen. The workflow contract test proves no job holding `statuses: write` checks out or executes head code, the evidence artifact comes only from the triggering run, and no cache is restored (P12) |
| **P1b — bootstrap close** | 1→2 boundary | Prove the gates on the PRs that built them | `gates` retro runner (runs `main`'s gates over each Wave 1 PR as data, D5) | SC-012: every Wave 1 PR has a bootstrap verdict and retro results; each failure remediated or overridden before any Wave 2 order is issued |
| **P2 — religion + learning** (during Wave 2, ≤ 3 workers shared with the SWV2 lanes) | 2 | Architecture religion, mining loop, rules-as-code, identity | Semgrep + import-linter pack; pattern rubric; corrections + repeat links + post-mortem gate; CODEOWNERS / identity adapter per D4; process-rule-cites-check; **constitution 2.0 as its own order + independent verdict**; lean always-applied rules; system-path hook (the advisory `subagentStart` spawn-guard moved to P1 slice C because FR-008's editor warning is P1); mutation gate (SWV2 Models lane); sealed trusted red-first run (D7) | SC-005b ≥ 90% effective coverage; SC-006 rule citations 100%; SC-007 mining loop live; mutation gate at 70% on changed lines; red-first judged from a sealed trusted run with parent-recorded outcomes, its status no longer "self-reported" (D7); all by sprint close |
| **P3 — portability** | sprint 03 (D1 waived) | Fixture-repo proof, live config drift, secret scan, one-service manifest | — | Out of this version |

**MVP definition**: an orchestrator can issue an order, claim it (refused beyond 3 or on an open governor decision), have a worker open a PR from `wo/<id>`, and see it move through the board purely from git/PR/check reality. Every sprint-01 drift seed is blocked in CI, and every override is reasoned and counted. Nothing in the bus was hand-edited.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Pydantic v2, Typer, httpx (GitHub REST), PyYAML, pytest; CI tools: Semgrep CE, import-linter, mutmut 3 (P2)

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
- [x] Governor decision **D5** locked 2026-10-05 (trusted-base CI): architecture-affecting → amended in place per §G.1 ([`PLAN_DELTA.md`](./PLAN_DELTA.md)); delta P* review run (`PLAN_REVIEW.md` § Delta review — D5, not approved) and triaged: governor locks **D6** (probe, then pin), **D7** (red-first strength per wave), **D8** (no `statuses: write` for the agents' App), all architecture-affecting and reconciled in place; P9 and P12 adopted. A narrow P* confirmation comes next

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
.github/workflows/factory-pr-evidence.yml   # untrusted: pull_request, contents: read (D5)
.github/workflows/factory-gates.yml         # trusted: workflow_run, main's code, statuses: write (D5)
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
