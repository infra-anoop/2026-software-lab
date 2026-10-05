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
