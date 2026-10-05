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

## Round 2 review

### Verdict

**Verdict: reject — one test-shape Blocker remains before implementation.**

T-A1 through T-A4 and T-A6 through T-A8 are resolved by executable assertions, and T-A5 now has the requested positive and negative cases. The new T-A5 policy, however, treats every check run visible on the PR as required; that is stricter than the frozen lifecycle contract, which says **required checks** must be green or overridden. The red-first counts, lint, formatting, frozen-interface check, and OpenSSL availability all reproduce.

### Findings

| ID | Severity | Tag | Locus | Finding | Suggested resolution |
|----|----------|-----|-------|---------|----------------------|
| T-A2-1 | Blocker | process | `tests/unit/test_lifecycle.py::test_accepted_needs_verdict_and_full_required_check_set`; `CHECK_CASES`; data-model Lifecycle | The test defines acceptance as every `factory/<gate>` named by `order.checks` being green/validly overridden **plus every check run on the head being green**. The frozen contract says “required checks green (or overridden),” not “all observed checks.” A conforming implementation that ignores an unrelated, advisory, skipped, or still-running non-required check run fails `mixed-runs`. The suite currently has no source of truth identifying which check runs are required, so it cannot honestly elevate all of them. | Keep exact `factory/<gate>` coverage for every order check. For check runs, introduce a contract/configured required-name set and test only those, or remove the all-runs requirement until branch-protection required checks are available. Add one green required run plus one unrelated pending run and require acceptance. |
| T-A2-2 | Debate | process | `tests/contract/test_status.py::test_status_json_sections_match_each_lifecycle_state`; `overrides_per_gate` | `overrides == {"red-first-proof": 1}` requires a sparse map, but the plan only requires counts per gate. A conforming dense renderer that also reports `"test-seam-ban": 0` fails despite preserving every count. This does not change what the governor gets; it is an unnecessary representation lock. | Assert `overrides["red-first-proof"] == 1` and that every additional value is a non-negative integer, unless the contract is amended to require sparse output. |
| T-A2-3 | Nit | process | `bus/orders/wo-20261004-factory-slice-a/verdict-01.yaml` | The round-one verdict faithfully preserves the decision, IDs, severities, tags, material findings, reviewer identity, reviewed SHA, bootstrap flag, and manual evidence. Its header says “transcribed verbatim” / “content unchanged,” although the finding prose is condensed from the review table. There is no substantive drift. | For future transcriptions, say “faithfully summarized” unless the bytes are actually copied verbatim. No correction is needed for adjudication. |
| T-A2-4 | Nit | process | T-A1–T-A8 remediation set | Strength: T-A1 exact placement, T-A2 branch ancestry, T-A3 stateful status POST, T-A4 cryptographic JWT check, T-A6 completed-wave dates, T-A7 stale-cap refusal, and T-A8 valid/invalid verdict paths each fail at the intended callable seam. No frozen CP0 interface was edited. | Preserve these assertions while narrowing T-A2-1 and T-A2-2. |

### Round-one resolution check

| Round-one finding | Round-2 judgment |
|-------------------|------------------|
| T-A1 board placement | Resolved in executable assertions. The specific placement choice is accepted: rejected work is blocked; stale work remains in flight with a stale overlay; merged/released work is terminal and absent from the current-work sections. |
| T-A2 branch-first commit | Resolved. The test selects the first branch-only commit, checks its `main` parent, exact added path, and content. |
| T-A3 REST status write | Resolved. The transport records POSTs, asserts host/path/auth/body, and read-after-write fails for a no-op writer. |
| T-A4 GitHub App token | Resolved for the original gap. RS256 signature, issuer, time bounds, installation path, returned token/expiry, and expired-response refusal are executable. |
| T-A5 required checks | Negative-path gap resolved, but the newly chosen “all check runs” definition is an over-constraint (T-A2-1). |
| T-A6 Wave 1 exit | Resolved. The working-day convention is accepted: the project checkpoint tables count the first order day as working day 1, so Thu 1 Oct → Wed 7 Oct is day 5 and Thu 8 Oct is day 6. |
| T-A7 stale consumes cap | Resolved by a CLI refusal test that also proves no push occurred. |
| T-A8 valid verdict path | Resolved with one successful commit and independent missing-path/missing-SHA refusals. |

