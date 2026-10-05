# Handoff (interim) — Factory v2 Slice B — drift gates + intent traceability

| Field | Value |
|-------|-------|
| Packet | `notes/packets/2026-10-04-factory-v2-slice-b.md` |
| Branch | `wo/wo-20261004-factory-slice-b` (base `origin/main` `da0505d`) |
| Status | **T\* round 2 applied; round-3 confirmation requested** — still phase 1 (red tests). No implementation yet. |
| Round 1 | `wo-20261004-factory-slice-b.verdict-01` (reject, merged from `review/wo-20261004-factory-slice-b` at `670f120`) → triage in `specs/001-factory-v2/TEST_REVIEW_SLICE_B.md` § Triage (round 1) + `bus/orders/wo-20261004-factory-slice-b/amendment-01.yaml` |
| Round 2 | `wo-20261004-factory-slice-b.verdict-02` (reject, merged `--no-ff` from `review/wo-20261004-factory-slice-b-r2` at `5464528`) → triage in § Triage (round 2) + `bus/orders/wo-20261004-factory-slice-b/amendment-02.yaml` (owned paths unchanged) |
| Tasks ticked | T039, T040, T061 (tests written). T041/T062 (T\* review) and T042–T049, T063 (impl) open |

## What changed

### Round 0 (`4e88515`) — 132 red tests

| File | Tests (round 0 → 1 → 2) | Gate / command |
|------|------:|----------------|
| `scripts/factory/tests/unit/gates/drift/helpers.py` | — | shared order/amendment builders, `assert_passes` / `assert_blocks` |
| `scripts/factory/tests/unit/gates/drift/test_owned_paths.py` | 12 → 12 → 12 | `diff-within-owned-paths` |
| `scripts/factory/tests/unit/gates/drift/test_test_seam.py` | 21 → 21 → 21 | `test-seam-ban` |
| `scripts/factory/tests/unit/gates/drift/test_deferral_words.py` | 27 → 33 → 33 | `deferral-words-need-od` |
| `scripts/factory/tests/unit/gates/drift/test_fidelity.py` | 26 → 32 → 61 | `order-fidelity-declared`, `lock.letter-tokens` |
| `scripts/factory/tests/unit/gates/drift/test_decision_ids.py` | 6 → 10 → 10 | `decision-request-no-ids` |
| `scripts/factory/tests/unit/gates/drift/test_catalog_linkage.py` | 14 → 34 → 51 | `catalog-test-linkage` |
| `scripts/factory/tests/unit/gates/drift/test_red_first.py` | 12 → 12 → 12 | `red-first-proof` |
| `scripts/factory/tests/contract/test_intent.py` | 14 → 18 → 18 | `factory check intent [--coverage [--require-target]]`, gate `factory-check-intent` |
| **Total** | **132 → 172 → 218** | |

### Round 1 — T\* triage applied

- **T-B1 (fidelity):** goal-only lock discovery.
  - The goal names D1's locked value (`Railway`) or the id `D1`, while the tasks and owned paths don't touch D1. Blocks with no Lock entry, passes with one.
  - Near-miss goals (`trailways`, `D10`) pass.
- **T-B2 (decision ids):** a modified request is judged whole, at head.
  - Blocks: an edit that adds an id to the prompt (`T042`) or jargon to an option label (`worktree`).
  - Passes: a clean edit.
  - Blocks: a label-only edit to a request whose prompt already quoted an id.
  - Untouched legacy requests stay exempt.
- **T-B3 (deferral):**
  - `→ sprint 03 (D1)` passes only with D1 waived. It blocks with D1 open or locked.
  - A sprint pointer with no OD blocks.
  - `→ backlog` and `→ someday` block.
- **T-B4 (intent, governor lock A):**
  - `--coverage` stays report-only and exits 0.
  - `--coverage --require-target` exits 1 at 17/19 and exits 0 at exactly 9/10 and at 19/20.
  - `tasks.md` T081 gains one line: `factory sprint close` must call `factory check intent --coverage --require-target`.
