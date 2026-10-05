# Contract — gate registry and CI checks

Registry: `scripts/factory/gates.yaml` (schema in [`../data-model.md`](../data-model.md) § Gate). CI is split into an untrusted and a trusted workflow (spec D5, FR-022a; § CI topology and trust boundary below). The trusted workflow `.github/workflows/factory-gates.yml` runs every registered CI gate from `main`'s code. Each gate reports a separate commit status `factory/<gate-id>` so branch protection can require each one.

## CI topology and trust boundary (D5, locked 2026-10-05)

**Workflows.**

| Workflow / job | Trigger | Permissions | Runs | Posts |
|----------------|---------|-------------|------|-------|
| `factory-pr-evidence.yml` ("Factory PR evidence") / `factory-tests` | `pull_request` | `contents: read` only (workflow level); no secrets | The head's own factory suite: `uv sync --locked` + `uv run pytest` in `scripts/factory`, full suite with no marker/keyword selector once Slices A and B are merged into C (PR-C5) | Its own job check only (`Factory tests`) |
| same workflow / `red-first-evidence` | `pull_request` | same | `main`'s red-first harness (checked out from `main` beside the head) executing the head's new and changed tests on base and head | Artifact `factory-evidence` (the evidence bundle) |
| `factory-gates.yml` ("Factory gates") / `factory-gates` | `workflow_run`: workflows `["Factory PR evidence"]`, types `[completed]` (any conclusion) | `contents: read`, `pull-requests: read`, `actions: read`, `statuses: write` | Only `main`'s code: default-branch checkout (no `ref:`), `persist-credentials: false`, `uv sync --locked --project scripts/factory` from `main`'s lock; `factory gate run --pr <N> --expect-head <sha> --evidence <dir>`; `factory status` into `$GITHUB_STEP_SUMMARY` | One `factory/<gate-id>` commit status per registered CI gate on the head SHA; `target_url` = this run |

**Head as data (trusted job).** Head commits are fetched as git objects (`git fetch --no-tags origin <head sha>`) and read only through `git show`, `git ls-tree`, `git diff` and `git archive` into a temporary directory outside the checkout. The trusted job never checks out the head, never creates a worktree for it, and never executes, imports or `uv sync`s anything from it: no head `pyproject.toml`/`uv.lock` install, no head scripts, no head tests, no head hooks.

**Which gates run.** `main`'s registry in the trusted checkout selects the gates and their entrypoints (`load_registry()` of the installed package). The head's `scripts/factory/gates.yaml` and `.cursor/hooks.json` are data: `gate.fail-mode-category`, `hook-has-ci-twin` and `factory check registry` validate them and block when they are missing or invalid (T-C2 unchanged). The head's registry never adds, removes or rewires a gate for its own run.

**Gate changes take effect after merge.** `workflow_run` takes the workflow file from the default branch, and the trusted job runs only `main`'s package. So a PR that changes a gate module, the registry, the runner, `overrides.py` or either workflow is judged by `main`'s current gates; its changes judge later PRs once merged (D5).

**Overrides.** Override messages are read from the head's `bus/orders/<order-id>/` as data and resolved by `main`'s `overrides.py` (§ Override resolution unchanged).

**Execution-derived gates.** A gate whose verdict needs head code executed takes its evidence from the bundle. Today that is only `red-first-proof`. Every other P1 gate judges git data directly in the trusted job. The existing validators run `main`'s `scripts/validate_secrets_schema.py` / `scripts/validate_deploy_env.py` against the exported head tree (they parse with `ast`/YAML and import nothing from it). A gate added later that needs head execution must declare it and get the same split (D5).

**Evidence bundle (`factory-evidence`, untrusted).** It is a Pydantic-modelled JSON document validated by `main`'s code, carrying at least `schema_version`, `base_sha`, `head_sha`, and for red-first each node id with its base and head outcome (and the base error class the red-first rule needs). The trusted gate fails closed, naming the reason, when the bundle is absent, unreadable, over the size limit in typed config, fails its schema, carries a `head_sha` other than the run's head, lists a test outside the test files the diff adds or changes, or omits such a file. The bundle never supplies the PR number, head SHA, base ref, order id or registry.

**PR identity and status target.** The PR number and head SHA come from the `workflow_run` event payload (`github.event.workflow_run.pull_requests`, `.head_sha`) and are confirmed through REST (same-repository PR, open, head SHA equal). If the PR's head has moved, the run posts nothing and exits 0; the newer evidence run triggers a newer judgment. Statuses go only to that head SHA.

