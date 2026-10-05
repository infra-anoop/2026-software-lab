# Handoff — 2026-10-04-factory-v2-slice-c

| Field | Value |
|-------|-------|
| Branch | `wo/wo-20261004-factory-slice-c` (pushed; **no PR opened**) |
| State | **Implemented T055–T060: all 254 Slice C tests green. T064 waits for Slice B** |
| Author model | Claude family (worker); one model for the whole run. The bootstrap verdict must come from a non-Anthropic reviewer (D3, FR-037) |
| Accept SHA (T* round 3) | **`9445788`**: `verdict-03` `decision: accept` (one strength nit, T-C3-1) |
| Tests since accept | `git diff 9445788 -- scripts/factory/tests` is **empty**. No accepted test was edited, skipped or weakened |
| Base | `origin/main` @ `c2af7f2` (CP0 merge `8cd8cb7`); Slice A (PR #20) is **not** merged here |
| Frozen CP0 files | not edited (`api.py`, `bus/`, `config/`, `gates/registry.py`, `cli/common.py`, `cli/app.py`) |

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

## Stop

Implementation done and pushed; **no PR opened** (orchestrator's call). Next steps for the orchestrator:

- Merge `main` once PR #20 lands, then resolve the `pyproject.toml` `[project.scripts]` and `acceptance.md` `handoff.concurrency_cap` conflicts.
- After Slice B's T063, run T064.
- Spawn the bootstrap verdict.
- Get governor approval of the `.cursor/` files at PR time.
