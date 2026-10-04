# T* test review — Factory v2 P0 contract freeze

Reviewed `wo/wo-20261003-factory-p0` at `926397b8aa6c447a2142864e1494ee01ac37fd94`.
Reviewer family: GPT/OpenAI; author family: Claude/Anthropic. Inputs were git artifacts only.

## A. Executive verdict

**Do not implement against these tests yet.** The red suites are honestly red, the model tests have strong negative coverage, and the worker's historical red-first claim is reproducible. However, the frozen GitHub interface cannot read the commit-status contexts that the design itself writes, so slices A/C cannot implement “required checks green” without amending CP0. The declared-lock seed also permits a materially thinner fidelity gate than SC-002/FR-019 require, and the worker-selected governor-jargon vocabulary is an unapproved product policy.

Decision: **reject** the P0 bootstrap pending T1 and governor disposition of T2/T5.

Strength: `test_bus_models.py` is unusually effective negative-contract coverage: 124/144 tests demonstrably failed against the permissive stub and all 144 pass against the implemented Pydantic models. The full suite's 50 expected failures are assertion failures with no collection/import failures.

## B. Findings table

| ID | Severity | Tag | Lens | Locus | Finding | Suggested resolution |
|----|----------|-----|------|-------|---------|----------------------|
| T1 | Blocker | arch | Frozen-interface sufficiency | `scripts/factory/src/factory/api.py` `GitHubPort`; slices A/C | `set_commit_status()` writes `factory/<gate-id>` commit-status contexts, but the port can only read Check Runs. GitHub commit statuses and Check Runs are separate APIs, so lifecycle cannot establish “required checks green” and derive `accepted` from the frozen interface. | Amend CP0 before slices: add a typed commit-status read operation/model (or lock all factory reporting to Check Runs and change the write API/contracts consistently). Add a port conformance test proving written status contexts can be read. |
| T2 | Debate | product | Lock fidelity | `tests/seeds/test_seeds.py::test_seed_declared_lock_violated`; `bus/models.py::Lock` | The seed catches only complete absence of the token `railway`. A lazy gate can pass a Fly/thinner implementation if “railway” remains in a comment, deleted line, order file, or documentation. `letter_tokens` may also be empty, making declared letter fidelity vacuously pass. This is weaker than SC-002/US3 #8 (“different tool or host, or thinner behavior”). | **product:** Governor chooses: (A) retain the locked semantic claim and require a non-empty token set plus positive substitute/thinning fixtures, or (B) explicitly narrow the product promise to lexical presence. Recommend A. |
| T3 | Debate | process | Contract coverage | `contracts/cli.md`; `tests/contract/test_cli_contract.py` | The contract says every command accepts `--json`, but only `status` and `check schema` exercise it. A lazy implementation can ignore or reject machine output on orders, claims, gates, decisions, scorecard, and mining while this suite goes green. | **process:** parameterize one parse/output-shape check over every command group; require valid JSON with a stable success/error envelope, not merely exit 0. |
| T4 | Later | arch | Cross-artifact consistency | `data-model.md` Gate row; `gates/registry.py`; `gates.yaml` | The implementation adds `scope: pr`, required by many plan/contract rows, while `data-model.md` still freezes only `changed_lines|repo`. The deviation is technically correct but leaves the source contract inconsistent. | Amend `data-model.md` to include `pr`; keep the registry behavior. |
| T5 | Debate | product | Governor-facing policy | `factory.toml [decision_lint].jargon`; seed `test_seed_jargon_to_governor` | The worker invented eight rejected terms. The seed mixes ids and jargon, so it can pass if only ids are detected and does not prove any configured term blocks. This controls which governor questions are rejected and therefore is product behavior, not harmless fixture detail. | **product:** Governor accepts/edits the vocabulary. Split tests into exact-id-regex cases and one case per configured jargon term, with allowed near-misses to constrain false positives. |
| T6 | Nit | process | Reproducibility | review-packet schema command | From `scripts/factory`, the listed `uv run factory check schema --path tests/fixtures/messages/` exits 3 because `factory.toml` is not found. The equivalent root command with `--repo .` passes. | Correct the packet/golden command or make repo-root discovery work from the uv-project directory. |

## C. Adversarial positions

### 1. Position: these tests would go green while a spec lock fails

The strongest case is lock fidelity. An implementation can scan the entire diff for each declared token and pass when the token appears in the immutable order YAML, documentation, a comment, or a deleted line, even while the actual output uses Fly or provides thinner behavior. The current seed only proves the no-token case and `Lock.letter_tokens` accepts `[]`. It therefore does not fail closed on the product's semantic “letter fidelity” promise.

