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

## Triage (orchestrator, round 1)

Agent-adjudicated (2026-10-04). Every finding is process-tagged. For T-C4 the letter of the "offline in < 300 ms" hook lock (`contracts/hooks.md`, plan Performance Goals) is kept: the full 300 ms end to end, with no startup allowance and no governor waive requested. Bus: `wo-20261004-factory-slice-c.verdict-01` (this review) and `.amend-01` (this triage, A1, owned-path widening). Test changes: `2997116`.

| ID | Disposition | Decided by | Resolution |
|----|-------------|------------|------------|
| T-C1 | accept | orchestrator (process) | `test_gate_run.py`: each `run` block is tokenized with `shlex` (comments, quoting, `&&`/`\|\|`/`;`/`\|`/subshells), with GitHub expressions substituted first. The gate step must be exactly one command, `factory gate run --pr <event number>` (after an optional `uv run [options]` prefix), so its exit status is the step's: no `continue-on-error` on the job or any step, no `if:`, default `bash` shell. The board step's `factory status` must redirect (`>`/`>>`) to `$GITHUB_STEP_SUMMARY` or pipe into `tee -a` it, and it must run before the gate step or under `always()`/`!cancelled()`. Each test first asserts that its oracle rejects no-op controls: `echo '…'`, `# …`, `true "…"`, `\|\| true`, `; exit 0`, `\| tee log`, `set +e`, wrong PR number, `echo factory status >> …`, `factory status` with no redirect, a redirect to `/dev/null` followed by an `echo` into the summary, and `tee` without `-a` |
| T-C2 | accept | orchestrator (process) | `test_registry_checks.py`: `test_fail_mode_passes_on_installed_registry` removed. A head with no registry, a registry deleted at head, or an unreadable registry blocks `gate.fail-mode-category` and names `scripts/factory/gates.yaml`. The same applies to `hook-has-ci-twin` (hooks present, no registry), `branch-protection-require-pr` (whose positive fixture now carries the real registry at head) and `factory check registry`. Every positive fixture carries a head registry. Production code has no fallback |
| T-C3 | accept | orchestrator (process) | `test_hooks.py` `PUSH_TO_MAIN` (30 forms, denied on any branch): refspecs `main:main`, `+HEAD:main`, `:main`, `:refs/heads/main`, `--delete`/`-d main`, multi-refspec. Option prefixes `git -C <repo>`, `-c k=v`, `--no-pager`; `/usr/bin/git`; `command git`, `env git`, `GIT_TRACE=1 git`. Quoted refspecs; chains `&&`, `;`, `\|\|`, `cd … &&`; subshell `( … )`; `bash -c '…'` / `sh -c "…"`. Main-only additions: `git -C <repo> commit`, `git -c … commit`, `command git commit`, `commit --amend`, `push -u origin HEAD`, `git -C <repo> push`. Allowed controls on `main`: `feature:feature`, `main:refs/heads/wo/…`, `HEAD:wo/…`, `git -C <repo> push origin wo/…`, `--delete wo/…`, `fetch`/`pull --ff-only origin main`, and `echo`/comment/`git log --grep`/`rg` text containing `git push origin main`. Two branch-semantics tests: `git -C <repo> commit` run from another `cwd` is judged by `<repo>`'s branch, and plain `git commit` in a non-repo `cwd` is allowed while `cd <repo> && git commit` is denied |
| T-C4 | accept — letter kept; **A1 approved** | orchestrator (process) | Console script `factory-hook = "factory.hooks.entry:main"` (lazy, minimal imports); `cli/app.py` untouched; `factory hook <name>` stays the slow path. `.cursor/hooks.json` → `.cursor/hooks/factory-hook.sh <name>` → venv `factory-hook`, else `uv run --project scripts/factory factory hook <name>` (not timed). Tests: the entry imports none of `typer`/`click`/`rich`/`httpx`/`factory.cli`/other slices' packages (subprocess check). Warm in-process budget 150 ms per hook, offline, with response and exit equal to `factory hook <name>`. The wrapper is exercised with fake executables (venv present → venv script with the hook name and stdin; venv absent → `uv run --project scripts/factory factory hook <name>`). `pyproject.toml` declares the script. The end-to-end test runs the exact `hooks.json` command through a shell from the repo root, takes the **median of 5**, and requires < 300 ms, using realistic payloads that take each hook's full path. Best-of-three is dropped. Measured here (median of 7): minimal entry (json + yaml + 3 git calls) 67 ms, including through a `sh` wrapper; full CLI 377 ms; `uv run` 371 ms; `import factory.api` alone 294 ms, so the entry must not import it |
| T-C5 | accept | orchestrator (process) | `test_gate_run.py::RecordedGates`: every registered CI gate's entrypoint is replaced by a recording stub (patched on the real module when it imports, else a stub module in `sys.modules`; `api.run_gate` resolves both at call time). `test_gate_run_calls_every_entrypoint_and_reports_what_each_returned`: `bus.immutable` and a second gate return failures and the rest pass. Requirements: every gate is called exactly once with the head sha and order id; each report outcome and the sentinel message match what that stub returned; exit 1. `test_gate_run_exit_0_only_when_every_entrypoint_passed`: all stubs pass → exit 0, every outcome `pass` |
| T-C6 | noted — strength | orchestrator (process) | Red-first shape kept: 252 Slice C tests collect and fail on `AssertionError` (0 errors, 0 xfail); the full suite is 368 failed / 237 passed (the 237 are unchanged); `ruff check` and `ruff format --check` pass |
| A2 | declined for Slice C | orchestrator (process) | `gate run --pr N` resolves the PR with the frozen `list_prs_by_head` over `wo/*` and `bus/*` heads and matches the number. See Later |
| Cursor output visibility | accept | orchestrator (process) | `owned-path-warn` moves to `postToolUse` with a matcher that hits `Write` and not `Read`/`Shell`/`Grep`/`Task`, and returns `additional_context`. It is not registered on `afterFileEdit`. The Cursor hooks docs (checked 2026-10-04) say `stop` supports `followup_message`, which Cursor "will automatically submit … as the next user message" (`loop_limit`, default 5), so `decision-in-chat` keeps it. `contracts/hooks.md` and T057 are amended |

