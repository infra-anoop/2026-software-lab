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

## Amendment 2 — T* re-review (verdict-02: reject) fixes

The round-2 re-review (`origin/review/wo-20261003-factory-p0-r2` at `9dd9c90`) found T1 and T3–T6 resolved and left two items open: T2 (governor: strict letter fidelity, thinner behavior must be automatic) and T7 (spec edits outside the owned paths). Before fixing them I merged `origin/main` (PRs #10–#13). The merge commit is `d14caf0` and had no conflicts. I did not merge the round-2 review branch.

### What changed

- **T2: thinner behavior is now mechanical.** The data-model Lock line defines the rule and the seeds test it. The `acceptance.md` row stays as it is.
  - `Lock` gains an optional `direction: min|max`. It applies to every **numeric token** of the lock, meaning a token that holds exactly one number, such as `cap 3`, `max_attempts: 2`, `$5`, or `70%`. `min` means the number is a floor, `max` means a ceiling, and leaving it unset means the number must match exactly. `direction` needs `fidelity: letter` and at least one numeric token. `models.py` exports `LOCK_NUMBER_RE` and `is_numeric_token` so slice B uses the same definition. I regenerated `order.schema.json`.
  - The rule on the Lock line looks only at *code lines*. A code line is a diff line outside `bus/` and outside `*.md` files that is not just a comment (`#`, `//`, `/*`, `*`, `--`). An added code line *honors* a token when it contains the token, case-insensitively. For a numeric token with a `direction`, it can also honor the token through a *counterpart*: a line where the text around the number matches the token (ignoring case and whitespace) and the number is equal or stronger. The PR is blocked in two cases:
    - **(a) removed:** a deleted code line contains a token, and no added code line honors it.
    - **(b) weakened:** an added counterpart of a numeric token uses a different number when `direction` is unset, a smaller number for `min`, or a larger number for `max`.
  - New red seeds (6):
    - `test_seed_lock_token_removed[deleted]`: one of two `railway up` lines is deleted.
    - `test_seed_lock_token_removed[restated_only_in_comment]`: the deleted line comes back only as a comment.
    - `test_seed_lock_numeric_token_weakened[min_floor_lowered]`: `fail_under=60` is added next to the `fail_under = 70` floor, with different spacing.
    - `test_seed_lock_numeric_token_weakened[max_ceiling_raised]`: `$12` is added next to the `$5` ceiling.
    - `test_seed_lock_numeric_token_weakened[exact_changed]`: `--cap 4` is added next to `cap 3`.
    - `test_seed_lock_numeric_token_weakened[exact_lowered_in_place]`: `cap 3` is changed to `cap 2`.
  - New near-miss guards that must pass (6), all in `test_seed_lock_thinner_near_miss_passes`: `min_floor_raised` (70 → 80), `max_ceiling_lowered` ($5 → $3), `token_restated_in_edited_line`, `numeric_token_restated_unchanged`, `token_moved_to_another_file`, and `unrelated_numbers` (`port = 8080`, plus `fail_under_ratio = 0.5`, which shares a prefix with the token).
  - All the new blocked seeds except `exact_lowered_in_place` leave every token present at head. A gate that only checks presence and substitutes therefore lets them through.
  - The `test_seed_declared_lock_violated` docstring no longer hands thinner behavior to the reviewer.
- **T7: the owned-paths amendment.** I recorded `wo-20261003-factory-p0.amend-01` at `bus/orders/wo-20261003-factory-p0/amendment-01.yaml`. Its fields are `kind: amendment`, `actor: orchestrator`, `actor_verified: false`, and `supersedes: [owned_paths]`. The new value is the packet's original list with the data-model entry widened to the Lock and Gate lines, plus `specs/001-factory-v2/contracts/cli.md`. Because `owned_paths` are globs, YAML comments in the file state the line scope of each entry. The packet's Owned paths now list both edits with "(via amend-01)" and point to the amendment.

### Red-first pairs (Amendment 2)

| Finding | Red commit (assertion) | Green commit |
|---------|------------------------|--------------|
| T2 models | `3fb79e4`: 12 failed, all `Lock has no direction field` or `bus models export no is_numeric_token` | `085ccf8` |
| T2 seeds | `3ebb520`: 12 new seeds, each failing `gate lock.letter-tokens is not implemented` | slice B |

The new seeds sit in a separate commit after the model change, so every seed fails by assertion and none fails while building its fixture.

**Rule consistency check (not committed).** I wrote a throwaway reference `lock.letter-tokens` that implements the Lock-line rule, ran all 19 lock seeds against it, and then deleted it.
- With the full rule, all 19 behaved as expected.
- With rules (a) and (b) turned off, exactly the 5 new blocked seeds that keep every token present at head were let through.
- **Note for slice B:** use `git diff --no-renames`. With rename detection on, a moved file has no +/- lines, so `token_moved_to_another_file` fails.

### Commands and results (Amendment 2)

| DoD | Command | Result |
|-----|---------|--------|
| 1 | `cd scripts/factory && uv sync --locked` | PASS |
| bus | `uv run factory check schema` (includes `amendment-01.yaml` and `verdict-01.yaml`) | PASS: `schema ok`, exit 0 |
| 2a | `uv run factory check schema --path tests/fixtures/messages/` | PASS: `schema ok` |
| 2c | `factory check schema --write` after the `Lock.direction` change | only `order.schema.json` changed. It is committed and the check is fresh |
| 3 | `uv run pytest -q tests/unit/test_bus_models.py` | 165 passed |
| 4 | `uv run pytest -q -m "not contract and not seed"` | 224 passed, 125 deselected |
| 4 | `uv run pytest -q tests/contract tests/seeds` | 112 failed, 13 passed. All 112 are `AssertionError`s. 0 collection or import errors, 0 `xfail` |
| — | `uv run pytest -q` (full) | **237 passed, 112 failed**: the earlier 225/100 plus 12 green model tests and 12 red seeds |
| 5 | `uv run ruff check .` / `ruff format --check .` | clean |
| 6 | `os.getenv` / `os.environ` outside `config/` | none |
| owned paths | `git diff --name-only origin/main...HEAD` | within the paths amended by amend-01, plus `bus/orders/wo-20261003-factory-p0/**`, this packet and handoff, and `TEST_REVIEW.md` (see the open question below) |

### Deviations (Amendment 2)

1. **The amendment file is named `amendment-01.yaml`, not `amend-01.yaml`.** The message id is `wo-20261003-factory-p0.amend-01`, but `contracts/messages.md` § Layout and the bus store expect the file `amendment-NN.yaml`. Under the name `amend-01.yaml`, `factory check schema` fails with exit 1 ("belongs at …/amendment-01.yaml"). The conservative choice was to follow the frozen layout so the file validates.
2. **`actor_model: claude-opus-5.5` and `actor_verified: false`.** The worker recorded the message on the orchestrator's instruction, so nothing verifies the actor. The orchestrator should correct the model if it is different.
3. **Line scope lives in YAML comments, not in `owned_paths`.** The model types `owned_paths` as globs, so a string like "data-model.md (Lock and Gate lines only)" would not match the file. The scope is stated in the amendment's comments and in the packet.
4. **`direction` is set per lock, not per token.** This keeps the model change to one field. If two numeric tokens need different directions, they go in separate locks.

### Open questions (Amendment 2)

| Class | Question |
|-------|----------|
| non_blocking | **`TEST_REVIEW.md` ownership.** In round 1, on the orchestrator's instruction, I filled the Resolution column of the orchestrator's triage table in `specs/001-factory-v2/TEST_REVIEW.md`. amend-01 lists exactly the two authorized paths and does not cover this file. If the owned-path record should cover it, the orchestrator can add an `amend-02` or treat review artifacts as orchestrator-owned. |
| non_blocking | **The round-2 review branch is not merged.** `verdict-02.yaml` and the Round 2 section of `TEST_REVIEW.md` are only on `origin/review/wo-20261003-factory-p0-r2`, and amend-01's `refs` names `verdict-02` by id. Merge it if the work branch should carry the whole bus history. |

The Amendment 1 open question about what counts as "added code" is resolved: the data-model Lock line now defines code lines.

## Amendment 3 — T* round 3 (verdict-03: reject) fix for T8

Round 3 (`origin/review/wo-20261003-factory-p0-r3` at `8f6594e`) found T2 and T7 resolved. It raised T8: the round-2 "removed" rule blocked deleting one of several token lines even when the remaining code still honors the lock. The governor adjudicated T8 on 2026-10-04 as a **per-file rule**. Both Amendment 2 open questions are closed: the orchestrator's `2cda4c9` merged the round-2 review history and recorded `amend-02`, which covers `TEST_REVIEW.md` and this order's bus directory.

### What changed

- **Merges.** I fast-forwarded to the orchestrator's `2cda4c9`, then merged `origin/review/wo-20261003-factory-p0-r3`. That merge was also a fast-forward to `8f6594e`, so there were no conflicts. `TEST_REVIEW.md` keeps the Triage table, followed by Round 2 and Round 3 as the reviewer wrote them.
- **Lock line (`192a12a`, covered by the Lock-line scope in amend-01).**
  - **New removal rule (a), per file:** a change is blocked when a code file that honored a token at base no longer honors it at head, whether the token was edited away or the file was deleted, unless an added code line elsewhere in the change honors it (a move).
  - **What passes:** deleting some of a file's occurrences while that file still honors the token.
  - **Unchanged:** "Code lines" are now defined over file contents as well as diff lines (same exclusions: `bus/`, `*.md`, comment-only lines). The `--no-renames` requirement is now written on the Lock line. The weakened rule (b) is unchanged.
- **Seeds (`f56a138`).**
  - `test_seed_lock_token_removed` is red (3 cases):
    - `only_file`: the token is removed from the only file that has it and is not added anywhere else.
    - `only_file_restated_in_comment`: the only occurrence becomes a comment.
    - `other_file_still_has_it`: `deploy.sh` loses the token while a changed `release.sh` still has it. This is blocked by the letter of the per-file rule, and it is the only seed a presence-only gate lets through.
  - New passing guards in `test_seed_lock_thinner_near_miss_passes`:
    - `t8_repro_one_of_two_lines_deleted`: the reviewer's repro, the old `[deleted]` seed.
    - `several_occurrences_deleted_file_still_has_token`: two of three lines deleted.
    - `occurrence_commented_out_file_still_has_token`: the old `[restated_only_in_comment]` fixture, which now passes.
    - `token_moved_to_another_file` is kept.
- **Triage row.** `TEST_REVIEW.md` has a T8 row: "accept — per-file removal rule", decided by "governor 2026-10-04", with the commits above as the resolution.

### Rule consistency check (reference gate, not committed)

I wrote a throwaway `lock.letter-tokens` that implements the Lock line, then deleted it.
- **Full rule:** all 23 lock seeds behaved as expected.
- **Removal rule off:** only `other_file_still_has_it` was let through.
- **Removal and presence rules off:** all removal and outside-code seeds were let through.
- **Weakened rule off:** exactly the 3 weakened seeds that keep the token present were let through.
- **Round-2 rule (deleted line with no restoring added line):** all 3 new T8 guards fail, so the guards catch the false positive.

### Commands and results (Amendment 3)

| DoD | Command | Result |
|-----|---------|--------|
| 1 | `cd scripts/factory && uv sync --locked` | PASS |
| bus | `uv run factory check schema` (covers amend-01/02 and verdict-01/02/03) | PASS: `schema ok` |
| 2a | `uv run factory check schema --path tests/fixtures/messages/` | PASS: `schema ok` |
| 4 | `uv run pytest -q -m "not contract and not seed"` | 224 passed, 129 deselected |
| 4 | `uv run pytest -q tests/contract tests/seeds` | 116 failed, 13 passed. All 116 are `AssertionError`s. 0 collection or import errors, 0 `xfail` |
| — | `uv run pytest -q` (full) | **237 passed, 116 failed**: the earlier 112 plus 1 new red removal seed and 3 new guards, which also go through `run_seed` and stay red until the gate exists |
| 5 | `uv run ruff check .` / `ruff format --check .` | clean |
| owned paths | `git diff --name-only 8c50726..HEAD` | worker edits: `test_seeds.py`, the data-model Lock line, the `TEST_REVIEW.md` Triage table, and this handoff. The rest are merged review and orchestrator files |

### Deviations (Amendment 3)

1. **I added a whole T8 Triage row on the orchestrator's instruction.** amend-02 limits worker edits in `TEST_REVIEW.md` to the Resolution column of the Triage table. The Disposition and Decided-by cells repeat the governor's adjudication word for word. No new amendment was asked for, so I did not record one. The orchestrator can add an `amend-03` if the reviewer needs the row authorship on record.
2. **`other_file_still_has_it` is blocked.** It follows the letter of the adjudication: the token disappears from a file that had it, and no added line elsewhere has it. That holds even though another changed file still honors the lock. If the governor meant the gentler reading (the reviewer's option A, "honored anywhere at head"), this one seed flips to a passing guard.

### Open questions (Amendment 3)

None that block. Deviation 2 is the only reading call left.