What would have to be true for the suite to be right anyway: the intended product contract would need to be lexical token presence only, despite SC-002 and US3 explicitly naming different hosts/tools and thinner behavior.

### 2. Position: these tests over-constrain implementation / test the wrong layer

The monolithic CLI file fixes exact fixture orchestration and exit codes before slice-specific contract tests exist. In particular, it assumes particular command option shapes and filesystem preparations while often asserting only the exit code, which can encourage handlers tailored to fixtures rather than observable effects. The later slice tests reduce this risk, but CP0 labels all command rows “contract” already.

What would have to be true for the suite to be right anyway: T013 is treated strictly as a command-registration/exit-taxonomy smoke suite, while T017–T061 remain mandatory before implementation and own all effect/output semantics.

## D. Catalog / contract coverage map

| Catalog id or contract hook | Test file / name | Can fail today? | Gap |
|-----------------------------|------------------|-----------------|-----|
| CLI exit taxonomy and refusal rows | `contract/test_cli_contract.py` | yes — 42 assertions red | Exit codes are covered; most effects and JSON shapes intentionally await slice tests. |
| Common CLI `--repo` | `contract/test_cli_contract.py` fixture calls | yes | Broadly exercised. |
| Common CLI `--json` | schema/status tests only | partly | Missing for most command groups (T3). |
| `bus.no_handwritten_status` / FR-003 | `unit/test_bus_models.py` forbidden-key matrix; schema contract | yes, green against implementation | Strong top-level and nested coverage. |
| T006 message constraints | `unit/test_bus_models.py` | yes, green | Strong; historical 124-red/20-pass proof reproduced. |
| `seed.substitution_undeclared` | `seeds/test_seeds.py::test_seed_undeclared_substitution` | yes — red because gate absent | Single realistic task/lock fixture. |
| `seed.substitution_declared` | `test_seed_declared_lock_violated` | yes — red because gate absent | Does not defeat lexical/token-presence shortcuts or empty token lists (T2). |
| `seed.hidden_deferral` | `test_seed_hidden_deferral` | yes — red because gate absent | Positive violation only; exemption edge tests are correctly scheduled for slice B. |
| `seed.not_red_first` | `test_seed_not_red_first` | yes — red because gate absent | Covers already-green test; import-error distinctions are scheduled in T040. |
| `seed.test_seam` | `test_seed_test_seam` | yes — red because gate absent | Covers `PYTEST_CURRENT_TEST`; remaining patterns await slice B. |
| `seed.outside_owned_paths` | `test_seed_outside_owned_paths` | yes — red because gate absent | Meaningful owned/unowned pair. |
| `seed.jargon_to_governor` | `test_seed_jargon_to_governor` | yes — red because gate absent | Mixed ids and jargon cannot identify which policy fired (T5). |
| `seed.catalog_unlinked` | `test_seed_catalog_unlinked` | yes — red because gate absent | Correctly ties `planned` to an implementing order. |
| Frozen API sufficiency for accepted lifecycle | `unit/test_api.py` | no | Runtime protocol conformance is checked, but no read-after-write status capability (T1). |

## E. Edit list

- `scripts/factory/src/factory/api.py`: add typed commit-status read capability or consistently switch the design to Check Runs.
- `scripts/factory/tests/fixtures/fake_github.py`: expose the same status-read behavior as the port.
- `scripts/factory/tests/unit/test_api.py`: prove commit statuses written by the gate runner are readable by lifecycle.
- `scripts/factory/src/factory/bus/models.py`: require non-empty `letter_tokens` for `fidelity: letter` if governor retains semantic letter fidelity.
- `scripts/factory/tests/seeds/test_seeds.py`: add token-present-but-substituted and thinner-behavior fidelity seeds.
- `scripts/factory/tests/seeds/test_seeds.py`: split id rejection from configured jargon rejection.
- `scripts/factory/tests/contract/test_cli_contract.py`: cover `--json` across command groups and validate JSON.
- `specs/001-factory-v2/data-model.md`: add `pr` to Gate scope.

## F. Questions for the human

1. Should “letter fidelity” remain semantic — blocking different tools/hosts and thinner behavior even when the named token still appears — or be narrowed to lexical token presence? Recommend semantic.
2. Do you accept the initial rejected-jargon vocabulary (`packet`, `worktree`, `subagent`, `slice`, `fidelity`, `owned paths`, `acceptance catalog`, `finish bar`), or should any term be allowed in governor-facing decisions?

## Command results