### Test-shape judgments

- **(a) Board placement — accept.** It matches the linear state machine and the board's current-work sections. T-A2-2 concerns only sparse-versus-dense override counts, not placement.
- **(b) Required-check set — over-constraint.** Gate statuses named by `order.checks` are required. Arbitrary observed check runs are not automatically required under the frozen contract.
- **(c) Working-day convention — accept.** Counting the first work-order day as day 1 matches CP0/CP1/CP2's “working day from first order” framing and the five-day maximum.
- **(d) Token signature/result shape — accept.** `factory.identity.app_token` is new Slice A code; adding keyword `now` and returning `.token` / `.expires_at` changes none of `api.py`, `bus/`, `config/`, `cli/app.py`, `cli/exit_codes.py`, or `gates/registry.py`.
- **OpenSSL oracle — accept.** `openssl dgst -sha256 -verify` independently checks the JWT bytes and does not depend on whether implementation signing uses PyJWT/cryptography or the CLI. OpenSSL 3.3.3 is present in `nix develop`; `ubuntu-latest` also supplies the stable `openssl dgst` interface. The tampered-input control proves the oracle is live.

### Fresh adversarial pass

The strongest still-green wrong implementation would enumerate every GitHub check run and refuse acceptance when any unrelated run is pending. That behavior passes the new tests but violates the narrower “required checks” lifecycle lock and can leave accepted work permanently in review because of advisory integrations. At the other extreme, the remediated tests now prevent the original no-op status writer, unsigned fake JWT, constant-`None` Wave 1 exit, stale-cap exclusion, always-refuse verdict, and misrendered board implementations.

### Verification record

| Check | Result |
|-------|--------|
| Reviewed head | `7a320aadb93be1c4445ef8c8a72e4e5b419d9bef` |
| Round-one verdict transcription | Substantively faithful; see T-A2-3. |
| Slice A 11-file run | Expected RED: **65 failed, 0 passed**; no collection errors or xfails. |
| Full suite | Expected RED: **181 failed, 237 passed**; no collection errors or xfails. |
| `uv run ruff check .` | PASS. |
| `uv run ruff format --check tests/contract tests/unit` | PASS — 19 files already formatted. |
| OpenSSL in Nix | PASS — OpenSSL 3.3.3. |
| Frozen CP0 files | PASS — no edits to `api.py`, `bus/`, `config/`, `cli/app.py`, `cli/exit_codes.py`, or `gates/registry.py`; the new bus verdict/amendment files are order records, not edits to `factory.bus`. |

## Triage (orchestrator, round 2)

Agent-adjudicated (2026-10-04); every round-2 finding is process-tagged. Bus: `wo-20261004-factory-slice-a.verdict-02` (reviewer) and `.amend-02` (this triage plus the JWT dependency decision).

| ID | Disposition | Decided by | Resolution |
|----|-------------|------------|------------|
| T-A2-1 | accept — option 2 (no configured required-run set, because `config/` is frozen CP0) | orchestrator (process) | `test_lifecycle.py::test_accepted_needs_verdict_and_full_required_check_set`: the required set is a `factory/<gate>` commit status for every gate in the order's `checks`, each green or failed and overridden for that same gate; other check runs are not required. Kept: `all-green`, `failed-overridden` (accepted); `status-failed`, `status-pending`, `status-missing`, `override-other-gate` (stay `in_review`). Removed `check-run-failed`; `mixed-runs` became `unrelated-run-pending` (all required statuses green plus one unrelated run in progress → accepted) |
| T-A2-2 | accept | orchestrator (process) | `test_status.py`: `overrides["red-first-proof"] == 1` and every other value is a non-negative integer, so a dense map such as `{"test-seam-ban": 0}` passes |
| T-A2-3 | noted — no change to `verdict-01` | orchestrator (process) | Future transcriptions say "faithfully summarized" unless the bytes are copied |
| T-A2-4 | noted — strengths | orchestrator (process) | No action |

