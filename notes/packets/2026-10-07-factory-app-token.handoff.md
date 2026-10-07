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
| `…::test_installation_token_is_reused_while_fresh_and_refreshed_at_the_margin` | Agent adapter with an injected clock: a 1-hour token is reused 30 minutes in and refreshed before the next request once 5 minutes are left (round 1, T-AT3) |
| `…::test_failing_api_call_and_failing_mint_keep_secrets_out_of_errors_and_logs` | Agent adapter: a 403 raises `GitHubError`, and a refused mint raises `GitHubError`/`AppTokenError`. No installation token, App JWT or key material in `str`/`repr`/the formatted exception chain, `repr(port)`, logs (DEBUG) or captured output |
| `tests/contract/test_app_token_e2e.py::test_every_cli_call_site_uses_the_provider_and_push_credentials_of_its_role` | Round 1, T-AT1: see § Round 1 resolution |
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

1. Refresh during a long push (token expiring mid-operation), and concurrent refresh, are not pinned.
2. Helper scoping: the e2e origin is `127.0.0.1`, so a helper scoped to `github.com` would fail the test. Scoping to origin's URL passes.
3. The observer is Python-level only (triage: no hooks below that). Process spawns are covered since round 2 (see below). Still not observed: writes made by a C extension, writes made by a child process (for example `git` writing its own config or credential files mid-run; only the final-tree persistence scan sees what remains), and a token in a child's environment or on a pipe. The environment and pipes are the sanctioned channels for an env-fed helper.

## Implementation (phase 2)

Round 3 review: `specs/001-factory-v2/TEST_REVIEW_APP_TOKEN.md` (T-AT1-R2 closed; T-AT2-R3 a bug, fixed below). Commits: self-test `25d4b4b`, implementation `61c66a8`, fixture follow-up `c1ecb84`. Handoff: `bus/orders/wo-20261007-factory-app-token/handoff.yaml`.

### T-AT2-R3 observer self-test

**New** `tests/contract/test_app_token_e2e.py::test_observer_reports_secrets_in_a_spawned_command_line[os.system | os.posix_spawn | os.spawnv]`. A canary token and a key line are passed in the argv of each API. `leaks()` must report exactly one argv entry with both secrets, under that API's event (`os.spawn` for the wrapper). The `os.spawnv` node also asserts on Linux that the `os._spawnvef` wrapper was hit once (`CredentialObserver.wrapped_spawns`). The harness no longer skips silently: on Linux, a missing `os._spawnvef` fails the `observer` fixture.

Bite check (throwaway, not committed): with the wrapper not installed, the `os.spawnv` node fails (`leaks()` reported `{}`), and the other two pass. With the symbol looked up under a missing name, every node errors at setup with "os._spawnvef is missing". Both edits were reverted before the commit.

### What was built (T036b)

| Where | What |
|-------|------|
| `identity/app_token.py` | `InstallationTokenSource`: the installation comes from `GET /repos/{o}/{r}/installation` with the App JWT (cached per source), then an in-process mint; the token is reused until `REFRESH_MARGIN` (5 minutes) is left. Missing App credentials raise `AppTokenError` at construction. App HTTP errors carry the status and path only (`from None`), and a key that cannot sign gives a fixed message. `InstallationToken.token` is `repr=False` |
| `github/rest.py` | `build_agent_github(settings, env, *, clock=None)`: recorded mode is `build_github`; verified mode builds `RestGitHub` with a `token_source` asked before each request. `AppTokenError` becomes `GitHubError` both at build and per request. `build_github` stays the CI client (GITHUB_TOKEN, never mints). `RestGitHub.__repr__` names only the repository |
| `cli/common.py` | `Deps.agent_github`, default `factory.github.rest:build_agent_github` (amendment-01; nothing else changed) |
| `cli/orders.py` | `claim`, `pr open` and `bus pr` use `DEPS.agent_github`; a build failure exits 4 |
| `orders/lease.py`, `orders/review.py` | `git_token(settings)`: None in recorded mode (ambient git credentials), else an App token source. Missing credentials are `External` before any git command runs. `fetch_or_fail` / `push_or_fail` take the token as a required argument, so no call site can silently fall back; a failed mint is `External` (exit 4) |
| `orders/git.py` | With a password, `fetch` / `push` run `git -c credential.helper= -c credential.helper=<helper>`. The reset drops ambient helpers, and the helper answers `get` with `x-access-token` and the token, which it reads from `FACTORY_GIT_APP_TOKEN` in its environment. Neither argv nor `GIT_TRACE` carries the token, and nothing is written to disk. `GIT_TERMINAL_PROMPT=0` |
| `config/settings.py` | `git_environment(extra)`: the inherited environment plus `extra`, for that git child (deviation: a function, no field) |
| `tests/fixtures/cli_runner.py` | Also substitutes `DEPS.agent_github` with the same FakeGitHub (amendment-01), `raising=False` so red-first can run the head tests on base |

