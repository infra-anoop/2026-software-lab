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
- `tests/unit/gates/drift/test_catalog_linkage.py`: normalize surrounding Markdown backticks around evidence ids.

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

## Triage (round 1)

Process findings were agent-adjudicated by the orchestrator (2026-10-04) with the reviewer's suggested resolutions. The product Debates T-B4, T-B5 and T-B6 were locked by the **governor on 2026-10-04**, at letter fidelity. Bus: `wo-20261004-factory-slice-b.verdict-01` (this review) and `.amend-01` (this triage, owned-path widening). Test changes land in the same commit as this section.

| ID | Disposition | Decided by | Resolution |
|----|-------------|------------|------------|
| T-B1 | accept | orchestrator (process) | `test_fidelity.py`: the order's tasks (`T001`) and owned paths (`apps/demo/app/calc.py`) do not touch D1, and the goal does: "Deploy the demo app on Railway before Friday." (the locked value) or "Settle the deploy host per D1 this week." (the decision id). With no D1 Lock entry it blocks naming D1; with one it passes. Near-miss goals "Add the trailways() fare lookup…" and "Fix the D10 retry count…" pass with no lock, so discovery uses whole words, not substrings |
| T-B2 | accept | orchestrator (process) | `test_decision_ids.py`: a clean request on the base, edited by the change to quote `T042` in the prompt or `worktree` in an option label, blocks and names the id or term and the request file. A clean edit passes. A request edited only in a label, whose prompt already quoted `T042`, still blocks: the whole request is judged at head. Untouched legacy requests stay exempt (existing test) |
| T-B3 | accept | orchestrator (process) | `test_deferral_words.py`: D1's status cell in the demo spec is rewritten per case. `→ sprint 03 (D1)` passes with D1 **waived**. It blocks with D1 **open** or **locked**. `→ sprint 03.` with no OD blocks even though a waived D1 exists. `→ backlog.` and `→ someday` block (not a file and not a phase). The OD id that serves a sprint pointer does not also satisfy the OD-id clause, or every unwaived sprint pointer would pass. `→ plan` and file pointers are unchanged |
| T-B4 | **option A — governor 2026-10-04** | governor (product) | Report now, block at sprint close. `factory check intent --coverage` stays report-only and exits 0 at any share (the existing 3/8 case). New sprint-close mode `--coverage --require-target`: 17/19 exits 1 with `error.details.coverage.share`; exactly 9/10 and 19/20 exit 0. `tasks.md` T081 gains the line: `factory sprint close` (gate `sprint-close-requires-postmortem`, P2, Wave 2) must call `factory check intent --coverage --require-target` and must not close when it exits non-zero |
| T-B5 | **locked — governor 2026-10-04** | governor (product) | Eval evidence is `eval:<repo-relative path>#<case-id>`. It counts only if the file exists at the PR head in git and holds a case with `id == <case-id>`. YAML or JSON files hold a top-level list, or a `cases:` list, of mappings with `id`; JSONL holds one object per line with `id`. `test_catalog_linkage.py`: all five forms pass. These block: a missing file; a missing case id (including a prefix or suffix of a real id); an id present only as another key's value; a `.txt` file; a file deleted at head; a file that exists only untracked in the working tree; and malformed references (no `#`, empty case id, an absolute path, a leading or inner `..`), each of which would resolve to the real case if followed. pytest node ids are unchanged. `contracts/gates.md` gains a § Catalog-linkage rule detail, and the `acceptance.md` lifecycle sentence and `evidence` field row name both forms |
| T-B6 | **locked — governor 2026-10-04** | governor (product) | A `kind: human` mapping counts toward coverage only with `status: exists`, meaning the governor has judged it. `planned` never counts. `test_intent.py`: an exists human and a planned human give 1/2. Flipping the planned mapping to `exists` in a new commit (the PR that records the judgment) gives 2/2. The rule is stated in the `test_intent.py` contract docstring. `data-model.md` is outside the amended paths (see handoff) |
| T-B7 | accept | orchestrator (process) | `test_presence_holds_on_this_repository` parses every discovered `specs/*/intent.yaml` (`north_star` + `intents`). It requires at least two files, each contributing ids, and requires the reported `intents` to equal their union with `unmapped == []`. No feature-002 ids are pinned |
| T-B8 | noted — strength | orchestrator (process) | Shape kept: 172 Slice B tests collect and fail on `AssertionError` (156 at "gate … is not implemented", 16 at the CLI exit code), with 0 errors and 0 xfail. Always-allow and always-block stubs still fail cases in every file. The full suite is 288 failed / 237 passed (the 237 are unchanged) |
| Question 9 | accept with minor edit | orchestrator (process) | Markdown backticks around evidence are ignored: guards for a node id and for an eval reference |

