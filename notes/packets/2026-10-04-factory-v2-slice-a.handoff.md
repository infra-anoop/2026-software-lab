# Handoff — 2026-10-04-factory-v2-slice-a

| Field | Value |
|-------|-------|
| Branch | `wo/wo-20261004-factory-slice-a` |
| State | **PR #20 review fixes implemented (phase 2); every Slice A test green except PR-A6's, which waits on Slice B's gate.** PR description untouched |
| Author model | Claude family (worker). The bootstrap verdict must come from a GPT-family reviewer (D3, FR-037) |
| Base | `origin/main` @ `b1760ec`, merged at `8235354`. Round-4 T* accept merged `--no-ff` at `b3a2a37` before any implementation commit |
| PR-fix test accept | T* round 7 (`verdict-08`, accept) merged `--no-ff` at **`ccb0b1a`**: the PR-fix accept-SHA. Fix code starts after it |
| Frozen CP0 files | not edited |

## PR #20 review fixes (phase 2, after `ccb0b1a`)

Implemented against the accepted tests as triaged in amendments 04–09. No test file changed after `ccb0b1a`.

| Finding | Behaviour now | Code |
|---------|---------------|------|
| PR-A2 ref-only plumbing | No command merges, checks out, resets or writes HEAD, index or worktree. Local `wo/<id>` moves only after origin accepted the push, by compare-and-swap `update-ref <new> <old>`. A branch checked out in any worktree (`git worktree list`) is left alone and the command exits 0 with a note: pick the event up with `git pull --ff-only`. A local branch that is not an ancestor of the pushed commit is left alone and reported. A rejected push changes no local ref (exit 2). Notes go to stderr and to `data.notes` under `--json` | `orders/git.py` (`advance_local_branch`, `checked_out_branches`), `orders/lease.py` (`push_or_fail`), `orders/review.py` |
| PR-A4 closed-unmerged PR frees a slot | Claim admission derives every other order with the board's `derive_order` (git plus PR reality through `GitHubPort`). Claimed, in review, accepted and rejected hold a slot; released (event or PR closed unmerged) and merged do not. A GitHub failure exits 4. Nothing is written for a closed PR | `orders/lease.py` (`active_orders`), `cli/orders.py` |
| PR-A5 Wave 1 exit (SC-013 letter) | Scope by `--sprint` (effective `refs` contain `notes/sprints/<S>.md`); cohort = orders issued before `bus/postmortems/wave1-retro.yaml` first landed on main. Exit = date of the first-parent main commit of the last cohort landing, only when (a) every cohort order has a run record, an accepted latest verdict and has landed, (b) every P1 entrypoint resolves, (c) that commit has `success` `factory/<gate>` for every P1 gate (through `DEPS.github`). Without a GitHub port the exit stays null | `metrics/scorecard.py`, `cli/board.py`, `orders/git.py` (`added_commits`) |
| PR-A7 porcelain rejection | Push outcome is read from `--porcelain` stdout: a `!` line is a lease conflict (exit 2), not exit 4 | `orders/git.py::push` |
| PR-A8 identical first-writer push | `--quiet` dropped; an `=` (up to date) line on a first-writer push (issue, claim, release, new run-complete, verdict, bus PR) raises `PushUpToDate`, i.e. lost (exit 2). Re-pushes of a worker's own branch (`pr open`, handoff without a new event) may be up to date | `orders/git.py::push`, call sites |
| PR-A6 handoff gate test | Stays red until Slice B lands `diff-within-owned-paths`. Checked by overlaying Slice B's `gates/drift/` from `origin/wo/wo-20261004-factory-slice-b` in a scratch run: the test then passes. The missing gate is the only reason it fails | none |
| PR-A3 packet | `notes/packets/2026-10-04-factory-v2-slice-a.md` matches `origin/main` | none |

`verdict` and `pr open` now build on origin's `wo/<id>` when the local branch is an ancestor of it (it lags after a checked-out claim), and on local `wo/<id>` otherwise (it may hold unpushed work).

### Accepted tests changed after the original accept `7d2467a`

Amendments only, each reviewed by the T* reviewer (gpt-5.6-sol). The last column names the finding that judged the change. `verdict-06` rejected round 5 on other findings, but it found these amendments justified; `verdict-08` accepted the whole set. Assertions changed only where the amendment says so.

