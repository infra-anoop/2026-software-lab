# Contract — gate registry and CI checks

Registry: `scripts/factory/gates.yaml` (schema in [`../data-model.md`](../data-model.md) § Gate). CI is split into an untrusted and a trusted workflow (spec D5, FR-022a; § CI topology and trust boundary below). The trusted workflow `.github/workflows/factory-gates.yml` runs every registered CI gate from `main`'s code. Each gate reports a separate commit status `factory/<gate-id>`. **Amended 2026-10-06 (governor, `PLAN_DELTA.md` Round 5):** a full `--pr` run (no `--gate`) then posts one summary status, `factory/gates`, on the head SHA, after the per-gate statuses. It is `success` only when every CI gate in `main`'s registry ran in that invocation and each outcome is `pass` or `overridden`; otherwise `failure`, naming the failing gates within the 140-character description limit. Branch protection requires `factory/gates`; the per-gate statuses stay for diagnosis and lifecycle (T105) but are not required. A `--gate` run (any explicit list, even a full one) is a subset run and posts no summary; a moved head posts nothing.

## CI topology and trust boundary (D5, locked 2026-10-05; hardened by D6–D8, delta P* P9/P12)

**Workflows.**

| Workflow / job | Trigger | Permissions | Runs | Posts |
|----------------|---------|-------------|------|-------|
| `factory-pr-evidence.yml` ("Factory PR evidence") / `factory-tests` | `pull_request` | `contents: read` only (workflow level); no secrets | The head's own factory suite: `uv sync --locked` + `uv run pytest` in `scripts/factory`, full suite with no marker/keyword selector once Slices A and B are merged into C (PR-C5) | Its own job check only (`Factory tests`) |
| same workflow / `red-first-evidence` | `pull_request` | same | `main`'s red-first harness (checked out from `main` beside the head) executing the head's new and changed tests on base and head | Artifact `factory-evidence` (the evidence bundle) |
| `factory-gates.yml` ("Factory gates") / `factory-gates` | `workflow_run`: workflows `["Factory PR evidence"]`, types `[completed]` (any conclusion) | `contents: read`, `pull-requests: read`, `actions: read`, `statuses: write` | Only `main`'s code on a fresh GitHub-hosted runner with no cache restore: default-branch checkout (no `ref:`), `persist-credentials: false`, `uv sync --locked --project scripts/factory` from `main`'s lock; artifact download per § Artifact provenance; `factory gate run --pr <N> --expect-head <sha> --evidence <dir>`; `factory status` into `$GITHUB_STEP_SUMMARY` | One `factory/<gate-id>` commit status per registered CI gate on the head SHA, then the `factory/gates` summary (amended 2026-10-06, Round 5), posted with the job's `GITHUB_TOKEN` (source: GitHub Actions); `target_url` = this run. In Wave 1 the `red-first-proof` description starts `self-reported:` (D7) |

**Head as data (trusted job).** Head commits are fetched as git objects (`git fetch --no-tags origin <head sha>`) and read only through `git show`, `git ls-tree`, `git diff` and `git archive` into a temporary directory outside the checkout. The trusted job never checks out the head, never creates a worktree for it, and never executes, imports or `uv sync`s anything from it: no head `pyproject.toml`/`uv.lock` install, no head scripts, no head tests, no head hooks.

**Which gates run.** `main`'s registry in the trusted checkout selects the gates and their entrypoints (`load_registry()` of the installed package). The head's `scripts/factory/gates.yaml` and `.cursor/hooks.json` are data: `gate.fail-mode-category`, `hook-has-ci-twin` and `factory check registry` validate them and block when they are missing or invalid (T-C2 unchanged). The head's registry never adds, removes or rewires a gate for its own run.

**Gate changes take effect after merge.** `workflow_run` takes the workflow file from the default branch, and the trusted job runs only `main`'s package. So a PR that changes a gate module, the registry, the runner, `overrides.py` or either workflow is judged by `main`'s current gates; its changes judge later PRs once merged (D5).

