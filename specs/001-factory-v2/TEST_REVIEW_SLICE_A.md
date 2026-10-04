# T* review — Factory v2 Wave 1 Slice A

## A. Executive verdict

**Verdict: reject — Do not implement against these tests yet.**

The 50 Slice A tests are honestly red at callable behavior seams, collect successfully, and lint cleanly; frozen CP0 interfaces were not edited. However, one order-issuance assertion is incompatible with the contract's branch-from-`main` topology, while several high-value locks can still go green with materially wrong behavior: board state placement, required-check handling, GitHub status writes, Wave 1 exit computation, and GitHub App JWT minting. Fix the Blockers before T034 implementation begins.

## B. Findings

| ID | Severity | Tag | Lens | Locus | Finding | Suggested resolution |
|----|----------|-----|------|-------|---------|----------------------|
| T-A1 | Blocker | process | Wrong-thing / SNR | `tests/contract/test_status.py::test_status_json_sections_match_each_lifecycle_state`; T017; `board.matches_reality` | The fixture creates every state, but the assertions do not require the board to render every state correctly. A merged order may still appear in `in_flight` or `blocked`; a released order may appear in `blocked` or `waiting_on_governor`; accepted has no state assertion; rejected may be placed in either of two sections. Such a renderer can pass while SC-001's “agrees with reality 100%” fails. | Assert an exact section and rendered state for every fixture order, plus absence from every incompatible section. Keep lifecycle-unit assertions, but make the board contract independently detect a bad renderer. |
| T-A2 | Blocker | process | Over-constraint / contract mismatch | `tests/contract/test_orders.py::test_order_issue_first_commit_is_only_the_order_file`; T026; data-model Lifecycle | The test runs `git rev-list --max-parents=0 origin/wo/<id>`, which returns the repository root commit for a branch created from `main`, not the order's first branch-only commit. A conforming implementation therefore fails this test unless it incorrectly creates an orphan branch. | Select the first commit in `origin/main..origin/wo/<id>` with `git rev-list --reverse`, then assert that commit's diff adds only the order file and has `origin/main` as its parent. |
| T-A3 | Blocker | process | Vacuous test | `tests/unit/test_github_adapter.py::test_adapter_commit_status_round_trip`; T019 / T021 | `set_commit_status()` is followed by a read from a static `combined_status.json` that already contains a `factory/*` context. A no-op status writer passes. The mock also does not assert the requested SHA, JSON body, or authorization, so the REST adapter may post the wrong status and still green. | Capture the POST request and assert method, `/statuses/<SHA>` path, auth header, and exact context/state/description/target payload. Make the subsequent read reflect the captured write or remove the misleading “round trip” claim. |
| T-A4 | Blocker | product | Lock fidelity | `tests/unit/test_identity.py::test_app_token_mints_jwt_and_exchanges_recorded_response`; D4-A / P5 GitHub App identity | The test accepts any three dot-separated strings as the App JWT. It does not verify RS256 signing, `iss = app_id`, bounded `iat`/`exp`, or that the recorded one-hour installation-token expiry is honored. A thinner fake token generator can pass while the governor does not receive the locked GitHub-verified identity boundary. | Decode and cryptographically verify the JWT with the generated public key; assert algorithm, issuer, and GitHub-valid time bounds. Assert the exchange path includes the requested installation id and expose/validate the recorded expiry or credential lifetime. |
| T-A5 | Blocker | process | Missing negative path | `tests/unit/test_lifecycle.py::test_accepted_needs_verdict_and_green_checks`; T018; FR-011 | Only the positive accept-plus-one-green-check case exists. An implementation that marks every `accept` verdict accepted while ignoring failed, pending, absent, or multiple required checks passes all lifecycle tests. | Parameterize failed, pending, missing, and mixed required-check cases; each must remain `in_review` (or the contractually selected non-accepted state). Include the required-check set, not merely any one green check. |
| T-A6 | Blocker | process | Vacuous catalog evidence | `tests/unit/test_scorecard.py::test_scorecard_computes_intent_yaml_metrics`; T031; `wave1.timebox` | The only `wave1_exit` assertion expects `None`. A constant-`None` implementation passes, so the test does not establish an exit date from run records or the five-working-day boundary named by SC-013/T031. | Add an all-merged/all-P1-complete fixture with a deterministic exit date, plus a boundary case proving working-day computation and start-to-exit duration. |
| T-A7 | Debate | process | Cross-layer gap | `tests/unit/test_lifecycle.py::test_stale_overlay_after_three_times_size_still_counts_toward_cap`; `tests/contract/test_claim.py`; T018/T027 | The stale test manually filters lifecycle states and merely confirms that stale remains `CLAIMED`; it never asks `factory claim` to refuse a fourth claim when one of the three active workers is stale. Claim code can incorrectly exclude stale orders and still pass. | Add a claim contract case with two fresh claims plus one stale claim, then require the fourth claim to exit 2. This is test-shape/SNR, not a new product choice. |
| T-A8 | Debate | process | Always-refuse implementation | `tests/contract/test_pr_and_verdict.py`; T029 | Both verdict tests are refusal-only. An implementation that rejects every verdict satisfies the family and isolation assertions. No test proves that a different-family reviewer with existing git paths at the named SHA can record a verdict. | Add one accepted verdict path and assert the committed verdict content. Add separate nonexistent-path and nonexistent-SHA negatives so “git path at a sha” is tested rather than filename heuristics. |
| T-A9 | Nit | process | Strength | Slice A test commit `7dc2359`; branch diff; required commands | Strength: all 50 new tests collect and fail at invocation/assertion seams (assertions or explicit `pytest.fail` for the missing callable), with zero collection errors or xfails. The diff stays within the packet's expressly allowed test/fixture/task/handoff paths, and no frozen CP0 file changed. | Preserve this red-first shape while fixing T-A1–T-A8; do not replace explicit call-site failures with module-level imports of new implementation modules. |