| Test | Change | Amendment | T* review |
|------|--------|-----------|-----------|
| `test_claim.py::test_claim_fast_forward_exactly_one_of_two_concurrent_wins` | The loser must exit 2 (PR-A7). Later the harness only: bounded, killable forked claimers instead of an untimed thread pool; assertions unchanged | amend-05; amend-09 | verdict-06 (T-A5-3); verdict-08 (T-A7-2) |
| `test_handoff.py::test_handoff_refuses_while_a_registered_gate_fails` | The fixture commits a valid handoff; the refusal must name `diff-within-owned-paths` (PR-A6) | amend-04 | verdict-06 (T-A5-3) |
| `test_handoff.py::test_handoff_writes_run_complete_event` | Reads the event from `origin/wo/<id>` (ref-only, PR-A2); assertions unchanged | amend-05 | verdict-06 (T-A5-3) |
| `test_pr_and_verdict.py::test_verdict_commits_valid_different_family_verdict` | Same read-path change | amend-05 | verdict-06 (T-A5-3) |
| `test_scorecard.py::test_scorecard_wave1_exit_when_every_order_merged` | Runs through the CLI; P1 statuses on the exit commit and resolvable P1 entrypoints (PR-A5, SC-013 letter) | amend-05 | verdict-06 (T-A5-3) |

New tests added by the same amendments: `test_git_safety.py` (amend-04, completed by amend-07); `test_claim.py` PR-A4, PR-A7 and PR-A8 cases (amend-04/05/06, rebuilt on the receive-pack barrier by amend-07/08); `test_scorecard.py` SC-013 cases (amend-05); `push_barrier.py` and `test_push_barrier.py` (amend-07/08).

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
| PR #20 fixes: `df2ee8f`, `621958f`, `a83fb28`, `d8f2c47`, `87f9fd9`, `5ea8197`; accepted at `ccb0b1a` (23 Slice A reds) | the phase-2 fix commit after `ccb0b1a` (22 green; PR-A6 waits on Slice B) |

## Commands and results