- **T-B5 (catalog linkage, governor lock):** eval evidence is `eval:<path>#<case-id>`.
  - Pass: all five supported file forms (YAML list, YAML `cases:`, JSON list, JSON `cases:`, JSONL).
  - Block: a missing file; a missing, prefix or suffix case id; an id present only in another key; a `.txt` file; a file deleted at head; a file that exists untracked only; and malformed references (no `#`, empty id, absolute path, leading or inner `..`).
  - Backticks around evidence are ignored (worker question 9).
  - `contracts/gates.md` gains § Catalog-linkage rule detail. The `acceptance.md` lifecycle sentence and `evidence` field row are amended.
- **T-B6 (intent, governor lock):** a `kind: human` mapping counts only with `status: exists`, so 1/2 → 2/2 once the planned mapping flips to `exists` in a new commit.
- **T-B7 (intent):** the repository presence smoke test compares against ids parsed from every discovered `specs/*/intent.yaml`. It requires at least 2 files, each contributing ids. No feature-002 ids are pinned.
- **amend-01:** widens owned paths to `contracts/gates.md` (the catalog-linkage rule only), the `acceptance.md` header and schema evidence lines, the one sprint-close line in `tasks.md`, the Triage sections of `TEST_REVIEW_SLICE_B.md` and the slice's bus directory. Validated with `factory check schema`; a deliberately broken copy was rejected by file name.

### Round 2 — T\* triage applied (orchestrator, process)

- **T-B2-1 (fidelity, 29 new):** lock-token discovery from Open Decisions status cells, under the orchestrator's pinned rule (see the `test_fidelity.py` docstring and § Triage (round 2)).
  - D1's status cell is replaced by real cells copied verbatim: factory D2 and D4, Smart Writer D2, durable-evals D4 and D6. A synthetic generic-span row is added.
  - Nine touching goals block with no D1 entry and pass with one.
  - Eleven goals that miss every token pass, including "3 workers", "use all of it", a split multiword span, code spans, links, dates and the status keyword.
  - Known limitation recorded: a numeric lock changed without naming its OD id is not discovered. A machine-readable token source is a Wave 2 post-mortem candidate.
- **T-B2-2 (catalog linkage, 17 new):** eval files fail closed.
  - Head blob, not the checkout: a tracked file without the case blocks even when the checkout's copy has it.
  - Tracked symlinks (mode 120000) block, with targets inside and outside the repo.
  - 14 malformed or wrong-shape files block.
- **amend-02:** records the triage. Owned paths are restated unchanged. Validated with `factory check schema`; a broken copy (`supersedes: [not_a_field]`) was rejected.

No production code changed, and no frozen CP0 file was edited.

## Commands + results

Run from `scripts/factory`:

| Command | Result |
|---------|--------|
| `nix develop ../.. -c uv run pytest -q` | **237 passed, 334 failed** (116 pre-existing red + 218 Slice B), 571 collected, **0 collection errors** |
| `… uv run pytest tests/unit/gates/drift tests/contract/test_intent.py` | 218 failed: 202 `AssertionError: gate <id> is not implemented`, 16 CLI exit-code assertions (exit 3 today); 0 errors, 0 xfail. All 46 round-2 tests fail at "not implemented" |
| `… uv run pytest -m "not contract and not seed"` (CI subset) | 224 passed, 200 failed (all 200 = Slice B drift unit tests), 147 deselected |
| `… uv run ruff check .` | All checks passed |
| `… uv run ruff format --check .` | 44 files already formatted |
| `… uv run factory check schema --repo ../..` | schema ok (amendment-02 included) |

**Vacuity check.** I re-ran the throwaway constant stubs, which live outside the repo and have been removed:
- An always-pass stub leaves failures in every Slice B file. Examples: catalog 23 of 34, deferral 18 of 33, fidelity 15 of 32, decision ids 6 of 10.
- An always-block stub fails every Slice B case, because the needles are absent.

**Fixture check.**
- The D1 status rewrite (waived, open, locked) produces the intended rows.
- Every eval fixture file parses to cases `adds-small` and `adds-large`.
- The real repository has two intent files: 001 with 50 ids, 002 with 31.

## Catalog → test map (Slice B rows)

