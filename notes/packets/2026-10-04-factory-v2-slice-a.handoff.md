# Handoff — 2026-10-04-factory-v2-slice-a (interim)

| Field | Value |
|-------|-------|
| Branch | `wo/wo-20261004-factory-slice-a` |
| State | **red; T* requested (T033)** |
| Author model | Claude family (worker). Bootstrap / T* verdict must come from a GPT-family reviewer (D3, FR-037) |
| Head | `7dc2359` |
| Base | `origin/main` @ `c2af7f2` (includes CP0 merge `8cd8cb7`) |
| Frozen CP0 files | not edited |

Pause here. The orchestrator spawns the T* reviewer on T017–T032 (`notes/packets/<date>-factory-v2-slice-a-test-review-t.md`) and resumes this worker for T021–T025 / T034–T038 after triage.

## Commits

| SHA | Role |
|-----|------|
| `350c15c` | packet Status → `in_progress` (CP0 merged 8cd8cb7; P0 T* accepted) |
| `7dc2359` | **red** tests T017–T020, T026–T032 + recorded GitHub fixtures + this slice's `tasks.md` checkboxes |

No green implement commit yet. Red/green pairs will be listed after T*.

## What landed (tests only)

- T017 `tests/contract/test_status.py` — one order per lifecycle state; board JSON sections `in_flight` / `blocked` / `waiting_on_governor` / `ready` / `overrides_per_gate` / `unverified_governor_actions`; fixture bus files have no forbidden status keys.
- T018 `tests/unit/test_lifecycle.py` — data-model § Lifecycle rules; `derive_snapshot(repo, github, settings=, now=)` must write nothing.
- T019 `tests/unit/test_github_adapter.py` + `tests/fixtures/github_recorded/*.json` — `GitHubPort` mapped from recorded REST.
- T020 `tests/unit/test_no_bookkeeping.py` — `count_bookkeeping_commits(repo, since=)`.
- T026–T030 contract tests for `order new/issue`, `claim`/`release` (incl. concurrent FF: exactly one wins), `handoff` (deviations, blocker_governor → exit 2 + board wait, run-complete), `pr open`/`verdict`, `bus pr`.
- T031 `tests/unit/test_scorecard.py` — `compute_scorecard`: drift, first-pass, decision points, governor minutes, rework, Wave 1 dates, FR-035 totals.
- T032 `tests/unit/test_identity.py` — recorded unverified; verified needs `governor_login` APPROVED review; App JWT + recorded installation-token exchange.

T017–T020 and T026–T032 are ticked in `tasks.md` (tests written, red). Implementation tasks remain open.

## Commands and results

Toolchain: `. /tmp/factory-env.sh` (Nix-store `uv` 0.4.30 + Python 3.12.8). `uv sync --locked` PASS. No `pip install`.

| DoD | Command | Result |
|-----|---------|--------|
| collect | `uv run pytest --co` on the 11 new files | **51 collected**, then folded to **50** after merging the green fixture-only status check into the red board test. 0 collection/import errors |
| new tests | `uv run pytest` on those 11 files | **50 failed**, 0 passed. Failures are `AssertionError` (CLI still exit 3) or `pytest.fail` (`Failed: factory.*.* is not implemented`). 0 `ERROR`, 0 `xfail` |
| full | `uv run pytest -q` | **166 failed, 237 passed** (was 116/237 at CP0 Amendment 3; +50 new red) |
| CI selector | `uv run pytest -q -m "not contract and not seed"` | **28 failed, 224 passed, 151 deselected** — the 28 new unit tests are unmarked, so `factory-tests` will be red on this PR until implement. Conservative: did not mark unit tests `contract` to hide them |
| lint | `ruff check .` / `ruff format --check` on the new files | PASS |

## Expected signatures (so implement matches the red tests)

