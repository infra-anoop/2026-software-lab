# PR review — Factory v2 Wave 1 Slice A

Reviewed PR: https://github.com/infra-anoop/2026-software-lab/pull/20  
Reviewed head: `ea6a554d19f494bda7710303ca323fd1df052d03`

## Verdict

**Reject.**

The accepted tests are untouched and Slice A's test set is green, but three blockers remain: the locked GitHub App identity is not connected to any production path, git plumbing updates the caller's checked-out branch through `git merge`, and the PR mutates the packet outside the effective owned paths. Closed-unmerged PR capacity and Wave 1 exit computation also differ from the approved lifecycle/spec.

## Findings

| ID | Severity | Tag | Locus | Finding | Suggested resolution |
|----|----------|-----|-------|---------|----------------------|
| PR-A1 | Blocker | product | `scripts/factory/src/factory/identity/app_token.py`; `github/rest.py`; `cli/orders.py` | D4-A is implemented only as isolated helpers. Nothing calls `mint_installation_token` or `git_credential_response`; REST still always uses `GITHUB_TOKEN`; no production path obtains an installation id or makes git pushes/REST calls as the App. T036 is therefore checked off without the locked separate-agent identity being usable when T065 turns the App on. | Amend the frozen configuration/interface if needed, then add a T*-reviewed end-to-end path that obtains an installation id, mints the short-lived token, supplies it ephemerally to git and REST, and proves it is never logged, persisted, or included in exceptions. |
| PR-A2 | Blocker | process | `scripts/factory/src/factory/orders/git.py::advance_local_branch`; callers in `orders/lease.py` and `orders/review.py` | The plumbing does touch the caller's index/worktree: when the order branch is checked out, `advance_local_branch` runs `git merge --ff-only`. `handoff_order` does this before push, so a rejected push can leave the local branch and worktree advanced to an unpushed commit. This violates the explicit git-safety requirement. | Keep plumbing ref-only and leave the caller's checked-out branch, index, and worktree unchanged, including on rejection. Add T*-reviewed dirty-worktree/index and push-rejection tests. |
| PR-A3 | Blocker | process | `notes/packets/2026-10-04-factory-v2-slice-a.md` | The PR rewrites the packet's hand-maintained `Status` and DoD checkboxes, but that packet is absent from the original and amended owned paths. This is both an out-of-scope edit and the bookkeeping pattern the factory is intended to replace. | Revert the packet changes; keep completion evidence in the append-only handoff/verdict artifacts. |
| PR-A4 | Should-fix | product | `scripts/factory/src/factory/orders/lease.py::holds_slot` | A closed-unmerged PR remains capacity-consuming until an explicit release because claim capacity uses only claim/release/on-main data. The approved lifecycle says closed-unmerged is `released` and excluded from active capacity. This can conservatively wedge the cap at three after abandoned PRs. | Include GitHub PR reality in admission, or define an automatic immutable release mechanism; add a contract case proving a closed-unmerged PR frees capacity. |
| PR-A5 | Should-fix | product | `scripts/factory/src/factory/metrics/scorecard.py::_wave1` | `wave1_exit` is set when every order currently visible has landed on `main`; it does not require every P1 check to be implemented and passing as SC-013 requires, and it is not scoped to Wave 1 or the requested sprint. Later orders can erase a previously computed Wave 1 exit. | Compute the Wave 1 cohort and exit from run/gate evidence, requiring all P1 checks passing, and make `--sprint` actually scope the calculation. Add pre-exit, completed-exit, and later-order regression tests. |
| PR-A6 | Should-fix | process | `scripts/factory/tests/contract/test_handoff.py::test_handoff_refuses_while_a_registered_gate_fails` | The reported false positive is confirmed: `_claimed` never commits a handoff, so the command refuses at `read_handoff` before a registered gate runs. The accepted test must not be edited directly in this PR. | Open a test-only follow-up, route it through T*, commit a valid handoff in the fixture, and assert the named gate failure/refusal. |

## Security

