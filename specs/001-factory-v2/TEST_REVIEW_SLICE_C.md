# T* review — Factory v2 Wave 1 Slice C

Reviewed `wo/wo-20261004-factory-slice-c` at `07d0c1254e7655f09dc388b424a8218dc62be5be`.
Reviewer family: GPT/OpenAI; author family: Claude/Anthropic. Inputs were git artifacts only.

## A. Executive verdict

**Verdict: reject — Do not implement against these tests yet.**

The 188 Slice C tests are honestly red: all fail at assertion/callable seams, the full suite is exactly **304 failed / 237 passed**, there are no collection errors or xfails, and Ruff is clean. The negative coverage for override identity, cap replay, immutable bus files, hook allow/deny responses, and frozen-file hygiene is strong. However, the workflow oracle accepts a no-op `echo`, the registry test requires a fail-open fallback when the canonical head registry is absent, and the shell-guard matrix misses straightforward command forms that bypass a list/substring implementation. The end-to-end 300 ms hook test is also not a stable CI oracle: this runner measured the unchanged CLI startup at **360–436 ms** before hook implementation.

## B. Findings

| ID | Severity | Tag | Lens | Locus | Finding | Suggested resolution |
|----|----------|-----|------|-------|---------|----------------------|
| T-C1 | Blocker | process | Vacuous assertion / authoritative CI | `test_gate_run.py::test_workflow_gate_run_on_the_pr_is_not_allowed_to_fail`; `::test_workflow_publishes_the_board_in_the_job_summary` | Both tests use substring membership. `run: echo 'factory gate run --pr ${{ github.event.number }}'` and `run: echo 'factory status' >> "$GITHUB_STEP_SUMMARY"` satisfy them without executing either command. A workflow that posts no gate statuses and no real board can go green. | Parse each `run` block as shell tokens or constrain an exact normalized command line. Add explicit no-op controls for `echo`, comments, and shell strings. Require the gate command's exit status to be the step status and the status command's stdout to be redirected/appended to `$GITHUB_STEP_SUMMARY`. |
| T-C2 | Blocker | process | Lock fidelity / fail-open input | `test_registry_checks.py::test_fail_mode_passes_on_installed_registry`; module contract “inputs from head” | The test requires `gate.fail-mode-category` to pass when the PR head has no `scripts/factory/gates.yaml`, by silently using the reviewer's installed registry. A PR can therefore remove or omit the canonical registry and still pass this gate against unrelated bytes. That contradicts the contract's head-as-input rule and weakens the registry from source of truth to optional fixture data. | Missing/unreadable head registry must block and name the path. Put a valid registry in every positive fixture. If fixture convenience still needs an installed registry, expose it explicitly in the fixture rather than making production behavior fall back. |
| T-C3 | Blocker | process | Missing negative path / branch lock | `test_hooks.py` `DENIED_ON_ANY_BRANCH`, `DENIED_ON_MAIN_ONLY`; catalog `branch.no_direct_main` | The matrix catches the listed spellings but omits common equivalent forms such as `git -C <repo> commit`, `git -C <repo> push origin main`, `command git push origin main`, `git push origin main:main`, and `git push origin :main`. A simple prefix/substring or exact-list guard can pass all tests while direct main writes remain available. | Add representative option-prefix, wrapper, explicit destination-ref, deletion-ref, and quoted/chained cases, with nearby allowed controls. Assert destination semantics, not one command spelling. |
| T-C4 | Debate | process | Over-constraint / flaky performance oracle | `test_hooks.py::test_live_hook_command_answers_within_budget`; amendment A1 | The hard 300 ms wall-clock assertion includes process scheduling, `uv`, editable-environment discovery, Python import, and Typer startup. It uses “best of three,” which hides some regressions while still failing under runner noise. Eight local measurements were 359.6–436.3 ms (median 382.9 ms) before hook behavior exists. This is not an honest deterministic gate on shared CI. | **process:** Keep the 300 ms product budget, but separate a deterministic warm in-process hook budget from an end-to-end benchmark/telemetry check with a calibrated startup allowance. Approve A1 only as a frozen-interface amendment that creates a genuinely lightweight entrypoint; do not use best-of-three wall time as the merge oracle. |
| T-C5 | Debate | process | Wrong-thing / runner invocation | `test_gate_run.py::test_gate_run_runs_every_registered_ci_gate` | The test proves that every registry id is *reported*, not that every entrypoint ran. A runner can enumerate the registry, invoke only selected gates, synthesize `pass` rows for the rest, and satisfy this test plus the per-gate unit tests. That is enough for an unselected broken gate to be reported green. | **process:** Add a full-run fixture with at least two gates whose observable outcomes/messages differ, including a sentinel failure, and require the full report and exit code to reflect both actual calls. |
| T-C6 | Nit | process | Strength | Slice C test commit; frozen CP0 paths; red-first record | Strength: all 188 new tests collect and fail without module-level imports of not-yet-existing modules; the focused suite is 188 failed / 0 passed, the full suite is 304 failed / 237 passed, and no frozen CP0 path changed. Override, verdict isolation, immutable-bus, cap timing, and hook response tests include meaningful pass and fail controls. | Preserve this red-first shape while fixing T-C1–T-C5. |