**Owned paths (amend-01).** Widened by `specs/001-factory-v2/contracts/gates.md` (the catalog-linkage rule detail only), `specs/001-factory-v2/acceptance.md` (the lifecycle sentence and `evidence` field row, besides this slice's evidence cells), `specs/001-factory-v2/tasks.md` (the one sprint-close line under T081, besides this slice's checkboxes), plus this file's Triage sections and the slice's bus directory.

Test-shape choices a round-2 reviewer may debate (none changes a frozen CP0 interface):
- **Goal discovery:** the locked value is the bold value after "—" in the OD status cell.
- **Modified requests:** they are judged whole, not only their added lines.
- **Sprint pointers:** a sprint pointer's OD does not double as an OD-id reference.
- **`--require-target` failure:** it carries `details.coverage`.
- **Eval files:** a `.yml` extension counts as YAML, and an unsupported extension blocks.

## Round 2 review

Reviewed `wo/wo-20261004-factory-slice-b` at `21fc8e35bb4875707b1c333abe9177e810fcf07c`.

### Verdict

**Verdict: reject — Do not implement against these tests yet.**

T-B2, T-B3, T-B4, T-B6, and T-B7 are resolved in executable assertions, and the focused/full counts reproduce exactly. T-B1's new goal cases are executable but encode a synthetic single-value table convention that does not constrain a parser against the lab's real Open Decision rows, which frequently contain multiple bold values, dates, explanatory prose, and multiword lock descriptions. T-B5 covers the five valid layouts and the named lexical path cases, but still permits a tracked symlink escape or fail-open handling of malformed supported files. Those two Blockers leave matching implementation unsafe.

### Findings

| ID | Severity | Tag | Lens | Locus | Finding | Suggested resolution |
|----|----------|-----|------|-------|---------|----------------------|
| T-B2-1 | Blocker | process | Lock discovery / fixture representativeness | `test_fidelity.py::test_declared_*goal*`; `order-fidelity-declared`; real `specs/*/spec.md` Open Decisions tables | The tests prove D1 and the single synthetic value `Railway`, but not the stated rule “locked value is the bold text after `—`” against real table shapes. Actual rows contain several bold values in one status (factory D2; Smart Writer D2; durable-evals D4), multiword descriptive locks (factory D4), and value prose mixed with dates/links. An implementation that extracts only the first bold span, hardcodes Railway, requires an entire multiword span, or splits it into generic words can pass all six goal tests while missing real locks or generating false positives. | Add table-driven cases copied from at least three real row shapes: multiple numeric values, provider/family values, and a multiword tool/identity lock. Pin whether each bold span is an independent whole phrase/token and add generic-word false-positive guards. Prefer an explicit machine-readable lock-token source if prose extraction cannot be defined without heuristics. |
| T-B2-2 | Blocker | process | Fail-closed eval validation / path traversal | `test_catalog_linkage.py` eval cases; governor lock T-B5 | Lexical absolute/`..`, deleted, untracked, unsupported-extension, and five valid-layout cases are strong, but two wrong implementations still green. First, `git ls-tree` followed by `Path.read_text()` can treat a tracked symlink as “in git at head” and follow it outside the repository. Second, a parser can catch malformed YAML/JSON/JSONL or wrong supported-file shapes and return pass; no assertion requires malformed content, non-list `cases`, non-mapping entries, or entries without `id` to block. The lock says the file itself contains one of the five exact layouts, so both paths must fail closed. | Add a tracked symlink whose target is outside the repo and contains the requested case; require block. Add malformed YAML, JSON, and JSONL plus valid syntax with a wrong top-level shape, non-list `cases`, and list entries lacking mapping/id; each must block. Reading the git blob at `head` rather than the checkout avoids symlink traversal and proves head custody directly. |
| T-B2-3 | Nit | process | Strength | round-1 remediation set; focused/full runs | Strength: modified requests are judged at head with clean and legacy controls; sprint pointers distinguish waived/open/locked decisions; report-only coverage and the 17/19, 9/10, 19/20 target boundaries match the governor lock; planned humans remain uncovered; all five valid eval layouts, exact ids, backticks, deletion, untracked files, and lexical traversal are covered. | Preserve these assertions while adding T-B2-1 and T-B2-2. |

