# Handoff — 2026-10-04-factory-v2-slice-c (interim)

| Field | Value |
|-------|-------|
| Branch | `wo/wo-20261004-factory-slice-c` |
| State | **red; T* requested (T054)** |
| Author model | Claude family (worker). Bootstrap / T* verdict must come from a GPT-family reviewer (D3, FR-037) |
| Head (tests) | `c5d1730` |
| Base | `origin/main` @ `c2af7f2` (includes CP0 merge `8cd8cb7`) |
| Frozen CP0 files | not edited |

Pause here. The orchestrator spawns the T* reviewer on T050–T053 (`notes/packets/<date>-factory-v2-slice-c-test-review-t.md`) and resumes this worker for T055–T060 after triage. T064 waits for slice B's `intent.coverage.group_by_intent()` on `main`.

## Commits

| SHA | Role |
|-----|------|
| `399dfd9` | packet Status → `in_progress` (CP0 merged 8cd8cb7) |
| `c5d1730` | **red** tests T050–T053 + this slice's `tasks.md` checkboxes |

No green implement commit yet. Red/green pairs will be listed after T*.

## What landed (tests only)

| Task | File | Tests | Covers |
|------|------|------:|--------|
| T050 | `tests/contract/test_gate_run.py` (`contract` marker) | 25 | `gate run --base/--head/--pr/--gate`, per-intent report, override resolution, `factory override`, workflow shape |
| T051 | `tests/unit/gates/test_registry_checks.py` | 34 | `gate.fail-mode-category`, `hook-has-ci-twin`, `check registry` / `check hooks`, `branch-protection-require-pr`, wrapped `validate-secrets-schema` / `validate-deploy-env` / `uv-sync-locked` |
| T052 | `tests/unit/gates/pr/test_bus_gates.py` | 18 | `bus.schema`, `bus.immutable` (+ `check immutability`), `bus.no-handwritten-status` |
| T052 | `tests/unit/gates/pr/test_order_gates.py` | 12 | `pr-links-order`, `order-blocked-on-open-human-od` (incl. effective order via amendment) |
| T052 | `tests/unit/gates/pr/test_concurrency_cap.py` | 8 | `spawn-concurrency-cap` CI twin (claim replay across `wo/*`, release/merge before vs after, racing claims) |
| T052 | `tests/unit/gates/pr/test_verdict_and_override.py` | 18 | `verdict.reviewer-family-differs`, `verdict.inputs-isolated`, `message.override` |
| T053 | `tests/unit/hooks/test_hooks.py` | 73 | `shell-guard`, `spawn-guard`, `owned-path-warn`, `decision-in-chat`; offline + < 300 ms; live `.cursor/hooks.json` registration (read only) |
| | shared helper `tests/unit/gates/pr/helpers.py` | | `assert_passes` / `assert_blocks` turn `GateEntrypointError` into an assertion failure |

**188 tests total.** T050–T053 are ticked in `tasks.md` (tests written, red). T054 onward stay open.

All tests drive frozen surfaces only: `api.run_gate(gate_id, GateContext)` and the CLI via `tests/fixtures/cli_runner`. They build temp repos with `RepoBuilder`. Nothing writes the live repo's `.cursor/hooks.json`; two tests read it.

## Commands and results

Toolchain: `. /tmp/factory-env.sh` (Nix-store `uv` + Python 3.12). `uv sync --locked` PASS. No `pip install`.

| DoD | Command (in `scripts/factory`) | Result |
|-----|---------|--------|
| new tests | `uv run pytest tests/unit/gates tests/unit/hooks tests/contract/test_gate_run.py --junitxml=…` | **188 failed, 0 passed, 0 errors.** JUnit: all 188 `AssertionError` (unregistered/unimplemented gate → `AssertionError: gate X is not implemented`; CLI stubs → exit-code assertions). 0 collection errors, 0 xfail |
| full | `uv run pytest -q` | **304 failed, 237 passed** (main at `c2af7f2`: 116 failed / 237 passed; +188 new red) |
| CI selector | `uv run pytest -q -m "not contract and not seed"` | **163 failed, 224 passed, 154 deselected.** The 163 new unit tests are unmarked (same choice as slice A), so `factory-tests` is red on this branch until implement |
| lint | `uv run ruff check .` / `uv run ruff format --check .` | PASS |
| fixture sanity | throwaway test (not committed): build the contract fixtures and `load_all` the bus at head | PASS (overrides and orders validate against `bus/models.py`) |

