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

## Amendment 1 — T* review (verdict-01: reject) fixes

Merged `origin/review/wo-20261003-factory-p0` (`TEST_REVIEW.md`, `bus/orders/wo-20261003-factory-p0/verdict-01.yaml`); appended the orchestrator triage verbatim; Resolution column filled per finding.

### What changed

- **T1 (blocker):**
  - `api.py` adds `CommitStatus{context, state, description, target_url}` and `GitHubPort.list_commit_statuses(sha)`, which returns the latest status per context and `[]` when there are none. The "Frozen at CP0" docstrings are kept.
  - `FakeGitHub` implements it.
  - Conformance helper `assert_commit_status_read_after_write(port)` in `tests/unit/test_api.py`, which slice A can reuse against the real adapter.
- **T2 (governor: strict):**
  - `Lock` with `fidelity: letter` requires non-empty, non-blank `letter_tokens`.
  - New optional `substitutes: list[str]`: values must be non-blank, and none may repeat a letter token.
  - Documented on the data-model Lock line. `order.schema.json` regenerated.
  - Seeds added:
    - token appears only outside code, one case each for a comment, a deleted line, the order file, and docs, while the code uses Fly
    - a registered substitute in added code next to the honored token
    - a false-positive guard where the honored lock passes
  - The seed docstring notes that "thinner behavior" stays with the reviewer's fidelity rubric.
- **T3:**
  - `cli/common.py` adds `JsonEnvelope`, `CliError`, and `CommandError`. `emit(command, …, data=…)` reports success. `not_implemented` now raises `CommandError(3)`.
  - `run()` turns `CommandError`, usage, config, and bus/registry errors into an error envelope under `--json`.
  - `contracts/cli.md` gains a § JSON envelope paragraph. `factory hook` is exempt.
  - `test_json_envelope` covers 26 scenarios across every command group, including refusal, usage, and config error paths.
- **T4:** data-model Gate `scope` lists `pr`.
- **T5:**
  - The jargon seed is split into the cases below. Each blocking case also requires the gate message to name the offending id or term.
    - 9 id-regex cases: one per letter of `\b[TFRPD]\d+\b`, plus `FR-\d+`, `SC-\d+`, `US\d+`, and `§`
    - an id in an option label
    - 8 per-term cases parameterized from `factory.toml`
    - a case-insensitive case
    - 4 near-miss cases that must pass
  - The fixture `factory.toml` now takes its jargon list from the repo's `factory.toml` instead of a 6-term copy.
- **T6:**
  - `config.settings.find_repo_root(start)` searches from the CWD up to the git root and never above it.
  - `cli.common.resolve_repo(repo)`: every command's `--repo` now defaults to `None` and is resolved this way.
  - A relative `check schema --path` now resolves against the CWD.

### Red-first pairs (amendment)

| Finding | Red commit (assertion) | Green commit |
|---------|------------------------|--------------|
| T1 | `de60b63`: 2 failed (`GitHubPort … has no operation to read them back`, `no commit-status read on the port`) | `a29b31b` |
| T6 | `50315d5`: 2 failed (`assert 3 == 0`, `assert 3 == 1`, "factory.toml: not found"); the git-root and explicit-`--repo` guards passed already | `f51929c` |
| T2 models | `670a6d5`: 8 failed (`DID NOT RAISE` ×4, `Lock has no substitutes field` ×4) | `8e2f3b7` |
| T3 | `ff1695c`: 26 failed (22 `expected exit N, got 3`; 4 envelope-shape assertions on `check schema`) | `c8fd90a` turns the 4 `check schema` cases green; the 22 slice-owned cases stay red |

The T2 lock seeds were committed together with the model change. Before it, two of them failed while building the fixture (`substitutes` was an unknown key) rather than by assertion, so I kept them out of the red commit. After `8e2f3b7`, all seeds fail by assertion.

### Commands and results (amendment)

