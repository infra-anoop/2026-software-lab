# Handoff (interim) — Factory v2 Slice B — drift gates + intent traceability

| Field | Value |
|-------|-------|
| Packet | `notes/packets/2026-10-04-factory-v2-slice-b.md` |
| Branch | `wo/wo-20261004-factory-slice-b` (base `origin/main` `da0505d`) |
| Status | **red; T\* requested (T041/T062)** — phase 1 only (red tests). No implementation yet. |
| Tasks ticked | T039, T040, T061 (tests written). T041/T062 (T\* review) and T042–T049, T063 (impl) open |

## What changed

New tests only. No production code, no edits to frozen CP0 files, `gates.yaml`, or `acceptance.md`.

| File | Tests | Gate / command |
|------|------:|----------------|
| `scripts/factory/tests/unit/gates/drift/helpers.py` | — | shared order/amendment builders, `assert_passes` / `assert_blocks` |
| `scripts/factory/tests/unit/gates/drift/test_owned_paths.py` | 12 | `diff-within-owned-paths` |
| `scripts/factory/tests/unit/gates/drift/test_test_seam.py` | 21 | `test-seam-ban` |
| `scripts/factory/tests/unit/gates/drift/test_deferral_words.py` | 27 | `deferral-words-need-od` |
| `scripts/factory/tests/unit/gates/drift/test_fidelity.py` | 26 | `order-fidelity-declared`, `lock.letter-tokens` |
| `scripts/factory/tests/unit/gates/drift/test_decision_ids.py` | 6 | `decision-request-no-ids` |
| `scripts/factory/tests/unit/gates/drift/test_catalog_linkage.py` | 14 | `catalog-test-linkage` |
| `scripts/factory/tests/unit/gates/drift/test_red_first.py` | 12 | `red-first-proof` |
| `scripts/factory/tests/contract/test_intent.py` | 14 | `factory check intent [--coverage]`, gate `factory-check-intent` |
| **Total new** | **132** | |

Every gate has pass and block cases. All fixtures are temp git repos built with `RepoBuilder.base_head_pair` and run through the frozen `factory.api.run_gate`. Intent tests drive the CLI through the `factory_cli` fixture with `FakeGitHub` commit statuses.

## Commands + results

Run from `scripts/factory`:

| Command | Result |
|---------|--------|
| `nix develop ../.. -c uv sync --locked` | ok |
| `nix develop ../.. -c uv run pytest -q` | **237 passed, 248 failed** (116 pre-existing red + 132 new), 485 collected, **0 collection errors** |
| `… uv run pytest -m "not contract and not seed"` (CI subset) | 224 passed, 118 failed (all 118 = new drift unit tests), 143 deselected |
| `… uv run ruff check .` | All checks passed |
| `… uv run ruff format --check .` | 44 files already formatted |

**How the new tests fail.** Each one fails on an assertion, not a collection or import error:

- Drift gates hit `AssertionError: gate <id> is not implemented` (the frozen `GateEntrypointError` is caught in `helpers.run_or_fail`).
- Intent tests hit the CLI exit-code assertion: today the command is an unknown-command usage error (exit 3), and the tests expect 0 or 1.
- No xfail. No module-level imports of slice-B modules.

**Vacuity check** (throwaway stub gates outside the repo, since removed):

- An always-pass stub fails every block case in every file.
- An always-block stub fails every pass case in every file.
- So no gate can satisfy a whole file with a constant answer.

**Red-first fixture check.** I ran a throwaway probe that executes raw pytest on base code with head tests overlaid, then on head. Every fixture behaves as its test describes:

- Assertion failure on base, pass on head.
- `NotImplementedError` on base.
- `ImportError` / `ModuleNotFoundError` for a name the PR adds.
- `ModuleNotFoundError: vendor_sdk_that_is_gone` for the unrelated broken module (the "base broken" case).
- `SKIPPED` via `importorskip` on base.
- Failing on head for the head-red case.
- An unchanged `test_add` passing in both.

## Catalog → test map (Slice B rows)

