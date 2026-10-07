# T* review packet: factory App token wiring (T036b), red tests

Order: `bus/orders/wo-20261007-factory-app-token/order.yaml`. Task: T036b in `specs/001-factory-v2/tasks.md`.
Phase 1 of 2: red tests only, no `src/` edits. Reviewer brief: `docs/agent-os/TEST_REVIEW_PROMPT.md`; findings go to `specs/001-factory-v2/TEST_REVIEW_APP_TOKEN.md`.

## Orchestrator rulings

2026-10-07, on the "verified mode without App credentials" question (verbatim):

> "Credentials follow the role, never a silent fallback. The trusted CI gate path (`factory gate run` / `factory gate evidence`, which posts factory/* statuses under D8) always uses the env GITHUB_TOKEN, in either identity mode, and never mints. Every agent-facing path (order, claim, release, handoff, pr, bus pr, and any push) in identity.mode = "verified" uses the App installation token; if App credentials are missing or minting fails it fails closed with the external-error exit code and does not fall back to GITHUB_TOKEN or ambient git credentials. Recorded mode is unchanged."

> "Also: a 404 on the installation lookup is a mint failure (same fail-closed path, exit 4)."

## What the tests pin

| Test | Pins |
|------|------|
| `tests/unit/test_github_adapter.py::test_credentials_follow_the_role_ci_keeps_github_token_agents_use_the_app` | Per the ruling. The CI adapter `build_github` (what `gate run` / `gate evidence` load through `DEPS.github`) keeps `GITHUB_TOKEN` in both modes and never mints, even with App credentials set. The agent adapter `build_agent_github(settings, env)` keeps `GITHUB_TOKEN` in recorded mode and sends the installation token in verified mode. In verified mode without App credentials it raises `GitHubError` or `AppTokenError` before sending any request: no request carries `GITHUB_TOKEN` |
| `…::test_verified_mode_finds_the_installation_from_the_repository_with_an_app_jwt` | Agent adapter: the installation id comes from `GET /repos/{owner}/{repo}/installation`, then `POST /app/installations/{id}/access_tokens`. Both carry an RS256 App JWT (`iss` = App id) that verifies against the throwaway public key. The id comes from the response (424242), not from config |
| `…::test_installation_token_is_reused_while_fresh_and_refreshed_before_expiry` | Agent adapter: a 1-hour token is reused; a token with 2 minutes left is replaced before the next call (refresh margin over 2 min, under 1 h) |
| `…::test_failing_api_call_keeps_the_installation_token_out_of_errors_and_logs` | Agent adapter: a 403 raises `GitHubError`; the token is absent from `str`/`repr`/the formatted exception chain, `repr(port)`, logs (DEBUG) and captured output |
| `tests/unit/test_identity.py::test_installation_token_repr_and_str_hide_the_token` | `InstallationToken`'s `repr`/`str`/format show no token value |
| `tests/contract/test_app_token_e2e.py::test_push_runs_as_the_app_only_in_verified_mode_and_leaves_no_token_behind` | `factory claim` end to end. Recorded mode pushes with ambient git credentials and never mints. Verified mode pushes as `x-access-token:<installation token>`, ahead of an ambient (Codespaces-style) credential helper, and no REST request carries `GITHUB_TOKEN`. No token or key line in any file under the test root (repo `.git/config`, origin, HOME, credential files, the `GIT_TRACE` command trace, `TMPDIR`), in history, `git config --list`, CLI output or logs |
| `…::test_verified_push_without_an_app_token_fails_closed_and_keeps_secrets_out[mint-refused \| app-not-installed \| no-app-credentials]` | Per the ruling: in verified mode, a mint answered 401, an installation lookup answered 404, or missing App credentials all give exit 4 (external). There is no push with ambient git credentials, no REST request with `GITHUB_TOKEN`, and neither the App JWT nor the key appears in output, logs or files |
| `…::test_refused_push_keeps_the_installation_token_out_of_the_error` | Origin answers 403 after the App authenticated: exit 4; the token is absent from output (git's stderr included), logs and files. This catches token-in-URL designs |

Harness: `origin` is served over smart HTTP by `git http-backend` behind a local `127.0.0.1` server that requires Basic credentials for receive-pack only (fetches are open). `RecordedApp` answers the App endpoints from `tests/fixtures/github_recorded/` (new file: `repo_installation.json`; it reuses `app_access_token.json` with `expires_at` re-based to "now + lifetime", and can answer the lookup with 404). Other REST paths are answered from the existing recordings, so `claim`'s reads work whether they reach `FakeGitHub` or a real agent adapter. The key is generated in the test (`cryptography`). The process environment is isolated: `GIT_CONFIG_GLOBAL` points at a decoy config, system config is off, prompts are off, proxies are cleared.

## Red output (full suite, head of this branch)

`10 failed, 1056 passed, 7 xfailed` (the 7 are the known strict T069/T081 xfails). Every failure is an assertion:
- REST (4 tests): `factory.github.rest must export build_agent_github(settings, env)`. The CI legs of the role test pass first (`build_github` already keeps `GITHUB_TOKEN`). Against the first-round entry point (`build_github`), the same assertions also failed on behaviour: the env token was sent where the installation token was expected, and no App requests were made.
- e2e push: the verified push presented `('governor', 'ghp_ambient_governor_token')`, not `x-access-token`.
- e2e fail-closed (3 nodes): the claim exits 0 because it pushed with ambient credentials.
- e2e refused push: the App credential was never presented.
- repr: `['repr', 'str', 'format']` all show the token (dataclass default repr).

The recorded-mode legs pass today, which shows the harness works. A throwaway check (not committed) confirmed the e2e push test can pass: a helper list reset plus an env-fed helper pushes as the App and leaves no trace on disk.

`ruff check` and `ruff format --check` pass.

## Design choice: installation id

**`GET /repos/{owner}/{repo}/installation` with the App JWT; no config field.** `owner/repo` is already `settings.github.repository`. The lookup needs no typed-config change (CP0-frozen settings stay as they are) and no extra value for the governor to copy at T065, and it cannot drift from the installation. It costs one JWT-authenticated GET per process; the implementation may cache it. A 404 on the lookup is a mint failure (ruling).

## Constraints the tests put on the implementation

- **Role split.** `build_github` stays the CI adapter (it is what `DEPS.github` loads for every command). The new `build_agent_github` in `rest.py` is the agent adapter. **Risk:** CLI commands in `cli/` (not owned; `DEPS` frozen at CP0) all call `DEPS.github(settings, env)` the same way. So agent-path REST calls (`pr open`, `bus pr`, `claim`'s reads) must switch to the App role inside `orders/` without breaking `FakeGitHub` substitution in the existing contract tests. If that cannot be done within owned paths, it is an order stop condition. REST wiring of the agent CLI paths is not pinned end to end; only the push is (through `claim`).
- Pushes and fetches go through `orders/git.py` without a new `factory.api` port. `orders/` builds the token source from `Settings` + `load_env()`.
- The installation token is minted in-process: the httpx transport is patched in this process, so a helper that re-mints in a child process would hit the network and fail.
- The helper must win over ambient helpers, for example by resetting with `credential.helper=` before the factory helper.
- No token in argv: `GIT_TRACE` logs helper command lines into the scanned tree.

## Edge cases left open

1. A token written to a temp file and deleted before the scan would not be caught; only files left behind are.
2. Refresh during a long push (token expiring mid-operation), and concurrent refresh, are not pinned.
3. Helper scoping: the e2e origin is `127.0.0.1`, so a helper scoped to `github.com` would fail the test. Scoping to origin's URL passes.
4. `release`, `handoff`, `order issue`, `pr open` and `bus pr` pushes and REST calls are not each driven end to end. They share `push_or_fail`, which `claim` exercises.
