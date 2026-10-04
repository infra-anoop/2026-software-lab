# Handoff — 2026-10-03-factory-v2-p0-contracts (P0 contract freeze, T001–T015)

| Field | Value |
|-------|-------|
| Branch | `wo/wo-20261003-factory-p0` (from `main` @ `9bb5525`) |
| Author model | Claude family (worker); bootstrap verdict must come from a GPT-family reviewer (D3, FR-037) |
| Tasks | T001–T015 ticked in `specs/001-factory-v2/tasks.md`; nothing else ticked |
| State | CP0 deliverables complete. Contract + seeds suites intentionally red (P1 work) |

## What changed

- **uv project** `scripts/factory/` (T001): Pydantic v2, Typer, httpx, PyYAML; dev pytest + ruff; `uv.lock` committed. Ruff bans `os.getenv` / `os.environ` outside `src/factory/config/` (TID251) and enforces annotations (ANN).
- **Config** (T002): root `factory.toml` (cap 3, horizon 60, stale ×3, families `claude→anthropic`, `gpt→openai`, `gemini→google`, identity `recorded`, rule paths, decision-lint jargon); typed loader `factory.config.settings` (`load_settings`, `load_env` — the only env read).
- **Workflows** (T003–T004): `verify-source.yml` legacy step now `pytest scripts/ -v --ignore=scripts/factory`; new `factory-gates.yml` with job `factory-tests` (`uv sync --locked` + `pytest -m "not contract and not seed"`, comment: drop selector at CP1) and placeholder job `factory-gates` (`continue-on-error: true` until CP2; runs `factory gate run --pr`).
- **Bus layout** (T005): `bus/{orders,decisions,corrections,postmortems}/.gitkeep`.
- **Message models** (T006) `bus/models.py`: envelope + 11 kinds, `extra="forbid"`, frozen, forbidden keys `status|state|done|progress` rejected at any depth, id patterns with real-date check, `actor_model` required unless governor, horizon via validation context, waived lock ⇒ `waiver_ref`, verdict severity/tag enums, override reason non-blank, governor-only override ⇒ governor actor.
- **Bus store** (T007) `bus/store.py`: read-only loader over working tree or a git ref; layout resolver (`expected_path`) rejects misplaced files; `load_all(repo, ref) -> list[Message]`.
- **Schemas** (T008) `bus/schema.py` + `cli/checks.py`: `factory check schema [--write] [--path …] [--json]`; canonical JSON per kind in `scripts/factory/schemas/` (11 files committed); stale/missing/orphan detection.
- **Gate registry** (T009) `gates/registry.py` + `gates.yaml`: 24 P1 rows, every row with an `entrypoint`; rule `governor-only ⇔ category ∈ {spend, secrets, irreversible, governor_decision}` enforced; data-model Gate line gained `` `entrypoint: "module:function"` `` (only edit to that file).
- **Frozen interfaces** (T010) `api.py`: `GateContext`, `GateResult`, `run_gate`, `OrderState`, `LifecycleSnapshot`, `GitHubPort`, `IdentityPort` (+ supporting types listed under Deviations); every docstring says "Frozen at CP0".
- **CLI skeleton** (T011): every command in `contracts/cli.md` registered; exit codes 0/1/2/3/4 in `cli/exit_codes.py`; unimplemented commands exit 3 with `factory <cmd>: not implemented`; `cli/common.py` holds the `DEPS` provider (GitHub/identity adapters loaded lazily from slice-A module paths; tests monkeypatch it).
- **Fixtures** (T012): `tests/fixtures/repo_builder.py` (bare origin + clone, isolated git env, message/event writers, demo feature, base/head pairs, `GateContext` builder), `fake_github.py` (`FakeGitHub` implements `GitHubPort`), `cli_runner.py`, `conftest.py`.
- **Contract test** (T013) `tests/contract/test_cli_contract.py` (`pytest.mark.contract`): one exit-code case per row of `contracts/cli.md`.
- **Seeds** (T014) `tests/seeds/test_seeds.py` (`pytest.mark.seed`): the 8 SC-002 seeds, each asserting the named gate blocks.
- **Model unit tests** (T015) `tests/unit/test_bus_models.py` (144 tests) + unit tests for store, schema export, registry, settings, api, repo builder.

## Commands and results

Toolchain: `. /tmp/factory-env.sh` puts the Nix-store `uv 0.4.30` and `python3 3.12.8` on PATH (see Deviations).