**JWT dependency (decided in `amend-02`, not added in this run):** the implementation signs the RS256 App JWT with `pyjwt[crypto]` (`>=2.9,<3`, which pulls `cryptography`). The owned paths now include `scripts/factory/pyproject.toml`, `uv.lock`, a new decision row in `research.md`, and the Primary Dependencies line in `plan.md`. Rejected alternatives: shelling out to the `openssl` CLI (a runtime binary dependency plus hand-rolled JWT encoding), and `githubkit`, a non-sibling full GitHub SDK with built-in App auth (it replaces the thin httpx adapter with a much larger surface).

### After T066

- After T066 (branch protection, CP2) the factory can read branch-protection required checks; T066a then adds non-factory required check runs to the required set, with lifecycle cases for a failed and a pending required run.

## Round 3 review

### Verdict

**Verdict: reject — the narrowed required-check rule still permits evidence-free acceptance.**

The `unrelated-run-pending` case correctly removes the round-2 over-constraint, and the dense override map now preserves exact fixture counts. But `WorkOrder.checks` is allowed to be empty, several existing fixtures deliberately use `checks=[]`, and lifecycle has no case preventing such an order from becoming accepted on a verdict alone. That violates FR-011's check-results-plus-independent-verdict lock.

### Findings

| ID | Severity | Tag | Locus | Finding | Suggested resolution |
|----|----------|-----|-------|---------|----------------------|
| T-A3-1 | Blocker | process | `tests/unit/test_lifecycle.py::test_accepted_needs_verdict_and_full_required_check_set`; `WorkOrder.checks`; FR-006/FR-011 | Option 2 is correct for unrelated check runs, but is too loose when `order.checks == []`: the required factory-status loop is vacuous, so an accept verdict can produce `accepted` with no machine-check evidence. The frozen model and generated schema permit an empty list, and existing contract fixtures use it. | Add an executable case proving empty `checks` cannot become accepted. Resolve without changing frozen CP0 models: either `order issue` refuses an empty check set, or lifecycle keeps the order non-accepted. Update empty-check helper fixtures to name a real gate. |
| T-A3-2 | Debate | process | Round-2 triage `### Later`; T066 in `tasks.md`; `deferral-words-need-od` | The intended CP2 follow-up is sensible, but T066 currently covers branch-protection settings/snapshot and does not explicitly task lifecycle ingestion or the promised failed/pending required-run cases. Also, a standalone `### Later` heading does not put the T066 pointer on the same line as the deferral word under the feature's own deferral rule. | Rename the heading to `### After T066` and amend T066 (or add a dependent task) to name lifecycle required-check ingestion and its two tests. |
| T-A3-3 | Nit | process | `test_status.py`; `amendment-02.yaml`; round-2 triage | Strength: dense override maps pass while every non-target count must correctly remain zero for this fixture. Amendment 02 faithfully records all round-2 dispositions, authorizes only the dependency/lock/research/plan paths needed for `pyjwt[crypto]`, and records the rejected OpenSSL-CLI and `githubkit` alternatives. | Preserve this shape. Add PyJWT, its lockfile update, one research decision row, and only the plan Primary Dependencies change during implementation as authorized. |

### Confirmation judgments

- **T-A2-1 option 2:** accepted for non-required/advisory runs, but rejected as complete because empty `checks` remains evidence-free (T-A3-1).
- **T-A2-2:** resolved. `red-first-proof == 1` plus all other listed counts exactly zero is faithful to the fixture and allows sparse or dense output.
- **Amendment 02 / dependency decision:** faithful. The selected `pyjwt[crypto] >=2.9,<3` and rejected OpenSSL CLI / `githubkit` alternatives are explicit. The widened paths are narrow and sufficient; no dependency or design file was changed prematurely.
- **Round-2 triage:** faithful except that its CP2 follow-up needs an explicit task and deferral-safe wording (T-A3-2).

### Verification record

| Check | Result |
|-------|--------|
| Reviewed head | `d79fbb67f7880cda59d919aefb9a65ced2011495` |
| Slice A 11-file run | Expected RED: **64 failed, 0 passed**; no collection errors or xfails. |
| Full suite | Expected RED: **180 failed, 237 passed**; no collection errors or xfails. |
| `uv run ruff check .` | PASS. |
| `uv run ruff format --check tests/contract tests/unit` | PASS — 19 files already formatted. |
| `factory check schema` | PASS — `schema ok`. |
| Frozen CP0 files | PASS — no frozen interface edits. |