## Behavior the tests lock in (implementer reference)

- **Gate messages** name the gate id and the offending path / order / decision / gate.
- **Report** (`gate run --json`, envelope `data` on exit 0, `error.details` on exit 1): `gates[{id, class, intents, outcome: pass|fail|overridden, messages, override?{id, actor, reason, verified}}]`, `intents{intent_id: [{gate, outcome}]}`, `override_counts{gate_id: n}`. `--head wo/<id>` sets the order id. It runs every non-hook registry gate.
- **Overrides** (contracts/gates.md § Override resolution): drift → orchestrator or governor, same gate, same order dir, `pr` matches; governor-only → `actor: governor`, plus `IdentityPort.is_governor_verified` in `verified` mode (called once). Overrides already on the base do not count. `factory override` writes `override-NN.yaml` with `gate_class` from the registry and rejects unregistered gates by name.
- **`--pr N`** posts one `factory/<gate-id>` commit status per gate via `DEPS.github.set_commit_status`. Overridden = `success` with description `overridden: …`.
- **Workflow**: exactly one `factory gate run … --pr` step, no `continue-on-error`, `permissions.statuses: write`, and a `factory status` step that writes to `$GITHUB_STEP_SUMMARY`.
- **Hooks**: `factory hook <name>` reads the Cursor JSON on stdin and prints one JSON object. `shell-guard` denies with `permission: "deny"` + exit 2. `spawn-guard` always allows and warns in `user_message`. `owned-path-warn` warns in `agent_message`. `decision-in-chat` warns in `followup_message`. Hooks are offline and answer in < 300 ms. The live `.cursor/hooks.json` is `version: 1` and uses the command `uv run --project scripts/factory factory hook <name>`.
- **Hook twins**: every hook gets a `gates.yaml` row `id: <hook-name>`, plus `hook_twin_of: <non-hook CI gate>`. The tests use spawn-guard → spawn-concurrency-cap and shell-guard → branch-protection-require-pr (a governor-only, irreversible row). Proposed but not fixed by tests: owned-path-warn → diff-within-owned-paths, decision-in-chat → decision-request-no-ids. These four hook rows and `branch-protection-require-pr` get added to `gates.yaml` in T057/T059.
- **Branch protection snapshot** `deploy/github/branch-protection.json` uses the classic REST `GET /branches/main/protection` shape. Required contexts must include `factory/<id>` for every P1 non-hook gate. Also required: `enforce_admins.enabled`, code-owner reviews, and empty bypass allowances.

## Manual equivalents of P1 gates (bootstrap, FR-037)

| Gate | Manual check | Result |
|------|--------------|--------|
| `red-first-proof` | Tests committed failing (188 `AssertionError`); no matching impl in `c5d1730` | pass (shown by hand) |
| `diff-within-owned-paths` | `git diff --no-renames --name-only origin/main...HEAD` | packet, this handoff, `tasks.md` (T050–T053 boxes), `tests/contract/test_gate_run.py`, `tests/unit/gates/**`, `tests/unit/hooks/**`. Nothing in frozen CP0 paths or other slices |
| `test-seam-ban` | no new src | n/a |
| `bus.immutable` / `bus.no-handwritten-status` | no `bus/` changes on this branch | pass |
| `decision-request-no-ids` | none raised | n/a |

`git diff --no-renames` (Amendment 3): no renames in this slice.

## Deviations

