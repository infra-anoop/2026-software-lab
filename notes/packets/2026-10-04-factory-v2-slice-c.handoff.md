# Handoff — 2026-10-04-factory-v2-slice-c (interim)

| Field | Value |
|-------|-------|
| Branch | `wo/wo-20261004-factory-slice-c` |
| State | **T* round 2 applied; round-3 confirmation requested (T054)** |
| Author model | Claude family (worker). Bootstrap / T* verdict must come from a GPT-family reviewer (D3, FR-037) |
| Head (tests) | `4bc0207` |
| Base | `origin/main` @ `c2af7f2` (includes CP0 merge `8cd8cb7`) |
| Frozen CP0 files | not edited |

Pause here. The round-2 verdict (`verdict-02`, reject) was merged from `origin/review/wo-20261004-factory-slice-c-r2` (`1d690f4`). Its product Blocker (spawn-guard visibility) was locked by the governor on 2026-10-04 as log-only. The triage is recorded in `specs/001-factory-v2/TEST_REVIEW_SLICE_C.md` § Triage (round 2) and `bus/orders/wo-20261004-factory-slice-c/amendment-02.yaml`. Next, the orchestrator spawns the round-3 confirmation reviewer and then resumes this worker for T055–T060. T064 waits for slice B's `intent.coverage.group_by_intent()` on `main`.

## Commits

| SHA | Role |
|-----|------|
| `399dfd9` | packet Status → `in_progress` (CP0 merged 8cd8cb7) |
| `c5d1730` | **red** tests T050–T053 + this slice's `tasks.md` checkboxes |
| `07d0c12` | interim handoff (red; T* requested) |
| `047d096` | merge of the round-1 review (`f83bb92`: `TEST_REVIEW_SLICE_C.md`, `verdict-01.yaml`) |
| `2997116` | **red** round-1 test changes (T-C1..T-C5), `contracts/hooks.md` A1 amendment, T057 wording |
| `e7e57b8` | round-1 triage, `amendment-01.yaml`, handoff |
| `8beb9be` | merge of the round-2 review (`1d690f4`: `TEST_REVIEW_SLICE_C.md` § Round 2 review, `verdict-02.yaml`) |
| `4bc0207` | **red** round-2 test changes (T-C2-1..T-C2-4); FR-008 line, `handoff.concurrency_cap` row and change-log row, `contracts/hooks.md`, `research.md` hooks block, T057 wording |
| (this commit) | round-2 triage, `amendment-02.yaml`, this handoff |

No green implement commit yet. Red/green pairs will be listed after T*.

## What changed in round 2

| Finding | Change |
|---------|--------|
| T-C2-1 (governor: log-only) | `spawn-guard` tests still require `permission: "allow"` for every launch, plus an advisory string for unclaimed or at-cap launches. They are renamed `…_allows_and_logs_…` / `…_allows_without_log_…` and claim nothing about visibility. No `preToolUse` test was added. FR-008, `handoff.concurrency_cap` ("editor launch logged (advisory)") and `contracts/hooks.md` ("logged in Hooks output, not shown") are amended |
| T-C2-2 | The 150 ms warm assertion is gone. `test_hook_entry_is_offline_and_matches_the_cli` keeps the offline, CLI-parity, exit-code and visible-field checks. The 300 ms end-to-end median of 5 and the import ban stay |
| T-C2-3 | `owned-path-warn` uses an anchored `Write\|Delete` matcher. The inside/outside tests run for both tools, with Delete payload `{file_path}` → `{file_path, deleted: true}`. The live matcher must not hit `Read`, `Shell`, `Grep`, `Task`, `WriteShellStdin`, `MCP:Write` or `MCP:Delete` |
| T-C2-4 | The gate step may have no `if:`, `always()` or `!cancelled()`, bare or wrapped in `${{ }}`. Any other condition (`false`, event filters, `failure()`, `always() && false`, …) fails, and the oracle self-checks prove it |
| T-C2-5 | none (strength) |
| `research.md` | The hooks decision block now describes the wrapper and console script, log-only spawn-guard, `postToolUse` `Write\|Delete` and `stop` → `followup_message` |

| File | Tests (round 1 → round 2) |
|------|------:|
| `tests/unit/hooks/test_hooks.py` | 130 → 132 |
| `tests/unit/gates/test_registry_checks.py` | 39 |
| `tests/contract/test_gate_run.py` (`contract` marker) | 27 |
| `tests/unit/gates/pr/test_bus_gates.py` | 18 |
| `tests/unit/gates/pr/test_verdict_and_override.py` | 18 |
| `tests/unit/gates/pr/test_order_gates.py` | 12 |
| `tests/unit/gates/pr/test_concurrency_cap.py` | 8 |
| **Total** | **252 → 254** |

All tests drive frozen surfaces only: `api.run_gate`, the CLI via `tests/fixtures/cli_runner`, and `factory.hooks.entry.main` imported inside the test. They build temp repos with `RepoBuilder`. Nothing writes the live repo's `.cursor/hooks.json`, `.cursor/hooks/` or `pyproject.toml`; the registration tests only read them.