**Shell interpolation.** Only `github.event.workflow_run.id`, the head SHA and the PR number reach `run:` steps, and only through `env:`. Branch names, titles, bodies and artifact contents never appear in a `${{ }}` expression inside `run:`.

**Bootstrap.** Before Slice C merges, `main` has neither the runner nor `factory-gates.yml`, so no `factory/*` status is posted for C's own PR. C merges on its FR-037 bootstrap verdict plus governor approval (D5); its sequence against the T066 required checks is spec **D6** (open). Phase 9 `factory retro` replays `main`'s gates over every Wave 1 PR as data.

**Banned (workflow contract test).** `pull_request_target` in any `.github/workflows/*` file that checks out or executes head code. Any job holding `statuses: write` (or `secrets.*`) on a `pull_request` trigger. Any `actions/checkout` `ref:` naming the head (`github.event.pull_request.head.*`, `github.event.workflow_run.head_*`, `refs/pull/*`) in the trusted workflow.

## Override resolution

A gate that fails looks for `bus/orders/<order-id>/override-NN.yaml` with `gate: <id>` in the PR head (read as data by `main`'s code, D5):

- `class: drift` → override by `orchestrator` or `governor` with a reason → status `success` with summary "overridden: <reason>"; counted.
- `class: governor-only` → override must have `actor: governor` and (under D4-A/B) a verified identity; otherwise stays `failure`.

## P1 registry (Wave 1)

| Gate id | Class | Category | Intents | Scope |
|---------|-------|----------|---------|-------|
| `bus.schema` | drift | drift | I-M2 | repo |
| `bus.immutable` | drift | drift | I-M2 | changed |
| `bus.no-handwritten-status` | drift | drift | I-M2 | changed |
| `factory-check-intent` (presence) | drift | drift | I-N1, I-P4 | repo |
| `red-first-proof` | drift | drift | I-B7, I-P2 | changed |
| `test-seam-ban` | drift | drift | I-A8 | changed |
| `diff-within-owned-paths` | drift | drift | I-B8, I-A8 | changed |
| `deferral-words-need-od` | drift | drift | I-B6 | changed (specs/**) |
| `order-fidelity-declared` + `lock.letter-tokens` | drift | drift | I-B5 | changed |
| `decision-request-no-ids` | drift | drift | I-B3 | changed |
| `catalog-test-linkage` | drift | drift | I-B7 | changed |
| `pr-links-order` | drift | drift | I-P1 | PR |
| `order-blocked-on-open-human-od` | governor-only | governor_decision | I-X3 | PR |
| `spawn-concurrency-cap` | drift | drift | I-X4 | PR |
| `verdict.reviewer-family-differs` + `verdict.inputs-isolated` | drift | drift | I-P3 | PR |
| `message.override` | governor-only | governor_decision | I-M1, I-P9 | PR |
| `gate.fail-mode-category` | drift | drift | I-P9 | repo |
| `hook-has-ci-twin` | drift | drift | I-G5 | repo |
| `branch-protection-require-pr` | governor-only | irreversible | I-P10 | repo — compares `deploy/github/branch-protection.json` with the expected settings: PR required, bypass off for everyone, required `factory/*` checks, code-owner review |
| `factory-status-test` | drift | drift | I-M4 | repo (unit) |
| existing: `validate-secrets-schema` | governor-only | secrets | I-O2, I-A3 | repo |
| existing: `validate-deploy-env`, `uv-sync-locked` | drift | drift | I-O1, I-O3 | repo |

**Deferral-words rule detail:** in `specs/**` and `notes/sprints/**`, the words *later, optional, deferred, TBD, future, stretch* need, on the same line or table row, one of: an Open Decision id that exists (`D\d+`), a pointer `→ <artifact>` to an existing file or phase (`→ plan`, `→ sprint 03` with a waived OD), or `[governor-judged]`. Spec-review tables ("Later → plan") satisfy it by pointer. Words inside backtick code spans (enum values, quoted rule text) are exempt.

## P2 registry (Wave 2, by sprint close)

`import-layers`, `agent-has-output-type`, `banned-getenv-outside-config`, `vendor-imports-only-in-adapters`, `generic-identifier-ban`, `lab-shared-declares-consumers`, `new-dependency-needs-decision-ref`, `research-decision-has-nonsibling-alt`, `od.arch-options-have-consequences`, `od.plain-options`, `message.correction` + `repeated-corrections`, `sprint-close-requires-postmortem`, `codeowners-governor-on-rule-paths` (governor-only, per D4), `process-rule-cites-check`, `mutation-changed-lines` (70%), `block-system-path-edits` (hook + CI twin).