| Catalog row | CP0 seed (T014) | Slice B tests |
|-------------|-----------------|---------------|
| `seed.substitution_undeclared` | `seeds/test_seeds.py::test_seed_undeclared_substitution` | `test_fidelity.py::test_declared_*` (9) |
| `seed.substitution_declared` | `test_seed_declared_lock_violated`, `test_seed_lock_*` | `test_fidelity.py::test_tokens_*`, `test_substitute_outside_added_code_passes` (17) |
| `seed.hidden_deferral` | `test_seed_hidden_deferral` | `test_deferral_words.py` (27) |
| `seed.not_red_first` | `test_seed_not_red_first` | `test_red_first.py` (12) |
| `seed.test_seam` | `test_seed_test_seam` | `test_test_seam.py` (21) |
| `seed.outside_owned_paths` | `test_seed_outside_owned_paths` | `test_owned_paths.py` (12) |
| `seed.jargon_to_governor` | `test_seed_decision_request_*`, `test_seed_jargon_to_governor` | `test_decision_ids.py` (6). Jargon list and near-misses are covered by the seeds |
| `seed.catalog_unlinked` | `test_seed_catalog_unlinked` | `test_catalog_linkage.py` (14) |
| `trace.presence` | — | `test_intent.py::test_presence_*`, `test_intent_without_a_checks_key_is_unmapped`, `test_a_registry_or_catalog_mapping_alone_keeps_presence`, `test_north_star_counts_as_an_intent`, `test_flow_and_block_style_checks_are_both_read`, `test_gate_*` (12) |
| `trace.effective_coverage` | — | `test_intent.py::test_coverage_counts_only_implemented_passing_or_governor_judged`, `test_coverage_drops_when_a_passing_check_starts_failing` (2) |

Not in this slice's red set:

- `handoff.per_intent_results` (T064): the runner file belongs to slice C. Slice B will supply `intent.coverage.group_by_intent()` at implementation time.
- `seed.code_before_test_review`: Wave 2.
- `acceptance.md` evidence cells (T049): filled when the tests turn green.

## Red-first commit pairs (DoD)

| Red commit | Green commit |
|------------|--------------|
| `4e88515` (all 132 tests) | pending (phase 2) |

## Amendment requests

None. The frozen CP0 interfaces were sufficient: `run_gate`, `GateContext`, `GateResult`, `RepoBuilder`, `factory_cli`, `FakeGitHub`, the bus models and the `gates.yaml` entrypoints.

## Open questions

The tests pin a conservative reading for each item below. T\* review may want to adjust these.

1. **non_blocking** — The catalog gate is judged on changed scope. `specs/smart-writer-v2/acceptance.md` has 4 `auto` rows and no evidence column. A repo-wide "every auto row has evidence" check would block every PR today.
   - Tests require evidence on auto rows the PR adds or edits, and on rows in the order's `checks`.
   - Untouched legacy rows pass.
   - This matches `scope: changed_lines` in the registry.
2. **non_blocking** — "Passing check" for `--coverage` means the latest `factory/<gate-id>` commit status on HEAD is `success`, read via `GitHubPort`. "Implemented" means the gate is registered in `gates.yaml` and its entrypoint imports. A self-reported "exists" mapping for an unregistered gate does not count.
3. **non_blocking** — `--coverage` below the 90% target exits 0 and reports the share. The tests do not pin a failing exit code below target, because the target is judged at sprint close.
4. **non_blocking** — Deferral phase pointers: only `→ plan` is pinned as a phase vocabulary word. File pointers must resolve at head.
5. **non_blocking** — Owned-paths behavior when `ctx.order_id is None` is not pinned.
6. **non_blocking** — Whether a glob `*` crosses `/` is not pinned. Only `**` nesting and sibling-prefix rejection are tested.
7. **non_blocking** — Named-lock discovery from the order goal alone (with no tasks or paths) is not pinned. Tests cover tasks, owned paths and amendments.
8. **non_blocking** — "Eval id" as catalog evidence is undefined in the contracts, so only pytest node ids are tested.
9. **non_blocking** — Evidence cells may wrap node ids in backticks. Tests use bare node ids.
10. **non_blocking** — Under the seam ban, app test files (`apps/<id>/tests/**`) are exempt. This is my reading of FR-013, which covers app code rather than tests.
11. **non_blocking** — Lock token presence rule: the PR's changed code files at head must honor each token. Comment-only lines, `*.md` and `bus/` don't count. Tokens in unchanged base files don't honor the diff.
12. **non_blocking** — Whether handoff `blocker_governor` question text should also be linted for ids. The tests cover decision requests only.
13. **non_blocking** — "Explicit governor-judged mapping" is read as an intent check with `kind: human` and `status: exists`, and it counts as covered. Whether a `kind: human` check with `status: planned` counts is not pinned.
14. **non_blocking** — The red-first gate does not require an order file: the CP0 seed passes an `order_id` that has no order file.

Nothing here is `blocker_governor`.

## Next

The orchestrator spawns the T\* review (T041/T062) on commit `4e88515`. After triage, phase 2 implements T042–T049 and T063 against these tests and turns the CP0 seeds green.