- App JWT construction uses PyJWT with RS256, `iat = now - 60s`, and `exp = now + 9m`, within GitHub's ten-minute bound.
- The App private key and `GITHUB_TOKEN` are read only in `factory.config` and held as `SecretStr` there. No `os.getenv`/`os.environ` use exists outside config.
- The REST adapter sends `GITHUB_TOKEN` only as an authorization header and does not deliberately include it in errors. The installation-token function does not log or write the returned token; the credential-protocol response necessarily contains it in memory.
- `deploy/secrets/schema.yaml` contains secret names and vault metadata, not secret values.
- PR-A1 is the material security/identity gap: because the App path is not integrated, the separate agent identity and its custody boundary are not operationally enforced.

## Spec fidelity

- Lifecycle required checks correctly use the order's complete `factory/<gate>` status set, allow same-gate overrides, and reject an empty check set.
- Board placement matches the accepted contract: claimed/in-review/accepted in flight, rejected blocked, governor overlays waiting, issued ready, and terminal orders omitted.
- Same-order claim races use plain fast-forward pushes; stale claims remain active; cap is three. PR-A4 records the closed-unmerged divergence.
- Verdict family and committed-input isolation are enforced.
- Bus models reject status/state/done/progress fields. Append-only mutation remains dependent on the Slice C `bus.immutable` gate.
- Order issuance uses `origin/main` as parent and adds only the order file in the first branch-only commit; pushes are neither to `main` nor forced. PR-A2 records the caller-worktree violation.
- Scorecard aggregates run events, verdicts, overrides, corrections, decisions, cost, and deviations, but PR-A5 means its Wave 1 exit is not the SC-013 exit.

## Verification record

| Check | Result |
|-------|--------|
| Worktree setup discovery | Checked repository root and worktree; no `.cursor/worktrees.json`, so setup was skipped. |
| Accepted-test immutability | `git diff 7d2467a HEAD -- scripts/factory/tests` was empty. |
| Frozen CP0 files | No edits to `api.py`, `bus/`, `config/`, `cli/app.py`, `cli/exit_codes.py`, or `gates/registry.py`; no modification/deletion of pre-existing `tests/fixtures/` files. The accepted `github_recorded/` additions are explicitly amendment-owned. |
| Diff hygiene | `git diff --check origin/main...HEAD` passed. |
| `nix develop ../.. -c uv sync --locked` | Environment-blocked: sandbox could not open `/nix/var/nix/db/big-lock`. No dependency change was made. |
| Full `pytest -q` | Using the existing locked Slice A venv with this worktree's `src` on `PYTHONPATH`: **341 passed, 78 failed**. |
| Remaining red classification | **26 contract + 52 seed**. The handoff maps these to Slice B, Slice C, or US7; no failure is in a Slice A-owned test file. The one handoff contract is Slice B-dependent and is also the false-positive follow-up in PR-A6. |
| `pytest -q -m "not contract and not seed"` | **263 passed, 156 deselected**. |
| `ruff check .` | Passed. |
| No ambient env reads | Only `factory/config/settings.py` uses `os.environ`; none uses `os.getenv` outside config. |
| Push safety scan | No force push and no push to `main`; PR-A2 covers index/worktree mutation. |

## Triage (PR review)

Orchestrator decisions on `wo-20261004-factory-slice-a.verdict-05`, recorded verbatim by the Slice A worker (2026-10-05). The chosen behaviours, the disclosed fidelity delta, and the open item are in `bus/orders/wo-20261004-factory-slice-a/amendment-04.yaml`.

- **PR-A1 (App identity not wired): DEFER within Wave 1, not dropped.**
  - Add task `T036b` to `specs/001-factory-v2/tasks.md`, right after T036, and leave T036 checked.
  - T036b text: wire the App installation token into the git credential helper and the REST client, including how the installation id is obtained (config amendment if needed). Use a recorded-response end-to-end test proving the token is never logged, persisted or put in exceptions. It MUST land before T065 flips `identity.mode = verified`.
  - Add a Phase 8 dependency note to the same effect. amendment-04 widens owned paths to `specs/001-factory-v2/tasks.md` for this edit only.
  - Rationale: the App does not exist yet (T065 is HITL), and D4's letter is 'set up during Wave 1'. That is still met.