### Round-1 finding resolution judgments

| Finding | Judgment | Evidence |
|---------|----------|----------|
| T-B1 | **Not fully resolved** | Goal-only D1 id/value block/pass and two near misses are executable, but they do not constrain the proposed parser against actual table diversity (T-B2-1). |
| T-B2 | **Resolved** | Prompt and option-label modifications block; clean modification passes; editing any part judges the whole head request; untouched legacy remains exempt. |
| T-B3 | **Resolved** | `→ sprint 03 (D1)` passes only with waived D1 and blocks for open/locked/no-OD; arbitrary phases block; plain existing OD and plan/file pointers retain their distinct behavior. |
| T-B4 | **Resolved** | Plain `--coverage` still succeeds at 3/8. `--coverage --require-target` fails at 17/19 and succeeds at exactly 9/10 and 19/20. T081 explicitly requires the sprint-close caller and refusal. The pending CLI-contract wording is an orchestrator edit, not a test defect. |
| T-B5 | **Not fully resolved** | Five valid layouts, exact case ids, missing/deleted/untracked files, backticks, unsupported extension, Unix absolute path and lexical `..` are covered. Symlink traversal and malformed supported files remain fail-open gaps (T-B2-2). |
| T-B6 | **Resolved** | `kind: human, status: planned` is uncovered at 1/2 and becomes covered only after a committed flip to `exists`, reaching 2/2. The pending FR-023/SC-005b wording is an orchestrator edit, not a test defect. |
| T-B7 | **Resolved** | The repository smoke independently parses every discovered intent file, requires multiple nonempty files, and compares the checker result to the exact union without naming another feature's ids. |

### Test-shape judgments

- **(a) Bold status-cell value extraction: reject as insufficiently pinned.** The repository consistently uses an em dash in many locked rows, but not a single-value grammar. Rows may contain several independently material bold values (`3`, `10`, `8`; OpenAI and Anthropic), a long bold phrase, links, and dates. The synthetic Railway row does not define how those become matchable lock tokens. This is T-B2-1.
- **(b) Sprint-pointer OD does not double-count: accept.** The general OD-reference alternative allows `deferred (D1)` while D1 is open. The more specific contract example `→ sprint 03` explicitly requires a waived OD; allowing the same open D1 to satisfy the generic clause would erase that condition. The tests preserve both forms.
- **(c) Backticks ignored: accept.** Backticks are Markdown presentation around the evidence cell, not part of the pytest node or eval reference. Separate node/eval guards make this normalization explicit.

### Fresh adversarial pass

**Wrong implementation that still greens:** parse only the first bold span after an em dash; recognize `Railway` and `D1`; validate eval paths with `git ls-tree`, then open the checkout path; on parse errors return “no violation.” It passes every current remediation assertion, misses later values in multi-value locks, can follow a tracked symlink outside the repository, and treats malformed supported eval files as linked.

**Over-constraint check:** judging a modified decision request as a whole is faithful because the head request is what reaches the governor. The sprint-pointer distinction is also faithful to the specific waived-OD clause. Requiring `.yml` as YAML and ignoring evidence backticks add compatible forms rather than rejecting a conforming implementation.

### Verification record

