# T* review — GitHub App token wiring

## A. Executive verdict

**Do not implement against these tests yet.** Round 1 reproduces the intended red state: the focused command reports 10 failed and 12 passed, all at missing behavior rather than collection failure. The tests strongly cover the `claim` push, installation lookup, 404/refused-mint exit behavior, and the direct CI/agent builders. They do not yet prove that every agent CLI call site uses the agent provider, and their leak oracle can miss credentials written transiently or exposed through unobserved credential forms.

## B. Findings

| ID | Severity | Lens | Locus | Finding | Suggested resolution |
|----|----------|------|-------|---------|----------------------|
| T-AT1 | Blocker | Lock fidelity / boundary coverage | `tests/unit/test_github_adapter.py::test_credentials_follow_the_role_ci_keeps_github_token_agents_use_the_app`; `tests/contract/test_app_token_e2e.py` | **Root-cause class: provider factories are tested without their CLI call sites.** A passing implementation can export correct `build_github` and `build_agent_github` functions, special-case `claim` pushes, but leave `pr open`, `bus pr`, `release`, `handoff`, `verdict`, other pushes, or the trusted gate commands wired to the wrong provider. Consequence: agent operations can silently use `GITHUB_TOKEN`/ambient credentials, or CI can mint as the App, violating the credential-role ruling and D8. Likelihood is high because amendment-01 exists precisely because the frozen shared provider originally made this wiring difficult. | **product** — smallest sufficient fix: add one table-driven call-site contract using distinguishable CI and agent provider spies. Exercise every GitHub-using command named by amendment-01 plus `gate run`/`gate evidence`, and assert all push entry points reach the shared verified credential path rather than ambient git credentials. |
| T-AT2 | Blocker | Secret non-disclosure | `_files_holding`; successful and failing leak assertions in `test_app_token_e2e.py`; `test_failing_api_call_keeps_the_installation_token_out_of_errors_and_logs` | **Root-cause class: the leak oracle observes final state, not secret-bearing operations, and its secret corpus is incomplete.** A green implementation may write a token to a temporary helper/file and delete it before the post-run scan, put it in a non-git child-process argument, or leak a successful App JWT or a private-key fragment other than the single selected line. The mint-failure tests also inspect CLI rendering but not `repr`/formatted traceback of the underlying exception chain. Consequence: installation tokens, App JWTs, or the long-lived private key can be exposed while the suite passes. Likelihood is material because temporary helper scripts and command-line credential injection are common implementation shortcuts. | **product** — smallest sufficient fix: install one shared credential-observation harness around the command that records filesystem write payloads (including deleted files), process argv, logs/output, and formatted exception chains; compare against installation tokens, every minted JWT, and the complete throwaway private key. Keep the existing final-tree scan as a persistence check. |
| T-AT3 | Debate | SNR / refresh semantics | `test_installation_token_is_reused_while_fresh_and_refreshed_before_expiry` | **process** — the real-clock fixture and `used[0] in {first, second}` permit a token with only two minutes left to be sent once even though the test claims a refresh margin greater than two minutes. The one-hour reuse property is only inferred from the replacement token. | Use an injected/fake clock: mint a one-hour token, prove reuse, advance to the declared refresh boundary, and prove refresh occurs before the next authenticated request. This removes timing ambiguity without prescribing an internal cache design. |
| T-AT4 | Nit | Strength | focused suite | Strength: the local smart-HTTP origin places an ambient helper ahead of the App path, so the verified `claim` test can detect a real silent fallback. Recorded mode remains exercised, installation lookup is response-derived, 404 and refused mint are pinned to exit 4, and the direct CI builder is asserted to retain `GITHUB_TOKEN` without minting. | Preserve these adversarial fixtures while closing T-AT1 and T-AT2. |

## C. Adversarial positions

1. **Position: these tests would go green while a spec lock fails** — Implement both builder functions correctly and make only `claim` use an App credential helper. Leave `pr open` and another push-producing command on `DEPS.github`/ambient git, while leaving `gate run` accidentally switchable to the agent provider. The current builder tests and `claim` end-to-end test pass, but credentials no longer follow the role. Separately, write the token to a temporary helper script, invoke it, and unlink it before return; the final filesystem scan passes.  
   **What would have to be true for the suite to be right anyway:** every named command must be mechanically forced through one already-covered provider/push path, and no implementation path may write or pass credentials before the post-run observations.

2. **Position: these tests over-constrain implementation / test the wrong layer** — The suite requires named builders, an in-process `httpx.Client`, repository installation lookup order, Basic username `x-access-token`, and a specific broad refresh interval. Most are justified by amendment-01, the recorded transport seam, GitHub's protocol, or the packet's installation-id lock. The weakest constraint is refresh timing: the test implies a margin greater than two minutes without a product-level numeric lock and uses wall-clock response rebasing.  
   **What would have to be true for the suite to be right anyway:** the packet's “over 2 minutes, under 1 hour” statement is accepted as the operative contract, and the implementation is intentionally in-process for the recorded transport.