## Triage (orchestrator, round 3)

Agent-adjudicated (2026-10-04); every round-3 finding is process-tagged. Bus: `wo-20261004-factory-slice-a.verdict-03` (reviewer) and `.amend-03` (this triage). The reviewed head already included the orchestrator's `d79fbb6` (other gates' override counts must be `0`).

| ID | Disposition | Decided by | Resolution |
|----|-------------|------------|------------|
| T-A3-1 | accept — lifecycle rule plus issuance refusal | orchestrator (process) | Lifecycle: `test_lifecycle.py::test_empty_checks_never_accepted` (an order with `checks: []`, an accept verdict, green `factory/*` statuses and a green check run stays `in_review`). Issuance: `test_orders.py::test_order_issue_refuses_empty_checks` (`factory order issue` exits 2; the JSON error message names `checks` and carries no ids; no `wo/<id>` branch is pushed and `main` does not move). The refusal sits at `order issue` only, because `order new` has no checks input and the P0 contract test `test_order_new_exit_0` must stay valid. Every existing `checks=[]` fixture still works without a frozen-file edit: the Slice A helpers (`test_handoff.py::_claimed`, `test_pr_and_verdict.py::claimed_with_handoff`) now name the registered gate `diff-within-owned-paths`, and the three P0 `test_cli_contract.py` uses issue through `RepoBuilder.issue_order` (git, not the CLI), so the refusal does not apply to them; they were not edited |
| T-A3-2 | accept | orchestrator (process) | Round-2 heading renamed to `### After T066`. `tasks.md` gains a single line, `T066a`, immediately after T066: lifecycle reads branch-protection required checks and adds non-factory required runs, with failed-run and pending-run tests (both stay `in_review`) |
| T-A3-3 | noted — strength | orchestrator (process) | No action |

## Round 4 review

### Verdict

**Verdict: accept.**

Both lines of defense are now executable: issuance refuses empty checks before pushing a work branch, and lifecycle independently refuses to derive `accepted` from an empty check set even when a verdict and unrelated green evidence exist. The order-issue placement is sufficient because `order new` is only a scaffold; the policy boundary is issuance, and lifecycle protects repositories created through lower-level/test paths. T066a makes the deferred non-factory required-run work explicit and failable.

### Findings

| ID | Severity | Tag | Locus | Finding | Suggested resolution |
|----|----------|-----|-------|---------|----------------------|
| T-A4-1 | Nit | process | `tests/contract/test_orders.py::test_order_issue_refuses_empty_checks` | The refusal correctly names `checks`, returns JSON exit 2, leaves `main` unchanged, and pushes no work branch. Its “no IDs” assertion spot-checks only `T026` and `FR-011`; another internal id form could still leak without failing this test. This does not weaken the empty-check policy. | Reuse the decision-id regex set or assert absence of all `T/F/R/P/D`, `FR-`, `SC-`, `US`, and `§` forms in the error message when next touching this test. |
| T-A4-2 | Nit | process | Round-3 remediation set; `amendment-03.yaml`; T066a | Strength: `test_empty_checks_never_accepted` defeats vacuous acceptance despite green unrelated statuses/runs; Slice A helpers now carry a real gate; unchanged P0 direct-git fixtures remain valid test scaffolding and cannot bypass either product defense; T066a names lifecycle ingestion plus failed and pending required-run tests. Amendment 03 faithfully restates amendment 02's owned paths and round-3 triage. | No blocking change. Proceed to implementation. |

### Confirmation judgments

- **Issuance placement:** sufficient. `order new` may produce an incomplete local scaffold, but `order issue` is the authoritative transition and now refuses empty checks without pushing or moving `main`.
- **Lifecycle defense:** sufficient and independent. Even a lower-level/imported empty-check order with an accept verdict and green unrelated evidence remains `in_review`.
- **P0 `checks=[]` fixtures:** acceptable. They are frozen lower-level CLI fixtures, bypass issuance intentionally, and do not assert accepted lifecycle state.
- **Slice A helpers:** corrected to the registered `diff-within-owned-paths` gate.
- **T066a:** present exactly once immediately after T066; it names branch-protection required-check ingestion and failed/pending non-factory required-run cases, both remaining `in_review`.
- **Amendment 03:** faithful; owned paths match amendment 02 and include only the previously authorized dependency/design paths plus existing Slice A/review paths.