| DoD | Command | Result |
|-----|---------|--------|
| 1 | `cd scripts/factory && uv sync --locked` | PASS (`Audited 25 packages`); `uv.lock` committed |
| 2a | `uv run --project scripts/factory factory check schema --path scripts/factory/tests/fixtures/messages/` | PASS — `schema ok`, exit 0 |
| 2b | `uv run --project scripts/factory factory check schema --write` | PASS — wrote 11 files (one per kind); `git status scripts/factory/schemas` clean (regeneration is byte-identical) |
| 2c | add `note: str \| None = None` to `Release`, then `factory check schema` | PASS — `release.schema.json: stale (run factory check schema --write)`, exit 1; reverted, exit 0. Also covered by unit + contract tests |
| 3 | `uv run --project scripts/factory pytest scripts/factory/tests/unit/test_bus_models.py` | PASS — 144 passed |
| 4 | `uv run --project scripts/factory pytest scripts/factory/tests/contract/test_cli_contract.py scripts/factory/tests/seeds/test_seeds.py` | 50 failed, 9 passed; 0 collection errors; 50 `AssertionError`s; 0 `xfail` in `tests/` |
| 4 | `cd scripts/factory && uv run pytest -m "not contract and not seed"` (the CI selector) | PASS — 197 passed, 59 deselected |
| 4 | full `uv run --project scripts/factory pytest scripts/factory/tests` | 206 passed, 50 failed (the intentional red set) |
| 5 | `uv run --project scripts/factory ruff check scripts/factory` | PASS — `All checks passed!` |
| 6 | ruff `ANN` rules (all signatures, tests included) + `rg -n 'os\.(getenv\|environ)' scripts/factory/src \| rg -v src/factory/config/` | PASS — none outside config. The only other repo hits are ruff ban messages in `pyproject.toml` and a string literal in the `test_seam` seed fixture (the seeded violation) |
| 7 | `api.py` review against T010 | PASS — all T010 names present; "Frozen at CP0" in every docstring |
| 8 | `tests/unit/test_registry.py` (hard-coded P1 id table vs `gates.yaml`) | PASS |
| — | legacy step `pytest scripts/ --ignore=scripts/factory --co` | 115 tests collected, none under `scripts/factory` |

### Intentionally red (P1 work), all by assertion

- **Contract (42 of 51)**: every failure is `AssertionError: expected exit N, got 3` (the command prints "not implemented"): 21 expect 0, 20 expect 2 (refusals), and 1 expects 4 (claim with origin unreachable). The 9 green cases are `check schema` ok/fail/json/misplaced/status-key and the usage/config error paths.
- **Seeds (8 of 8)**: each is `AssertionError: gate <id> is not implemented`, for `order-fidelity-declared`, `lock.letter-tokens`, `deferral-words-need-od`, `red-first-proof`, `test-seam-ban`, `diff-within-owned-paths`, `decision-request-no-ids`, and `catalog-test-linkage`. `run_gate` raises `GateEntrypointError` (fail closed), and the seed helper converts that into an assertion failure instead of a collection or import error.

## Manual equivalents of P1 gates (bootstrap verdict input, FR-037)

| Gate | Manual check | Result |
|------|--------------|--------|
| `red-first-proof` | `851cd11` committed `test_bus_models.py` against a permissive stub: **124 failed / 20 passed**, failures `DID NOT RAISE` plus one `KeyError` raised inside a test body (no collection errors). `63ab273` added the real models: 144 passed. The other P0 unit tests (store, schema, registry, settings, api, repo builder) landed in the same commit as or after their code. They are red relative to `main` only because the names they import do not exist there. Declared here, not hidden |
| `diff-within-owned-paths` | `git diff --name-only main...HEAD` filtered by the packet's owned paths | Nothing outside them except this handoff file (required by the DoD). `verify-source.yml` diff is the single `pytest scripts/` line; `data-model.md` diff is the single Gate line |
| `test-seam-ban` | `rg -n 'PYTEST_CURRENT_TEST\|"pytest" in sys\.modules\|\bTESTING\b\|\bIS_TEST\b\|sk-test' scripts/factory/src` | none. Test injection uses the explicit `DEPS` provider plus monkeypatch, with no branch on test mode |
| `bus.no-handwritten-status` | forbidden-key validator + `invalid_messages/order-with-status.yaml` | rejected (unit + contract) |
| `deferral-words-need-od` | read every changed spec line (`data-model.md` Gate line, `tasks.md` checkboxes) | no deferral words added |
| `order-fidelity-declared` / `lock.letter-tokens` | packet Fidelity table vs code | Pydantic v2 + Typer + httpx + PyYAML (no click-only CLI, no dataclass messages, no `requests`); uv project at `scripts/factory`; no status fields on the bus; cap 3 / horizon 60; `gpt → openai`; identity is the `IdentityPort` Protocol only (GitHub App adapter left to slice A) |
| `decision-request-no-ids` | not applicable | no decision requests raised |
| `uv-sync-locked` | DoD 1 | pass |

