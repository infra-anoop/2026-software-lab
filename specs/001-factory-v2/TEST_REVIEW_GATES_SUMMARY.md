# T* review — `factory/gates` summary (round 1)

## A. Executive verdict

**Changes-needed.** Round 1 uses the normal bar. The focused suite is honestly red
(14 failed, 76 passed), and it strongly pins installed-registry selection, status order,
override success, ruleset replacement, and source pinning. It does not pin the decided
meaning of explicit `--gate` selection, and its missing-gate oracle is disconnected from
the CLI path that posts the trusted summary. Implementation should not start against this
test set until T-GS1 and T-GS2 are resolved.

## B. Findings

| ID | Severity | Tag | Lens | Locus | Finding | Suggested resolution |
|----|----------|-----|------|-------|---------|----------------------|
| T-GS1 | Blocker | product | Lock fidelity | `test_gate_run_pr_posts_one_status_per_gate`; `PLAN_DELTA.md` Round 5 | **Root-cause class: boundary case not exercised.** The only no-summary case selects two gates. An implementation that posts `factory/gates` whenever the explicit selection happens to contain every installed CI gate passes the suite, but contradicts the orchestrator ruling that any explicit `--gate` list is a subset run. **Consequence:** an operator's explicit-list diagnostic run can satisfy the required merge context even though the locked full-run mode was not invoked. **Likelihood:** medium; comparing selected count/set with the registry is a plausible implementation shortcut. | Smallest fix: one contract regression invoking `--gate` once for every installed CI gate and asserting the exact posted contexts exclude `factory/gates`. |
| T-GS2 | Blocker | product | Test seam / fail closed | `test_summary_fails_naming_a_registered_ci_gate_that_did_not_run`; CLI summary tests | **Root-cause class: oracle disconnected from posting path.** The missing-gate assertion calls a newly invented pure helper directly, but no contract test makes the CLI post a summary from a report missing an installed gate. An implementation can provide a correct but unused `summary_status`, while the CLI independently posts success whenever all entries present in its report passed. **Consequence:** a runner/report regression that omits a gate can produce a trusted green required context despite the governor's “every CI gate ... ran in that invocation” lock. **Likelihood:** low-to-medium; the current runner emits one entry per selected gate, but this summary exists specifically to fail closed if that invariant regresses. | Smallest fix: one CLI-level regression that substitutes a run report omitting an installed CI gate, then requires the posted `factory/gates` status to be `failure` naming that gate. Test behavior, not whether a particular helper was called. |
| T-GS3 | Should | process | Over-specification | `tests/unit/gates/test_runner.py` | The tests require the exact new symbol and signature `factory.gates.runner.summary_status(report, gates)`, although the governor lock and T107 specify observable CLI/status behavior, not this internal API. A correct inline or differently factored implementation is rejected. This is especially avoidable because the helper test still does not prove the CLI uses the helper. | Replace the exact-symbol unit seam with the behavior-level missing-report-entry contract regression from T-GS2; retain a pure-function test only if the implementation independently chooses that seam. |
| T-GS4 | Nit | process | Strength | focused suite | Strength: all 14 expected failures are assertion failures at the intended missing behavior, with no collection error. The contract cases exercise the real CLI and status adapter, prove the summary is last, distinguish installed from head registry, and cover pass/fail/override outcomes; the ruleset cases pin `factory/gates` to `github.actions_app_id` and make the summary-only target pass once implemented. | Keep these controls while resolving T-GS1–T-GS3. |

## C. Adversarial positions

1. **Position: these tests would go green while a lock fails.** Implement
   `summary_status` correctly but never call it. In the CLI, post success when all report
   entries are `pass` or `overridden`, and post a summary whenever the selected gate set
   equals the installed set. Every current test can pass: ordinary full runs contain all
   entries, two selected gates post no summary, and the direct helper reports a missing
   gate correctly. Yet an omitted report entry produces a false green, and an explicit
   full `--gate` list posts a forbidden summary. **What would have to be true for the
   suite to be right anyway:** review would have to guarantee helper wiring and define
   “subset” by set inequality rather than by presence of `--gate`, contrary to the ruling.

