# PR implementation review — GitHub App token wiring

Decision: **reject**

| id | severity | tag | location | issue | fix |
|---|---|---|---|---|---|
| R-AT1 | Blocker | product | `scripts/factory/src/factory/identity/app_token.py` (`find_installation_id`, `mint_installation_token`, `InstallationTokenSource.token`); `scripts/factory/src/factory/cli/app.py::run` | Successful HTTP responses with malformed JSON or missing/invalid fields escape as `KeyError`, JSON decode errors, or `ValueError`, rather than `AppTokenError`. The CLI does not map those exceptions to external exit 4. An invalid `expires_at` value is also copied into `ValueError` text, so a hostile response can place token-shaped content in the exception chain. This violates the fail-closed mint contract and the exception non-disclosure ruling. A probe against a 201 `{}` mint response raised `KeyError('expires_at')`. | Validate lookup and mint response decoding inside the App-token boundary. Convert all response-shape and timestamp errors to a fixed, secret-free `AppTokenError` using `from None`, so REST and git paths both produce exit 4. Add direct and CLI tests for malformed lookup and mint responses, including token-shaped malformed fields. |

## Judgments

- The three handoff deviations comply with the rulings and stop conditions: `git_environment()` is plumbing rather than typed configuration, `raising=False` is confined to the cross-revision fixture, and verified fetch correctly uses the App role.
- Two token mints in verified `claim`, `pr open`, and `bus pr` are acceptable. REST and git own separate in-process sources because the approved provider interface does not expose a shared source; this costs one extra installation-token mint but does not weaken role separation, refresh behavior, or fail-closed handling.
- Both overrides state true reasons. The observer self-test exercises the real observer and its `os.spawnv` assertion reaches the `_spawnvef` wrapper; the deferral-word hit is reviewer record text rather than postponed work.
- The green tests exercise production source: direct adapter tests cover lookup, mint, cache, refresh, and REST redaction; command tests run production git transport and credential helper behavior. Provider spies and recorded HTTP fixtures replace boundaries without bypassing the source under review.
- The diff is inside amendment-01 owned paths, `tasks.md` is unchanged, `cli/common.py` changes only add the approved agent provider, typed configuration is unchanged, and identity mode is not flipped.
- Full suite: 1070 passed, 7 xfailed. The requested gate run reported the two documented gate findings plus the expected review-branch-name `pr-links-order` failure; this invocation did not apply the committed overrides.

## Triage (orchestrator, round 1)

| id | Ruling | Fix required |
|----|--------|--------------|
| R-AT1 (Blocker) | Accept. Tagged product, but it applies the locked fail-closed and no-disclosure rulings and chooses no new behaviour, so the orchestrator adjudicates it | Red tests first: direct and CLI cases for a malformed installation lookup and a malformed mint (empty body, invalid JSON, missing or wrong-typed `token`/`expires_at`/`id`, and a token-shaped invalid `expires_at`), each expecting exit 4 and no response content in output, logs or the exception chain. Then convert every response-shape and timestamp error inside the App-token boundary to a fixed, secret-free `AppTokenError` raised `from None` |

The reviewer's judgments on the deviations, the two-token mint and both overrides are accepted as written.
