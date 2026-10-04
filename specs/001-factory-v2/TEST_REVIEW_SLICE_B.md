# T* review — Factory v2 Wave 1 Slice B

Reviewed `wo/wo-20261004-factory-slice-b` at `7ec3c233feca1fa9eb21782abda5ef3784599086`.
Reviewer family: GPT/OpenAI; author family: Claude/Anthropic. Inputs were git artifacts only.

## A. Executive verdict

**Verdict: reject — Do not implement against these tests yet.**

The 132 Slice B tests are honestly red: the focused suite is exactly **132 failed**, the full suite is **248 failed / 237 passed**, all new failures reach assertion seams, there are no collection errors or xfails, and Ruff is clean. The locked token-removal, numeric-direction, no-renames, red-first, deferral-word, decision-id, jargon, and test-seam rules have substantial positive and negative coverage; independent constant-answer probes also show that neither always-allow nor always-block can green the drift suite. However, implementations can still ignore named locks mentioned only in an order goal, lint only newly added decision-request files, and mishandle the contract's sprint-phase deferral pointers while going green. The effective-coverage tests also explicitly green a 37.5% result without any executable sprint-close enforcement of the catalog's 90% shall; two adjacent coverage semantics remain genuine product choices.

## B. Findings

| ID | Severity | Tag | Lens | Locus | Finding | Suggested resolution |
|----|----------|-----|------|-------|---------|----------------------|
| T-B1 | Blocker | process | Lock fidelity / missing path | `test_fidelity.py`; T046; `order-fidelity-declared` | The test module says named locks touched by the effective order's “owned paths or goal” require declarations, but it exercises tasks and owned paths only. An implementation that never scans `goal` passes all tests, so an order can say “deploy this on Railway” with no D1 fidelity entry. This is also worker question 7. | Add a goal-only fixture whose text names the locked decision/tool while tasks and owned paths do not; require D1 to block when absent and pass when declared. Add a near-miss goal so discovery is not arbitrary substring matching. |
| T-B2 | Blocker | process | Changed-scope bypass | `test_decision_ids.py::test_only_requests_added_by_the_change_are_judged`; T047; FR-017 | Tests cover newly added requests and an untouched bad legacy request, but not an existing clean request modified to add an id or jargon. An implementation that scans added files only—not added lines in modified request files—goes green while a changed governor-facing request carries `T042`, `SC-002`, or `worktree`. | Add modified-request cases for prompt and option label, plus a clean modification pass. Judge the request at head whenever its file has added lines; keep untouched legacy exempt. |
| T-B3 | Blocker | process | Exact contract fidelity | `test_deferral_words.py::test_passes_with_a_phase_pointer`; `contracts/gates.md` deferral rule; worker question 4 | Only `→ plan` is pinned. The contract separately allows `→ sprint 03` **with a waived OD**, but no test proves that exact pass case or rejects an arbitrary/missing phase. An implementation may accept every `→ <words>` token or reject the conforming waived-sprint pointer and still green. | Add `→ sprint 03 (D1)` with a fixture OD whose status is waived; add negatives for a nonexistent phase, an unwaived/open OD, and a sprint pointer with no OD. Preserve existing file-pointer resolution. |
| T-B4 | Debate | product | Catalog-auto / threshold timing | `test_intent.py::test_coverage_counts_only_implemented_passing_or_governor_judged`; SC-005; catalog `trace.effective_coverage`; worker question 3 | The test requires exit 0 while reporting **3/8 = 37.5%**. Reporting below target before sprint close is reasonable, but no test or task makes the catalog's “≥90% at sprint close” auto shall fail anywhere. Greening this suite can therefore leave SC-005b permanently below target. The unresolved product behavior is when the threshold becomes blocking, not whether 90% exists. | **product:** choose (A) keep `--coverage` report-only and add a sprint-close/`--require-target` mode that exits 1 below 90%, or (B) make `--coverage` itself fail below 90% at all times. Recommend A; test below/equal/above threshold and wire the sprint-close caller. |
| T-B5 | Debate | product | Undefined contract vocabulary | `test_catalog_linkage.py`; T048; FR-018; worker question 8 | The task and FR-018 allow evidence to name a pytest node id **or eval id**, but every executable case is pytest-only and no artifact defines an eval-id syntax or registry. An implementation that rejects every eval reference passes; inventing a syntax during implementation would create product behavior. | **product:** define the accepted eval-id form and authoritative existence source (for example `eval:<catalog-id>` resolved in a named registry), then add one valid and one missing eval case. If eval evidence is not wanted in Wave 1, narrow FR-018/T048 explicitly rather than silently omitting it. |
| T-B6 | Debate | product | Coverage semantics | `test_intent.py::test_coverage_counts_only_implemented_passing_or_governor_judged`; FR-023; worker question 13 | Only a `kind: human, status: exists` mapping is tested as governor-judged. The repository's real intent files contain `kind: human, status: planned`; whether those count can materially move the reported share and the 90% sprint-close result. Both counting and excluding them can green this suite. | **product:** lock whether `kind: human` is sufficient by declaration, or whether only `status: exists` means the governor has actually judged it. Recommend `exists` only; add planned/existing cases and define what event changes the status. |
| T-B7 | Nit | process | Over-constraint / wrong layer | `test_intent.py::test_presence_holds_on_this_repository` | The repo-level smoke test hardcodes intent ids from unrelated feature 002 (`SW-N1`, `SW-Q1`). A valid rename or replacement in that feature can fail Slice B even when every intent remains mapped and the checker is correct. | Assert that all discovered feature files contribute intents, or compare against ids parsed directly from those files; avoid pinning another feature's product vocabulary in this contract test. |
| T-B8 | Nit | process | Strength | Slice B test commit `4e88515`; P0 seeds; focused/full runs | Strength: every drift file contains real pass and block controls; always-allow produced **66 failed / 52 passed**, always-block produced **90 failed / 28 passed**. The locked per-file token-removal and numeric-direction matrices are inherited from P0 seeds, red-first distinguishes qualifying imports from unrelated base breakage, and no frozen CP0 file changed. | Preserve these controls and the assertion-first import shape while fixing T-B1–T-B6. |