## C. Adversarial positions

### 1. These tests would go green while a spec lock fails

The strongest case is authoritative CI. Replacing the workflow gate step with an `echo` containing the expected text passes T-C1's current oracle while running no gates and posting no `factory/<gate-id>` statuses. Independently, a shell guard tailored to the enumerated strings can allow `git -C <repo> push origin main` and still satisfy every hook test. The suite would therefore report the branch/PR lock and CI authority as implemented while both are bypassable.

What would have to be true for the suite to be right anyway: workflow review would need to be permanently manual, and agents would need to use only the exact command spellings in the parameter list. Neither is a product lock.

### 2. These tests over-constrain implementation / test the wrong layer

The strongest case is hook latency. The test treats shared-runner wall time for `uv` + Python + all CLI imports as a deterministic property of hook logic, then takes the best of three samples. A conforming fast hook can fail because the runner is noisy; a regressed hook can pass because one sample was lucky. The installed-registry fallback also tests fixture convenience as production behavior, forcing a conforming fail-closed implementation to fail a positive test.

What would have to be true for the suite to be right anyway: CI would need a guaranteed process-startup latency envelope below 300 ms, and the product contract would need to declare the canonical registry optional. Neither condition is recorded.

## D. Catalog / contract coverage map

| Catalog id or contract hook | Test file / name | Can fail today? | Gap |
|-----------------------------|------------------|-----------------|-----|
| `branch.no_direct_main` | `test_hooks.py` shell-guard matrix; `test_registry_checks.py` branch-protection cases | yes | Straightforward shell-equivalent bypasses are absent (T-C3). Required-check set and board placement are settled by prior review and are not re-raised here. |
| `handoff.concurrency_cap` | `test_concurrency_cap.py`; spawn-guard tests; Slice A claim tests | yes | CI replay covers no claim, third/fourth, release/merge ordering, and one-second races. Equal timestamps are unspecified, so no new product lock is inferred. |
| `override.reason_required` | P0 `test_cli_contract.py::test_override_refuses_empty_reason`; `test_bus_models.py::test_override_reason_non_empty` | yes | Covered outside the newly added file; Slice C should link this existing node as evidence. |
| `override.surfaced_counted` | `test_gate_run.py::test_drift_override_with_reason_passes_and_is_surfaced`; `::test_override_counts_every_override_of_a_gate`; prior Slice A board override test | yes | Runner report/count is strong; board placement/count was settled in Slice A. |
| `override.governor_only` | governor-only runner tests; `test_verdict_and_override.py` message-override tests; P0 CLI refusal | yes | Recorded and verified identity modes, wrong actor, wrong class, and wrong PR are covered. |
| `gate.fail_mode_category` | `test_registry_checks.py` class/category matrix | yes | Missing head registry incorrectly passes (T-C2). |
| `gate.hook_has_twin` | `test_registry_checks.py` hook/twin negative matrix; live registration test | yes | Missing row, missing twin, hook-to-hook twin, non-factory command, and malformed JSON are covered. |
| Gate-run JSON, exit codes, intent grouping, commit statuses | `test_gate_run.py` | yes | Full-run report does not prove every entrypoint was invoked (T-C5). |
| `bus.schema`, `bus.immutable`, `bus.no-handwritten-status` | `test_bus_gates.py`; P0 model tests | yes | Strong add/modify/delete/move, misplaced file, head-vs-working-tree, and nested forbidden-key coverage. |
| `pr-links-order`, open human decision | `test_order_gates.py` | yes | Work and bus PR positive/negative paths plus effective amendments are covered. |
| reviewer family and git-artifact isolation | `test_verdict_and_override.py`; Slice A verdict contract | yes | Latest verdict behavior matches the frozen lifecycle contract. |
| `shell-guard` response | `test_hooks.py` | yes | Correct allow/deny JSON and exit taxonomy are pinned; command-language coverage is incomplete (T-C3). |
| `spawn-guard` response | `test_hooks.py` | yes | `subagentStart` supports `permission` and `user_message`; tests pin our JSON contract and do not assert Cursor UI rendering. |
| `owned-path-warn` response | `test_hooks.py` | yes | Tests pin `agent_message`, but `afterFileEdit` does not advertise that output field in the Cursor hook skill; visibility is not proved. Keep this as advisory/telemetry unless registration moves to an event supporting `additional_context`. |
| `decision-in-chat` response | `test_hooks.py` | yes | Final-turn, code-question-mark, old/new request, and missing transcript paths are covered as our JSON contract. |
| Workflow authority and summary | `test_gate_run.py` workflow tests | yes | No-op shell text passes (T-C1). |