**Overrides.** Override messages are read from the head's `bus/orders/<order-id>/` as data and resolved by `main`'s `overrides.py` (§ Override resolution unchanged).

**Execution-derived gates.** A gate whose verdict needs head code executed takes its evidence from the bundle. Today that is only `red-first-proof`. Every other P1 gate judges git data directly in the trusted job. The existing validators run `main`'s `scripts/validate_secrets_schema.py` / `scripts/validate_deploy_env.py` against the exported head tree (they parse with `ast`/YAML and import nothing from it). A gate added later that needs head execution must declare it and get the same split (D5).

**Evidence bundle (`factory-evidence`, untrusted; model owned by Slice C, T097).** The artifact holds exactly one file, `factory-evidence.json`: UTF-8 JSON, at most `evidence_max_bytes` (typed config in `factory.toml`, default 1 MiB). It is validated by `main`'s Pydantic model with unknown keys forbidden at every level:

| Field | Type | Meaning |
|-------|------|---------|
| `schema_version` | `1` | Bundle format version |
| `kind` | `"factory-evidence"` | Fixed |
| `base_sha`, `head_sha` | 40-hex strings | The pair the producer ran on |
| `red_first.status` | `"ran"` \| `"crashed"` | `crashed`: the producer could not produce facts (exception, run crash, timeout) |
| `red_first.error` | string \| null | Raw text when `crashed`; null when `ran` |
| `red_first.tests[]` | list | One raw fact per new or changed test function, sorted by `node_id`; empty when `crashed` |
| `tests[].node_id` | string | Repo-relative `path::name` (`path::Class::name`) |
| `tests[].base_outcome`, `tests[].head_outcome` | `passed` \| `failed` \| `error` \| `skipped` \| `not_collected` | pytest's outcome per side; `error` = setup or teardown error; `not_collected` = absent on that side or its file failed collection |
| `tests[].base_error` | string \| null | Raw collection or error text from the base run, unclassified |

**Raw facts, not classification.** Slice B's `red_first.collect_facts(ctx)` returns the raw per-test facts; the producer (`factory gate evidence`) only serializes them. A producer exception or an outcome word outside the vocabulary is written as `status: crashed` with the raw text, never as a guessed outcome. No field carries a judgment: words such as "red", "base broken" or "not red" are not outcome values, and an extra key (a `verdict`, a PR number, an order id) fails the schema. The trusted judge alone classifies, with the red-first rule of `red-first-proof` (a base `failed` is red; a base `error` / `not_collected` is red only when every missing name in `base_error` is a module or symbol the PR adds; every test must be `passed` on head).

**Fail closed.** The trusted gate fails, naming the reason, when the bundle is absent, unreadable (not UTF-8 or not JSON), over the size limit (checked before parsing), fails its schema, carries a `head_sha` other than the run's head, has `status: crashed`, lists a node that is not a new or changed test function, or omits one. The set of new and changed test functions is derived by `main`'s code from git data (AST over base and head sources, no execution). The bundle never supplies the PR number, head SHA, base ref, order id or registry.

**Red-first strength (D7).**
- **Wave 1:** the bundle is produced by a job that executes head tests, so its outcomes are **self-reported**: binding rules catch mix-ups, not fabrication. Every `red-first-proof` status description starts with `self-reported:`, and the gate's report says the outcomes came from the read-only run. For FR-012 the proof of record is the independent T* reviewer's re-run, recorded in the T* review.
- **Wave 2 (T104):** a **sealed trusted run** replaces the bundle as red-first's input. Per P19, the sealed runner and its runner-owned outcome capture run in a **separate job with no status-write permission**; the status-writing job executes no head code and validates only that exact job/run's parent-recorded result, as hostile data. In the sealed job, `main`'s harness runs the head's new and changed tests in a locked-down sandbox with no credentials:
  - `persist-credentials: false`, and no job token or runner directory reachable from the sandbox;
  - a separate user or container;
  - the head tree mounted read-only;
  - outcomes recorded by the parent process from the child's exit status and parent-side result capture, never from a file the head can write.

  The `self-reported:` prefix then goes.