The gate path is untouched: `gate run` and `gate evidence` still build only `DEPS.github`.

### Results

- Full suite (`nix develop ../.. -c uv run pytest -q` from `scripts/factory`): **1070 passed, 7 xfailed** (the strict T069/T081 xfails). The 11 red T036b nodes pass with no test function edited in phase 2. `ruff check` and `ruff format --check` pass.
- `factory gate run --base origin/main --head HEAD` (at `c1ecb84`, before the handoff commit): 22 passed, 3 failed:
  - `red-first-proof`: the observer self-test passes on base, as a harness self-test must. The four e2e tests are red on base since `c1ecb84`. Needs an orchestrator ruling (handoff open question).
  - `deferral-words-need-od`: `TEST_REVIEW_APP_TOKEN.md` line 88 ("optional", reviewer text) and line 98 ("deferred", triage text) were flagged. Neither is a deferral, and the worker left other authors' record lines alone (handoff open question).
  - `verdict.reviewer-family-differs`: no handoff at head; the handoff is committed after this run.
- Rerun at `fbff904` (handoff committed): **23 passed, 2 failed** (`red-first-proof` and `deferral-words-need-od`, as above).

### Bounded behaviour not pinned by tests

- A verified `claim`, `pr open` or `bus pr` mints twice: once in the REST adapter and once in `orders/` for git. `DEPS.agent_github`'s signature cannot hand its source to `orders/`.
- A token that expires during one long git command is not refreshed mid-command (edge case 1). Each fetch or push asks the source first, so it starts with at least 5 minutes left.
- The helper is scoped to the one git command, not to a host (edge case 2).

## Round 2 resolution

Review: `specs/001-factory-v2/TEST_REVIEW_APP_TOKEN.md` (round 2 rejected; triage at `e0a03cd`). Test changes only; no `src/`. The round 1 rows below still hold, with the round 2 changes on top.

| Finding | Test | What it now pins |
|---------|------|------------------|
| T-AT1-R2 (Debate) | **Changed** `test_every_cli_call_site_uses_the_provider_and_push_credentials_of_its_role` | Every command, `gate run` included, must now exit **0**: the `gate run --gate diff-within-owned-paths --pr` leg runs over the staged verdict PR, which stays inside its owned paths, so the gate passes. A new `reads_github` flag requires the command to ask **its own role's** provider at least once: `gate run` must call `DEPS.github` (CI), and `claim`, `pr open` and `bus pr` must call `DEPS.agent_github`. The existing checks stay: a CI command never asks the agent provider, never mints and never pushes. `gate evidence` builds no GitHub adapter, so it carries no `reads_github` |
| T-AT2-R2 (Blocker) | **Changed harness** `CredentialObserver` in `test_app_token_e2e.py` (used by every e2e test) | Spawns are recorded by one `sys.addaudithook(_spawn_audit)`, registered once per process and routed to the active observer through module-level `_ACTIVE` (monkeypatched per test, so it is a no-op outside the `observer` fixture). It records the command or argv of `os.system`, `os.posix_spawn` (also `os.posix_spawnp`), `os.exec` (the `os.exec*` family) and `subprocess.Popen` (so `run`, `check_output`, `shell=True`). The `subprocess.Popen` subclass wrapper is gone because the hook replaces it. One wrapper stays, on `os._spawnvef`: POSIX `os.spawn*` forks first and audits `os.exec` only in the child, where the parent cannot see it, and the `os.spawn` audit event exists only on Windows. The same `secret_kinds` corpus is checked as before |

Spawn check (throwaway, not committed): with the observer installed, a fake token or a key fragment was passed in the command line of each of these APIs, and each was recorded exactly once with the secret detected (`leaks()` reported all 11, key fragment as `private key`):
- `os.system`, `os.posix_spawn`, `os.posix_spawnp`;
- `os.spawnv`, `os.spawnlp`, `os.spawnvpe`;
- `os.execv` and `os.execvpe` (on a missing path, so the audit fires and then the call raises);
- `subprocess.run` (list and `shell=True`), `subprocess.check_output`.