**Owned paths (amend-01).** Widened by `scripts/factory/pyproject.toml` (the `factory-hook` line only; Slice A adds `pyjwt` to the same file), `scripts/factory/uv.lock`, `specs/001-factory-v2/contracts/hooks.md` and the T057 wording in `tasks.md`. **One path beyond the orchestrator's list:** the A1 wrapper needs a file, so `.cursor/hooks/factory-hook.sh` is included. If the orchestrator vetoes it, the fallback can be an inline `sh` expression in each `hooks.json` command, and only `HOOK_COMMAND`/`WRAPPER` in the tests change.

Test-shape choices a round-2 reviewer may debate (none changes a frozen CP0 interface): the 150 ms warm budget; the board-step ordering rule (before the gate step, or `always()`); the gate step's "no `if:`" rule; hooks resolving the repository from `workspace_roots[0]`; and `shell-guard` tracking `cd` within a chain.

### Later

- `GitHubPort.get_pr(number)`: add only if enumerating `wo/*` and `bus/*` heads becomes material (profiling or portability).

## Round 2 review

Reviewed `wo/wo-20261004-factory-slice-c` at `e7e57b8f6abcb2e5eccec67e3a70997bcafc609e`.

### Verdict

**Verdict: reject — one product Blocker and two process Debates remain.**

T-C1, T-C2, T-C3, and T-C5 are resolved by executable assertions. T-C4's end-to-end oracle is now materially better and has enough measured headroom, but the extra 150 ms warm assertion is an unapproved stricter budget. More importantly, the current Cursor documentation confirms that neither `subagentStart` nor `preToolUse` delivers its warning fields when permission is `allow`; therefore the always-allow spawn guard cannot satisfy FR-008's visible in-editor warning. The expected red counts, lint, formatting, schema, and frozen-file checks reproduce.

### Round-one resolution check

