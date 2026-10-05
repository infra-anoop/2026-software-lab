# Handoff — Factory v2 Slice B — drift gates + intent traceability

| Field | Value |
|-------|-------|
| Packet | `notes/packets/2026-10-04-factory-v2-slice-b.md` |
| Branch | `wo/wo-20261004-factory-slice-b` (base `origin/main` `da0505d`; `origin/main` `b1760ec` merged at `33fbc9d`) |
| Status | **Implemented.** All 218 Slice B tests and all 52 seeds are green. No PR is opened (orchestrator's call) |
| Accept-SHA | `a68b95d884c65eea1e805835cf54b9b1c17ffdda`: the `--no-ff` merge of `review/wo-20261004-factory-slice-b-r3` (`wo-20261004-factory-slice-b.verdict-03`, accept) |
| Round 1 | `wo-20261004-factory-slice-b.verdict-01` (reject, merged from `review/wo-20261004-factory-slice-b` at `670f120`) → triage in `specs/001-factory-v2/TEST_REVIEW_SLICE_B.md` § Triage (round 1) + `bus/orders/wo-20261004-factory-slice-b/amendment-01.yaml` |
| Round 2 | `wo-20261004-factory-slice-b.verdict-02` (reject, merged `--no-ff` from `review/wo-20261004-factory-slice-b-r2` at `5464528`) → triage in § Triage (round 2) + `bus/orders/wo-20261004-factory-slice-b/amendment-02.yaml` (owned paths unchanged) |
| Implement | `amendment-03.yaml` widens owned paths to the FR-023 / SC-005(b) lines of `spec.md` and the `factory check intent` row of `contracts/cli.md`, and records the governor locks of 2026-10-04 |
| Pre-PR | `amendment-04.yaml` records the packet revert to `origin/main` (the packet leaves owned paths) and the orchestrator-authorized one-word edit to reviewer text at `TEST_REVIEW_SLICE_B.md` line 80 |
| Tasks ticked | T039, T040, T041, T042–T048, T061, T062, T063. **T049 stays open** (two `seed.*` rows remain `planned`; see § Catalog evidence) |

## PR review rework, phase 1 (verdict-04, reject)

PR #22 review merged `--no-ff` at `55dfa3f` (`review/wo-20261004-factory-slice-b-pr` `d2a5eb9`). Triage: `amendment-05.yaml` and `PR_REVIEW_SLICE_B.md` § Triage (PR review). Red tests only; accepted tests are unchanged (`git diff a68b95d HEAD` lists only the two new files under `scripts/factory/tests`).

| Finding | New tests | Red / green |
|---------|-----------|-------------|
| PR-B1 | `tests/unit/gates/drift/test_deferral_pointer_targets.py` | 9 red (directory ×5, symlink ×3, gitlink), 5 green controls |
| PR-B4 | `tests/unit/gates/drift/test_red_first_child_env.py` | 13 red (12 leaked variables + env-access scan), 3 green |
| PR-B3 evidence shape | none: Slice C's contract does not pin it (§ Triage, items 1–6) | — |
| PR-B2 | none: investigation + proposal in § Triage | — |

Every red fails by assertion (`let the violation through`, `blocked a clean change … does not pass on head`, `environment access outside factory.config`). Phase 2 waits on the T\* review and on R1 (config owned path) / R2 (pinned bundle model).

## Implementation (phase 2)

**Accepted tests are unchanged since accept.** `git diff a68b95d HEAD -- scripts/factory/tests` is empty. No frozen CP0 file (`api.py`, `bus/`, `config/`, `cli/app.py`, `cli/exit_codes.py`, `gates/registry.py`, `tests/fixtures/`) changed. `gates.yaml` needed no edits: all nine Slice B entrypoints were pre-registered and now import.

| Commit | Change |
|--------|--------|
| `0336b25` | `gates/drift/_git.py` (git reads at merge-base / head, `--no-renames`, regular blobs only), `_common.py` (effective order = order + amendments in order; glob, code-line and whole-word helpers), `_specs.py` (pipe tables, Open Decisions, lock tokens, task lines); `fidelity.py`: `order-fidelity-declared`, `lock.letter-tokens` (T046) |
| `71efad9` | `owned_paths.py`: `diff-within-owned-paths` (T044); `decision_ids.py`: `decision-request-no-ids` (T047) |
| `5ae820d` | `deferral_words.py`: `deferral-words-need-od` (T045); `test_seam.py`: `test-seam-ban` (T043) |
| `9507726` | `catalog_linkage.py`: `catalog-test-linkage`, pytest node ids via AST and eval cases via head blob (T048) |
| `76a75de` | `red_first.py`: `red-first-proof`, base tree with changed test support overlaid vs head tree, each run in a child pytest (T042) |
| `40dab71` | `intent/coverage.py`: presence, effective coverage, `presence_gate` (`factory-check-intent`) and `group_by_intent()` for T064; `cli/intent.py`: `factory check intent [--coverage [--require-target]]` (T063) |
| `63eb0bf` | `amendment-03.yaml`; `spec.md` FR-023 and SC-005(b); `contracts/cli.md` check-intent row; `contracts/gates.md` eval head-blob / symlink / malformed wording |
| `5b6a575` | `acceptance.md` evidence for nine Slice B rows; `tasks.md` checkboxes |
| `39e8354` | Fix found by running the gates on this branch: `red-first-proof` extracts the whole tree, because `scripts/factory/tests/conftest.py` reads the repo-root `factory.toml`. A pytest abort (exit 2–4) with no reports is a crash, not "not collected" |
| `33fbc9d` | Merge of `origin/main` `b1760ec` (#19; no overlap with this branch) |
| `e1c67ea` | `amendment-04.yaml`; packet reverted to `origin/main`; `TEST_REVIEW_SLICE_B.md` line 80 "optional" → "surrounding" |

### Catalog evidence (T049)

Filled with real node ids: `seed.substitution_declared`, `seed.hidden_deferral`, `seed.not_red_first`, `seed.test_seam`, `seed.outside_owned_paths`, `seed.jargon_to_governor`, `seed.catalog_unlinked`, `trace.presence`, `trace.effective_coverage`.

Left `planned`:
- **`seed.substitution_undeclared`.** The row expects "Issuing is refused", which is Slice A's `factory order new` / `order issue` refusal (`test_cli_contract.py::test_order_new_refuses_touched_named_lock_without_fidelity`, still red). Slice B's PR-side gate is covered by `seeds/test_seeds.py::test_seed_undeclared_substitution` (green). Pointing the row at the gate seed would thin the row's outcome, so it waits for Slice A.
- **`seed.code_before_test_review`.** This is Wave 2 (FR-012b).

### Deviations

- **red-first child process.** Tests run in a child `python -c <bootstrap>` (through `uv run --directory <project> --locked` when the project has a `pyproject.toml`). The child removes inherited `PYTEST_*` variables from its own environment before importing pytest, so an outer pytest run cannot leak options. The parent reads no environment (TID251 / I-A3 hold); the only `os.environ` text is inside the child's bootstrap source string. Conservative choice: no `env=` built from the parent's environment.
- **red-first runtime.** On this branch (130 new or changed tests, base `origin/main`) the gate takes about 110 seconds, because the whole repo is extracted twice and a project venv is created per tree. The timeout stays at 900 seconds.
- **`contracts/cli.md`.** The shared `factory check schema | intent | …` row loses `intent` / FR-023; `factory check intent` gets its own row. No other command's text changed.

### Cross-slice dependencies

- **Slice A:** `factory check intent --coverage` builds its GitHub port through `DEPS.github` → `factory.github.rest:build_github` (T021). Until that lands, `--coverage` outside tests exits 3 with "adapter … is not available"; presence needs no adapter. `seed.substitution_undeclared` evidence waits on Slice A's `order new` refusal.
- **Slice C:** T064 (runner per-intent report) consumes `factory.intent.coverage.group_by_intent(results, registry)`. It groups by each result's `intent_ids`, falling back to the gate's registry `intents`. `factory gate run` / CI statuses (T058/T059) produce the `factory/<gate-id>` statuses that effective coverage reads.
- **Not copied or reimplemented:** no Slice A or C module. The effective-order helper (`gates/drift/_common.py:effective_order`) is local to the drift gates and reads only the frozen `bus/` models.

### Gates run by hand on this branch (bootstrap verdict input, FR-037)

`run_gate(<id>, GateContext(base=origin/main b1760ec, head=e1c67ea, order_id=None, bus_snapshot=load_all(head)))` from `scripts/factory`:

| Gate | Result |
|------|--------|
| `factory-check-intent` | pass (81 intents mapped) |
| `red-first-proof` | pass (130 new or changed tests red on base, green on head) |
| `test-seam-ban`, `decision-request-no-ids`, `catalog-test-linkage` | pass |
| `deferral-words-need-od` | pass. It blocked line 80 of `TEST_REVIEW_SLICE_B.md` before amend-04 |
| `order-fidelity-declared`, `lock.letter-tokens`, `diff-within-owned-paths` | pass vacuously (no order file on the bus for this Wave 1 packet). Manual equivalent: the gate's own `Change.of(ctx).files` + `matches_any` against amend-04 `owned_paths` puts 37 changed paths in scope and none outside. No named lock is touched |

## Test-phase history

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

No production code changed in the test phase, and no frozen CP0 file was edited.

## Commands + results

Phase 2, re-run at `e1c67ea` (after the `origin/main` merge and amend-04) from `scripts/factory`:

| Command | Result |
|---------|--------|
| `nix develop ../.. -c uv run pytest -q` | **509 passed, 62 failed**, 571 collected. All 62 are in `tests/contract/test_cli_contract.py`, for commands other lanes own: Slice A 39 (`status`, `decisions`, `scorecard`, `order new/issue`, `claim`, `release`, `handoff`, `pr open`, `verdict`, `bus pr`), Slice C 18 (`override`, `gate run`, `hook`, `check hooks/registry/immutability`, `retro`), US7 / Wave 2 5 (`correction new`, `sprint close`). Each fails with exit 3 "not implemented" |
| `… uv run pytest tests/unit/gates/drift tests/contract/test_intent.py` | **218 passed** |
| `… uv run pytest -m seed` | **52 passed** |
| `… uv run pytest -m "not contract and not seed"` (CI subset) | **424 passed**, 147 deselected |
| `… uv run pytest tests/contract/test_cli_contract.py -k intent` | 2 passed |
| `… uv run ruff check .` | All checks passed |
| `… uv run ruff format --check .` | 57 files already formatted |
| `… uv run factory check schema` | schema ok (amendment-04 included) |

Phase 1, at the round-2 head (kept for the record):

| Command | Result |
|---------|--------|
| `nix develop ../.. -c uv run pytest -q` | 237 passed, 334 failed (116 pre-existing red + 218 Slice B), 571 collected, 0 collection errors |
| `… uv run pytest -m "not contract and not seed"` (CI subset) | 224 passed, 200 failed (all 200 = Slice B drift unit tests), 147 deselected |

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

## Red-first commit pairs (DoD)

Red commits: `4e88515` (132 tests), round-1 triage `21fc8e3` (40 tests), round-2 triage `d36172e` (46 tests). Accepted at `a68b95d`.

| Tests | Green commit |
|-------|--------------|
| `test_fidelity.py` (61), lock seeds | `0336b25` |
| `test_owned_paths.py` (12), `test_decision_ids.py` (10), their seeds | `71efad9` |
| `test_deferral_words.py` (33), `test_test_seam.py` (21), their seeds | `5ae820d` |
| `test_catalog_linkage.py` (51), `test_seed_catalog_unlinked` | `9507726` |
| `test_red_first.py` (12), `test_seed_not_red_first` | `76a75de` |
| `test_intent.py` (18), `test_cli_contract.py -k intent` (2) | `40dab71` |

## Amendment requests

No changes to frozen CP0 interfaces.

Done in amend-03 (were open requests here):
1. **T-B6 wording.** FR-023 and SC-005(b) now define governor-judged as `kind: human` with `status: exists`.
2. **T-B4 caller.** `contracts/cli.md` lists `--require-target` on its own `factory check intent` row. SC-005(b) states that coverage is report-only during the sprint.

Done in amend-04 (pre-PR):
1. **Deferral-words hit on this branch.** `TEST_REVIEW_SLICE_B.md` § F line 80 now reads "surrounding Markdown backticks", an orchestrator-authorized one-word edit to reviewer text that keeps the review's meaning. `deferral-words-need-od` passes.
2. **Packet revert.** `notes/packets/2026-10-04-factory-v2-slice-b.md` is back to its `origin/main` content. Completion evidence is in this handoff and the verdicts only.

**Follow-up the orchestrator is scheduling** (not in this branch):
- **Red-first whole-repo test.** No accepted test pins that `red-first-proof` unpacks the whole repo. It must, because `scripts/factory/tests/conftest.py` reads the repo-root `factory.toml`; that is what broke this branch's self-run before `39e8354`. Accepted tests are frozen, so the test lands in a follow-up order with its own T\* review.

**For the orchestrator** (outside my line scope):
1. **FR-018 eval wording.** FR-018 says "names an existing test or eval". It agrees with the head-blob lock in `contracts/gates.md`, so I left it unedited (outside amend-03's line scope).

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

The orchestrator opens the Slice B PR when ready (not opened by the worker). T049 closes when Slice A's `order new` refusal lands and `seed.substitution_undeclared` gets its evidence. T064 runs in Slice C's lane on top of `group_by_intent()`.