| DoD | Command | Result |
|-----|---------|--------|
| 1 | `cd scripts/factory && uv sync --locked` | PASS |
| 2a | `uv run --project scripts/factory factory check schema --path scripts/factory/tests/fixtures/messages/` | PASS, exit 0 |
| 2a (T6) | `cd scripts/factory && uv run factory check schema --path tests/fixtures/messages/` (packet-exact) | PASS, exit 0 (was exit 3) |
| bus | `uv run --project scripts/factory factory check schema` (includes the merged `verdict-01.yaml`) | PASS, exit 0 |
| 2b | `… factory check schema --write` | 11 files, no diff after the T2 regeneration |
| 2c | `factory check schema` after the T2 `Lock` change, before regenerating | `order.schema.json: stale`, exit 1; exit 0 after `--write` |
| 3 | `… pytest scripts/factory/tests/unit/test_bus_models.py` | 153 passed |
| 4 | `… pytest scripts/factory/tests/contract scripts/factory/tests/seeds` | 100 failed, 13 passed. 0 collection errors, 100 `AssertionError`s, 0 `xfail` |
| 4 | `cd scripts/factory && uv run pytest -m "not contract and not seed"` | 212 passed, 113 deselected |
| — | full `… pytest scripts/factory/tests` | 225 passed, 100 failed (the intentional red set) |
| 5 | `… ruff check scripts/factory` and `ruff format --check` | clean |
| 6 | `os.getenv` / `os.environ` outside `config/`; test-seam scan of `src/` | none / none |

### Intentionally red now (100, all by assertion)

- **Contract (64):** the 42 original exit-code cases plus 22 slice-owned `test_json_envelope` cases. Every one is `expected exit N, got 3`: 40 expect 0, 23 expect 2, and 1 expects 4.
- **Seeds (36):**
  - `undeclared_substitution`, `hidden_deferral`, `not_red_first`, `test_seam`, `outside_owned_paths`, and `catalog_unlinked`
  - 7 lock-fidelity seeds
  - 23 decision-request seeds
  - Each fails `gate <id> is not implemented`. The near-miss and honored-lock guards also go through `run_seed`, so they stay red until the gate exists.

### Deviations (amendment)

1. **Extra paths, both named by the amendment:** `specs/001-factory-v2/contracts/cli.md` (one paragraph, as T3 instructs) and the data-model Lock line (as T2 instructs). Both sit outside the original owned paths.
2. **Every command now defaults `--repo` to `None`** and resolves it with `resolve_repo`, including the slice-owned stub modules (`cli/{board,orders,gates,intent,mining}.py`). Only the option default changed; the stubs still raise not-implemented.
3. **Relative `check schema --path` now resolves against the CWD**, not the repo root. This is the usual CLI behavior and what makes the packet-exact command work. All absolute-path callers are unchanged.
4. **New frozen helpers in `cli/common.py`:** `CommandError`, `CliError`, `JsonEnvelope`, and `emit(command, …)`, which replaces the old `emit(payload, …)`. Slice commands must report through `emit` and `CommandError`, or the envelope tests stay red.
5. **Seed choices beyond the brief:**
   - false-positive guards (`test_seed_lock_honored_passes` and the near-miss cases)
   - the requirement that blocked decision requests name the offender
   - a case-insensitive jargon case
   - an id in an option label
   These tighten the gates and don't change policy. Slice B may push back through the orchestrator.

### Open questions (amendment)

| Class | Question |
|-------|----------|
| non_blocking | **Lock substitutes:** what counts as "added code" for `lock.letter-tokens`? The seeds treat comments, deleted lines, the order file, and docs (`docs/**`, `*.md`) as not code, and shell scripts and config files as code. Slice B should confirm the exact rule. |
| non_blocking | **Plural jargon:** should plural forms (`slices`, `packets`) block? The seeds don't decide this; the near-miss cases only fix that `sliced` and `packaging` pass. |

These earlier open questions are now resolved: commit-status read (T1), Gate `scope: pr` (T4), and the jargon list (T5, governor accepted it).
