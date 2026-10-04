# Handoff — 2026-10-04-factory-v2-slice-c (interim)

| Field | Value |
|-------|-------|
| Branch | `wo/wo-20261004-factory-slice-c` |
| State | **T* round 1 applied; round-2 review requested (T054)** |
| Author model | Claude family (worker). Bootstrap / T* verdict must come from a GPT-family reviewer (D3, FR-037) |
| Head (tests) | `2997116` |
| Base | `origin/main` @ `c2af7f2` (includes CP0 merge `8cd8cb7`) |
| Frozen CP0 files | not edited |

Pause here. The round-1 verdict (`verdict-01`, reject) was merged from `origin/review/wo-20261004-factory-slice-c` (`f83bb92`). The orchestrator's triage is recorded in `specs/001-factory-v2/TEST_REVIEW_SLICE_C.md` § Triage (orchestrator, round 1) and `bus/orders/wo-20261004-factory-slice-c/amendment-01.yaml`. The orchestrator spawns the round-2 T* reviewer, then resumes this worker for T055–T060 after triage. T064 waits for slice B's `intent.coverage.group_by_intent()` on `main`.

## Commits

| SHA | Role |
|-----|------|
| `399dfd9` | packet Status → `in_progress` (CP0 merged 8cd8cb7) |
| `c5d1730` | **red** tests T050–T053 + this slice's `tasks.md` checkboxes |
| `07d0c12` | interim handoff (red; T* requested) |
| `047d096` | merge of the round-1 review (`f83bb92`: `TEST_REVIEW_SLICE_C.md`, `verdict-01.yaml`) |
| `2997116` | **red** round-1 test changes (T-C1..T-C5), `contracts/hooks.md` A1 amendment, T057 wording |
| (this commit) | triage section, `amendment-01.yaml`, this handoff |

No green implement commit yet. Red/green pairs will be listed after T*.

## What changed in round 1

| Finding | Change |
|---------|--------|
| T-C1 | Workflow tests tokenize each `run` block (`shlex`; comments, quoting, operators). The gate step must be exactly `factory gate run --pr <event number>`, so its exit status is the step's. `factory status` must redirect or `tee -a` to `$GITHUB_STEP_SUMMARY`, and run before the gate step or under `always()`. Each test first proves that its oracle rejects echo, comment, string, `\|\| true`, pipe and `set +e` no-ops |
| T-C2 | Missing, deleted or unreadable head `scripts/factory/gates.yaml` blocks and names the path (`fail-mode`, `hook-twin`, `branch-protection`, `check registry`). No fallback |
| T-C3 | 30 push-to-main spellings plus main-only `-C`/`-c`/wrapper commit forms, with nearby allowed controls. `-C`/`cd` branch semantics are tested |
| T-C4 | A1 as approved: `factory-hook` console script, `.cursor/hooks/factory-hook.sh` wrapper, slow-path fallback. Tests: import ban, warm 150 ms budget with CLI parity, wrapper behavior with fake executables, `pyproject` script, and end-to-end median of 5 < 300 ms on realistic payloads |
| T-C5 | Recording stubs for every registered CI gate. Differing outcomes (two failures) → exit 1 with each stub's message; all pass → exit 0 |
| Visibility | `owned-path-warn` → `postToolUse` (`Write` matcher, `additional_context`); `decision-in-chat` keeps `stop` → `followup_message` |

| File | Tests (round 0 → round 1) |
|------|------:|
| `tests/unit/hooks/test_hooks.py` | 73 → 130 |
| `tests/unit/gates/test_registry_checks.py` | 34 → 39 |
| `tests/contract/test_gate_run.py` (`contract` marker) | 25 → 27 |
| `tests/unit/gates/pr/test_bus_gates.py` | 18 |
| `tests/unit/gates/pr/test_verdict_and_override.py` | 18 |
| `tests/unit/gates/pr/test_order_gates.py` | 12 |
| `tests/unit/gates/pr/test_concurrency_cap.py` | 8 |
| **Total** | **188 → 252** |

All tests drive frozen surfaces only: `api.run_gate`, the CLI via `tests/fixtures/cli_runner`, and, new in this round, `factory.hooks.entry.main` imported inside the test. They build temp repos with `RepoBuilder`. Nothing writes the live repo's `.cursor/hooks.json`, `.cursor/hooks/` or `pyproject.toml`; the registration tests only read them.

## Commands and results

Toolchain: `. /tmp/factory-env.sh` (Nix-store `uv` + Python 3.12). `uv sync --locked` PASS. No `pip install`.

| DoD | Command (in `scripts/factory`) | Result |
|-----|---------|--------|
| Slice C tests | `uv run pytest tests/unit/gates tests/unit/hooks tests/contract/test_gate_run.py --junitxml=…` | **252 failed, 0 passed, 0 errors**; JUnit: all 252 `AssertionError`; 0 collection errors, 0 xfail; no module-level import of a missing module |
| oracle controls | failure messages of the workflow tests | each fails on the live workflow (`continue-on-error`, missing `statuses: write`, no summary step), after its no-op controls passed |
| full | `uv run pytest -q` | **368 failed, 237 passed** (main: 116 / 237; +252 Slice C red; the 237 unchanged) |
| CI selector | `uv run pytest -q -m "not contract and not seed"` | **225 failed, 224 passed, 156 deselected** (225 unmarked Slice C unit tests) |
| lint | `uv run ruff check .` / `uv run ruff format --check .` | PASS |
| bus | `uv run factory check schema --repo ../..` | `schema ok` (a copy of amendment-01 with a bad `supersedes` field is rejected, so the check really reads it) |