| Command | Result |
|---------|--------|
| `uv sync --locked` from `scripts/factory` | PASS after using a worktree-local uv cache; 25 packages installed/audited from lock |
| `uv run pytest -q` | Expected RED: **50 failed, 206 passed**; 42 CLI assertions report expected 0/1/2/4 but got 3, and 8 seeds report missing gate entrypoints; no collection/import failures |
| `uv run pytest -q -m "not contract and not seed"` | PASS: **197 passed, 59 deselected** |
| `uv run ruff check .` | PASS |
| packet-exact `uv run factory check schema --path tests/fixtures/messages/` from `scripts/factory` | FAIL: exit 3, `factory.toml: not found` (T6) |
| equivalent root invocation with `--repo .` | PASS: `schema ok` |
| historical `851cd11` model test run | Expected RED reproduced: **124 failed, 20 passed** |
| changed paths vs packet ownership | PASS; no out-of-scope path |
| production test-seam scan | PASS; no match |
| Pydantic v2 / Typer / httpx / PyYAML, cap 3, horizon 60 | PASS |

## Worker deviations and open questions disposition

### Deviations

1. `/tmp` worktree: accepted; harness constraint only.
2. Direct Nix-store uv/Python: accepted; no durable pip install.
3. Added `scope: pr`: implementation choice accepted, but contract documentation needs T4.
4. Registered existing checks at P0: accepted; registry completeness benefits slices.
5. Entrypoint module allocation: accepted; matches slice ownership.
6. Additional in-scope support files/tests: accepted.
7. Supporting API types: accepted except the missing status-read type/operation in T1.
8. Open field-name choices: accepted as conservative and schema-tested.
9. Loader skips postmortems: accepted for P0 because no postmortem message kind exists; keep the open question tracked.
10. `infra-anoop` login: accepted; GitHub-valid correction.
11. Worker-seeded jargon list: finding T5.
12. `--lock ID=...` option: accepted; needed to express the CLI contract.
13. Typer private Click handling: accepted; Typer letter lock remains intact.

### Open questions

1. Named-lock discovery: non-blocking for CP0, but T2 requires the semantic/lexical product lock before slice B.
2. Postmortem format/kind: non-blocking for P0; must be resolved before US7.
3. Gate `pr` scope: T4.
4. Jargon vocabulary: T5, governor decision.
5. Frozen files owned by no slice: accepted; amendment path is explicit.
6. Missing commit-status read: T1 blocker.
7. Adapter factory paths: accepted as a minimal frozen convention.

## Triage (orchestrator, 2026-10-03)

| ID | Disposition | Decided by | Resolution |
|----|-------------|------------|------------|
| T1 | accept — amend CP0 | orchestrator (arch) | `api.py`: `CommitStatus` + `GitHubPort.list_commit_statuses(sha)` (latest per context), frozen-at-CP0 docstrings kept; `FakeGitHub` implements it; `test_api.py::test_fake_github_commit_status_read_after_write` via reusable `assert_commit_status_read_after_write(port)` (red `de60b63` → green `a29b31b`) |
| T2 | accept — strict (semantic) letter fidelity, as spec US3 #8 / SC-002 already say | governor 2026-10-03 | `Lock`: `fidelity: letter` requires non-empty, non-blank `letter_tokens`; optional `substitutes` (non-blank, none repeats a token); data-model Lock line documents it; model tests red `670a6d5` → green `8e2f3b7`. Seeds: kept `test_seed_declared_lock_violated`; added `test_seed_lock_token_only_outside_code[comment|deleted_line|order_file|docs]`, `test_seed_lock_registered_substitute_in_added_code`, and false-positive guard `test_seed_lock_honored_passes`; docstring notes thinner behavior stays with the reviewer's fidelity rubric (reject blocks merge) |
| T3 | accept | orchestrator (process) | `cli/common.py`: `JsonEnvelope` / `CliError` / `CommandError`; `run()` prints the error envelope for refusals, usage, and config errors; `contracts/cli.md` § JSON envelope (hook exempt). `test_cli_contract.py::test_json_envelope` over 26 scenarios covering every command group (red `ff1695c` → `check schema` cases green `c8fd90a`; 22 slice-owned cases red by exit-code assertion) |
| T4 | accept | orchestrator (arch) | data-model Gate `scope: changed_lines\|repo\|pr` (`332381d`) |
| T5 | accept the eight-term jargon list as is; future misses are added as governor corrections | governor 2026-10-03 | Seed split (`1619456`): `test_seed_decision_request_quotes_an_id[T\|F\|R\|P\|D\|FR\|SC\|US\|section-sign]`, `…_id_in_option_label`, `…_uses_configured_jargon[<each of the 8 terms>]` (parameterized from `factory.toml`; fixture config now derives its list from it), `…_jargon_is_case_insensitive`, near-miss passes `…_near_miss_allowed[packaging\|sliced-bread\|t-shirt-python-3.12\|p2p-us-budget]`; blocking cases also require the gate message to name the offender |
| T6 | accept — discover repo root | orchestrator (process) | `config.settings.find_repo_root` walks from the CWD up to the git root; `cli.common.resolve_repo` used when `--repo` is omitted; relative `--path` resolves against the CWD. Tests in `test_settings.py` (red `50315d5` → green `f51929c`); packet-exact command from `scripts/factory` now exits 0 |