Run in `scripts/factory` via `nix develop ../.. -c uv run …`. Phase 2 (PR #20 fixes):

| Check | Result |
|-------|--------|
| Slice A 13 files (+ `push_barrier` meta-tests) | **93 passed, 1 failed**: the failure is PR-A6's `test_handoff_refuses_while_a_registered_gate_fails`, which waits on Slice B |
| Race tests (atomic race, PR-A7, PR-A8, during-push divergence, push rejection, 4 harness meta-tests), 12 runs | **12/12 green**, 9 passed each run |
| Full `pytest -q` | **368 passed, 79 failed** (at `ccb0b1a`: 347 / 100). The 79 are listed below; none is a Slice A command except PR-A6 |
| CI selector `-m "not contract and not seed"` | **277 passed, 0 failed**, 170 deselected |
| `ruff check .` / `ruff format --check .` | PASS / PASS (70 files) |
| `factory check schema` | `schema ok` |

Phase 1 (original implementation, for the record):

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
| `test_handoff.py::test_handoff_refuses_while_a_registered_gate_fails` (PR-A6) | **Slice B** | Same cause as the P0 handoff refusal: `diff-within-owned-paths` is not on this branch. Passes with Slice B's `gates/drift/` overlaid |

79 = 26 contract (25 Slice B/C/US7 + the P0 handoff refusal) + 52 seeds + PR-A6. The 78 non-PR-A6 failures are the same tests as at `ccb0b1a`.

Every P0 contract and envelope test for a Slice A command passes, except the Slice B-dependent handoff refusal above.

## Deviations (why + conservative choice)

1. **`handoff` skips gates that are not importable yet** (`GateEntrypointError`). In round 0 I recommended fail-closed. Fail-closed would turn the accepted exit-0 tests red until Slices B and C land: Slice A `test_handoff_writes_run_complete_event`, P0 `test_handoff_exit_0`, and the `handoff` JSON envelope. The skipped gates are printed ("not enforced locally yet") and returned as `gates_not_enforced` in JSON. CI `factory-gates` stays the authority. Conservative part: every P1 gate with scope `changed_lines` or `repo` runs (not just the order's `checks`), and any failure refuses.
2. ~~`test_handoff_refuses_while_a_registered_gate_fails` passes for the wrong reason.~~ Fixed by amendment-04 (PR-A6): the fixture commits a valid handoff and the test names the gate, so it is red until Slice B.
3. ~~Claim leases come from git only.~~ Superseded by PR-A4: admission uses the board's lifecycle derivation, so a PR closed unmerged frees its slot without a release event.
4. **A lost claim race refreshes the loser's view** (`1313d28`). After a rejected push, `claim`/`release`/`verdict`/`handoff` fetch before refusing, so the loser's `origin/wo/<id>` shows the winning claim. Without this the race test failed in 3 of 8 runs, whenever the second clone won.
5. **`order new` additions.** `--check` (default: every P1 gate id, matching the `factory/<gate>` statuses CI posts), `--owned-path` (default: backticked paths in the task lines), `--intent` and `--actor-model` (default `unrecorded`; `release` too). All are optional, so the contract's options are unchanged. A task tagged `[OD:<id>]` touching a locked decision needs `--lock`; the letter tokens come from the text after "—" in the spec's Open Decisions `status` cell. An unlocked decision refuses outright.
6. **`handoff` writes `run-complete.yaml`** with `cost_usd: null` (estimated), `governor_interrupts: 0`, and `wall_minutes` from `claimed_at` to now. It only does this when the file is absent, so a worker that records real cost commits its own. The handoff must already be committed on `wo/<id>`; it is read from HEAD, not the working tree.
7. **Scorecard** (revised by PR-A5). Git for every metric, plus `GitHubPort` commit statuses for SC-013 (c). "Landed" means the order file reached `main` (first-parent). `--sprint` now scopes `orders`, every `wave1_*` field and the other order-derived metrics (runs, drift, first-pass, rework, overrides, wall/cost/deviations). `main`-derived ones (decision points, governor minutes, corrections, bookkeeping commits) stay repo-wide: `refs` scoping says nothing about them. Extra keys: `orders`, `runs_complete`, `overrides_per_gate`, `corrections`, `bookkeeping_commits`.
8. **Paging and blockers.** REST lists take one page of 100. A `blocker_governor` question counts as answered once a decision lock on `main` lists the order id in `refs`.
9. **Credential helper.** `identity/app_token.git_credential_response` returns the git credential-protocol answer, but nothing installs it into git config yet. The App does not exist (T065), and contracts/cli.md has no command for it.

## Open questions

| Class | Question |
|-------|----------|
| non_blocking (now evidenced; decide before Slice B merges) | `handoff` runs every importable local P1 gate. With Slice B's `gates/drift/` overlaid on this branch (scratch run, not committed), PR-A6 and the P0 refusal pass, but **six accepted exit-0 handoff tests go red**: `test_handoff.py::test_handoff_writes_run_complete_event`, `::test_handoff_blocker_governor_exits_2_and_waits_on_board`, P0 `test_cli_contract.py::test_handoff_exit_0` and `test_json_envelope[handoff-handoff]`, and `test_git_safety.py::test_handoff_and_verdict_leave_a_checked_out_order_branch_where_it_was[handoff]` / `::test_handoff_push_rejection_leaves_local_refs_and_worktree_unchanged`. Refusals: `order-fidelity-declared` (fixture lacks `specs/001-factory-v2/spec.md`), `lock.letter-tokens` (D2 `70%`), `catalog-test-linkage` (order check `diff-within-owned-paths` has no acceptance row). Running only the order's `checks` would break the P0 refusal test, which uses `checks: []`. Needs an orchestrator call: which gates handoff runs locally, or frozen fixtures that satisfy them (CP0 amendment) |
| ~~non_blocking~~ | ~~T* follow-up for deviation 2~~: done (amendment-04, PR-A6) |
| ~~non_blocking~~ | ~~Should a PR closed unmerged also free a claim slot?~~ Yes: PR-A4, implemented |
| later (T-A7-3) | Suite-wide timeout policy for synchronous fixture/CLI calls, when CP0 fixtures are next amended |

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
- PR #20 code review (`verdict-05`, reject) triaged in amendments 04–06. PR-fix tests went through T* rounds 5–7 (`verdict-06` reject, `verdict-07` reject, `verdict-08` accept; amendments 07–09) and were accepted at `ccb0b1a`.

## Stop

The orchestrator opens the PR and spawns the bootstrap verdict. This worker did not open a PR.