## C. Adversarial positions

### 1. These tests would go green while a spec lock fails

The strongest case is D4-A: `mint_installation_token` may generate `a.b.c`, POST it to the recorded endpoint, and return the fixture token. The test calls that a GitHub App JWT even though no signature or claims are checked. Independently, lifecycle can treat an accept verdict as accepted despite failed required checks, and scorecard can return `wave1_exit = None` forever. These are not cosmetic gaps: they undermine verified governor identity, machine-decided acceptance, and the Wave 1 time-box.

The suite would be right anyway only if production code were independently constrained by another reviewed cryptographic/status/check contract. No such Slice A test is named as evidence here.

### 2. These tests over-constrain implementation / test the wrong layer

The strongest case is order issuance: selecting the root commit with `--max-parents=0` encodes an orphan-branch topology that directly contradicts “create `wo/<id>` from `main`.” The GitHub adapter tests also patch global `httpx.Client` and match broad path suffixes, coupling construction details while failing to inspect the request semantics that matter.

The suite would be right anyway only if `wo/*` branches were intentionally orphaned and the contract/data model were amended to say so. They are not.

## D. Catalog / contract coverage map

| Catalog id or contract hook | Test file / name | Can fail today? | Gap |
|-----------------------------|------------------|-----------------|-----|
| `board.matches_reality` | `test_status.py::test_status_json_sections_match_each_lifecycle_state` | yes | Does not pin every order to its exact section/state (T-A1). |
| `bus.no_handwritten_status` | `test_status.py` fixture walk; P0 model tests | yes | Slice test checks fixture branches; schema behavior is principally P0 evidence. |
| Lifecycle state machine | `test_lifecycle.py` | yes | Required-check negative paths absent (T-A5). |
| `history.no_bookkeeping` | `test_no_bookkeeping.py` | yes | Covers status+SHA rewrite, real work, and append event; a SHA-only rewrite case would improve precision. |
| `seed.substitution_undeclared` | `test_orders.py::test_order_new_refuses_touched_named_lock_without_fidelity` | yes | Refusal covered; valid locked-order scaffold remains in P0 CLI contract evidence. |
| `handoff.open_od_refused` | `test_orders.py::test_order_issue_refuses_open_human_decision_in_plain_language` | yes | Plain prompt and JSON refusal covered. |
| Order branch topology | `test_orders.py::test_order_issue_first_commit_is_only_the_order_file` | yes | Current assertion rejects the specified topology (T-A2). |
| `handoff.concurrency_cap` (claim half) | `test_claim.py` | yes | Cap 3, overlap, blocked, already-claimed, release and same-order race covered; stale-at-cap integration absent (T-A7). |
| `handoff.done_requires_green` | `test_handoff.py` | yes | Refusal can be caused by any failure; test does not name the failing gate/result. |
| Run-complete event | `test_handoff.py::test_handoff_writes_run_complete_event` | yes | Presence of field names is checked; values and estimate semantics are not. |
| `handoff.reviewer_family` | `test_pr_and_verdict.py::test_verdict_refuses_same_family_reviewer` | yes | No valid-verdict success path (T-A8). |
| `handoff.reviewer_isolated` machine half | `test_pr_and_verdict.py::test_verdict_refuses_input_that_is_not_a_git_path` | yes | No valid path-at-SHA success or independent bad-SHA case (T-A8). |
| Bus PR allowed paths | `test_bus_pr.py` | yes | Positive and negative paths covered. |
| `scorecard.computed` | `test_scorecard.py` | yes | Core aggregate values covered. |
| `wave1.timebox` | `test_scorecard.py` | nominally | No computed exit or five-day boundary (T-A6). |
| GitHub REST adapter | `test_github_adapter.py` | yes | Status write is vacuous; requests are under-asserted (T-A3). |
| GitHub App identity lock | `test_identity.py` | yes | Recorded/verified review paths covered; cryptographic token fidelity absent (T-A4). |