| Round-one finding | Round-2 judgment |
|-------------------|------------------|
| T-C1 workflow no-op oracle | **Resolved.** The parser substitutes the PR expression, tokenizes shell commands/operators, rejects the supplied echo/comment/string/error-swallowing controls, requires one executable gate command, and separately proves a real summary redirect/append. The board-before-gate or `always()` rule correctly keeps the summary available on red PRs. |
| T-C2 registry fallback | **Resolved.** Missing, deleted, malformed, and CLI-missing registries block and name the canonical path; positive fixtures carry a head registry. |
| T-C3 shell bypasses | **Resolved.** Thirty destination-main forms, wrappers, option prefixes, nested shells, branch-sensitive `-C`/`cd`, and nearby allowed controls make a spelling-list implementation materially harder. |
| T-C4 hook latency | **Partly resolved.** The lightweight script, wrapper behavior, import ban, CLI parity, and exact-command median-of-five test are sound. The measured 67 ms median gives the 300 ms end-to-end check useful margin. The independent 150 ms warm limit is stricter than the approved contract (T-C2-2). |
| T-C5 synthesized all-gates report | **Resolved.** Recording stubs prove every non-hook registry entrypoint is called exactly once with the expected head/order, two distinct failures and messages reach the report, any failure yields exit 1, and all-pass yields exit 0. |

### Findings

| ID | Severity | Tag | Lens | Locus | Finding | Suggested resolution |
|----|----------|-----|------|-------|---------|----------------------|
| T-C2-1 | Blocker | product | Lock fidelity / hook visibility | `contracts/hooks.md` spawn-guard row and Visibility; `test_hooks.py` spawn tests; FR-008 | Official Cursor docs say `subagentStart.user_message` is shown only when denied. `preToolUse` does match `Task`, but its `user_message` and `agent_message` are likewise delivered only when denied; `ask` is accepted by schema but not enforced. Therefore the candidate `preToolUse` hook returning `permission: allow` plus `agent_message` remains invisible and cannot satisfy “in-editor launches beyond the cap MUST be warned about.” The current tests prove only that our JSON contains a string. | **product:** Governor chooses: (A) restore denial/confirmation for unclaimed or over-cap Task launches, making the documented denial message visible; or (B) amend FR-008/catalog/contract to say advisory events are logged in the Hooks channel rather than visibly warned. No documented pre-spawn event provides a visible non-denying warning. |
| T-C2-2 | Debate | process | Over-constraint / performance | `test_hook_entry_is_offline_warm_fast_and_matches_the_cli`; `WARM_BUDGET_SECONDS = 0.15` | The approved letter is <300 ms end to end. A conforming implementation taking 170 ms warm and 230 ms end to end fails this extra 150 ms assertion despite meeting the contract. The exact-command median-of-five test already guards the real product budget, while the import ban and CLI parity guard architecture and behavior. | **process:** Remove the 150 ms hard assertion or make it diagnostic. If headroom is desired as policy, record it as an explicit contract amendment rather than a hidden tighter gate. Keep the 300 ms median-of-five test. |
| T-C2-3 | Debate | process | Missing mutation path / matcher fidelity | `test_live_owned_path_warn_matches_write_tools_only`; amended hooks contract | The official generic matcher vocabulary includes both `Write` and `Delete`; there is no documented `StrReplace` tool name. Matching only `Write` leaves agent file deletions outside owned paths unwarned. Shell edits remain outside this advisory hook's reliable path extraction and are appropriately left to the authoritative CI twin. | **process:** Register and test an anchored `Write|Delete` matcher, with payload/path handling for both official tool types. Do not invent undocumented `StrReplace` names; add new names only when Cursor documents or emits them. |
| T-C2-4 | Nit | process | Over-constraint | `test_workflow_gate_run_on_the_pr_is_not_allowed_to_fail` | Rejecting every `if:` is stricter than necessary: `if: always()` still executes the exact authoritative command. This is low impact because the intended workflow needs no condition, but it is representation coupling rather than command semantics. | Accept for this bootstrap workflow, or narrow the assertion to reject conditions that can skip a pull-request gate. The board execution rule should remain. |
| T-C2-5 | Nit | process | Strength | Round-1 remediation set and red-first record | Strength: the workflow controls are adversarial, registry tests fail closed, shell tests distinguish destination refs from harmless text, and gate stubs prove invocation rather than report synthesis. All 252 Slice C tests remain intentionally red without collection errors or xfails, and frozen CP0 files remain unchanged. | Preserve these assertions while resolving T-C2-1 through T-C2-3. |

### Worker deviations