**Red output (full suite, this branch): `11 failed, 1056 passed, 7 xfailed`** (the 7 are the known T069/T081 strict xfails). `ruff check` and `ruff format --check` pass. Every failure is an assertion. The call-site table now has 13 problems, all role or credential ones. Every command exits 0, and `gate run` and `gate evidence` are clean:
- `order issue`, `release`, `handoff` and `verdict` pushed as `['governor']`, not the App.
- `claim`, `pr open` and `bus pr` asked the CI provider, **never asked the agent provider**, and pushed as `['governor']`.

The other 10 red nodes are unchanged from round 1.

Bounded gaps that remain (see edge case 3): C-level writes, file writes made inside child processes, and env/pipe transport.

## Round 1 resolution

Review: `specs/001-factory-v2/TEST_REVIEW_APP_TOKEN.md` (rejected). Triage + amendment-01 (`DEPS.agent_github`) at `754742c`. Test changes only; no `src/`.

| Finding | Test | What it now pins |
|---------|------|------------------|
| T-AT1 (Blocker) | **New** `tests/contract/test_app_token_e2e.py::test_every_cli_call_site_uses_the_provider_and_push_credentials_of_its_role` | Verified mode with one table over all nine commands. `Providers` installs distinguishable spies on `DEPS.github` (CI) and `DEPS.agent_github` (agent), both over one `FakeGitHub`. The agent commands (`order issue`, `claim`, `release`, `handoff`, `pr open`, `verdict`, `bus pr`) must never ask the CI provider, and each push must authenticate as `x-access-token` (the App), never with ambient git credentials. The CI commands (`gate run --pr`, `gate evidence`) must never ask the agent provider, never mint and never push. Every command must also exit as expected, so a setup failure cannot pass as a role result. The observer below runs across the whole table |
| T-AT2 (Blocker) | **New harness** `CredentialObserver` (`observer` fixture) in `test_app_token_e2e.py`, now in every e2e test; secret corpus via `secret_kinds` in `test_github_adapter.py`; **changed** `test_failing_api_call_and_failing_mint_keep_secrets_out_of_errors_and_logs` | The observer records payloads written to regular files through `open` / `io.open` (so `Path.write_*`, `os.fdopen`, `tempfile`) and `os.write`, kept even when the file is deleted. It also records every child argv (`subprocess.Popen`) and the in-flight exception chain (`repr` + formatted traceback) whenever a command raises `CommandError`. These are checked together with output, logs and the final-tree persistence scan. The corpus is the installation token(s) (verbatim and as the Basic `x-access-token:` credential), every App JWT the recorded App saw, and any 16-character window of the throwaway key's base64 body. The unit failing-call test gains a refused-mint leg that checks `str`/`repr`/traceback of the mint failure for JWTs and key material |
| T-AT3 (Debate, process) | **Changed** `tests/unit/test_github_adapter.py::test_installation_token_is_reused_while_fresh_and_refreshed_at_the_margin` | Injected clock: `build_agent_github(settings, env, clock=...)` (optional keyword; `DEPS.agent_github`'s two-argument call still works). It mints a 1-hour token, reuses it 30 minutes in, and once `REFRESH_MARGIN` = **5 minutes** is left it refreshes before the next request: credentials `[first, first, second]`, 2 mints |
| T-AT4 (Nit) | — | Adversarial fixtures kept |

Fixture note: in verified mode, `handoff` runs `branch-protection-require-pr`, which then requires code-owner review. The call-site table therefore commits `require_code_owner_review: true` to the fixture `main` snapshot, the state T065 sets.

Harness bite check (throwaway, not committed): with the observer installed, it reported all four of these: a token written to a `NamedTemporaryFile` that was then deleted, a key fragment `os.write`-n to an `mkstemp` file that was then unlinked, a token in a child argv, and a token in a chained exception at `CommandError`.

**Red output (full suite, this branch): `11 failed, 1056 passed, 7 xfailed`** (the 7 are the known T069/T081 strict xfails). `ruff check` and `ruff format --check` pass. Every failure is an assertion:
- Call-site table, 10 problems, all role or credential ones (every command exits as expected):
  - `order issue`, `release`, `handoff` and `verdict` pushed as `['governor']`, not the App.
  - `claim`, `pr open` and `bus pr` asked the CI provider, and pushed as `['governor']`.
  - `gate run` and `gate evidence` are clean today, inside the red test.
- REST (4): `factory.github.rest must export build_agent_github(settings, env)`.
- e2e push: the verified push presented `('governor', 'ghp_ambient…')`.
- e2e fail-closed (3 nodes): the claim exits 0 because it pushed with ambient credentials.
- e2e refused push: the App credential was never presented.
- repr: `['repr', 'str', 'format']` show the token.