| Catalog row | CP0 seed (T014) | Slice B tests |
|-------------|-----------------|---------------|
| `seed.substitution_undeclared` | `seeds/test_seeds.py::test_seed_undeclared_substitution` | `test_fidelity.py::test_declared_*` (44) |
| `seed.substitution_declared` | `test_seed_declared_lock_violated`, `test_seed_lock_*` | `test_fidelity.py::test_tokens_*`, `test_substitute_outside_added_code_passes` (17) |
| `seed.hidden_deferral` | `test_seed_hidden_deferral` | `test_deferral_words.py` (33) |
| `seed.not_red_first` | `test_seed_not_red_first` | `test_red_first.py` (12) |
| `seed.test_seam` | `test_seed_test_seam` | `test_test_seam.py` (21) |
| `seed.outside_owned_paths` | `test_seed_outside_owned_paths` | `test_owned_paths.py` (12) |
| `seed.jargon_to_governor` | `test_seed_decision_request_*`, `test_seed_jargon_to_governor` | `test_decision_ids.py` (10) |
| `seed.catalog_unlinked` | `test_seed_catalog_unlinked` | `test_catalog_linkage.py` (51) |
| `trace.presence` | — | `test_intent.py::test_presence_*`, `test_intent_without_a_checks_key_is_unmapped`, `test_a_registry_or_catalog_mapping_alone_keeps_presence`, `test_north_star_counts_as_an_intent`, `test_flow_and_block_style_checks_are_both_read`, `test_gate_*` (12) |
| `trace.effective_coverage` | — | `test_intent.py::test_coverage_*`, `test_planned_human_mapping_is_not_governor_judged`, `test_require_target_*` (6) |

Not in this slice's red set:
- `handoff.per_intent_results` (T064): the runner file belongs to Slice C. Slice B supplies `intent.coverage.group_by_intent()`.
- `seed.code_before_test_review`: Wave 2.
- `acceptance.md` evidence cells (T049): filled when the tests turn green.

## Red-first commit pairs (DoD)

| Red commit | Green commit |
|------------|--------------|
| `4e88515` (132 tests) + round-1 triage `21fc8e3` (40 tests) + round-2 triage commit (46 tests) | pending (phase 2) |

## Amendment requests

No changes to frozen CP0 interfaces. The orchestrator's amend-01 handles the owned-path widening.

**For the orchestrator** (outside my paths):
1. **T-B6 wording.** "Explicit governor-judged mapping" is defined in `spec.md` FR-023, SC-005b and US5 #2. To match the lock, it could read "a `kind: human` mapping with `status: exists`, flipped by the PR that records the governor's judgment". I recorded the rule in the `test_intent.py` contract docstring and in the triage only.
2. **T-B4 caller.** The new T081 line covers the sprint-close caller. `contracts/cli.md` may want `--require-target` listed under `factory check intent`; that file is not in my paths.

## Open questions

All are **non_blocking**. Nothing here needs a governor decision.

**Settled in round 1:**
- **Question 3** (threshold): T-B4, option A.
- **Question 4** (phase pointers): T-B3.
- **Question 7** (goal discovery): T-B1.
- **Question 8** (eval ids): T-B5.
- **Question 9** (backticks): accepted with the reviewer's minor edit.
- **Question 13** (planned human): T-B6.

**Accepted as written by the reviewer:** questions 1, 2, 5, 6, 10, 11, 12 and 14.

**Settled in round 2:**
- **Goal discovery source:** replaced by the orchestrator's lock-token rule (T-B2-1).
- **Sprint pointers** and **backticks:** accepted by the reviewer.
- **Modified requests**, **`--require-target` failures** and **`.yml` files:** not contested.
- **Identity:** not contested. It stays unpinned.

**New test-shape choices a round-3 reviewer may debate** (also listed in § Triage (round 2)):
1. **Status keyword.** The leading bold `locked` / `re-locked` is the status, not a value, so it is on the stop list.
2. **Currency.** `$10` counts as numeric or unit-only.
3. **Locked rows.** A re-locked row is a locked row. Bold spans in waived or open rows are not pinned.
4. **Symlinks.** An in-repo symlink target also blocks, because the rule is the tracked mode.
5. **One bad entry.** A bad entry blocks the whole eval file, even when the requested case is valid.

## Next

The orchestrator spawns the round-3 T\* confirmation (T041/T062) on this branch head. After it accepts, phase 2 implements T042–T049 and T063 against these tests and turns the CP0 seeds green.