## Round 2 — re-review at `b878606`

### Verdict

**Reject.** T1, T3, T4, T5, and T6 are resolved with direct test and code evidence. T2 is improved but not resolved at the governor's strict semantic fidelity: the automatic catalog row still includes thinner behavior, while the new seed explicitly delegates that case to a reviewer. The amendment also changed frozen spec contracts outside the order's owned paths without adding a bus amendment.

### Finding resolutions

| ID | Resolution | Evidence |
|----|------------|----------|
| T1 | **Resolved** | `GitHubPort.list_commit_statuses()` and typed `CommitStatus` now cover the missing read API. `assert_commit_status_read_after_write()` verifies latest-per-context, SHA isolation, field preservation, and empty results against `FakeGitHub`; the unit suite passes. |
| T2 | **Not resolved** | `Lock` now rejects empty/blank letter tokens, models distinct registered substitutes, and seeds token-only-in-comment/deleted-line/order/docs plus Fly substitution and a passing Railway case. But `acceptance.md` `seed.substitution_declared` and US3 scenario 8 require blocking a different tool/host/**thinner behavior** automatically; `test_seed_declared_lock_violated` explicitly says thinner behavior is left to reviewer judgment. Greening these tests can therefore leave the auto catalog promise false. |
| T3 | **Resolved** | `test_json_envelope` covers 26 success/refusal/usage/config scenarios across every non-hook command group and validates exact success/error envelope keys, command path, error code, and non-blank message. The still-unimplemented scenarios fail first on the expected exit assertion, then will exercise envelope shape when slices implement them. |
| T4 | **Resolved** | The Gate contract now includes `scope: changed_lines\|repo\|pr`, matching the registry and PR-scoped gates. |
| T5 | **Resolved** | Tests independently cover all id forms, option labels, each of the governor-approved eight configured terms, case insensitivity, offender naming, and four near-miss passing guards. The fixture reads the repository jargon list rather than a stale copy. |
| T6 | **Resolved** | Repo discovery walks from CWD only to the git root, explicit `--repo` wins, and relative schema paths remain CWD-relative. The packet-exact command now exits 0 with `schema ok`; tests cover nested discovery, git-root confinement, and explicit override. |

### New findings

| ID | Severity | Tag | Lens | Locus | Finding | Suggested resolution |
|----|----------|-----|------|-------|---------|----------------------|
| T7 | Blocker | process | Owned-path enforcement | commits `8e2f3b7`, `c8fd90a`; `specs/001-factory-v2/data-model.md`, `contracts/cli.md` | The fixes changed frozen spec contracts outside the P0 order's owned paths. The original packet allowed only the data-model Gate line for `entrypoint`; it did not authorize the Lock line or `contracts/cli.md`. No `<order-id>.amend-NN` bus message records expanded ownership, despite the handoff calling this “Amendment 1.” This contradicts FR-014 and the bootstrap owned-path manual equivalent. | Add and validate an order amendment authorizing the exact spec paths/changes, or move the contract edits to an appropriately owned orchestrator order before accepting the bootstrap verdict. |

No other new test weakness was found. The T1 conformance test is behavioral rather than protocol-presence-only; the T3 tests do not pass vacuously; and the T5 passing guards constrain obvious false positives.

### Commands

| Command | Result |
|---------|--------|
| `cd scripts/factory && uv sync --locked` | PASS — 25 packages installed/audited from the lock |
| `uv run pytest -q` | Expected RED — **100 failed, 225 passed**; all failures are `AssertionError`; no collection, `ImportError`, or `ModuleNotFoundError` failures |
| `uv run ruff check .` | PASS |
| `uv run factory check schema --path tests/fixtures/messages/` | PASS — `schema ok` |
| changed paths vs authorized ownership | FAIL — the Lock line in `data-model.md` and `contracts/cli.md` are outside the recorded order ownership (T7) |