**Artifact provenance (P12).** The trusted job downloads the evidence only:
- from the exact triggering run, `github.event.workflow_run.id`;
- from this repository: `github.event.workflow_run.repository` and `head_repository` must both equal `github.repository`, otherwise it posts nothing and exits 0;
- by the exact name `factory-evidence` (no `pattern:`, no `merge-multiple`);
- into a fresh temporary directory outside the checkout.

`factory gate run --evidence` accepts a directory holding exactly one file, `factory-evidence.json`. An empty directory, a missing `--evidence`, any other file name or any second file fails each execution-derived gate closed, naming the reason; the other gates still run.

**Privileged environment (P12).** The trusted job runs on a fresh GitHub-hosted runner. It restores no cache that any workflow triggered by a PR can write: no `actions/cache` (restore or save), `setup-uv` with `enable-cache: false`, no `setup-python` cache. Tools come from pinned actions and `main`'s lockfile only.

**Status source (P9, D8).** Only the trusted job posts `factory/*` statuses. Branch protection requires every `factory/*` context with the GitHub Actions integration as its expected source. **Amended 2026-10-06 (governor, `PLAN_DELTA.md` Round 5):** the one required `factory/*` context is `factory/gates`; the snapshot's required checks are exactly `Factory tests`, `Verify Source / verify` and `factory/gates`, each with `integration_id` 15368. Adding, renaming or removing a gate is a reviewed code change, not a ruleset edit. The snapshot `deploy/github/branch-protection.json` records, per required context, that integration's app id as read from the live API. **Amended 2026-10-06 (governor: a repository ruleset, not classic branch protection):** the snapshot is the "get a repository ruleset" body, and the entries are `rules[type=required_status_checks].parameters.required_status_checks[]` `{context, integration_id}`. `branch-protection-require-pr` compares every entry's `integration_id` with typed config `github.actions_app_id` (in `factory.toml`; 15368, read from live check runs 2026-10-06). An entry without an `integration_id`, with `-1` (any source) or with another app's id fails the gate. No identity the factory controls holds `statuses: write` besides the trusted job: the agents' App has none (D8), and the factory mints no token with it. A status or same-named check run from any other source (for example the Codespace user token) cannot satisfy the rule.

**PR identity and status target.** The PR number and head SHA come from the `workflow_run` event payload (`github.event.workflow_run.pull_requests`, `.head_sha`) and are confirmed through REST (same-repository PR, open, head SHA equal). If the PR's head has moved, the run posts nothing and exits 0; the newer evidence run triggers a newer judgment. Statuses go only to that head SHA.

**Shell interpolation.** Only `github.event.workflow_run.id`, the head SHA and the PR number reach `run:` steps, and only through `env:`. Branch names, titles, bodies and artifact contents never appear in a `${{ }}` expression inside `run:`.

**Bootstrap.** Before Slice C merges, `main` has neither the runner nor `factory-gates.yml`, so no `factory/*` status is posted for C's own PR. C merges on its FR-037 bootstrap verdict plus governor approval (D5). Then, per spec **D6** (probe, then pin):
1. Merges freeze.
2. A non-merging probe PR obtains trusted `factory/*` statuses.
3. Branch protection requires every `factory/*` context with GitHub Actions pinned as expected source. **Amended 2026-10-06 (governor, `PLAN_DELTA.md` Round 5):** the ruleset requires `factory/gates` (pinned, P9) instead of one context per gate; the probe PR is re-run after T107 merges, and `factory/gates` must fail on it.
4. The live rule is read back and verified against the snapshot.
5. Only then do merges reopen. No merge happens between C's merge and step 4.

Phase 9 `factory retro` replays `main`'s gates over every Wave 1 PR as data.