### Verification record

| Check | Result |
|-------|--------|
| Reviewed head | `e42b379a6f0fc3d8f7a6306fd0b6cd1bf2da9b2a` |
| Slice A 11-file run | Expected RED: **66 failed, 0 passed**; no collection errors or xfails. |
| Full suite | Expected RED: **182 failed, 237 passed**; no collection errors or xfails. |
| `uv run ruff check .` | PASS. |
| `uv run ruff format --check tests/contract tests/unit` | PASS — 19 files already formatted. |
| `factory check schema` | PASS — `schema ok`. |
| Diff hygiene | PASS — `git diff --check d79fbb6..e42b379`. |

## Round 5 (PR-fix tests)

### Verdict

**Verdict: reject — two test-shape Blockers remain before the PR fixes are implemented.**

The accepted-test amendments are justified and preserve their original assertions, all 17
PR-fix reds fail against the reviewed implementation, and the suite is jointly satisfiable.
The concurrency orchestration is not deterministic on a loaded runner, however, and the git
safety cases do not cover the full ref-only behavior pinned by amendment 04.

### Findings

| ID | Severity | Tag | Locus | Finding | Suggested resolution |
|----|----------|-----|-------|---------|----------------------|
| T-A5-1 | Blocker | process | `test_claim.py::test_lost_claim_race_at_the_push_is_refused`; `::test_identical_same_second_claims_have_one_winner` | The one- and three-second `receivepack` sleeps do not synchronize both claimers past fetch before either push lands. On a loaded two-core runner, the second future may start or fetch after the first push, then refuse as already claimed. Both tests can therefore pass without exercising the PR-A7 porcelain-rejection or PR-A8 up-to-date outcome; PR-A7 can also invert its hard-coded first winner. Eight local repetitions produced the intended reds, but repetition does not remove the scheduling race. | Replace elapsed-time ordering with an explicit pre-push barrier and deterministic receivepack release order. Assert evidence that each intended push outcome was actually reached. |
| T-A5-2 | Blocker | process | `test_git_safety.py`; PR-A2 behavior in amendment 04 | Successful checked-out-branch cases cover claim and release only; handoff and verdict can still move the caller checkout and pass. There is no linked-worktree case, no successful CAS advancement of a non-checked-out local branch, and no divergent-local-branch case. The rejection fixture moves origin before command start, so an implementation that refuses during an initial fetch can pass without proving push-rejection rollback safety. | Add success cases for handoff and verdict, a branch checked out in another linked worktree, successful non-checked-out CAS advancement, and divergent-local refusal. Force the remote move after event construction and before push for rejection safety. |
| T-A5-3 | Nit | process | Accepted amendments; scorecard fixtures and choices | Strength: reading `origin/wo/<id>` is the correct consequence of ref-only plumbing; exit 2 strengthens the race contract; the valid handoff fixture removes the PR-A6 false positive; and the scorecard now runs through the CLI with status evidence on the exact exit commit. The `sys.modules` fixtures are legitimate sibling-module seams, not production test branching: normal import resolution is still exercised and the scorecard never runs a gate. The retro-on-main boundary and `refs` sprint membership are explicit, coherent, and satisfiable. | Preserve these choices while fixing T-A5-1 and T-A5-2. |

### Amendment and choice judgments

- **Accepted tests:** all amendments are justified and are not weakenings. The two event tests
  retain their assertions and read the authoritative pushed ref. Requiring exit 2 removes an
  external-error escape hatch. The handoff test now reaches and names the registered gate.
  The accepted Wave 1 exit cases add, rather than substitute, P1 implementation and status
  evidence.
- **P1 entrypoint stubs:** accepted. Slices B and C own the real modules; a unit fixture may
  supply those collaborators while testing ordinary `importlib`/`getattr` resolution. There is
  no app-code test-only branch and the stub raises if the scorecard improperly executes a gate.
- **Wave 1 boundary:** accepted provisionally as the first main commit containing
  `bus/postmortems/wave1-retro.yaml`. T069 creates that artifact and T070 forbids Wave 2 issuance
  before retro disposition, so later orders cannot move or erase the computed Wave 1 exit.