## Commands and results

Toolchain: `. /tmp/factory-env.sh` (Nix-store `uv` + Python 3.12). `uv sync --locked` PASS. No `pip install`.

| DoD | Command (in `scripts/factory`) | Result |
|-----|---------|--------|
| Slice C tests | `uv run pytest tests/unit/gates tests/unit/hooks tests/contract/test_gate_run.py` | **254 failed, 0 passed, 0 errors**; all `AssertionError`; 0 collection errors, 0 xfail; no module-level import of a missing module |
| oracle controls | failure messages of the workflow tests | each fails on the live workflow (`continue-on-error`, missing `statuses: write`, no summary step), after its no-op and condition controls passed |
| full | `uv run pytest -q` | **370 failed, 237 passed** (main: 116 / 237; +254 Slice C red; the 237 unchanged) |
| CI selector | `uv run pytest -q -m "not contract and not seed"` | **227 failed, 224 passed, 156 deselected** |
| lint | `uv run ruff check .` / `uv run ruff format --check .` | PASS (43 files formatted) |
| bus | `uv run factory check schema --repo ../..` | `schema ok`, including `amendment-02.yaml` |

## Hook latency (this Codespace, median of 7 runs, measured in round 1)

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

A minimal entrypoint meets the 300 ms letter with a wide margin. Implementation constraint: the hook entry must not import `factory.api` or `factory.bus.models`, because the pydantic models alone cost about 250 ms. On the fast path, bus YAML is read with `yaml` and plain dict checks.

## Cursor hook outputs (docs checked 2026-10-04)

Source: `https://cursor.com/docs/agent/hooks` (fetched with `curl`), confirmed independently by the round-2 reviewer.

- `stop` → `followup_message`, which Cursor auto-submits as the next user message (`loop_limit`, default 5). `decision-in-chat` is visible.
- `postToolUse` → `additional_context`. `owned-path-warn` is visible for `Write` and `Delete`.
- `subagentStart` / `preToolUse` messages are delivered only on denial. **Resolved by governor lock (2026-10-04, option B):** `spawn-guard` is log-only. Its advisory reaches the Hooks output channel only; enforcement is `factory claim` plus CI.

## Manual equivalents of P1 gates (bootstrap, FR-037)

| Gate | Manual check | Result |
|------|--------------|--------|
| `red-first-proof` | Round-2 tests committed failing (254 `AssertionError`); no matching impl in `4bc0207` | pass (shown by hand) |
| `diff-within-owned-paths` | `git diff --no-renames --name-only origin/main...HEAD` | Changed: packet, handoff, `tasks.md` (T050–T053 boxes, T057 wording) and `contracts/hooks.md`. `spec.md` (FR-008 line only) and `research.md` (hooks block only). `acceptance.md` (`handoff.concurrency_cap` row and one change-log row). `TEST_REVIEW_SLICE_C.md`: reviewer sections arrived via merge; the worker wrote the Triage sections. `bus/orders/wo-20261004-factory-slice-c/`: `verdict-01` and `verdict-02` (reviewer), `amendment-01` and `amendment-02`. Plus the Slice C test files. All within amend-02 owned paths |
| `test-seam-ban` | no new src | n/a |
| `bus.immutable` | only additions under `bus/orders/wo-20261004-factory-slice-c/` | pass |
| `bus.no-handwritten-status` | amendments carry no status/state/progress keys | pass |
| `decision-request-no-ids` | none raised | n/a |

`git diff --no-renames` (Amendment 3): no renames in this slice.

## Deviations

1. Worktree is `/tmp/cursor-worktrees/factory-slice-c/repo` (the sandbox blocks `~/.cursor/worktrees`). It is reused from round 0 rather than created again with the `/worktree` script. No `.cursor/worktrees.json` exists, so there is no setup to run. The toolchain is `/tmp/factory-env.sh` rather than an interactive `nix develop`.
2. `.cursor/hooks/factory-hook.sh` is an owned path (accepted by the round-2 reviewer, deviation (a)).
3. Workflow oracle rules beyond the reviewer's round-1 letter, both accepted in round 2:
   - The board step runs before the gate step or under `always()`/`!cancelled()`.
   - The gate step is a single command whose exit status is the step's. Its `if:` is now narrowed to never-skipping conditions (T-C2-4).
4. `tasks.md` T053 still describes the spawn-guard test as "advisory warning". The text is accurate in substance; it is not reworded because only the T057 wording is owned.

## Open questions

| Class | Question |
|-------|----------|
| non_blocking | Running `contract` tests in CI stays deferred to CP1/CP2 per the reviewer. T059 removes only the step-level `continue-on-error` and makes the gate step authoritative |

No `blocker_governor` questions. No frozen-interface amendment requested beyond A1 (approved); A2 is declined (see Later in the round-1 triage).

## Stop

**T* round 2 applied; round-3 confirmation requested (T054).** Do not implement until the orchestrator records the round-3 result.