## E. Edit list

- `test_orders.py`: select the first branch-only commit, not the repository root.
- `test_status.py`: assert exact state/section membership and incompatible-section absence for all orders.
- `test_lifecycle.py`: add failed, pending, missing, and mixed required-check acceptance cases.
- `test_github_adapter.py`: capture and assert the complete status POST.
- `test_identity.py`: verify JWT signature, claims, timing, installation id, and token expiry.
- `test_scorecard.py`: add a completed Wave 1 exit-date and five-working-day boundary fixture.
- `test_claim.py`: prove a stale claim still consumes one of the three slots.
- `test_pr_and_verdict.py`: add a valid verdict success path and explicit missing-path/missing-SHA cases.

## F. Questions for the human

None. Strict letter fidelity is already locked; the product Blocker requires stronger evidence for that lock, not a new product decision.

## Verification record

| Check | Result |
|-------|--------|
| Worktree setup discovery | Checked repository root and worktree; no `.cursor/worktrees.json`, so setup was skipped. |
| `uv sync --locked` | PASS under `nix develop` (`uv` was not on the ambient PATH). |
| Full `uv run pytest -q` | Expected RED: **166 failed, 237 passed**. No collection errors; Slice A contributes 50 failures on top of the prior 116 red tests. |
| Slice A 11-file pytest run | Expected RED: **50 failed, 0 passed**. Failures are assertions or explicit missing-callable `pytest.fail` at test call sites, not collection errors. |
| `uv run ruff check .` | PASS — `All checks passed!` |
| Frozen CP0 diff | PASS — no changes to `api.py`, `bus/`, `config/`, `cli/app.py`, `cli/exit_codes.py`, or `gates/registry.py`. |
| Diff hygiene | PASS — `git diff --check origin/main...HEAD`. |

## Triage (orchestrator, round 1)

Agent-adjudicated (2026-10-04). Every finding is process-tagged except T-A4, which strengthens evidence for the already-locked D4-A GitHub App identity (letter fidelity), so no new governor decision is needed. Bus: `wo-20261004-factory-slice-a.verdict-01` (this review, transcribed) and `.amend-01` (this triage). Test changes: `aa2bc5a`.

