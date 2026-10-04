# Handoff — 2026-10-04-factory-v2-slice-a

| Field | Value |
|-------|-------|
| Branch | `wo/wo-20261004-factory-slice-a` |
| State | **implemented; all Slice A tests green; PR not opened** (orchestrator opens it and spawns the bootstrap verdict) |
| Author model | Claude family (worker). The bootstrap verdict must come from a GPT-family reviewer (D3, FR-037) |
| Base | `origin/main` @ `b1760ec`, merged at `8235354`. Round-4 T* accept merged `--no-ff` at `b3a2a37` before any implementation commit |
| Frozen CP0 files | not edited |

## What changed (T021–T025, T034–T038)

Code under `scripts/factory/src/factory/`. All of it is new except the two CLI modules, which replace stubs.

| Area | Module | Task |
|------|--------|------|
| GitHub REST (`GitHubPort`, httpx, Bearer token from `EnvSettings`) | `github/rest.py` | T021 |
| Read model over git: every `origin/wo/*` order plus `main`'s bus; effective order = order + amendments | `lifecycle/view.py` | T022 |
| Lifecycle derivation (writes nothing) | `lifecycle/derive.py` | T022 |
| Board JSON + markdown; `status`, `decisions` | `board/render.py`, `cli/board.py` | T023 |
| Bookkeeping-commit counter | `metrics/history.py` | T024 |
| `order new`, `order issue`, `claim`, `release`, `handoff`, `pr open`, `verdict`, `bus pr` | `orders/{scaffold,lease,review,messages,paths,errors}.py`, `cli/orders.py` | T034 |
| git plumbing (`hash-object` / `mktree` / `commit-tree` / plain push; never touches the caller's index) | `orders/git.py` | T034 |
| Scorecard + `scorecard` command | `metrics/scorecard.py`, `cli/board.py` | T035 |
| Identity: `recorded` never verifies; `verified` requires an APPROVED review by `governor_login` | `identity/adapter.py` | T036 |
| App JWT (PyJWT RS256, `iat` = now−60 s, `exp` = now+9 min) → installation token; refuses an already-expired token; credential-helper answer | `identity/app_token.py` | T036 |
| `tooling:` section (`factory` → `codespace`, names `FACTORY_GITHUB_APP_ID` / `FACTORY_GITHUB_APP_PRIVATE_KEY`, no values) and its validator + tests | `deploy/secrets/schema.yaml`, `scripts/validate_secrets_schema.py`, `scripts/test_validate_secrets_schema.py` | T037 |
| Dependency `pyjwt[crypto]>=2.9,<3` (`uv.lock`: pyjwt 2.15.1, cryptography); research decision row; plan Primary Dependencies line | `pyproject.toml`, `uv.lock`, `research.md`, `plan.md` | amend-02 |
| Evidence cells for the 11 Slice A rows (T025/T038); Slice A checkboxes ticked (T021–T025, T033–T038) | `acceptance.md`, `tasks.md` | T025, T038 |

## Red → green commit pairs

| Red (tests committed failing) | Green |
|-------------------------------|-------|
| `7dc2359` T017–T020, T026–T032; T* fixes `aa2bc5a`, `ee992a0`, `d79fbb6`, `656b065`; accepted at `7d2467a` | `afd6fdc` (all 66 Slice A tests), plus `1313d28` (race flake, below) |
| `66ca359` T037 tooling tests (4 failed against the old validator, checked by stashing the impl) | `1d47681` |

## Commands and results

Run in `scripts/factory` via `nix develop ../.. -c uv run …`.

| Check | Result |
|-------|--------|
| Slice A 11 files | **66 passed, 0 failed** |
| Race test `test_claim_fast_forward_exactly_one_of_two_concurrent_wins`, run 25 times | 25/25 pass (before `1313d28`: 3 of 8 failed) |
| Full `pytest -q` | **341 passed, 78 failed** (was 237 / 182). +104 = the 66 Slice A tests + 38 P0 contract tests for Slice A commands. All 237 previously passing tests still pass |
| CI selector `-m "not contract and not seed"` | **263 passed, 0 failed**, 156 deselected |
| `ruff check .` / `ruff format --check .` | PASS / PASS (67 files) |
| `scripts/test_validate_secrets_schema.py` (root, `uv run --with pytest --with pyyaml`) | 14 passed |
| `uv run scripts/validate_secrets_schema.py` | `secrets schema OK` |
| `factory decisions` / `factory scorecard --json` on this repo | exit 0. 0 orders: the bootstrap orders were issued as packets, so no branch carries a bus `order.yaml` yet |
| No `os.getenv` / `os.environ` outside `factory/config/` | confirmed (ruff TID251 + grep) |

## Tests still red, by owner

| Test(s) | Owner | Why |
|---------|-------|-----|
| `test_cli_contract.py::test_handoff_refuses_while_a_gate_fails` | **Slice B** | Slice A command, but the refusal comes from `diff-within-owned-paths` (`factory.gates.drift.owned_paths`), which is not on this branch. `handoff` runs it as soon as it is importable |
| `test_cli_contract.py`: `override` (4), `gate run`, `hook` (2), `check hooks/registry/immutability`, `retro`, plus their `test_json_envelope` cases | Slice C | commands not implemented here |
| `test_cli_contract.py::test_check_intent_exit_0` + `test_json_envelope[check intent]` | Slice B | |
| `test_cli_contract.py`: `correction new`, `sprint close` (2), plus their envelope cases | US7 (Wave 2) | |
| `tests/seeds/test_seeds.py` (52) | Slice B | drift gates |

78 = 26 contract (25 Slice B/C/US7 + the handoff refusal above) + 52 seeds.

Every P0 contract and envelope test for a Slice A command passes, except the Slice B-dependent handoff refusal above.

## Deviations (why + conservative choice)

1. **`handoff` skips gates that are not importable yet** (`GateEntrypointError`). In round 0 I recommended fail-closed. Fail-closed would turn the accepted exit-0 tests red until Slices B and C land: Slice A `test_handoff_writes_run_complete_event`, P0 `test_handoff_exit_0`, and the `handoff` JSON envelope. The skipped gates are printed ("not enforced locally yet") and returned as `gates_not_enforced` in JSON. CI `factory-gates` stays the authority. Conservative part: every P1 gate with scope `changed_lines` or `repo` runs (not just the order's `checks`), and any failure refuses.
2. **`test_handoff_refuses_while_a_registered_gate_fails` passes for the wrong reason.** Its `_claimed` fixture never commits a handoff, so `handoff` refuses with "no handoff" before any gate runs. Per the rules I did not edit the accepted test. For the gate behaviour, the evidence cell cites the P0 test (red until Slice B), not this one. Suggested follow-up T* fix: commit a valid handoff in that test.
3. **Claim leases come from git only.** An order holds a slot from its claim until a release event or until its order file is on `main`. The concurrency test runs without a GitHub fake, and the packet makes git the lease authority. So a PR closed unmerged with no release event still holds a slot until `factory release` (the board shows it `released`). Fix: release it.
4. **A lost claim race refreshes the loser's view** (`1313d28`). After a rejected push, `claim`/`release`/`verdict`/`handoff` fetch before refusing, so the loser's `origin/wo/<id>` shows the winning claim. Without this the race test failed in 3 of 8 runs, whenever the second clone won.
5. **`order new` additions.** `--check` (default: every P1 gate id, matching the `factory/<gate>` statuses CI posts), `--owned-path` (default: backticked paths in the task lines), `--intent` and `--actor-model` (default `unrecorded`; `release` too). All are optional, so the contract's options are unchanged. A task tagged `[OD:<id>]` touching a locked decision needs `--lock`; the letter tokens come from the text after "—" in the spec's Open Decisions `status` cell. An unlocked decision refuses outright.
6. **`handoff` writes `run-complete.yaml`** with `cost_usd: null` (estimated), `governor_interrupts: 0`, and `wall_minutes` from `claimed_at` to now. It only does this when the file is absent, so a worker that records real cost commits its own. The handoff must already be committed on `wo/<id>`; it is read from HEAD, not the working tree.
7. **The scorecard reads git only** (no `GitHubPort` in `compute_scorecard`). "Merged" means the order file landed on `main` (first-parent). `--sprint` is echoed but does not filter yet (sprint scoping is US7). Extra keys: `orders`, `runs_complete`, `overrides_per_gate`, `corrections`, `bookkeeping_commits`.
8. **Paging and blockers.** REST lists take one page of 100. A `blocker_governor` question counts as answered once a decision lock on `main` lists the order id in `refs`.
9. **Credential helper.** `identity/app_token.git_credential_response` returns the git credential-protocol answer, but nothing installs it into git config yet. The App does not exist (T065), and contracts/cli.md has no command for it.

## Open questions

| Class | Question |
|-------|----------|
| non_blocking | When Slices B and C land, `handoff` will run about ten local P1 gates. P0's exit-0 handoff fixture changes `calc.py` with no test, so `red-first-proof` / `catalog-test-linkage` may refuse it. Should handoff run only the order's `checks` plus `diff-within-owned-paths`? (P0's refusal test uses `checks: []`, so "all registered gates" is what the tests require today.) |
| non_blocking | T* follow-up for deviation 2 (commit a valid handoff in the Slice A gate-refusal test)? |
| non_blocking | Should a PR closed unmerged also free a claim slot? That needs GitHub in `claim`. Today it takes an explicit `release`. |

No `blocker_governor` questions.

## Manual equivalents of P1 gates (bootstrap verdict input, FR-037)

| Gate | Manual check | Result |
|------|--------------|--------|
| `red-first-proof` | Tests landed failing at `7dc2359` (and T* fix commits) before `afd6fdc`. T037 tests failed 4/14 against the old validator before `1d47681` | pass |
| `diff-within-owned-paths` | `git diff --name-only origin/main...HEAD`: Slice A src dirs, `cli/board.py`, `cli/orders.py`, the Slice A tests + `github_recorded/**`, `pyproject.toml`, `uv.lock`, the secrets schema + validator + test, `acceptance.md`, `tasks.md`, `research.md`, `plan.md`, `TEST_REVIEW_SLICE_A.md`, this order's bus dir, the packet + this handoff. No frozen CP0 file, no other slice's path | pass |
| `test-seam-ban` | `rg 'PYTEST\|pytest\|TESTING\|FakeGitHub\|is_test'` over the new src: no matches. Tests substitute adapters only through `DEPS` / `httpx.Client` | pass |
| `bus.no-handwritten-status` / `bus.schema` | Written events are built through `parse_message` (forbidden keys rejected); `test_status` walks every bus YAML on every fixture branch | pass |
| `order-fidelity-declared` / `lock.letter-tokens` | No order touches a named lock in this slice's own work. `order new` refuses a touched lock without `--lock` (T026) | n/a / tested |
| `decision-request-no-ids` | Refusals shown to the governor carry the decision prompt only; tests assert no `T0xx` / `FR-0xx` | pass |
| `deferral-words-need-od` | No "later/TODO/defer" introduced in spec, plan, or tasks text | pass |

## History (T* rounds)

T017–T032 went red at `7dc2359`. Four T* rounds by gpt-5.6-sol (openai) followed; triage for each is in `specs/001-factory-v2/TEST_REVIEW_SLICE_A.md`, with `verdict-01..04.yaml` and `amendment-01..03.yaml` in `bus/orders/wo-20261004-factory-slice-a/`:

- Round 1 rejected; T-A1…T-A9 applied at `aa2bc5a`.
- Round 2 rejected: the required set narrowed to the order's `factory/<gate>` statuses; pyjwt authorized.
- Round 3 rejected: empty `checks` is never accepted, and `order issue` refuses it.
- Round 4 accepted at `7d2467a`.

## Stop

The orchestrator opens the PR and spawns the bootstrap verdict. This worker did not open a PR.