- **PR-A2 (git plumbing touches caller's worktree): FIX.** Plumbing must be ref-only:
  - never run `git merge` or checkout, and never touch the caller's index or worktree, including when the order branch is checked out;
  - on push rejection, leave local refs unchanged.
  - If the branch is checked out, do not move it. Report or skip as appropriate, and document the chosen behaviour in amendment-04.
- **PR-A3 (packet edited outside owned paths): FIX.** Revert `notes/packets/2026-10-04-factory-v2-slice-a.md` to its origin/main content. Completion evidence lives in the handoff and verdicts only.
- **PR-A4 (closed-unmerged PR keeps a slot): FIX to spec letter.** A closed-unmerged PR is `released` and frees capacity. Admission uses the same lifecycle derivation, including PR reality, that the board uses. There is no new write path.
- **PR-A5 (Wave 1 exit): FIX to SC-013 letter.** `wave1_exit` requires every P1 check implemented and passing, is scoped to the Wave 1 cohort, and `--sprint` actually scopes it. Later orders must not erase a computed exit. (→ `bus/orders/wo-20261004-factory-slice-a/amendment-04.yaml`)
- **PR-A6 (vacuous handoff-gate test): FIX the test.** The fixture commits a valid handoff and the test asserts the named gate failure.

### Phase 1 record (tests first)

| Finding | Tests (new unless noted) | State before the fix |
|---------|--------------------------|----------------------|
| PR-A2 | `tests/contract/test_git_safety.py::test_claim_leaves_a_dirty_index_and_worktree_untouched`, `::test_event_commands_leave_a_checked_out_order_branch_where_it_was[claim\|release]`, `::test_handoff_push_rejection_leaves_local_refs_and_worktree_unchanged` | red: `git merge --ff-only` adds the event to the caller's index/worktree and moves the checked-out branch; handoff moves it before a push that is then rejected |
| PR-A3 | — (packet reverted to origin/main) | — |
| PR-A4 | `tests/contract/test_claim.py::test_closed_unmerged_pr_frees_capacity`; guard `::test_open_pr_still_holds_a_slot` | red: cap reached with the closed-PR order counted; guard green |
| PR-A5 | `tests/unit/test_scorecard.py::test_scorecard_wave1_not_exited_until_every_order_has_run_record_and_acceptance[no-run-record\|no-verdict\|latest-verdict-reject]`, `::test_scorecard_wave1_exit_survives_later_orders`, `::test_scorecard_sprint_scopes_wave1`; guard `::test_scorecard_cli_wave1_exit_after_rework_accepted` | red: exit set from landings alone; a post-retro order erases it; `--sprint` is echoed, not applied; guard green |
| PR-A6 | `tests/contract/test_handoff.py::test_handoff_refuses_while_a_registered_gate_fails` (changed: fixture commits a valid handoff; asserts exit 2 naming `diff-within-owned-paths`) | red until Slice B lands the gate: handoff now reaches the gate step and reports it not enforced |

Also found while writing the tests: `git push --porcelain` reports a non-fast-forward rejection on stdout, but `orders/git.py::push` checks only stderr for rejection markers. So a lost race exits 4 (external) instead of 2 (refused). The rejection test pins exit 2, and the accepted race test already allows either code.

### Orchestrator decisions on the Phase 1 open items (amendment-05)

Recorded verbatim by the Slice A worker (2026-10-05). The exit rule, the new finding and what this supersedes in amendment-04 are spelled out in `bus/orders/wo-20261004-factory-slice-a/amendment-05.yaml`.

1. **Push-race defect (porcelain `[rejected]` on stdout): FIX later in phase 2.** Now, tighten the accepted race test so a lost race must exit 2 (lease conflict), not 4. Add this as a finding `PR-A7` (should-fix, process; found by implementer) in amendment-05. (→ `bus/orders/wo-20261004-factory-slice-a/amendment-05.yaml`)
2. **Accepted tests reading the local checked-out `wo/<id>`: AMEND.**
   - Change `test_handoff_writes_run_complete_event` and `test_verdict_commits_valid_different_family_verdict` to read the new commit from `origin/wo/<id>`, the pushed ref. Change only the read path, not the assertions.
   - Ref-only plumbing, with no move of a checked-out branch, stands.
3. **SC-013 'every P1 check implemented and passing': keep to the LETTER and do NOT waive.** Wave 1 exit requires all three of the following:
   - (a) every Wave 1 order has a run record and has been accepted and landed, as you have it;
   - (b) every `priority: P1` row in `gates.yaml` is implemented, meaning its entrypoint resolves;
   - (c) the `main` commit at the exit point has a `success` `factory/<id>` commit status for every P1 gate. Read this through the same recorded-REST GitHub port the lifecycle uses.
   - Amend the accepted exit fixture/test to include those statuses, and add negative cases: one P1 status missing or failing means no exit, and one P1 entrypoint unresolvable means no exit.
   - Remove the 'fidelity gap' disclosure from amendment-04 by superseding it in amendment-05.
4. **Wave 1 boundary = `bus/postmortems/wave1-retro.yaml` landing on main; sprint membership = `refs` include `notes/sprints/<S>.md`: ACCEPTED provisionally.** The T* reviewer will judge both. Make sure they are spelled out in the test docstrings.
5. **Severity mismatch:** in amendment-05, state that PR-A4/A5/A6 are should-fix. Do not edit verdict-05; it is immutable.

### Phase 1 record, round 2 (supersedes the PR-A5 row above)

| Finding | Tests | State before the fix |
|---------|-------|----------------------|
| PR-A2 | amended accepted reads: `tests/contract/test_handoff.py::test_handoff_writes_run_complete_event`, `tests/contract/test_pr_and_verdict.py::test_verdict_commits_valid_different_family_verdict` (read `origin/wo/<id>` after fetch; assertions unchanged) | green; they stay green once the checked-out branch is no longer moved |
| PR-A5 | amended accepted: `tests/unit/test_scorecard.py::test_scorecard_wave1_exit_when_every_order_merged[fifth-working-day\|sixth-working-day]` (P1 statuses on the exit commit, P1 entrypoints resolvable, read via `factory scorecard --json`); new `::test_scorecard_wave1_not_exited_unless_every_p1_gate_implemented_and_green[status-missing\|status-failure\|status-on-other-commit\|unresolvable]`; the round-1 PR-A5 tests now run via the CLI with (b) and (c) satisfied | amended accepted: green; new: red, because exit is set from landings alone |
| PR-A7 | amended accepted: `tests/contract/test_claim.py::test_claim_fast_forward_exactly_one_of_two_concurrent_wins` (loser must exit 2); new `::test_lost_claim_race_at_the_push_is_refused` (deterministic) | amended: green in 12 of 12 runs (the loser usually refuses at "already claimed"); new: red, `[0, 4]` |

### Orchestrator decision on identical same-second claims (amendment-06)

Recorded verbatim by the Slice A worker (2026-10-05). Details are in `bus/orders/wo-20261004-factory-slice-a/amendment-06.yaml`.

Good catch on the identical same-second claim. Decision (orchestrator, process, spec letter of one-winner claims): FIX it as **PR-A8** (blocker, process, found by implementer). Do not change the frozen bus schema.

Rule for phase 2: a claim or release push whose remote ref was already at our commit counts as a LOST race. Porcelain `=` / `[up to date]` means the push did nothing for us, so it must exit 2 (lease conflict), not 0. The same applies to any event push that must be first-writer.

| Finding | Test | State before the fix |
|---------|------|----------------------|
| PR-A8 | new `tests/contract/test_claim.py::test_identical_same_second_claims_have_one_winner` (clock, commit dates and actor pinned; receivepack delays make the second push find origin already at its commit) | red: `[0, 0]`, both claimers report the same SHA |

## Round 2

Reviewed head: `e2f6816b836189b0af4ba0c694fc3036280132d7`

### Verdict

**Accept with recorded Later items.**

There are no Round 2 Blockers. PR-A2 through PR-A8 are fixed at their root
classes, with the accepted remediation tests unchanged since `ccb0b1a`. PR-A1
is not wired end to end yet, but it is now an explicit pre-activation dependency:
T036b must land before T065 can switch identity to verified mode. That sequencing
prevents the unintegrated App path from being presented as live authority.

### Finding resolution

| Finding | Judgment | Root-cause resolution / regression check |
|---------|----------|------------------------------------------|
| PR-A1 | **Later — sequenced, not root-fixed yet** | The disconnected identity path remains. T036b now names the complete integration (installation id, App token, git credential path, REST path, and non-disclosure test) and is a mandatory predecessor of T065's verified-mode switch. Recorded below as Later, not silently accepted as complete. |
| PR-A2 | **Fixed at root** | Shared git plumbing is ref-only: no merge/checkout/reset/index/worktree write. Origin is updated first; a local branch moves only by compare-and-swap after success, and never while checked out in any worktree. Divergence and rejected pushes leave it alone. Handoff and verdict use the authoritative remote tip when the checked-out branch lags. |
| PR-A3 | **Fixed at root** | The packet exactly matches `origin/main`; status and completion stay in the append-only handoff/verdict records. |
| PR-A4 | **Fixed at root** | Claim admission now uses the same `derive_order` lifecycle as the board. A closed-unmerged PR derives `released` and frees capacity; open, accepted, and rejected PRs still hold a slot. |
| PR-A5 | **Fixed at root** | Wave 1 exit requires every cohort order landed with a run and latest accepted verdict, every P1 entrypoint resolvable, and every `factory/<gate>` status successful on the exit commit. The retro landing closes the cohort, and `--sprint` scopes order-derived metrics. |
| PR-A6 | **Fixed at the test root** | The fixture now commits a valid handoff and reaches `diff-within-owned-paths`; its single red is the disclosed Slice B dependency, not the old pre-gate false positive. |
| PR-A7 | **Fixed at root** | Push classification reads the porcelain status line on stdout. `!` is a lease refusal (exit 2), while transport failures remain external (exit 4). |
| PR-A8 | **Fixed at root** | First-writer pushes treat porcelain `=` / up-to-date as a lost race. The shared behavior covers issue, claim, release, new run-complete, verdict, and bus-PR creation; idempotent non-first-writer pushes opt out explicitly. |

### Blockers

None.

### Later

1. **PR-A1 — App identity production integration (product).** Owner: Slice A /
   orchestrator before T065. Complete T036b and its recorded-response custody
   test before verified mode can be enabled.
2. **T-A7-3 — suite-wide synchronous timeout policy (process).** Existing
   in-process CLI calls and frozen fixture subprocesses are not uniformly
   timeout-bounded. The new race/barrier harness itself is bounded and
   self-cleaning; handle the broader policy when CP0 fixtures are amended.

### Safety and regression review

- The ref-only implementation contains no merge, checkout, switch, reset,
  read-tree, stash, force push, or push-to-main path.
- Push rejection updates neither the caller's local branch nor its checkout.
  Successful local advancement is compare-and-swap and occurs only after origin
  accepts the event.
- Closed-PR capacity reads through the existing GitHub port and writes no
  synthetic release.
- P1 scorecard checks resolve entrypoints but never execute gates; status
  evidence is read through the same latest-per-context GitHub port as lifecycle.
- The FR-037 order, claim, and handoff validate. The disclosed
  `size_minutes: 1`, catalog gate-id behavior, Slice B-dependent PR-A6 red, and
  six handoff-fixture integration reds are accepted cross-slice facts, not new
  findings.

### Verification record

| Check | Result |
|-------|--------|
| Worktree setup discovery | Checked repository root and worktree; no `.cursor/worktrees.json`, so setup was skipped. |
| Locked sync | PASS — 29 locked packages installed under Nix. |
| Accepted remediation tests | PASS — `git diff ccb0b1a HEAD -- scripts/factory/tests` is empty. |
| Full `pytest -q` | Expected cross-slice red — **368 passed, 79 failed** in 61.28 s: 26 contract, 52 Slice B seeds, and the one PR-A6 integration test. |
| CI selector | PASS — **277 passed, 170 deselected** in 22.72 s. |
| `ruff check` / `ruff format --check` | PASS — all checks passed; 70 files formatted. |
| `factory check schema --repo ../..` | PASS before verdict-09 — `schema ok`. |
| Packet restoration | PASS — packet is byte-identical to `origin/main`. |
| Frozen CP0 files | PASS — no changes to the frozen source/model/fixture paths. |