## C. Adversarial positions

### 1. These tests would go green while a spec lock fails

The strongest simple implementation reads only `order.tasks` and `owned_paths` for fidelity declarations, scans only newly added decision-request files, treats any `→ words` as a valid phase pointer, and always exits 0 after printing coverage. It passes the current tests while missing a Railway lock stated only in `goal`, allowing jargon introduced into an existing governor request, accepting invented deferral phases, and reporting 37.5% coverage forever despite the automatic sprint-close 90% shall. A pytest-only catalog parser can also reject all eval evidence without detection.

What would have to be true for the suite to be right anyway: goals would need to be excluded from lock discovery, changed requests would need to mean added files only, phase pointers would need no vocabulary/OD validation, and SC-005b would need a separate scheduled enforcement test. The artifacts say the opposite or provide no such separate task.

### 2. These tests over-constrain implementation / test the wrong layer

The strongest case is the live-repository presence smoke: it embeds feature 002's specific intent ids in a Slice B contract test. Presence should prove discovery and mapping across feature files, not freeze another feature's vocabulary. The suite otherwise mostly tests observable gate results through `run_gate` and CLI envelopes rather than implementation internals. The changed-row catalog rule is not an over-constraint: it is the registry's `changed_lines` scope and protects untouched legacy catalogs from blocking every PR.

What would have to be true for the current test to be right anyway: `SW-N1` and `SW-Q1` would need to be permanent cross-feature interface ids. No such lock exists.

## D. Catalog / contract coverage map

| Catalog id or contract hook | Test file / name | Can fail today? | Gap |
|-----------------------------|------------------|-----------------|-----|
| `seed.substitution_undeclared` / `order-fidelity-declared` | P0 seed; `test_fidelity.py::test_declared_*` | yes | Goal-only discovery missing (T-B1). |
| `seed.substitution_declared` / `lock.letter-tokens` | P0 token-removal, substitute, numeric-direction and guard seeds; `test_fidelity.py::test_tokens_*` | yes | Locked per-file removal, `min|max`, comments, unchanged files, substitutes, and no-renames are covered. |
| `seed.hidden_deferral` / `deferral-words-need-od` | P0 seed; `test_deferral_words.py` | yes | Exact words/scopes/code spans and file pointers covered; waived sprint-phase semantics missing (T-B3). |
| `seed.not_red_first` / `red-first-proof` | P0 seed; `test_red_first.py` | yes | Real assertion/exception, PR-added import names, unrelated base breakage, skips, changed/new/head-red/no-test cases covered; no order file is correctly unnecessary. |
| `seed.test_seam` / `test-seam-ban` | P0 seed; `test_test_seam.py` | yes | Real app-code patterns, changed-line scope, near misses, outside roots, and app test-file exemption covered. |
| `seed.outside_owned_paths` / `diff-within-owned-paths` | P0 seed; `test_owned_paths.py` | yes | Added/modified/deleted paths, sibling-prefix, amendments, own bus dir, missing order, and `--no-renames` move case covered. |
| `seed.jargon_to_governor` / `decision-request-no-ids` | P0 exact regex/jargon/near-miss seeds; `test_decision_ids.py` | yes | Modified existing request bypass missing (T-B2). |
| `seed.catalog_unlinked` / `catalog-test-linkage` | P0 seed; `test_catalog_linkage.py` | yes | Added/edited auto rows, missing evidence/file/function, deleted row, headers, effective checks and untouched legacy covered; eval evidence undefined/untested (T-B5). |
| `trace.presence` / `factory-check-intent` | `test_intent.py::test_presence_*`, mapping-source, multi-feature, north-star, YAML-style and gate cases | yes | Repo smoke over-pins unrelated ids (T-B7). |
| `trace.effective_coverage` | `test_intent.py::test_coverage_counts_only_implemented_passing_or_governor_judged`; `::test_coverage_drops_when_a_passing_check_starts_failing` | partly | Implemented/importable/latest-success semantics can fail; 90% sprint-close enforcement and planned-human semantics are absent (T-B4, T-B6). |