| Check | Result |
|-------|--------|
| Reviewed head | `21fc8e35bb4875707b1c333abe9177e810fcf07c` |
| Slice B focused suite | Expected RED — **172 failed** in 56.57 s; no collection errors or xfails |
| Full suite | Expected RED — **288 failed / 237 passed** in 84.36 s; no collection errors or xfails |
| `nix develop ../.. -c uv run ruff check .` | PASS |
| 90% boundaries | 17/19 failure; 9/10 and 19/20 success are executable assertions |
| Eval valid layouts | YAML list, YAML `cases`, JSON list, JSON `cases`, JSONL all present |
| Frozen CP0 files | PASS — no round-1 remediation changed a frozen CP0 file |
| Diff hygiene | PASS — `git diff --check 7ec3c23..21fc8e3` |

## Triage (round 2)

Both findings are process-tagged and were adjudicated by the **orchestrator on 2026-10-05**. Bus: `wo-20261004-factory-slice-b.verdict-02` (this review) and `.amend-02` (this triage; owned paths unchanged from amend-01 and restated). Test changes land in the same commit as this section.

| ID | Disposition | Decided by | Resolution |
|----|-------------|------------|------------|
| T-B2-1 | accept, with a pinned rule | orchestrator (process) | **Lock tokens.** Each bold span in a locked (or re-locked) row's status cell is an independent token. It matches as a whole phrase, case-insensitive, on word boundaries. A multiword span is never split into words. **Not tokens:** purely numeric or unit-only spans (`3`, `70%`, `$10`, `60 minutes`); spans shorter than 3 characters; single generic words (`yes`, `no`, `on`, `off`, `all`, `none`); and the leading status keyword (`locked`, `re-locked`). Links, dates, code spans and plain prose are ignored. Numeric locks are discovered only by their OD id. **Tests** (`test_fidelity.py`): D1's status cell is replaced by a real cell, copied verbatim from factory D2 (`70%`), Smart Writer D2 (`3`, `10`, `8`), durable-evals D6 (`$10`), durable-evals D4 (re-locked; `OpenAI`, `writer is Anthropic`, with code spans, plain-prose providers, a date and a link) and factory D4 (a multiword GitHub App identity phrase), plus a synthetic row of generic, short and unit spans. Nine touching goals each block with no D1 entry and pass with one. Eleven goals that miss every token pass, including "3 workers", "use all of it", a split multiword span, `OpenAIClient`, plain-prose `Gemini`, a code span, a link, a date and the word "locked" |
| T-B2-2 | accept | orchestrator (process) | `test_catalog_linkage.py`: the eval file is read as the git blob at head. A file tracked at head without the case blocks even when the checkout's copy holds it. A tracked symlink (mode 120000, asserted) blocks whether its target is inside the repo or outside it; both targets hold the requested case, and the checkout is left on head. Fourteen malformed or wrong-shape files block, each still naming `adds-small` (except the empty one): YAML, JSON and JSONL syntax errors (one bad JSONL line among good ones); an empty file, a scalar, a mapping without `cases`, a single JSON mapping, and a JSONL line that is not an object; a `cases` value that is a mapping or a string; entries that are strings, or mixed; and an entry, or a JSONL line, without `id` beside a valid `adds-small` |
| T-B2-3 | noted — strength | orchestrator (process) | Round-1 assertions are kept unchanged. 218 Slice B tests (46 new) fail on `AssertionError: gate … is not implemented` or the CLI exit code, with 0 errors and 0 xfail. The full suite is 334 failed / 237 passed (the 237 are unchanged) |

**Known limitation (T-B2-1).** An order that changes a numeric lock without naming its OD id (for example "lower the mutation threshold to 60%") goes undiscovered by `order-fidelity-declared`. The test pins this as a pass. `lock.letter-tokens` still checks numeric tokens on declared locks. A machine-readable lock-token source is a **Wave 2 post-mortem candidate**; it is not built now.

Test-shape choices a round-3 reviewer may debate (none changes a frozen CP0 interface):
- **Status keyword.** The leading bold `locked` / `re-locked` is the row's status, not a value. It joins the generic stop list, so the goal "Keep the locked rows untouched." does not touch D1.
- **Currency.** `$10` counts as numeric or unit-only.
- **Locked rows.** A re-locked row is a locked row. Bold spans in waived or open rows are not pinned.
- **Symlinks.** An in-repo target also blocks, because the rule is the tracked mode, not where the link points.
- **One bad entry.** A bad entry blocks the whole file, even when the requested case is a valid entry.