| ID | Disposition | Decided by | Resolution |
|----|-------------|------------|------------|
| T-A1 | accept | orchestrator (process) | `test_status.py`: an `EXPECTED` map pins each fixture order to exactly one order section, its rendered `state`, and its exact `overlays`; every order is asserted absent from the other three order sections. Placement: issued → `ready`; claimed, in_review, accepted → `in_flight`; stale → `in_flight` as `claimed` + `stale`; rejected → `blocked`; blocked-on-governor → `waiting_on_governor` as `issued` + `blocked_on_governor`; merged and released → on no order section. Also `overrides_per_gate == {"red-first-proof": 1}`, exactly one unverified governor action naming the accepted order and gate, and the in-review card shows `factory-tests` |
| T-A2 | accept | orchestrator (process) | `test_orders.py`: first commit of `git rev-list --reverse origin/main..origin/wo/<id>`; its only parent is `origin/main`; `diff-tree --name-status` is exactly `A bus/orders/<id>/order.yaml`; committed content equals the scaffolded order. Orphan-branch fallback removed |
| T-A3 | accept | orchestrator (process) | `test_github_adapter.py`: stateful `RecordedGitHub` transport stores statuses only from captured POSTs. New `test_set_commit_status_posts_exact_request` asserts one POST to `/repos/fixture/demo/statuses/<SHA>` on the configured host, `Authorization` `Bearer`/`token` + the env token, and the exact `context/state/description/target_url` body. The round-trip test now runs the CP0 conformance helper `assert_commit_status_read_after_write` against the REST port (a no-op writer fails it) |
| T-A4 | accept | orchestrator (lock evidence, D4-A letter) | `test_identity.py`: JWT header `alg == RS256`; signature verified against the generated public key with `openssl dgst -sha256 -verify` (same `openssl` the test already used for key generation, with a tampered-input negative control), so no new Python dependency was added; `iss == "12345"`; `now-60 ≤ iat ≤ now`; `now < exp ≤ now+600`; one POST to exactly `/app/installations/67890/access_tokens`. `mint_installation_token(..., now=)` returns an object with `.token` and `.expires_at` (the recorded 1-hour expiry). `test_app_token_refuses_recorded_token_already_expired`: a recorded token already expired at `now` raises an error that mentions expiry |
| T-A5 | accept | orchestrator (process) | `test_lifecycle.py::test_accepted_needs_verdict_and_full_required_check_set` (8 cases). Required set = a `factory/<gate-id>` commit status for every id in the order's `checks` (success, or failed with an override for that gate) and every check run on the PR head completed with success. Accepted: `all-green`, `failed-overridden`. Stay `in_review`: `status-failed`, `status-pending`, `status-missing`, `override-other-gate`, `check-run-failed`, `mixed-runs` (one green run + one in progress). The board fixture's accepted order now carries the same full set (one status overridden) |
| T-A6 | accept | orchestrator (process) | `test_scorecard.py::test_scorecard_wave1_exit_when_every_order_merged[fifth-working-day\|sixth-working-day]`: two orders run complete, accepted, and merged into `main` in git at fixed dates. `wave1_exit` = date of the last merge; new keys `wave1_working_days` (start day = day 1, Saturday/Sunday skipped) and `wave1_within_timebox`. Start Thu 1 Oct → exit Wed 7 Oct = day 5, within; exit Thu 8 Oct = day 6, not within (a calendar-day count gives 7 and fails the first case). The existing `wave1_exit is None` case is kept |
| T-A7 | accept | orchestrator (process) | `test_claim.py::test_stale_claim_still_counts_toward_cap`: two fresh claims + one stale claim (size 10, last commit days old); the fourth claim exits 2, names the cap, and pushes nothing. The lifecycle stale test's redundant `!= RELEASED` filter was removed |
| T-A8 | accept | orchestrator (process) | `test_pr_and_verdict.py::test_verdict_commits_valid_different_family_verdict`: an openai-family verdict whose inputs exist at the branch head exits 0 and adds exactly one commit that adds only `bus/orders/<id>/verdict-01.yaml`, with `id/decision/findings/reviewer_model/reviewer_family/inputs/bootstrap` equal to the submitted file. `test_verdict_refuses_input_absent_from_git[missing-path\|missing-sha]`: exit 2, the refusal names the absent path or the sha, and the branch head does not move |
| T-A9 | accept | orchestrator (process) | Shape kept: new modules are still imported inside the tests (`importlib` + `pytest.fail` at the call site); 65 Slice A tests collect and fail (0 errors, 0 xfail); full suite 181 failed / 237 passed (the 237 are unchanged); `ruff check .` and `ruff format --check` pass |

Test-shape choices above that a round-2 reviewer may debate (none changes a frozen CP0 interface): the board placement of rejected (`blocked`) and stale (`in_flight`); the required-check set definition; the working-day convention; and the `mint_installation_token(now=)` → `.token` / `.expires_at` signature.