- **Sprint membership:** accepted as an order `refs` entry for `notes/sprints/<S>.md`. It is an
  immutable, explicit relation and the CLI cases prove both scoped and unscoped behavior.
- **Concurrency timing:** rejected. Fixed clocks make commits reproducible, but receivepack
  sleeps do not make thread scheduling or pre-push progress deterministic.
- **Satisfiability:** the amended and new requirements can pass together: build and push event
  commits ref-only, classify rejected/up-to-date first-writer pushes as refusal, derive capacity
  from lifecycle plus PR reality, and compute a CLI scorecard from the scoped pre-retro cohort,
  accepted run records, resolvable P1 entrypoints, and statuses on the exit commit.

### Verification record

| Check | Result |
|-------|--------|
| Reviewed head | `a83fb28befb464155607846db4cbbe600aaa724f` |
| Full `uv run pytest -q` | Expected RED: **95 failed, 342 passed** in 87.34s; the prior 78 baseline failures remain and 17 PR-fix tests are red; no collection errors or xfails. |
| PR-A7 / PR-A8 repetitions | Both tests produced their intended current-code failures in **8/8** runs each; T-A5-1 is the structural scheduling gap. |
| Failure reasons | PR-A2 cases fail on checkout/ref mutation; PR-A4 on retained closed-PR capacity; PR-A5 on landing-only/unscoped exit logic; PR-A7 on exit 4; PR-A8 on two exit-0 claimers. |
| `uv run ruff check tests` | PASS. |
| `uv run ruff format --check tests/contract tests/unit` | PASS — 20 files already formatted. |
| `factory check schema` | PASS before verdict-06; rerun after writing the verdict. |
| Production-source diff | PASS — `git diff ea6a554 a83fb28 -- scripts/factory/src` is empty. |
| Test diff hygiene | PASS — `git diff --check ea6a554 a83fb28 -- scripts/factory/tests`. |
| Bus append-only | PASS through reviewed head — amendment-04, amendment-05, amendment-06 and verdict-05 are additions; no existing bus record is modified or deleted. |

## Triage (round 5)

Recorded by the Slice A worker on the orchestrator's instruction (2026-10-05). Details: `bus/orders/wo-20261004-factory-slice-a/amendment-07.yaml`.

**Decision (orchestrator, process):** FIX both T-A5-1 and T-A5-2. Keep every amendment and choice T-A5-3 accepted. The CPU-stress run was skipped on orchestrator instruction: the barrier makes ordering independent of load by construction, and 12/12 repeat runs are sufficient evidence.

**Barrier** (`scripts/factory/tests/contract/push_barrier.py`). Each clone's `remote.origin.receivepack` is a wrapper that git runs only when the command connects to push, after fetch and event build. It writes `arrived-<n>`, blocks until `go-<n>`, records origin's refs (the exact advertisement) in `advertised-<n>`, then execs `git-receive-pack`. Waits are bounded: the wrapper gives up after 30 s; the test fails if a command exits before arriving, or if arrival takes over 30 s.

- **PR-A7:** both claimers arrive, so both built on the unclaimed tip. Claimer 1 is released and exits, then claimer 2. Claimer 2 is advertised claimer 1's commit, which it does not hold, so git rejects client-side (`[rejected] (fetch first)`). The winner order is fixed at `[0, 2]`.
- **PR-A8:** same orchestration with clock, commit dates and actor pinned. Claimer 2 holds the advertised commit (it built it itself), so its push is up to date. Hand-verified: with `--quiet` git prints only `Done` (exit 0); without it, `=` … `[up to date]`. Phase 2 must drop `--quiet` or compare the remote ref.
- **Push rejection:** origin moves only while the handoff push is held, so an initial fetch cannot refuse.