## Hook latency (this Codespace, median of 7 runs)

| Path | Median | Range |
|------|------:|------|
| `.venv/bin/python -c pass` | 28 ms | 19–30 |
| `import yaml` | 80 ms | 52–98 |
| `import pydantic` | 84 ms | 77–90 |
| `import factory.bus.models` | 257 ms | 241–329 |
| `import factory.api` | 294 ms | 277–344 |
| minimal entry (json + yaml + 3 `git` calls), direct | 67 ms | 61–85 |
| same, through a `sh` wrapper | 67 ms | 61–76 |
| `.venv/bin/factory hook` (full CLI, today's stub) | 377 ms | 337–451 |
| `uv run --project scripts/factory factory hook` | 371 ms | 338–533 |

A minimal entrypoint meets the 300 ms letter with wide margin, so no stop was needed. Implementation constraint: the hook entry must not import `factory.api` or `factory.bus.models` (pydantic models alone cost about 250 ms). Bus YAML gets read with `yaml` plus plain dict checks on the fast path.

## Cursor hook outputs (docs checked 2026-10-04)

Source: `https://cursor.com/docs/agent/hooks` (fetched with `curl`; WebFetch is unavailable to subagents). The installed client (`cursor-agent-exec`) confirms the `postToolUse` payload: file writes and edits report `tool_name: "Write"` and `tool_input {file_path, content}`.

- **`stop` supports `followup_message`.** The docs say: "When provided and non-empty, Cursor will automatically submit it as the next user message." It is capped by `loop_limit` (default 5). So `decision-in-chat`'s warning is visible, and it re-prompts the agent. Its JSON contract test is kept.
- `postToolUse` → `additional_context` ("Extra context injected into the conversation after the tool result"). `owned-path-warn` uses it.
- **Governor-visible limitation:** `subagentStart` output is `permission` and `user_message`, and the docs describe `user_message` as "Message shown to the user when the subagent is denied". `spawn-guard` always allows (FR-008 waive), so its warning likely reaches only the Hooks output channel. Making it visible would mean denying spawns, which changes product behavior and needs a governor decision. Not changed; recorded in `contracts/hooks.md`.

## Manual equivalents of P1 gates (bootstrap, FR-037)

| Gate | Manual check | Result |
|------|--------------|--------|
| `red-first-proof` | Round-1 tests committed failing (252 `AssertionError`); no matching impl in `2997116` | pass (shown by hand) |
| `diff-within-owned-paths` | `git diff --no-renames --name-only origin/main...HEAD` | packet, handoff, `tasks.md` (T050–T053 boxes + T057 wording), `contracts/hooks.md`, `TEST_REVIEW_SLICE_C.md` (reviewer sections via merge; Triage by worker), `bus/orders/wo-20261004-factory-slice-c/{verdict-01 (reviewer), amendment-01}.yaml`, Slice C test files. All within amend-01 owned paths |
| `test-seam-ban` | no new src | n/a |
| `bus.immutable` | only additions under `bus/orders/wo-20261004-factory-slice-c/` | pass |
| `bus.no-handwritten-status` | amendment-01 carries no status/state/progress keys | pass |
| `decision-request-no-ids` | none raised | n/a |

`git diff --no-renames` (Amendment 3): no renames in this slice.

## Deviations

1. Worktree is `/tmp/cursor-worktrees/factory-slice-c/repo` (the sandbox blocks `~/.cursor/worktrees`); reused from round 0 rather than created again with the `/worktree` script. No `.cursor/worktrees.json` exists, so there is no setup to run. Toolchain is `/tmp/factory-env.sh` rather than an interactive `nix develop`.
2. **One owned path beyond the orchestrator's widening list:** `.cursor/hooks/factory-hook.sh`, the A1 wrapper ("a tiny wrapper falls back"), because it needs a file. Conservative alternative if vetoed: an inline `sh` expression in each `hooks.json` command; only `WRAPPER`/`HOOK_COMMAND` in `test_hooks.py` and `factory_hook()` in `test_registry_checks.py` would change.
3. The T-C1 oracle adds two rules beyond the reviewer's letter. The gate step has no `if:`. The board step runs before the gate step or under `always()`/`!cancelled()`, so the board is published when gates fail. Both are needed for the step to be authoritative and for the board to appear on red PRs.
4. The warm in-process budget is 150 ms ("well under 300"); the measured logic cost of the prototype is about 40 ms.
5. `research.md` still says `.cursor/hooks.json` calls `factory hook <name>` and lists `afterFileEdit`. That file is outside Slice C's owned paths, so it is left for the orchestrator; `contracts/hooks.md` is the amended contract.

## Open questions

| Class | Question |
|-------|----------|
| non_blocking | `spawn-guard` warning visibility (see above). Accept the advisory warning landing only in the Hooks output channel, or should the governor revisit the FR-008 waive? |
| non_blocking | `.cursor/hooks/factory-hook.sh` as an owned path (deviation 2) |
| non_blocking | Running `contract` tests in CI stays deferred to CP1/CP2 per the reviewer; T059 removes only the step-level `continue-on-error` and makes the gate step authoritative |

No `blocker_governor` questions. No frozen-interface amendment requested beyond A1 (approved), and A2 is declined (see Later in the triage).

## Stop

**T* round 1 applied; round-2 review requested (T054).** Do not implement until the orchestrator records round-2 triage.