## E. Edit list

- `tests/contract/test_gate_run.py`: reject `echo`/comment/string no-ops and assert executable workflow command structure.
- `tests/contract/test_gate_run.py`: add a full-run fixture proving multiple registered entrypoints actually execute.
- `tests/unit/gates/test_registry_checks.py`: replace installed-registry fallback success with missing-head-registry failure.
- `tests/unit/hooks/test_hooks.py`: add `git -C`, wrappers, destination refspecs, and deletion-ref negatives with allowed controls.
- `tests/unit/hooks/test_hooks.py`: split deterministic hook work from end-to-end startup benchmarking; remove best-of-three as a merge oracle.
- `acceptance.md`: when implementation lands, link existing P0 nodes for `override.reason_required` and Slice A board evidence rather than duplicating them.

## F. Questions for the human

None. T-C1–T-C5 are contract/test-quality corrections, not new product choices.

## Amendment requests and worker questions

- **A1 — fast hook path: approve the need, not the current oracle.** The exact command already costs 360–436 ms here, so Slice C cannot meet the letter budget through hook logic alone. A `main()` conditional after `factory.cli.app` imports is too late; the amendment must provide a genuinely lazy/lightweight entrypoint (or a separate console script plus corresponding hook-contract change). Keep 300 ms as the target, but do not gate shared CI on the current best-of-three test.
- **A2 — `GitHubPort.get_pr(number)`: decline for Slice C.** The frozen port can resolve the small repository's `wo/*` and `bus/*` heads via `list_prs_by_head` and match the number. That is bounded by the stated scale and preserves CP0. Add `get_pr` later only if profiling or portability shows the enumeration is material.
- **Cursor output visibility:** `subagentStart` officially supports `permission` and `user_message`; the spawn test is correctly shaped. `afterFileEdit` does not list `agent_message` as a supported output. The current tests should be read only as our JSON contract, not proof that Cursor displays the warning. If visibility is required, move/add registration to `postToolUse` and return `additional_context`; that is a product/contract amendment, not a test assumption.
- **Spawn warning at cap:** keep the warning even when the prompt names an already claimed order. A second launch is still an additional worker while three are active; the hook is advisory.
- **Cap replay after later release/merge:** keep claim-time replay. It is the contractually named race closure; later capacity does not retroactively validate an over-cap claim.
- **Latest verdict wins:** keep it. This matches the frozen lifecycle definition and permits a later independent correction.
- **Missing head registry:** reject fallback; see T-C2.
- **Review-packet location:** keep `notes/packets/` for this repo. Portability is P3; move it to config when that work begins.
- **Contract marker in CI:** leaving contract tests selected out is acceptable only through CP1 as recorded in the workflow comment; T059/CP2 must remove the temporary selector or otherwise run the full authoritative contract suite.

## Verification record

| Check | Result |
|-------|--------|
| Reviewed head | `07d0c1254e7655f09dc388b424a8218dc62be5be` |
| Locked sync | PASS — 25 locked packages installed/audited under Nix |
| Slice C focused suite | Expected RED — **188 failed, 0 passed** in 55.13 s; no collection errors or xfails |
| Full suite | Expected RED — **304 failed, 237 passed** in 84.10 s; no collection errors or xfails |
| `nix develop ../.. -c uv run ruff check .` | PASS |
| Hook startup sample | 8 runs: **359.6–436.3 ms**, median **382.9 ms** |
| Frozen CP0 files | PASS — no changes to `api.py`, `bus/`, `config/`, `cli/app.py`, `cli/exit_codes.py`, `gates/registry.py`, or existing `tests/fixtures/` |
| Changed paths | PASS — packet/handoff, T050–T053 tests/helper, and Slice C task checkboxes only |
| Worktree setup | No `.cursor/worktrees.json` in either repository root or worktree; setup skipped after both checks |