## D. Catalog / contract coverage map

| Catalog id or contract hook | Test file / name | Can fail today? | Gap |
|-----------------------------|------------------|-----------------|-----|
| T036b credential role split | `test_credentials_follow_the_role_ci_keeps_github_token_agents_use_the_app` | yes | Builders only; CLI provider selection is not covered. |
| Amendment-01 agent command routing | no complete test | no | Agent REST and push call sites can remain on the CI/ambient path. |
| D8 CI token path | builder role test | yes | `gate run` and `gate evidence` call-site wiring is not exercised. |
| Repository installation lookup + RS256 JWT | `test_verified_mode_finds_the_installation_from_the_repository_with_an_app_jwt` | yes | Strong direct adapter coverage. |
| Refresh before expiry | `test_installation_token_is_reused_while_fresh_and_refreshed_before_expiry` | yes | Wall-clock ambiguity permits one near-expiry use. |
| Token-safe value rendering | `test_installation_token_repr_and_str_hide_the_token` | yes | Covers installation-token object only. |
| REST failure redaction | `test_failing_api_call_keeps_the_installation_token_out_of_errors_and_logs` | yes | Does not include App JWT/private key or mint-failure exception objects. |
| Verified push identity / recorded compatibility | `test_push_runs_as_the_app_only_in_verified_mode_and_leaves_no_token_behind` | yes | Covers `claim`; final-state scan misses deleted temporary files. |
| Missing credentials / mint refusal / installation 404 | parametrized fail-closed test | yes | Exit and no-fallback behavior are strong; transient/exception leak surfaces remain. |
| Refused authenticated push | `test_refused_push_keeps_the_installation_token_out_of_the_error` | yes | CLI rendering and surviving files covered. |

## E. Edit list

- `tests/contract/test_app_token_e2e.py`: add one table-driven provider/push-routing contract for all amendment-01 agent commands and both CI gate commands.
- `tests/contract/test_app_token_e2e.py`: replace final-state-only leak checking with a shared write/argv observer while retaining the final-tree scan.
- `tests/contract/test_app_token_e2e.py`: include all captured App JWTs and the complete throwaway private key in the secret corpus on successful and failing paths.
- `tests/unit/test_github_adapter.py`: inspect formatted mint-failure exception chains for JWT/private-key disclosure.
- `tests/unit/test_github_adapter.py`: drive refresh with an injected clock and assert fresh reuse followed by pre-request refresh at the boundary.

## F. Questions for the human

None. The two blockers require fidelity to already-recorded credential-role and non-disclosure rulings; they do not require a new product choice.

## Triage (orchestrator, round 1, 2026-10-07)

Reviewer text above is unchanged. T-AT1 and T-AT2 are credential-safety harm: fixed now, as suggested. Their product tag needs no governor choice, because the governor-level rule (credentials follow the role, never a silent fallback) is already set in the packet's Orchestrator rulings.

| Finding | Decision | Change |
|---------|----------|--------|
| T-AT1 (Blocker) | **Fix as suggested.** | One table-driven call-site contract with distinguishable CI and agent provider spies (`DEPS.github`, `DEPS.agent_github`). It covers every GitHub-using agent command named by amendment-01 (claim, release, handoff, pr open, verdict, bus pr) plus `gate run` and `gate evidence`. Agent commands may use only the agent provider and CI commands only the CI provider. Every push entry point goes through the verified credential path, not ambient git credentials |
| T-AT2 (Blocker) | **Fix as suggested, bounded.** | One shared observation harness for the e2e tests. It records payloads written through Python file APIs (`open`, `Path.write_*`, `os.write`, tempfile), including files deleted afterwards, every child-process argv (subprocess spawn), logs and output, and formatted exception chains (`repr` and traceback). The secret corpus is the installation token(s), every minted App JWT, and the complete throwaway private key (any 16-character window of its base64 body). The final-tree scan stays as the persistence check. Do not hook below the Python level |
| T-AT3 (Debate, process) | **Fix.** | Injected or fake clock: mint a one-hour token, prove reuse, advance to the declared refresh boundary, prove refresh before the next authenticated request |
| T-AT4 (Nit, strength) | Keep the adversarial fixtures | — |

Round 2 is the reviewer's check of these changes.

## Round 2

**Decision: Do not implement against these tests yet.** The full suite reproduced the expected red state: 11 failed, 1056 passed, and 7 expected failures, with the changed tests failing on assertions. T-AT3 is resolved; the five-minute refresh margin contradicts no spec or contract. The code-owner-review snapshot is a legitimate verified-mode fixture state because T065 flips both identity mode and that ruleset requirement. T-AT1 is substantially improved but its gate-run leg can pass without a successful CI path, and T-AT2 still permits the exact command-line credential exposure the finding required the observer to catch.

