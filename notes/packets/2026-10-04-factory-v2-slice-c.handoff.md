# Handoff — 2026-10-04-factory-v2-slice-c

| Field | Value |
|-------|-------|
| Branch | `wo/wo-20261004-factory-slice-c` (pushed; draft PR #21) |
| State | **Implemented T055–T060, then Phase 6a T094–T099: every Slice C test green. T064 and the `red_first.py` split wait for Slice B; T100 for A and B** (see § Phase 6a phase 2) |
| Author model | Claude family (worker); one model for the whole run. The bootstrap verdict must come from a non-Anthropic reviewer (D3, FR-037) |
| Accept SHA (T* round 3) | **`9445788`**: `verdict-03` `decision: accept` (one strength nit, T-C3-1) |
| Tests since accept | Through T060, `git diff 9445788 -- scripts/factory/tests` was **empty**. Phase 6a: the round-4 oracle fix plus two one-line test repairs (listed in § Phase 6a phase 2) |
| Base | `origin/main` @ `c2af7f2` (CP0 merge `8cd8cb7`); Slice A (PR #20) is **not** merged here |
| Frozen CP0 files | not edited through T060. Phase 6a amended `api.py`, `config/settings.py` and `cli/app.py` additively under `amendment-06` |

## Commits

| SHA | Role |
|-----|------|
| `c5d1730`, `2997116`, `4bc0207` | **red**: tests T050–T053 (rounds 0, 1, 2) |
| `9445788` | review merge: accept, round 3 (`verdict-03`) |
| `d938443` | **green**: PR gates and bus gates (T056); `gates/pr/*`, `gates/repo/{_git,bus_schema}.py` |
| `c9f4256` | **green**: repo gates, registry rows, `check hooks\|registry\|immutability` (T056, T058, T059 registry part) |
| `fb7c391` | **green**: Cursor hooks package plus the `factory-hook` console script (T057) |
| `67c7ff9` | **green**: gate runner, override resolution, `factory override\|gate run\|hook` (T055, T058, T060 CLI) |
| `cb4eb3a` | `.cursor/hooks.json` and `.cursor/hooks/factory-hook.sh` (T057) — **flagged, see below** |
| `4e53801` | `.github/workflows/factory-gates.yml` made authoritative (T059) |
| `0baa329` | `acceptance.md` evidence cells (T060) and `tasks.md` T054–T060 ticked |
| (this commit) | this handoff |

Red/green pairs:

| Red | Green |
|-----|-------|
| T050 (`test_gate_run.py`) | `67c7ff9` (runner, CLI) and `4e53801` (workflow) |
| T051 (`unit/gates/pr/*`) | `d938443` |
| T052 (`test_registry_checks.py`) | `c9f4256` |
| T053 (`test_hooks.py`) | `fb7c391` and `cb4eb3a` |

## Commands and results

Toolchain: `nix develop ../.. -c uv sync --locked` in `scripts/factory` passed, using Nix-store `uv` and Python 3.12. No `pip install`.

| DoD | Command (in `scripts/factory`) | Result |
|-----|---------|--------|
| Slice C tests | `uv run pytest tests/unit/gates tests/unit/hooks tests/contract/test_gate_run.py` | **254 passed, 0 failed** |
| CI selector | `uv run pytest -m "not contract and not seed"` | **451 passed, 0 failed**, 156 deselected |
| full | `uv run pytest` | **505 passed, 102 failed**. Every failure is Slice A, Slice B, or out of scope (list below) |
| lint | `uv run ruff check .` / `uv run ruff format --check .` | PASS (70 files) |
| bus | `uv run factory check schema --repo ../..` | `schema ok` |
| lock | `uv lock --locked` | unchanged. A `[project.scripts]` line does not alter `uv.lock` |
| evidence ids | every test id written into `acceptance.md` by this slice | 19 ids, 80 cases, all pass |

### Remaining full-suite failures (102), all outside Slice C

| Owner | Failures | Cause |
|-------|---------:|-------|
| Slice A | `test_cli_contract.py`: `status`, `decisions`, `scorecard`, `order new/issue`, `claim`, `release`, `handoff`, `pr open`, `verdict`, `bus pr`, `correction new`, `sprint close`, and their `test_json_envelope[...]` cases | `factory <cmd>: not implemented` (PR #20 not merged) |
| Slice B | all 52 `tests/seeds/test_seeds.py` cases | `factory.gates.drift.*` not importable; the runner reports "not implemented" and fails closed |
| Slice B | `test_check_intent_exit_0`, `test_json_envelope[check intent]` | `factory check intent` not implemented |
| Slice B, plus a gate with no owner (below) | `test_check_registry_exit_0`, `test_json_envelope[check registry]` | `check registry` imports every entrypoint, and `factory.gates.drift.*`, `factory.intent.coverage` and `factory.gates.repo.status_test` are missing |
| T069 (Phase 9) | `test_retro_exit_0`, `test_json_envelope[retro]` | `factory retro` is out of scope |

Slice C's own P0 contract tests in `test_cli_contract.py` all pass (14 cases):
- `override`: 4 cases;
- `gate run`;
- `hook`: 2 cases;
- `check hooks`;
- `check immutability`;
- the `test_json_envelope` cases for those commands.

## Hook latency (wrapper end to end, as Cursor runs it)

The accepted test `test_live_hook_command_answers_within_budget` passes for all four hooks: median of 5 runs, under 300 ms, from the repo root with realistic fixture payloads.

Measured by hand on the live worktree (median of 5, through `.cursor/hooks/factory-hook.sh`):

| Hook | Median |
|------|------:|
| `shell-guard` (deny path) | 53 ms |
| `spawn-guard` (log path, refs and claims read) | 74 ms |
| `owned-path-warn` (warn path, YAML read) | 70 ms |
| `decision-in-chat` | 51 ms |

The fast path imports only stdlib modules plus `yaml`, which `owned-path-warn` loads lazily, and does no network I/O. It never imports `factory.api`, `bus.models`, pydantic, typer or click (enforced by the import-ban test). The `uv run` fallback costs about 370 ms. It is used only when `scripts/factory/.venv` was never synced.

## Flagged for governor approval at PR time (editor and agent behaviour)

- **`.cursor/hooks.json`** (new) registers four hooks for every agent in this repo, the main session included:
  - `subagentStart` → `spawn-guard`: **log-only**. It always returns `permission: "allow"`; any advisory goes to `user_message` in the Hooks output only. This matches the governor lock and FR-008 "logged".
  - `beforeShellExecution` → `shell-guard`: **denies** (exit 2) the following:
    - `git commit` while `main` is checked out;
    - any push whose destination is `main` (including `--all`, `--mirror` and `--branches`);
    - force pushes;
    - `pip install`, `python -m pip install` and `uv pip install`;
    - `gh workflow run`;
    - writes to `/etc`, `/usr` or `~/.config` outside the repo;
    - `nix-env -i`.
  - `postToolUse` (matcher `^(?:Write|Delete)$`) → `owned-path-warn`: warn-only, via `additional_context`.
  - `stop` → `decision-in-chat`: warn-only, via `followup_message`. Cursor auto-submits that message as a follow-up.
- **`.cursor/hooks/factory-hook.sh`** (new, mode 100755): execs `scripts/factory/.venv/bin/factory-hook`, else `uv run --project scripts/factory factory hook <name>`.
- Hooks fail open: a crash returns the quiet response, and CI is authoritative. They take effect only once merged to `main` and opened at the repo root. They do not affect this worktree's session.

## CI workflow change (`.github/workflows/factory-gates.yml`)

- The `factory-gates` job now has `statuses: write`. `continue-on-error` is removed, so the gate step is authoritative.
- The new `Board in job summary` step runs under `if: ${{ !cancelled() }}`: `factory status >> "$GITHUB_STEP_SUMMARY"`.
- **Consequence:** this job is **red on any PR until Slice A and Slice B land**:
  - `gate run --pr` needs Slice A's REST `GitHubPort` (T021). Without it, `gate run` exits EXTERNAL.
  - The Slice B drift gates and `factory-status-test` fail closed as "not implemented".
  - The summary step needs Slice A's `factory status`.
  - Suggested merge order: A → B → C, or merge C last with `main` merged in.

## Cross-slice dependencies

| On | What | Effect here |
|----|------|-------------|
| Slice A T021 | `factory.github.rest:build_github` (the real `GitHubPort`) | `gate run --pr` in CI and the commit statuses. Coded and tested against `FakeGitHub` through `DEPS` |
| Slice A | `factory status` (board) | the summary step of the workflow |
| Slice A | `acceptance.md` row `handoff.concurrency_cap` | Slice A's branch rewrites this row and **reverts the governor-locked wording** "editor launch logged (advisory)" to "editor launch warned". Expect a merge conflict; keep the locked "logged (advisory)" wording. The PR-gate half (`tests/unit/gates/pr/test_concurrency_cap.py`) and the editor half (`test_hooks.py::test_spawn_guard_allows_and_logs_at_cap`) should be appended to that row's evidence after the merge |
| Slice B | `factory.gates.drift.*`, `factory.intent.coverage` | seeds, `check registry`, and a full `gate run` |
| Slice B T063 | `intent.coverage.group_by_intent()` | **T064** (per-intent section in `runner.py`). The runner already reports `intents` and a "per intent:" text section; T064 will swap in Slice B's grouping |
| unowned | `factory-status-test` → `factory.gates.repo.status_test:run` (I-M4, board) | Registered in `gates.yaml` at CP0, but no Slice C task or test covers it. The path falls under this slice's `gates/repo/**`, yet the check belongs to the board (Slice A), so it was **not** implemented. Orchestrator: assign it to Slice A, or amend this order |

## Dependency changes

- `scripts/factory/pyproject.toml`: one line, `factory-hook = "factory.hooks.entry:main"` under `[project.scripts]`. No new packages.
- `uv.lock`: unchanged. A conflict with Slice A in `pyproject.toml` is possible only on that `[project.scripts]` table.

## Files touched outside `scripts/factory` (whole branch vs `origin/main`)

- `.cursor/hooks.json`, `.cursor/hooks/factory-hook.sh` (new; flagged above).
- `.github/workflows/factory-gates.yml`.
- `specs/001-factory-v2/`:
  - `acceptance.md`: this slice's evidence cells and change-log rows; the `handoff.concurrency_cap` wording came from the round-2 lock.
  - `tasks.md`: T050–T060 boxes and the T057 wording.
  - `spec.md`: the FR-008 line only, from round 2.
  - `research.md`: the hooks block only.
  - `contracts/hooks.md`.
  - `TEST_REVIEW_SLICE_C.md`: Triage sections, plus the reviewer sections that arrived via merge.
- `bus/orders/wo-20261004-factory-slice-c/`: `amendment-01`, `amendment-02`, and `verdict-01..03` (reviewer).
- `notes/packets/2026-10-04-factory-v2-slice-c{,.handoff}.md`.

All of these are within the amendment-02 owned paths.

## Conservative implementation choices (for the reviewer)

1. **Overrides.** The registry class decides, not the class written in the message:
   - `drift` gates honor an orchestrator or governor override.
   - `governor-only` gates honor only `actor: governor`, and also require `IdentityPort.is_governor_verified` when `identity.mode = "verified"`.
   - When the override names a PR, it must match.
   - Only honored overrides of failing gates are counted.
2. **`gate run --pr`.** The base is the tip of `origin/<base_ref>`, not the merge base, so the cap gate sees merges. Gates read commits only (`git show`, `cat-file --batch`, three-dot `--no-renames` diffs), never the working tree. The `check *` CLIs read the working tree.
3. **Fail closed.** A gate whose entrypoint is missing reports "not implemented", and a gate that raises reports "crashed". Both fail.
4. **`order-blocked-on-open-human-od`.** A decision counts as locked only when its lock is on the **base**.
5. **`uv-sync-locked`.** Checks only that each app has a `uv.lock`. It does not resolve, so CI stays offline. A stricter `uv lock --locked` per app is possible later.
6. **`validate-secrets-schema` / `validate-deploy-env`.** Run the existing scripts in a `git archive` of the head tree, with a 300 s timeout.
7. **`shell-guard`.** Judges what the shell would run:
   - It tokenizes the command; quoted or commented text never executes.
   - It follows `cd`/`pushd`, `git -C`/`--git-dir`/`--work-tree`, `env -C`, and wrappers (`command`, `env`, `sudo`, `exec`, `nohup`, `nice`, `timeout`, `stdbuf`, `xargs`).
   - It recurses into `sh|bash|zsh -c` and `eval`, up to depth 5.
   - It reads the branch from the HEAD file of the repository the command targets.
   - It is not a full shell: `$(...)` and variable expansion are left as literal text.
8. **`spawn-guard`.** Reads local and remote-tracking `wo/*` refs, with no fetch. An order is active when it has a claim and no release on a tip, and its tips are not all merged into `main`/`origin/main`. It logs when the task names no active order and no existing review packet, or when the active count is at least the cap.
9. **`owned-path-warn`.** Judges the repository that contains the file (nearest `.git`, so nested worktrees use their own branch). It reads the working tree's `order.yaml` plus `amendment-NN` files in numeric order. It is quiet inside `bus/orders/<own-id>/` and off `wo/*` branches.
10. **`decision-in-chat`.** Judges only the assistant text after the last user entry, with fenced and inline code removed. A request counts as "new" when `bus/decisions/*/request.yaml` is absent from both `main` and `origin/main`.

## Tests believed vacuous or wrong

None found wrong; none needed changing. One weak assertion, noted for a future round and not acted on: `test_spawn_guard_allows_and_logs_at_cap` checks only that `"3"` appears in the advisory. Any text containing the digit would pass. The fixture order ids contain no `3`, so it is not vacuous today.

## Deviations

1. The worktree is `/workspaces/2026-software-lab/.worktree-home/.cursor/worktrees/factory-slice-c-impl`, recreated because `/tmp` was wiped. It was made with `git worktree add -B` from `origin/wo/wo-20261004-factory-slice-c` (`cd1132c`), then `origin/review/wo-20261004-factory-slice-c-r3` was merged (`9445788`).
2. `factory-status-test` was left unimplemented; see the cross-slice table above.
3. `tasks.md` T053 wording still says "advisory warning" (unchanged; only T057 wording is owned).

## Phase 6a rework, phase 1 (2026-10-05): red tests only

PR review PR-C1 to PR-C4 and spec D5 to D8. No implementation in this phase; T* review comes next.

- **New red tests:**
  - `tests/contract/test_ci_trust_boundary.py` (T094, 50 tests): the two-workflow topology and the banned forms; main's gate code and registry, with head as data; P12 provenance; the evidence bundle and the fail-closed judge; `self-reported:` statuses; the `factory gate evidence` producer.
  - `tests/unit/gates/test_registry_checks.py` (P9, 6 tests).
  - `tests/unit/hooks/test_hook_wrapper.py` (T095 / PR-C2, 12 tests).
- **Accepted tests amended:**
  - The three T059 workflow tests in `test_gate_run.py` moved to the trusted-job tests in `test_ci_trust_boundary.py`.
  - The branch-protection `snapshot()` fixture now pins each required context to the GitHub Actions app id (P9).
- **Slice B seam stubbed:** `factory.gates.drift.red_first.collect_facts`, through `sys.modules`, when absent.
- **PR-C4:** the packet is restored to its `origin/main` content.
- **Bootstrap messages:** `order.yaml`, `claim.yaml` and `handoff.yaml` (FR-037) are in the branch-tip commit.

## Phase 6a rework, phase 2 (2026-10-05): T* round 4 triage and implementation

`verdict-07` (round 4) rejected on one Blocker, T-C4-1: the trusted-job oracle was a denylist that `env bash -c`, `command bash -c` and `git -C . checkout` bypassed. Triage in `amendment-06.yaml` and `TEST_REVIEW_SLICE_C.md` § Triage (round 4): fix now, with no fifth T* round; verification moves to the PR code re-review.

- **Commits:** `370df0f` (review merge, round 4), `97d4969` (T-C4-1 allowlist oracle, red), `c1907ec` (implementation, green), then this handoff commit.
- **Oracle fix (`97d4969`):** the denylist (`FORBIDDEN_PROGRAMS`, `FORBIDDEN_GIT`, `head_code_reason`, its fixtures and `test_trusted_steps_never_execute_head_code`) became an allowlist. `test_trusted_job_is_exactly_the_allowlist` requires the trusted job's steps to equal three SHA-pinned actions with listed `with:` keys and three commands compared as parsed argv. One regression test covers the class, parametrized over the three bypass forms plus an unlisted `echo`. Denylist assertions the allowlist covers were removed.
- **Implementation (`c1907ec`), T097 and T098:**
  - `factory-pr-evidence.yml` (untrusted): `pull_request`, `contents: read`, no secrets. `Factory tests` runs the full suite with no selector (T100's test). `red-first-evidence` runs `factory gate evidence` and uploads `factory-evidence`.
  - `factory-gates.yml` (trusted): `workflow_run` of "Factory PR evidence" `completed`; same-repository runs only; exactly the allowlist; actions pinned to commit SHAs.
  - CP0 amendments approved in `amendment-06`: `GitHubPort.get_pr` (with `FakeGitHub`), typed `evidence_max_bytes` and `github.actions_app_id`, and `gate evidence` in `cli/app.py`.
  - `gates/evidence.py`: the producer, a strict bundle loader and a fail-closed judge. `red-first-proof` statuses start `self-reported:` (D7).
  - Validators run `main`'s scripts with `--repo-root <exported head>` (both scripts gained `--repo-root`).
  - `branch-protection-require-pr` fails unless every required `factory/*` context is pinned to the configured Actions app id (P9).
  - `ci-cd-pipeline.yml`: workflow-level `permissions: contents: read`.
  - `factory-hook.sh`: venv, then `uv`, then `nix develop`, then the hook's quiet fail-open JSON with the reason on stderr and exit 0.
- **Accepted tests touched beyond the oracle:** two lines, each because no implementation could pass the test as written.
  - `test_registry_checks.py::test_branch_protection_compares_with_the_configured_actions_app_id` built two contexts in one repo, and the second recreated branch `feature/head`. It now deletes that branch locally and on the fixture origin between the two. Both assertions are unchanged.
  - `test_ci_trust_boundary.py::test_trusted_gate_step_runs_every_gate_bound_to_the_event` found the download step by identity (`is`) across two YAML loads. It now compares by equality.
- **Results:** full suite 574 passed, 102 failed. The 102 are exactly the pre-round baseline: Slice A's `test_cli_contract.py` (50) and Slice B's `tests/seeds/test_seeds.py` (52). Every Slice C test is green. `ruff check` and `ruff format --check` pass in `scripts/factory`. The validator scripts' lint findings are unchanged from `main`. `factory check schema` passes.
- **`factory gate run --base origin/main --head wo/wo-20261004-factory-slice-c`:** 12 passed, 13 failed. The failures:
  - 9 Slice B gates are not importable yet;
  - `factory-status-test` has no owner (see the cross-slice table);
  - `branch-protection-require-pr` lacks the T066 snapshot (governor, D6);
  - `validate-secrets-schema` and `validate-deploy-env` fail because `main`'s copies predate `--repo-root`. This is a one-time bootstrap failure: with this branch as the base, both pass.
- **Cross-slice:**
  - Slice A's REST adapter (`factory.github.rest`) must implement `GitHubPort.get_pr`.
  - Slice B owns the `red_first.py` producer/judge split. `gates/evidence.py` imports `collect_facts` lazily and records `crashed` while it is absent.
  - The `Factory tests` check stays red until A and B are merged into C, because the selector is gone.
- **Later (owner Slice C, review at the Wave 1 retro):**
  - T-C4-2: a wrong `base_sha` in the bundle is untested; the judge does not check it.
  - T-C4-3: the evidence producer's main checkout is not proven.
  - T-C4-4: malformed output from the Nix fallback is untested; the wrapper relays it as is.
- **Not done here:** nothing posted or changed on GitHub besides the branch push; draft PR #21 is still a draft; repository settings, branch protection and the D6 probe are left to the governor.

## Stop

Phase 6a phase 2 done and pushed; draft PR #21 left as a draft. Next: the PR code re-review of the allowlist (T-C4-1), then the steps below.

Earlier next steps for the orchestrator:

- Merge `main` once PR #20 lands, then resolve the `pyproject.toml` `[project.scripts]` and `acceptance.md` `handoff.concurrency_cap` conflicts.
- After Slice B's T063, run T064.
- Spawn the bootstrap verdict.
- Get governor approval of the `.cursor/` files at PR time.

## Integration (post A+B merge), 2026-10-06

Replacement worker; the previous session hung after `5c925a1` (merge of `main` @ `2a591f9`, Slices A and B; real `red_first.collect_facts` seam; T100).

- **Full suite** (`uv run pytest -q -p no:cacheprovider`): **1034 passed, 9 failed, 3 min 22 s**. Every failure is in `test_cli_contract.py` and belongs to an unbuilt task. No Slice C test is red, and nothing came from the integration.
  - T102: `test_check_registry_exit_0` and `test_json_envelope[check registry]`. `factory.gates.repo.status_test` doesn't exist yet.
  - T069: `test_retro_exit_0` and `test_json_envelope[retro]` (`factory retro`: not implemented).
  - T081: `test_correction_new_exit_0`, `test_sprint_close_refuses_without_postmortem`, `test_sprint_close_refuses_undispositioned_correction`, `test_json_envelope[correction new]` and `test_json_envelope[sprint close]`.
- **Integration fix (`d78ee66`, fixture only, amend-08 path):** `factory gate run --base origin/main --head HEAD` failed `red-first-proof` on 156 Slice C tests with "base broken: errors before the test body runs".
  - Cause: `RepoBuilder.plant_lab_inputs()` copied `deploy/github/branch-protection.json`. That file isn't on `main`, so on the base side of the gate (head tests over the base tree) fixture setup raised.
  - Fix: the fixture now skips a copied lab input that is absent from its source tree. On head both files exist, so head behaviour is unchanged.
  - Untouched: the gates, the set of gates `handoff` runs, and every test assertion.
  - After the fix, `--gate red-first-proof` passes.
- **`factory gate run` against `main`** (before the fix): 19 passed, 6 failed. Excluding `red-first-proof` (fixed above), the five remaining are:
  - `factory-status-test`: T102.
  - `validate-secrets-schema` and `validate-deploy-env`: `main`'s copies predate `--repo-root`. This is the known one-time bootstrap failure; they pass once C is the base.
  - `pr-links-order`: an artifact of the detached-HEAD local run. It passes with `--head origin/wo/wo-20261004-factory-slice-c`.
  - **`deferral-words-need-od` (Slice B's T045 gate, drift class) is open and needs an orchestrator decision.** It flags 27 lines in this branch's `specs/001-factory-v2/` docs: `TEST_REVIEW_SLICE_C.md`, `PLAN_REVIEW.md`, `PLAN_DELTA.md`, `spec.md` (FR-022a, the D5 row, the P2 "stretch" row), `tasks.md:234`, `contracts/gates.md`, `acceptance.md` and `research.md`.
    - Several of these lines are governor-verbatim quotes or reviewer-authored findings. Adding `→` pointers would change recorded wording, so I left them as they are.
    - The choices: an orchestrator override for PR #21, or a docs pass that adds pointers to the agent-authored lines only.
- **Lint / schema:** `ruff check` and `ruff format --check` (135 files) pass, and `factory check schema` reports `schema ok`.
- **Snapshot vs live ruleset 24554609:** the live body equals `deploy/github/branch-protection.json` once server metadata is removed, except for the 25 `factory/*` `required_status_checks` entries (`integration_id` 15368). Those exist only in the snapshot, as the T103 step 3 target.
- **Not done:** PR #21 is still a draft. GitHub settings and rulesets are untouched.