- **(a) `.cursor/hooks/factory-hook.sh` — accept.** Amendment 01 expressly owns the file. A tiny executable wrapper is clearer and more testable than four duplicated inline shell expressions. The venv-first path preserves the 300 ms target; the `uv run` fallback is a sensible degraded path when setup is absent and its exemption is explicit in the amended contract.
- **(b) workflow rules — mostly accept.** Publishing the board before a potentially failing gate, or under `always()`/`!cancelled()`, is necessary for “same board in the job summary on every PR.” Requiring the gate command's status to remain the step status is also correct. The blanket no-`if:` rule is unnecessarily broad (T-C2-4), but not a blocker.
- **(c) `postToolUse` owned-path warning — accept the event/output, widen the matcher.** `additional_context` is the documented visible post-success channel. Cursor documents `Write` and `Delete`, not `StrReplace`; test both official mutation tools. This remains advisory—repository-side `diff-within-owned-paths` is authoritative.

### Spawn-guard documentation answer and recommended test

The official page `https://cursor.com/docs/agent/hooks` currently states:

- `preToolUse` fires for all tools, including `Task`, and a matcher may select `Task`.
- `preToolUse.user_message` is “shown to the user when the action is denied.”
- `preToolUse.agent_message` is “fed back to the agent when the action is denied.”
- `permission: ask` is accepted by schema but “not enforced for preToolUse today.”
- `subagentStart.user_message` is shown when the subagent is denied; `ask` is unsupported and treated as deny.

So the orchestrator's candidate `preToolUse` allow-plus-`agent_message` fix is not supported by the documented delivery semantics. `postToolUse` can inject `additional_context` for `Task`, but it runs after the tool result—after the subagent finishes—not as a launch warning.

After the governor chooses T-C2-1:

1. **If denial is restored:** add a `preToolUse` or `subagentStart` test with an over-cap/unclaimed Task payload; require `permission: deny`, exit 2, and a nonempty documented denial message. Keep positive claimed/under-cap cases `allow`. The live registration test must prove the exact `Task` matcher.
2. **If log-only advisory is accepted:** keep the current allow response test, rename it so it does not claim visibility, and amend FR-008 plus the catalog evidence to “logged in Hooks output.” Do not add a preToolUse `agent_message` assertion.

There is no documented event that delivers a visible warning before spawn while still allowing that spawn.

### Fresh adversarial pass

The strongest still-green wrong behavior is an always-allow spawn hook that emits an ignored `user_message`; every current hook unit test passes while the mandated warning is invisible. Separately, a Write-only matcher permits an agent Delete operation outside owned paths without advisory context. On the over-constraint side, a 170 ms warm hook with a 230 ms end-to-end command is contract-conforming but fails the private 150 ms threshold.

No new gap was found in gate invocation, override semantics, concurrency replay, verdict isolation, immutable bus behavior, or workflow no-op detection.

### Questions for the human

1. Cursor provides no documented visible, non-denying pre-spawn warning. Should over-cap/unclaimed Task launches be denied with a visible message, or should FR-008 be amended to require only a Hooks-channel audit log? Recommend denial: it restores the original safety outcome and makes the hook behavior testable.

### Verification record

| Check | Result |
|-------|--------|
| Reviewed head | `e7e57b8f6abcb2e5eccec67e3a70997bcafc609e` |
| Official Cursor docs | Fetched `https://cursor.com/docs/agent/hooks`; `Task` matcher confirmed; allow-plus-message visibility not supported |
| Locked sync | PASS — 25 locked packages audited under Nix |
| Slice C focused suite | Expected RED — **252 failed, 0 passed** in 67.36 s; no collection errors or xfails |
| Full suite | Expected RED — **368 failed, 237 passed** in 94.22 s; no collection errors or xfails |
| `nix develop ../.. -c uv run ruff check .` | PASS |
| `nix develop ../.. -c uv run ruff format --check .` | PASS — 43 files formatted |
| `factory check schema` before reviewer verdict | PASS on the worker head per handoff; rerun with verdict-02 below |
| Frozen CP0 files | PASS — no changes to `api.py`, `bus/` package, `config/`, `cli/app.py`, `cli/exit_codes.py`, `gates/registry.py`, or existing `tests/fixtures/` |
| Changed paths | PASS under packet + amendment-01 ownership |

## Triage (round 2)

Recorded 2026-10-04. T-C2-1 is a product Blocker, locked by the governor (option B, log-only); the rest are process findings adjudicated by the orchestrator. Bus: `wo-20261004-factory-slice-c.verdict-02` (the round 2 review) and `.amend-02` (this triage plus the owned-path widening). Test and doc changes: `4bc0207`.