| ID | Severity | Tag | Round-2 finding | What to change |
|----|----------|-----|-----------------|----------------|
| T-AT1-R2 | Debate | process | The table requires normal exits for agent commands, but `gate run` accepts either 0 or gate failure and only asserts that the agent provider was not called. An early gate failure that never constructs the CI provider therefore satisfies this leg. `gate evidence` correctly need not construct any GitHub adapter. | Make the staged gate pass, require exit 0, and assert that `gate run` called the CI provider at least once while never calling the agent provider. |
| T-AT2-R2 | Blocker | product | **Root-cause class: incomplete Python process-spawn interception.** `CredentialObserver` wraps `subprocess.Popen` but explicitly omits `os.system` and `os.posix_spawn*`. An implementation can put the installation token directly in a git/helper command line through either standard Python API and pass every observer assertion. Consequence: the token is exposed through the process list despite a green security suite; the likelihood is material because shell-based credential helpers are a common shortcut. The declared C-extension writes, child-process file writes, and env/pipe channel are acceptable bounded gaps: the current codebase uses Python `subprocess`, the intended helper needs a non-argv transport, and final-state scanning remains. | Smallest sufficient fix: intercept `os.system`, `os.posix_spawn`, and `os.posix_spawnp` in the shared observer and apply the same secret corpus to their command/argv. No below-Python syscall tracer is required. |

T-AT3 is closed. The fake clock proves one-hour reuse and refresh before the request at five minutes remaining; the chosen margin is an implementation bound, not a contradiction of a locked numeric requirement.

## Triage (orchestrator, round 2)

Both findings accepted; round 3 is the last review round under constitution §J.

| id | Ruling | Fix required |
|----|--------|--------------|
| T-AT1-R2 (Debate, process) | Accept as written | Stage a passing gate for `gate run`, require exit 0, and assert the CI provider was called at least once and the agent provider never |
| T-AT2-R2 (Blocker) | Accept. Tagged product, but it only makes the leak check stricter and chooses no product behaviour, so the orchestrator adjudicates it | The shared observer also covers `os.system`, `os.posix_spawn` and `os.posix_spawnp`, with the same secret corpus applied to their command or argv. Preferred mechanism: one `sys.addaudithook` routed to the active observer (events `os.system`, `os.posix_spawn`, `os.exec`, `os.spawn`, `subprocess.Popen`), which also covers the `os.exec*` and `os.spawn*` families. A throwaway check shows each API is caught |

The bounded gaps the reviewer accepted (C-level writes, child-process file writes, env and pipe transport to the credential helper) stay as recorded in the handoff packet.

## Round 3

**Decision: Do not implement against these tests yet.** The full suite reproduced the stated red result: 11 failed, 1056 passed, and 7 expected failures, all 11 at assertions. T-AT1-R2 is resolved: every staged command exits 0, the staged verdict PR genuinely passes `diff-within-owned-paths`, `gate run` calls the CI provider, and it does not appear among the call-site test's 13 intended role/credential failures. T-AT2-R2 is behaviorally covered today, but the `os.spawn*` coverage rests on an optional private CPython hook with no committed assertion that the hook remains active.

| ID | Severity | Tag | Final-round finding | Disposition |
|----|----------|-----|---------------------|-------------|
| T-AT2-R3 | Blocker | product | **Harm statement: credential exposure. Root-cause class: the security observer's private-hook path has no executable self-check.** On Linux, `os.spawn*` is observed only by wrapping private `os._spawnvef`; the harness silently skips that wrapper when the symbol is absent, and no committed test invokes `os.spawn*` or proves the wrapper recorded a canary. A CPython/Nix change can therefore let an implementation put the installation token in an `os.spawn*` argv while this suite stays green. The current pinned Python exposes `_spawnvef(mode, file, args, env, func)`, so the wrapper works now, but the uncommitted throwaway check is not regression evidence. | **Bug — must still be fixed.** Add one committed, parametrized observer bite test that passes synthetic secret canaries through a representative audit-hook spawn and through `os.spawn*`, then asserts `CredentialObserver.leaks()` reports them. On this supported Linux test environment, fail explicitly if the private spawn hook is unavailable or not hit. This is the smallest sufficient fix; no syscall tracer is required. |

T-AT1-R2 is closed. No other final-round finding meets the constitution §J harm bar.

## Triage (orchestrator, round 3)

Round 3 was the last T* round (constitution §J). Its one finding is a bug, so it is fixed in this order.

| id | Ruling | Fix required |
|----|--------|--------------|
| T-AT2-R3 (Blocker, bug) | Accept. It only makes the leak check stricter and chooses no product behaviour, so the orchestrator adjudicates it | One committed, parametrized observer self-test: synthetic secret canaries passed through a representative audit-hook spawn (`os.system` or `os.posix_spawn`) and through `os.spawnv`, asserting `CredentialObserver.leaks()` reports each one. On Linux it fails explicitly if `os._spawnvef` is missing or the wrapper is not hit |

There is no fourth T* round. The orchestrator checks that the self-test exists and fails when the wrapper is disabled, and the PR reviewer judges it with the implementation.