| Finding | Test | State before the fix |
|---------|------|----------------------|
| T-A5-1 / PR-A7 | `test_claim.py::test_lost_claim_race_at_the_push_is_refused` (rewritten) | red `[0, 4]` |
| T-A5-1 / PR-A8 | `test_claim.py::test_identical_same_second_claims_have_one_winner` (rewritten) | red `[0, 0]` |
| T-A5-2 / PR-A2 | `test_git_safety.py::test_handoff_and_verdict_leave_a_checked_out_order_branch_where_it_was[handoff\|verdict]` (new) | red: branch moved |
| T-A5-2 / PR-A2 | `test_git_safety.py::test_claim_leaves_an_order_branch_checked_out_in_another_worktree_alone` (new) | red: branch moved |
| T-A5-2 / PR-A2 | `test_git_safety.py::test_claim_fast_forwards_an_order_branch_that_is_not_checked_out` (new) | green guard |
| T-A5-2 / PR-A2 | `test_git_safety.py::test_claim_leaves_a_diverged_local_order_branch_alone[before-command\|during-push]` (new) | red: no `git pull --ff-only` report |
| T-A5-2 / PR-A2 | `test_git_safety.py::test_handoff_push_rejection_leaves_local_refs_and_worktree_unchanged` (rewritten on the barrier) | red: branch moved |

Divergence follows amendment-04's letter: origin takes the event (exit 0), and the divergent local branch is left alone and reported. Repetitions: 12/12 identical outcomes.

## Round 6 (PR-fix tests)

### Verdict

**Verdict: reject — T-A5-2 is resolved, but T-A5-1 remains open on bounded execution.**

The receive-pack barrier removes the round-5 scheduling race: both pushes are held after
event construction, release order is explicit, and the recorded advertisement proves PR-A7
reaches `fetch first` while PR-A8 reaches the identical-commit/up-to-date path. The PR-A2
suite now covers handoff, verdict, linked worktrees, successful non-checked-out CAS,
pre-existing and during-push divergence, and rejection after event construction. However,
the stated timeout does not bound the enclosing executor shutdown, so a command that hangs
after release can still hang pytest indefinitely.

### Findings

| ID | Severity | Tag | Locus | Finding | Suggested resolution |
|----|----------|-----|-------|---------|----------------------|
| T-A6-1 | Blocker | process | `test_claim.py::_held_race`; `test_git_safety.py::_claim_while_held`; `::test_handoff_push_rejection_leaves_local_refs_and_worktree_unchanged` | Each `Future.result(timeout=...)` sits inside `with ThreadPoolExecutor(...)`. If a factory command hangs after its barrier is released, the timeout raises, then `ThreadPoolExecutor.__exit__` calls `shutdown(wait=True)` and waits without a bound for that same running future. The wrapper and arrival poll are bounded, but the test process is not; the “every wait is bounded” requirement is therefore not met. | Run held commands in a killable process/subprocess and terminate it at the deadline, or add an equivalent hard test-wide timeout that demonstrably interrupts executor shutdown. Keep the current barrier ordering and advertisement assertions. |
| T-A6-2 | Nit | process | `push_barrier.py`; PR-A7 / PR-A8 | Strength: there is no residual scheduling race in the intended push outcome. Both clients reach the wrapper before either receives an advertisement; claimer 1 exits before claimer 2 is released; the loser-object and advertised-ref assertions distinguish `fetch first` from up-to-date. Twelve fresh repetitions were identical. | Preserve this orchestration while fixing T-A6-1. |
| T-A6-3 | Nit | process | `test_git_safety.py`; PR-A2 | Strength: every new red case fails at the asserted PR-A2 seam against current code. Handoff/verdict and linked-worktree cases observe branch movement; both divergence cases observe the missing pull instruction while preserving the divergent ref; rejection observes local branch movement after the barrier proves origin moved only at push. The non-checked-out CAS guard passes as intended. | No change. |

### Round-five resolution check

- **T-A5-1:** partially resolved. Deterministic path selection is resolved; bounded execution is
  not, because executor context shutdown can wait forever after a future timeout.
- **T-A5-2:** resolved. Coverage is complete for the behaviors requested in round 5.
- **Joint satisfiability:** yes. Ref-only event commits, compare-and-swap local advancement,
  checked-out/diverged branch preservation, exit-2 push-race classification, and a killable
  bounded test harness can all hold together.
- **Red-first honesty:** yes. Full collection succeeds; failures are assertions, there are no
  xfails, and no test imports a missing implementation module at module scope.

### Verification record