## Deviations (why + conservative choice)

1. **Worktree lives in `/tmp/cursor-worktrees/…`**, not `~/.cursor/worktrees`, because the sandbox denied writes there. Git state is unaffected.
2. **`nix develop` could not run** (`/nix/var/nix/db/big-lock: Permission denied`). I used the same Nix-store `uv` and Python 3.12 binaries directly, with `UV_PYTHON_DOWNLOADS=never`, and installed nothing with pip. CI uses `astral-sh/setup-uv`, which matches the existing workflows.
3. **Gate `scope` adds `pr`** alongside `changed_lines|repo`, because PR-metadata gates (links, verdicts, override, cap) are neither. `data-model.md` was not changed beyond the allowed Gate line (see open question).
4. **The existing checks are registered in P0** (`validate-secrets-schema`, `validate-deploy-env`, `uv-sync-locked`, ci_job `verify`), overlapping T059. This satisfies DoD "every P1 gate". Slice C only implements their entrypoints in `gates/repo/existing.py`.
5. **Entrypoint module choices**: drift gates go in `factory.gates.drift.*` (slice B), intent in `factory.intent.coverage:presence_gate` (slice B), PR gates in `factory.gates.pr.*` (slice C), and repo gates (including `bus.schema` and `factory-status-test`) in `factory.gates.repo.*` (slice C). Each fits a slice's owned paths. Slices may adjust their own rows.
6. **Files beyond those named in tasks**: `cli/common.py`, `bus/schema.py`, `tests/conftest.py`, `tests/fixtures/cli_runner.py`, `tests/fixtures/__init__.py`, plus extra unit tests. All are inside `scripts/factory/**`.
7. **`api.py` has supporting types beyond T010's names**: `GateEntrypointError`, `OVERLAY_STATES`, `OrderLifecycle`, `PullRequest`, `PullRequestReview`, `CheckRun`, `CommitStatusValue`. The ports cannot be typed without them. I kept them minimal (the REST subset the contracts use).
8. **Field names the data model leaves open**:
   - handoff `open_questions: [{question, class}]`
   - amendment `values`
   - run-complete `cost_usd_estimated` (default true)
   - verdict `manual_equivalents` (required when `bootstrap: true`)
   - decision lock id `<decision-id>.lock`
   - decision ids are kebab slugs
   - envelope `actor_verified` stored with default false; the identity adapter must not trust the stored value
9. **The loader skips `bus/postmortems/`**, because there is no message kind for post-mortems.
10. **`governor_login = "infra-anoop"`**: `research.md` writes `infra_anoop`, but GitHub logins cannot contain underscores. The value comes from the repo owner in `[github] repository`.
11. **The decision-lint jargon list is seeded by me** from the agent-os vocabulary (packet, worktree, subagent, slice, fidelity, owned paths, acceptance catalog, finish bar).
12. **`order new --lock ID=letter|intent|waived`**: I added this option so the `undeclared_substitution` contract row is expressible.
13. **Typer 0.27 vendors click privately**, so `run()` catches Typer's exceptions instead of importing click. The CLI is still Typer, which is the letter lock.

## Open questions

| Class | Question |
|-------|----------|
| non_blocking | Where do named locks live for `order-fidelity-declared` / `lock.letter-tokens`? The fixture assumes locked rows in the spec's Open Decisions table plus `[OD:D#]` task tags. Slice B should confirm or amend the fixture through the orchestrator. |
| non_blocking | The post-mortem file format and message kind are unspecified (US7). The loader skips `bus/postmortems/` for now. |
| non_blocking | `data-model.md` Gate `scope` should list `pr`. That needs a spec edit outside this packet. |
| non_blocking | The governor may want to review the decision-lint jargon list in `factory.toml`. |
| non_blocking | `cli/common.py`, `tests/conftest.py`, `tests/fixtures/**`, and `tests/contract/test_cli_contract.py` are owned by no slice. Changes should go through an orchestrator amendment, like `api.py`. |
| non_blocking | `GitHubPort` has no commit-status read. If lifecycle "required checks green" needs statuses as well as check runs, slice A must request an amendment. |
| non_blocking | Adapter factory paths `factory.github.rest:build_github(settings, env)` and `factory.identity.adapter:build_identity(settings, github)` are frozen for slice A by `cli/common.py`. |

No `blocker_governor` questions.