## Round 3

Reviewed `wo/wo-20261004-factory-slice-b` at `d36172e805c80c7740ac6fa1feee895efe513063`.

### Verdict

**Verdict: accept — implementation may proceed against these tests.**

T-B2-1 and T-B2-2 are resolved as triaged. The lock-token matrix uses the real
factory D2/D4, Smart Writer D2 and durable-evals D4/D6 status cells, exercises
each material phrase as an independent case-insensitive whole-phrase token, and
guards numeric/unit-only, short, generic, status-keyword, code, link, date,
plain-prose and split-phrase false positives. The catalog-linkage matrix proves
head-blob custody, rejects tracked symlinks by mode whether their target is
inside or outside the repository, and fails closed on all 14 malformed or
wrong-shape layouts.

The positive and negative expectations are jointly satisfiable: a parser can
select locked/re-locked rows, extract qualifying bold spans after the status
marker, compare them to the order goal on case-insensitive phrase boundaries,
and separately discover numeric locks by OD id; catalog linkage can inspect the
head tree mode, read only a regular-file blob, parse the extension-specific
layout strictly, and require every entry to be a mapping with `id`. No case
requires incompatible output for the same effective input.

### Findings

None.

### Round-2 finding resolution

| Finding | Judgment | Evidence |
|---------|----------|----------|
| T-B2-1 | **Resolved** | 29 added cases cover the five real status-cell shapes plus the synthetic exclusion row; touching goals block without D1 and pass with D1 declared, while the negative matrix protects phrase boundaries and exclusions. |
| T-B2-2 | **Resolved** | 17 added cases prove head-blob reads, both symlink directions, and 14 malformed/wrong-shape failures, including one bad entry beside a valid requested case. |

### Test-shape judgments

1. **Accept — status keyword.** Leading `locked` / `re-locked` describes row
   state rather than lock value; excluding it prevents generic “locked rows”
   prose from touching every decision.
2. **Accept — currency.** `$10` is a numeric amount and is consistently handled
   with the other numeric/unit-only values through OD-id discovery.
3. **Accept — locked rows.** Re-locked rows carry an active lock; waived and open
   rows do not. Restricting token extraction to locked/re-locked status avoids
   declaring superseded or undecided content as letter locks.
4. **Accept — symlinks.** Blocking mode `120000` independent of target location
   gives one auditable head-tree rule and prevents checkout-dependent behavior.
5. **Accept — malformed entry.** One invalid entry makes the declared eval file
   fail closed; silently skipping it would permit ambiguous partial evidence.

### Verification record

| Check | Result |
|-------|--------|
| Reviewed head | `d36172e805c80c7740ac6fa1feee895efe513063` |
| Locked sync | PASS — 25 locked packages installed under Nix |
| Slice B focused suite | Expected RED — **218 failed** in 120.31 s; assertion failures only, no collection errors or xfails |
| Full suite | Expected RED — **334 failed / 237 passed** in 150.47 s; the 237 passing baseline is unchanged |
| CI selector | Expected RED — **224 passed / 200 failed**, 147 deselected; all 200 failures are Slice B drift tests |
| Red-first imports | PASS — tests import existing public factory/fixture modules; no module-level import of a missing implementation module |
| Satisfiability | PASS — no contradictory expectations found in the round-2 additions or inherited suite |
| Production source | PASS — no changes under `scripts/factory/src`, `apps`, `modules`, `deploy`, or `db` from base `da0505d` |
| Owned paths | PASS — round-2 diff is within amendment-02's restated paths; no frozen CP0 source changed |
| Bus append-only | PASS — amendments and verdicts are added records; no prior bus record was rewritten |
| `ruff check` / `ruff format --check` | PASS — all checks passed; 44 files formatted |
| `factory check schema --repo ../..` | PASS — `schema ok` |
| Worktree setup | No `.cursor/worktrees.json` in repository root or worktree; setup skipped after both checks |