| Export | Call |
|--------|------|
| `factory.lifecycle.derive.derive_snapshot` | `(repo: Path, github: GitHubPort, *, settings=None, now=None) -> LifecycleSnapshot` |
| `factory.github.rest.build_github` | `(settings, env) -> GitHubPort` (httpx; tests inject `httpx.Client` transport) |
| `factory.metrics.history.count_bookkeeping_commits` | `(repo, *, since: str) -> int` |
| `factory.metrics.scorecard.compute_scorecard` | `(repo, *, settings=None) -> dict` with keys `drift`, `first_pass_acceptance`, `decision_points_per_feature`, `governor_minutes`, `governor_minutes_estimated`, `rework_loops`, `wave1_start`, `wave1_exit`, plus FR-035 totals |
| `factory.identity.adapter.build_identity` | `(settings, github) -> IdentityPort` |
| `factory.identity.app_token.mint_installation_token` | JWT from App id + PEM, POST `/app/installations/{id}/access_tokens` |

Board JSON (inside the `--json` envelope `data`): snake_case section names as listed above. Scorecard formulas used in T031: drift = share of `run_complete` orders with no drift correction (2 runs, 1 correction → 0.5); first-pass = share whose first verdict is accept (0.5); decision points = locks per `feature`; `governor_minutes` summed from locks and flagged estimated; `rework_loops` = reject-first orders; `wave1_start` from earliest issue; `wave1_exit` is `None` while an order is still open/rejected.

Gates for handoff local refusal: a change outside owned paths must make `factory handoff` exit 2. Slice B owns `diff-within-owned-paths`; until that gate exists this test stays red even after CLI wiring unless the command fail-closes when `run_gate` raises `GateEntrypointError`. Conservative choice: keep the test; implementer should treat unimplemented registered gates as failing the handoff (FR-009).

## Manual equivalents of P1 gates (bootstrap, FR-037)

| Gate | Manual check | Result |
|------|--------------|--------|
| `red-first-proof` | These tests are committed failing (50 assertion/`Failed`). No matching impl in this commit | pass (shown by hand) |
| `diff-within-owned-paths` | `git diff --name-only origin/main...HEAD` | packet, this handoff, `tasks.md` checkboxes, listed test files, `github_recorded/**`. Nothing in frozen CP0 paths or other slices |
| `test-seam-ban` | no `PYTEST_CURRENT_TEST` / test flags in new src (no new src) | n/a |
| `bus.no-handwritten-status` | T017 walks every `bus/` YAML on every branch of the fixture | asserted in the red test |
| `order-fidelity-declared` / `lock.letter-tokens` | no product impl this commit | n/a |
| `decision-request-no-ids` | none raised | n/a |

`git diff --no-renames` (Amendment 3): no renames in this slice.

## Deviations

1. Worktree is `/tmp/cursor-worktrees/factory-slice-a/repo` (sandbox blocks `~/.cursor/worktrees`). Leftover local branch was rebased onto `origin/main` (`c2af7f2`).
2. Board JSON keys and scorecard formulas are locked by the tests because the contracts name sections in prose, not a schema. T* may debate the names; changing them is a test amendment, not a frozen-interface amendment.
3. Concurrent claim uses two working copies + `ThreadPoolExecutor` calling `factory.cli.app.run` (not two `FactoryCli`s) so capsys is not shared.

## Open questions

| Class | Question |
|-------|----------|
| non_blocking | Should unimplemented registered gates fail `factory handoff` (recommended, FR-009 fail-closed) or skip until slice B lands? |
| non_blocking | CI job `factory-tests` uses `-m "not contract and not seed"`, so the 28 new unit tests will fail that job on this PR. Drop the selector at CP1 (P0 comment) or keep the PR red until implement? |
| non_blocking | Scorecard `wave1_exit`: I treated "still rejected / unmerged" as not exited. Confirm before T035. |

No `blocker_governor` questions. No frozen-interface amendment requested.

## Stop

**red; T* requested (T033).** Do not implement until the orchestrator records T* triage.
