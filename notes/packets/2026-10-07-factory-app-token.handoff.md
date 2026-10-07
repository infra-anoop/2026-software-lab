# T* review packet: factory App token wiring (T036b), red tests

Order: `bus/orders/wo-20261007-factory-app-token/order.yaml`. Task: T036b in `specs/001-factory-v2/tasks.md`.
Phase 1 of 2: red tests only, no `src/` edits. Reviewer brief: `docs/agent-os/TEST_REVIEW_PROMPT.md`; findings go to `specs/001-factory-v2/TEST_REVIEW_APP_TOKEN.md`.

## What the tests pin

| Test | Pins |
|------|------|
| `tests/unit/test_github_adapter.py::test_app_installation_token_is_used_only_in_verified_mode_with_app_credentials` | REST credential by mode: recorded mode keeps `GITHUB_TOKEN` even when App credentials are set (no mint); verified mode with App credentials sends the installation token; verified mode **without** App credentials keeps `GITHUB_TOKEN` (the trusted CI job posts `factory/*` statuses with Actions' token; D8: the App has no `statuses: write`) |
| `…::test_verified_mode_finds_the_installation_from_the_repository_with_an_app_jwt` | Installation id from `GET /repos/{owner}/{repo}/installation`, then `POST /app/installations/{id}/access_tokens`; both carry an RS256 App JWT (`iss` = App id) that verifies against the throwaway public key; the id comes from the response (424242), not config |
| `…::test_installation_token_is_reused_while_fresh_and_refreshed_before_expiry` | A 1-hour token is reused across calls; a token with 2 minutes left is replaced before the next call (refresh margin over 2 min, under 1 h) |
| `…::test_failing_api_call_keeps_the_installation_token_out_of_errors_and_logs` | A 403 in verified mode raises `GitHubError`; the token is absent from `str`/`repr`/the formatted exception chain, `repr(port)`, logs (DEBUG) and captured output |
| `tests/unit/test_identity.py::test_installation_token_repr_and_str_hide_the_token` | `InstallationToken`'s `repr`/`str`/format show no token value |
| `tests/contract/test_app_token_e2e.py::test_push_runs_as_the_app_only_in_verified_mode_and_leaves_no_token_behind` | `factory claim` end to end. Recorded mode pushes with ambient git credentials and never mints. Verified mode pushes as `x-access-token:<installation token>`, ahead of an ambient (Codespaces-style) credential helper. No token or key line in any file under the test root (repo `.git/config`, origin, HOME, credential files, `GIT_TRACE` command trace, `TMPDIR`), in history, `git config --list`, CLI output or logs |
| `…::test_failing_mint_stops_the_push_and_keeps_secrets_out_of_the_error` | Verified mode with a refused mint (401): exit 4 (external), **no** push with ambient credentials as a fallback, and neither the App JWT nor the key in output, logs or files |
| `…::test_refused_push_keeps_the_installation_token_out_of_the_error` | Origin answers 403 after the App authenticated: exit 4; the token is absent from output (git's stderr included), logs and files. This catches token-in-URL designs |

Harness: `origin` is served over smart HTTP by `git http-backend` behind a local `127.0.0.1` server that requires Basic credentials for receive-pack only (fetches are open). App endpoints are answered by `RecordedApp` from `tests/fixtures/github_recorded/` (new: `repo_installation.json`; `app_access_token.json` reused, with `expires_at` moved to "now + lifetime" so the recording never goes stale). The key is generated in the test (`cryptography`). The process environment is isolated: `GIT_CONFIG_GLOBAL` points at a decoy config, system config is off, prompts are off, proxies are cleared.

## Red output (full suite, head of this branch)

`8 failed, 1056 passed, 7 xfailed` (the 7 are the known strict T069/T081 xfails). Every failure is a real assertion, not an import error:
- REST: the data requests carry `ghs_test_recorded` (env token) where the installation token is expected; there are no App requests (`[] == [GET …/installation, POST …/access_tokens]`).
- e2e push: the verified-mode push presented `('governor', 'ghp_ambient_governor_token')`, not `x-access-token`. Failing mint: the claim exits 0 because nothing was minted. Refused push: the App credential was never presented.
- repr: `['repr', 'str', 'format']` all show the token (dataclass default repr).
The recorded-mode legs pass today, which shows the harness works. A throwaway check (not committed) confirmed the e2e push test can pass: a helper list reset plus an env-fed helper pushes as the App and leaves no trace on disk.

`ruff check` and `ruff format --check` pass.

## Design choice: installation id

**`GET /repos/{owner}/{repo}/installation` with the App JWT; no config field.** `owner/repo` is already `settings.github.repository`. The lookup needs no typed-config change (CP0-frozen settings stay as they are) and no extra value for the governor to copy at T065, and it cannot drift from the installation. It costs one JWT-authenticated GET per process; the implementation may cache it. Not choosing it would mean adding `[github] app_installation_id` to `factory.toml` (allowed by the order, but unnecessary).

## Constraints the tests put on the implementation

- Pushes and fetches go through `orders/git.py` without a new `factory.api` port. `claim` gets a `FakeGitHub`, so `orders/` must build the token source itself from `Settings` + `load_env()`.
- The installation token is minted in-process: the e2e test's httpx transport is patched in this process, so a helper that re-mints in a child process would hit the network and fail.
- The helper must win over ambient helpers, for example by resetting with `credential.helper=` before the factory helper.
- No token in argv: `GIT_TRACE` logs helper command lines into the scanned tree.

## Edge cases left open (for the T* reviewer to rule on)

1. **Verified mode without App credentials falls back to `GITHUB_TOKEN` for REST.** This is pinned because of D8 and CI. It is fail-open in a Codespace whose key is missing: workers would act as the governor. Alternatives: fail closed in the Codespace, or key the fallback on something CI-specific. Pushes in that case are not pinned.
2. A REST mint failure (as opposed to a push mint failure): which error type the CLI sees (`GitHubError` → exit 4?) is not pinned.
3. Installation lookup 404 (App not installed on the repo): not pinned beyond "mint failure is external".
4. A token written to a temp file and deleted before the scan would not be caught; only files left behind are.
5. Refresh during a long push (token expiring mid-operation), and concurrent refresh, are not pinned.
6. Helper scoping: the e2e origin is `127.0.0.1`, so a helper scoped to `github.com` would fail the test. Scoping to origin's URL passes.