## E. Worker open-question judgments

1. **Accept** — catalog linkage judges rows added/edited in changed scope plus ids in the effective order's checks. Untouched legacy rows may pass; this matches the registered `changed_lines` scope and FR-018 lifecycle.
2. **Accept** — “implemented, passing” means a registered gate with an importable entrypoint and latest `factory/<gate-id>` status on HEAD equal to `success`. The status transition test proves latest-result behavior.
3. **Flag — T-B4 (product)** — report-only below target is acceptable before sprint close, but the 90% auto shall needs an executable blocking boundary.
4. **Flag — T-B3** — `→ plan` alone does not cover the exact waived-sprint phase rule.
5. **Accept** — `ctx.order_id is None` is not pinned for the owned-path gate; PR-level order linkage supplies that precondition. Missing named orders already fail closed.
6. **Accept** — single-star slash semantics are not locked. Nested `**` and sibling-prefix safety cover the material ownership boundary.
7. **Flag — T-B1** — the task explicitly names goal discovery; it needs a test.
8. **Flag — T-B5 (product)** — eval evidence requires a defined id form and source of truth.
9. **Accept with minor edit** — Markdown backticks are presentation, not a distinct evidence id; normalize them and add a guard when next editing this file.
10. **Accept** — app test files are exempt because FR-013 bans seams in application code. The test correctly prevents a broad `apps/**` substring scanner.
11. **Accept** — changed code lines, comment/doc/bus exclusions, unchanged-base non-evidence, per-file removal, move exception, and substitutes are pinned across Slice B plus P0 seeds.
12. **Accept** — the frozen message contract scopes the lint to decision requests, not handoff questions.
13. **Flag — T-B6 (product)** — planned versus existing human mappings changes effective coverage and needs a lock.
14. **Accept** — red-first is a diff/test property and does not require an order file; order linkage is a separate PR gate.

## F. Edit list

- `tests/unit/gates/drift/test_fidelity.py`: add goal-only named-lock discovery block/pass/near-miss cases.
- `tests/unit/gates/drift/test_decision_ids.py`: add modified existing request prompt/label violations and clean modification.
- `tests/unit/gates/drift/test_deferral_words.py`: pin waived sprint-phase pointers and reject arbitrary/unwaived phases.
- `tests/contract/test_intent.py`: add the chosen 90% enforcement boundary with below/equal/above cases.
- `tests/contract/test_intent.py`: pin planned versus existing human mapping semantics.
- `tests/unit/gates/drift/test_catalog_linkage.py`: add valid/missing eval evidence after its syntax is locked.
- `tests/contract/test_intent.py`: remove hardcoded feature-002 intent ids from the repo smoke.
- `tests/unit/gates/drift/test_catalog_linkage.py`: normalize optional Markdown backticks around evidence ids.

## G. Questions for the human

1. Should coverage below 90% merely report until sprint close and then block, or should `factory check intent --coverage` fail below 90% immediately? Recommend report now, block in an explicit sprint-close/required-target mode.
2. What exact evidence form should an automated eval use, and where must that id exist to count? Recommend a namespaced form such as `eval:<id>` resolved against one versioned registry.
3. Does a planned human check already count as “governor-judged,” or only one marked existing after judgment? Recommend only existing judgments count.

## H. Verification record

| Check | Result |
|-------|--------|
| Reviewed head | `7ec3c233feca1fa9eb21782abda5ef3784599086` |
| Locked sync | PASS — 25 locked packages installed/audited under Nix |
| Slice B focused suite | Expected RED — **132 failed** in 27.17 s; no collection errors or xfails |
| Full suite | Expected RED — **248 failed / 237 passed** in 54.30 s; no collection errors or xfails |
| `nix develop ../.. -c uv run ruff check .` | PASS |
| Always-allow drift stub | Rejected — **66 failed / 52 passed** |
| Always-block drift stub | Rejected — **90 failed / 28 passed** |
| Frozen CP0 files | PASS — no changes to `api.py`, `bus/`, `config/`, `cli/app.py`, `cli/exit_codes.py`, `gates/registry.py`, or existing `tests/fixtures/` |
| Changed paths before review output | PASS — packet/handoff, T039/T040/T061 tests/helper, and Slice B task checkboxes only |
| Worktree setup | No `.cursor/worktrees.json` in repository root or worktree; setup skipped after both checks |