| ID | Disposition | Decided by | Resolution |
|----|-------------|------------|------------|
| T-C2-1 | **locked — option B (log-only)** | governor (product), 2026-10-04 | `spawn-guard` allows every launch. When the launch is unclaimed, or when the active count is at or over the cap, it writes an advisory that Cursor records only in the Hooks output channel: logged, not shown. Enforcement stays authoritative in `factory claim` (the 4th claim is refused) and in CI (no merge without a valid claim). Tests: the allow-response tests stay, renamed so they claim nothing about visibility (`test_spawn_guard_allows_and_logs_…`, `…_allows_without_log_…`), and the assertion message says the hook is log-only. No `preToolUse` `agent_message` assertion is added. Docs: the FR-008 line in `spec.md` now reads "logged by an advisory hook (Hooks output channel; Cursor shows hook messages only on denial)", followed by "(Governor 2026-10-04: log-only, no visible warning.)". The `handoff.concurrency_cap` shall cell in `acceptance.md` reads "editor launch logged (advisory)", with a matching 2026-10-04 change-log row. In `contracts/hooks.md`, the spawn-guard row and the Visibility note say "logged in Hooks output, not shown" |
| T-C2-2 | accept | orchestrator (process) | The hard 150 ms warm assertion and `WARM_BUDGET_SECONDS` are removed. `test_hook_entry_is_offline_warm_fast_and_matches_the_cli` becomes `test_hook_entry_is_offline_and_matches_the_cli`, which checks offline operation, the response, the exit code and the visible fields against `factory hook <name>`. The 300 ms end-to-end median-of-five test of the exact `hooks.json` command, the import ban and CLI parity stay |
| T-C2-3 | accept | orchestrator (process) | `owned-path-warn` is registered on `postToolUse` with an anchored `Write\|Delete` matcher. The quiet-inside and warn-outside owned-path tests are parametrized over `Write` (`tool_input` `{file_path, content}`) and `Delete` (`tool_input` `{file_path}`, `tool_output` `{file_path, deleted: true}`). `test_owned_path_quiet_for_non_mutating_tools` checks that `Read` stays quiet. `test_live_owned_path_warn_matches_exactly_write_and_delete` requires the live matcher, under JS-style `re.search`, to hit `Write` and `Delete` but not `Read`, `Shell`, `Grep`, `Task`, `WriteShellStdin`, `MCP:Write` or `MCP:Delete`. No undocumented tool names (for example `StrReplace`) are added. Edits made through the shell remain the job of the CI twin, `diff-within-owned-paths` |
| T-C2-4 | accept the narrowing | orchestrator (process) | `test_workflow_gate_run_on_the_pr_is_not_allowed_to_fail` now rejects only gate-step conditions that can skip the step on a PR. No condition, `always()` and `!cancelled()` (bare or wrapped in `${{ }}`) are allowed. Its oracle self-checks reject `false`, `${{ false }}`, event-name filters, `failure()`, `always() && false` and `!cancelled() && github.actor == 'governor'`. The board-before-gate (or `always()`/`!cancelled()`) rule, the no-`continue-on-error` rule and the exact single-command rule are unchanged |
| T-C2-5 | noted — strength | orchestrator (process) | No action. Red-first shape kept: 254 Slice C tests (252 + the two `Delete` parametrizations) collect and fail on `AssertionError`, with 0 errors and 0 xfails. The full suite is 370 failed / 237 passed (the 237 are unchanged). The CI selector `-m "not contract and not seed"` gives 227 failed / 224 passed. `ruff check` and `ruff format --check` pass |
| Stale doc | fixed | orchestrator (process) | The `research.md` "Editor hooks (FR-022)" decision block now describes the amended design. The `factory-hook` console script runs through `.cursor/hooks/factory-hook.sh`: venv first, with `uv run` as the fallback. `spawn-guard` on `subagentStart` is log-only, `owned-path-warn` uses `postToolUse` with `Write\|Delete`, and `decision-in-chat` uses `stop` → `followup_message` |

**Owned paths (amend-02).** Adds `specs/001-factory-v2/spec.md` (only the FR-008 line) and `specs/001-factory-v2/research.md` (only the hooks decision block). It widens the line scope of the already-owned `acceptance.md` by the `handoff.concurrency_cap` shall cell and one change-log row; Slice B edits the header lines and Slice A the evidence cells. The T057 wording in `tasks.md` (owned since amend-01) now names the `Write|Delete` matcher and calls spawn-guard log-only.