2. **Position: these tests over-constrain implementation / test the wrong layer.**
   `summary_status(report, gates)` is an implementation-shaped API created only by the
   tests. The lock requires one correctly computed commit status; it does not require a
   reusable runner helper, that name, or that tuple signature. A correct implementation
   local to `gate_run`, or one based on a typed summary object, fails before behavior is
   observed. **What would have to be true for the suite to be right anyway:** the helper
   must be an approved plan contract rather than an author-selected seam; no such
   contract appears in Round 5 or T107.

## D. Coverage map

| Lock / contract hook | Test file / name | Can fail today? | Gap |
|----------------------|------------------|-----------------|-----|
| Full no-`--gate` PR run posts `factory/gates` on head | `test_gate_run_pr_posts_gates_summary_success_when_every_gate_passes` | yes | None. |
| Every installed CI gate ran; missing gate fails | `test_summary_fails_naming_a_registered_ci_gate_that_did_not_run` | yes, unit seam only | CLI can bypass the oracle (T-GS2). |
| Installed registry, not head registry | `test_gate_run_pr_gates_summary_follows_the_installed_registry_not_the_head` | yes | None. |
| Pass/overridden are success; failure names failing gates | three summary contract cases | yes | Covered for two failures and one override. |
| Summary follows every per-gate status | `test_gate_run_pr_posts_gates_summary_after_every_gate_status` | yes | None; accepted crash-before-summary behavior follows from ordering. |
| Any explicit `--gate` selection posts no summary | `test_gate_run_pr_posts_one_status_per_gate` | partly | Explicit list containing every installed gate is untested (T-GS1). |
| Moved head posts nothing | `test_moved_head_posts_nothing_and_exits_0` | yes | Existing trust-boundary coverage. |
| Ruleset requires summary, not per-gate contexts | expected-ruleset and missing-summary cases | yes | Correct summary-only ruleset is the passing target. |
| `factory/gates` pinned to Actions app | unpinned / other-app / configured-app cases | yes | None. |

## E. Edit list

- `scripts/factory/tests/contract/test_gate_run.py`: add an explicit all-installed-`--gate`
  case asserting no `factory/gates` status.
- `scripts/factory/tests/contract/test_gate_run.py`: add one CLI-level omitted-report-entry
  case requiring a failing summary that names the missing installed gate.
- `scripts/factory/tests/unit/gates/test_runner.py`: remove the mandatory exact helper seam,
  or retain it only after implementation chooses that factoring.

## F. Questions for the human

None. The orchestrator already ruled that every explicit `--gate` invocation is a subset
run, including an explicit full list.

## Round 2

### Verdict

**Accept.** T-GS1 through T-GS3 are resolved without introducing a new problem. The
revised focused suite is honestly red: **15 failed, 76 passed**, with all eight summary
contract cases failing at the absent `factory/gates` behavior and the seven snapshot
cases failing at the old per-gate requirement. No T-GS5 finding is warranted.

### Finding dispositions

| Finding | Disposition | Verification |
|---------|-------------|--------------|
| T-GS1 | Resolved | `test_gate_run_pr_explicit_gate_list_posts_no_summary_even_when_it_names_every_gate` first proves the no-`--gate` path must post a success summary, then clears recorded statuses and invokes the same CLI with every installed id supplied via `--gate`; it requires exactly the per-gate contexts and no summary. This distinguishes mode selection from set equality. |
| T-GS2 | Resolved | `test_gate_run_pr_gates_summary_fails_when_the_report_omits_an_installed_gate` wraps the real runner and patches the name actually imported by the CLI. The red run proves the seam bit: `factory/bus.schema` was absent while every other per-gate status was posted, and the test then failed only because the not-yet-implemented summary was absent. A green implementation must post failure naming the omitted installed gate from the altered report. |
| T-GS3 | Resolved | The mandatory `summary_status(report, gates)` symbol test was deleted. Missing-gate and description-limit behavior now run through the CLI/status adapter, so inline or differently factored correct implementations remain valid. |
| T-GS4 | Retained strength | Existing CLI, ordering, installed-registry, outcome, ruleset and app-pinning controls remain intact. |

### New-problem check

No new finding. In particular, the T-GS2 monkeypatch is not a dead seam: the observed
status list omitted `factory/bus.schema`, which can only happen after the wrapped report
returned to the real CLI posting loop. Patching both the runner module and the CLI's
imported alias supports either existing call shape without requiring the implementation
to add a test-only branch.