| Check | Result |
|-------|--------|
| Reviewed head | `d8f2c471b178444b1815d99255374ea4326d11c7` |
| Full `uv run pytest -q` | Expected RED: **100 failed, 343 passed**; 443 collected; no collection errors or xfails. |
| PR-A7 / PR-A8 repetitions | **12/12 identical**: existing atomic-race guard passed; PR-A7 failed `[0, 4]` versus `[0, 2]`; PR-A8 failed `[0, 0]` versus `[0, 2]`. |
| Focused PR-A2 / race run | **11 failed, 1 passed**. The successful non-checked-out CAS case is the intended green guard; all red cases failed at their stated current-code seam. |
| `factory check schema` | PASS — `schema ok` before verdict-07. |
| Production-source diff | PASS — `git diff ea6a554..d8f2c47 -- scripts/factory/src` is empty. |
| Bus append-only | PASS through reviewed head — all six records since `ea6a554` are additions; none is modified or deleted. |
| Worktree setup | Checked repository root and worktree; no `.cursor/worktrees.json`, so setup was skipped. `nix develop ../.. -c uv sync --locked` passed. |

## Triage (round 6)

Recorded by the Slice A worker on the orchestrator's instruction (2026-10-05). Details: `bus/orders/wo-20261004-factory-slice-a/amendment-08.yaml`.

**Decision (orchestrator, process):** FIX T-A6-1. Keep the barrier ordering and advertisement assertions (T-A6-2) and the PR-A2 coverage (T-A6-3) unchanged.

**Killable held commands** (`scripts/factory/tests/contract/push_barrier.py`). There is no executor any more. `PushBarrier.spawn` forks each held command into a child that leads its own process group, which its git and receive-pack processes inherit. A fork rather than a fresh interpreter keeps the in-process test state: the pinned clock for PR-A8 and the fake GitHub behind `factory_cli`. The child returns its result or traceback through a pickle file. `wait_arrived` and `result` only poll with deadlines. On an arrival or result timeout, a command exiting before it arrives, or leaving the `with` block, every child's group is SIGKILLed and reaped. Survivors are checked through `/proc`: anything alive after `KILL_SECONDS` (10 s) fails the test, and every other case fails with a message naming its cause. Call sites change only from `pool.submit` / `future.result` to `barrier.spawn` / `barrier.result`, in the same order as before.

| Finding | Test | State |
|---------|------|-------|
| T-A6-1 | `test_claim.py::_held_race` (PR-A7, PR-A8); `test_git_safety.py::_claim_while_held`; `::test_handoff_push_rejection_leaves_local_refs_and_worktree_unchanged` | unchanged reds: `[0, 4]`, `[0, 0]`, no pull report, branch moved |
| T-A6-1 (meta) | `test_push_barrier.py::test_a_claimer_that_never_arrives_fails_within_the_bound` (new) | green |
| T-A6-1 (meta) | `test_push_barrier.py::test_a_claimer_held_at_origin_that_never_exits_fails_within_the_bound` (new; a real git push held at the wrapper) | green |
| T-A6-1 (meta) | `test_push_barrier.py::test_leaving_the_block_kills_a_command_that_is_still_running` (new) | green |
| T-A6-1 (meta) | `test_push_barrier.py::test_a_command_returns_its_value_or_reports_its_exception` (new) | green |

Evidence: sabotaging PR-A7 so claimer 2 is never released, with a 3 s bound, failed in 3.4 s ("command 2 did not exit within 3s; killed every held command") and left no processes behind. Full suite: 100 failed, 347 passed (the 100 reds are unchanged; the 4 meta-tests are new). The barrier tests ran 12 times with identical outcomes every time. Not changed: the accepted atomic-race guard `test_claim_fast_forward_exactly_one_of_two_concurrent_wins` uses no barrier and still uses an untimed `ThreadPoolExecutor`.

**Follow-up before round 7** (`amendment-09.yaml`; orchestrator, process; same class as T-A6-1; assertions unchanged). The atomic-race guard now runs its two claims as killable `HeldCommands` children with a bounded `result` (60 s). It still uses no barrier, and its assertions are untouched. `PushBarrier` now extends `HeldCommands`, the barrier-free spawn / kill-group / reap base class. An audit of `scripts/factory/tests` found no other executor, thread, or untimed `.result()` / `.join()` wait. Results: full suite 100 failed, 347 passed. Race tests: 12 of 12 runs identical, atomic guard green in every run.