1. The worktree is `/tmp/cursor-worktrees/factory-slice-c/repo` because the sandbox blocks `~/.cursor/worktrees`. Leftover local branch reset from `origin/main`. The two unpushed commits were rebased onto `c2af7f2`, which only adds a `bus/corrections/` file. No force-push.
2. I used `/tmp/factory-env.sh` (Nix-store `uv` + Python) instead of an interactive `nix develop`. Same as slice A.
3. `branch-protection-require-pr` tests are in `test_registry_checks.py`. The gate belongs to slice C per the packet Fidelity table (T066 is the governor's HITL settings step plus the snapshot).
4. The report keys, hook output keys and hook-twin row shape are fixed by the tests, because the contracts describe them in prose rather than a schema. If T* wants different names, that means editing the tests, not amending a frozen interface.

## Amendment requests (frozen CP0 files)

| Class | Request |
|-------|---------|
| non_blocking | **Hook latency vs `cli/app.py`.** `factory hook` through the full Typer app takes about 350–400 ms in the venv, because `cli/app.py` imports every slice's command module. Bare `python -c` takes about 40 ms. The < 300 ms budget (contracts/hooks.md) cannot be met by slice C alone. Ask: either a fast path in `cli/app.py` `main()` that dispatches `argv[1] == "hook"` straight to `factory.cli.gates` (or `factory.hooks`) before building the app, or a separate console script in `pyproject.toml` (e.g. `factory-hook = "factory.hooks.main:main"`), with `.cursor/hooks.json` pointing at that. Both files are orchestrator-owned. The end-to-end test (`test_live_hook_command_answers_within_budget`) also counts `uv run --project` startup, so the second option might also need `--no-sync` or a direct venv path in `hooks.json`. If so, the test command string changes too |
| non_blocking | **`GitHubPort.get_pr(number)`.** `gate run --pr N` needs the PR's head/base sha and head ref, but the port only has `list_prs_by_head`. Ask: add `get_pr(number) -> PullRequest` to `api.GitHubPort`, the REST adapter (slice A) and `FakeGitHub`. Fallback without the amendment: enumerate `wo/*` and `bus/*` heads and call `list_prs_by_head` until the number matches. The tests seed `FakeGitHub` through `create_pr`, so both approaches pass them |

## Open questions

| Class | Question |
|-------|----------|
| non_blocking | Cursor appears to ignore `afterFileEdit` output (the client does not read a response for that event). In practice `owned-path-warn` may only be visible in the hook log. Should it also be registered on `postToolUse` with `additional_context`? Tests assert the `agent_message` key only |
| non_blocking | `subagentStart` `user_message` on `allow`: the client may only show it on deny/ask. The spawn warning is advisory by the FR-008 waive. Is a warning that might be invisible acceptable, or should `spawn-guard` also add `additional_context`? |
| non_blocking | `spawn-guard` at cap: tests warn when the active count is ≥ 3 even if the prompt names an already-claimed order (letter of T053). Confirm or exempt already-active orders |
| non_blocking | `spawn-concurrency-cap`: a claim that exceeded the cap stays blocked even after an earlier order merges later (replay is at claim time). Confirm this is intended vs re-evaluating at PR time |
| non_blocking | `verdict.reviewer-family-differs` uses the **latest** verdict on the order. An earlier same-family verdict followed by a cross-family one passes. Confirm |
| non_blocking | Repo-scope gates read `scripts/factory/gates.yaml` at head and fall back to the installed registry when it is missing at head. Confirm the fallback (vs fail-closed) |
| non_blocking | Review-packet recognition in `spawn-guard`: tests only fix that a prompt naming an existing `notes/packets/…-test-review-t.md` is quiet and a missing one warns. The `notes/packets/` location is specific to this repo, so it should move to `factory.toml` if other repos adopt the factory |
| non_blocking | Whether to run `contract` tests in CI (marker selector in `factory-gates.yml`) is left to CP1, as the P0 comment says. T059 removes only the `continue-on-error` on `factory gate run` |

No `blocker_governor` questions.

## Stop

**red; T* requested (T054).** Do not implement until the orchestrator records T* triage.