**Banned (workflow contract test).**
- `pull_request_target` in any `.github/workflows/*` file that checks out or executes head code.
- Any job holding `statuses: write` (or `secrets.*`) on a `pull_request` trigger.
- In the trusted workflow:
  - any `actions/checkout` `ref:` naming the head (`github.event.pull_request.head.*`, `github.event.workflow_run.head_*`, `refs/pull/*`);
  - any cache restore or save;
  - any artifact download by `pattern:`, with `merge-multiple`, from a `run-id` other than `github.event.workflow_run.id`, or from another repository.

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
| `branch-protection-require-pr` | governor-only | irreversible | I-P10 | repo — compares `deploy/github/branch-protection.json` (the `main` repository ruleset, amended 2026-10-06) with the expected settings: active branch ruleset on `refs/heads/main`, empty bypass list, rules `pull_request`, `required_status_checks`, `non_fast_forward`, `deletion`; required checks include `factory/gates` (amended 2026-10-06, governor, `PLAN_DELTA.md` Round 5: instead of every P1 `factory/<gate-id>` context) and each entry is pinned to the GitHub Actions app id (P9); the head registry must still be readable; code-owner review is required once `identity.mode = "verified"` (after T065) |
| `factory-status-test` | drift | drift | I-M4 | repo (unit) |
| existing: `validate-secrets-schema` | governor-only | secrets | I-O2, I-A3 | repo |
| existing: `validate-deploy-env`, `uv-sync-locked` | drift | drift | I-O1, I-O3 | repo |

**Deferral-words rule detail:** in `specs/**` and `notes/sprints/**`, the words *later, optional, deferred, TBD, future, stretch* need, on the same line or table row, one of: an Open Decision id that exists (`D\d+`), a pointer `→ <artifact>` to an existing file or phase (`→ plan`, `→ sprint 03` with a waived OD), or `[governor-judged]`. Spec-review tables ("Later → plan") satisfy it by pointer. Words inside backtick code spans (enum values, quoted rule text) are exempt.

**Deferral pointer targets (Slice B PR review, amendment-05):** a pointer's artifact counts only when it is a regular file blob at head (mode `100644` or `100755`) or a named phase. A tracked directory, symlink or gitlink does not count.

**Order `checks` kinds (amendment-06, amendment-08):** `catalog-test-linkage` classifies catalog rows first. An id that is a catalog row is always judged for linkage, even when it is also a registered gate id. An id that is no catalog row but is a registered gate belongs to that gate. An id that is neither blocks.

**Catalog-linkage rule detail:** every `how: auto` row in an `acceptance.md` carries `evidence`. A row whose id is in the PR's effective order `checks` must name existing evidence, not `planned` (FR-018). Rows the PR adds or edits and the order's rows are judged; untouched rows are not. Evidence is judged at the PR head in git, and Markdown backticks around the value are ignored. Two forms are accepted (governor 2026-10-04):

- **pytest node id** `<repo-relative path>::<test name>`: the file exists at head and defines that test.
- **eval case** `eval:<repo-relative path>#<case-id>`: the file is read as the git blob at the PR head (never the checkout) and contains a case with `id == <case-id>`. The file is YAML or JSON (a top-level list, or a `cases:` list, of mappings with an `id` key) or JSONL (one object per line with `id`). A reference with no `#`, an absolute path, or a `..` segment is malformed and blocks. A tracked symlink blocks, whatever it points to. Malformed YAML, JSON or JSONL (any bad line), a wrong top-level shape, a `cases` that is not a list, and an entry that is not a mapping with `id` all block.

## P2 registry (Wave 2, by sprint close)

`import-layers`, `agent-has-output-type`, `banned-getenv-outside-config`, `vendor-imports-only-in-adapters`, `generic-identifier-ban`, `lab-shared-declares-consumers`, `new-dependency-needs-decision-ref`, `research-decision-has-nonsibling-alt`, `od.arch-options-have-consequences`, `od.plain-options`, `message.correction` + `repeated-corrections`, `sprint-close-requires-postmortem`, `codeowners-governor-on-rule-paths` (governor-only, per D4), `process-rule-cites-check`, `mutation-changed-lines` (70%), `block-system-path-edits` (hook + CI twin).
