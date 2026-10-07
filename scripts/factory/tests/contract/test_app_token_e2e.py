"""T036b — factory pushes run as the GitHub App in verified mode, and the token stays secret.

`origin` is served over smart HTTP by `git http-backend` behind a local server that wants
HTTP Basic credentials for pushes. An ambient credential helper stands in for the
Codespaces one (it answers with the governor's GITHUB_TOKEN). The App endpoints answer
from `github_recorded/`; the App key is a throwaway made in the test. No real App, key or
network.
"""

from __future__ import annotations

import base64
import builtins
import io
import logging
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import traceback
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Self

import pytest

from factory.api import GitHubPort
from factory.cli import exit_codes
from factory.cli.common import DEPS, CommandError
from factory.config.settings import EnvSettings, Settings
from tests.fixtures.cli_runner import CliResult, FactoryCli
from tests.fixtures.fake_github import FakeGitHub
from tests.fixtures.repo_builder import RepoBuilder, message, order, yaml_text
from tests.unit.test_github_adapter import (
    APP_ID,
    INSTALLATION_TOKEN,
    RecordedApp,
    RecordedGitHub,
    app_key,
    credential,
    patch_transport,
    secret_kinds,
)

pytestmark = pytest.mark.contract

AMBIENT_TOKEN = "ghp_ambient_governor_token"
AMBIENT = ("governor", AMBIENT_TOKEN)
APP_CREDENTIAL = ("x-access-token", INSTALLATION_TOKEN)
AMBIENT_HELPER = f"""#!/bin/sh
if [ "$1" = get ]; then
  printf 'username={AMBIENT[0]}\\npassword={AMBIENT_TOKEN}\\n'
fi
"""
CLEARED_ENV = (
    "GIT_ASKPASS",
    "SSH_ASKPASS",
    "GIT_CONFIG_COUNT",
    "GIT_CONFIG_PARAMETERS",
    "GH_TOKEN",
    "GITHUB_API_URL",
    "GITHUB_REPOSITORY",
    "FACTORY_GITHUB_APP_ID",
    "FACTORY_GITHUB_APP_PRIVATE_KEY",
    "http_proxy",
    "https_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "all_proxy",
)


class GitHttpOrigin:
    """`<project_root>/origin.git` over smart HTTP; pushes need credentials in `accepted`.

    Every Basic credential a push request presents is recorded in `presented`. With
    `refuse_pushes`, an accepted push is answered 403.
    """

    def __init__(
        self,
        project_root: Path,
        accepted: set[tuple[str, str]],
        *,
        refuse_pushes: bool = False,
    ) -> None:
        self.project_root = project_root
        self.accepted = accepted
        self.refuse_pushes = refuse_pushes
        self.presented: list[tuple[str, str]] = []
        self._git = shutil.which("git") or "git"
        origin = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

            def do_GET(self) -> None:
                origin.serve(self)

            def do_POST(self) -> None:
                origin.serve(self)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_address[1]}/origin.git"

    def __enter__(self) -> Self:
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._server.shutdown()
        self._server.server_close()

    def serve(self, request: BaseHTTPRequestHandler) -> None:
        path, _, query = request.path.partition("?")
        body = _read_body(request)
        user = ""
        if path.endswith("/git-receive-pack") or "service=git-receive-pack" in query:
            presented = _basic(request.headers.get("Authorization"))
            if presented is not None:
                self.presented.append(presented)
            if presented is None or presented not in self.accepted:
                _reply(request, 401, {"WWW-Authenticate": 'Basic realm="fixture origin"'}, b"")
                return
            if self.refuse_pushes:
                _reply(request, 403, {"Content-Type": "text/plain"}, b"pushes are refused\n")
                return
            user = presented[0]
        env = {
            "GIT_PROJECT_ROOT": str(self.project_root),
            "GIT_HTTP_EXPORT_ALL": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "HOME": str(self.project_root),
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "REQUEST_METHOD": request.command,
            "CONTENT_TYPE": request.headers.get("Content-Type", ""),
            "CONTENT_LENGTH": str(len(body)),
            "REMOTE_ADDR": "127.0.0.1",
            "REMOTE_USER": user,
        }
        if request.headers.get("Content-Encoding"):
            env["HTTP_CONTENT_ENCODING"] = request.headers["Content-Encoding"]
        if request.headers.get("Git-Protocol"):
            env["GIT_PROTOCOL"] = request.headers["Git-Protocol"]
        result = subprocess.run(
            [self._git, "http-backend"], input=body, env=env, capture_output=True, check=False
        )
        head, payload = _split_cgi(result.stdout)
        status, headers = 200, {}
        for line in head.splitlines():
            name, _, value = line.partition(":")
            if name.lower() == "status":
                status = int(value.split()[0])
            elif name:
                headers[name] = value.strip()
        _reply(request, status, headers, payload)


def _read_body(request: BaseHTTPRequestHandler) -> bytes:
    if "chunked" in request.headers.get("Transfer-Encoding", ""):
        chunks = []
        while True:
            size = int(request.rfile.readline().split(b";")[0].strip(), 16)
            if size == 0:
                request.rfile.readline()
                return b"".join(chunks)
            chunks.append(request.rfile.read(size))
            request.rfile.readline()
    return request.rfile.read(int(request.headers.get("Content-Length") or 0))


def _basic(header: str | None) -> tuple[str, str] | None:
    if not header or not header.startswith("Basic "):
        return None
    user, _, password = base64.b64decode(header.removeprefix("Basic ")).decode().partition(":")
    return user, password


def _split_cgi(output: bytes) -> tuple[str, bytes]:
    for separator in (b"\r\n\r\n", b"\n\n"):
        head, found, payload = output.partition(separator)
        if found:
            return head.decode("latin-1"), payload
    return "", output


def _reply(
    request: BaseHTTPRequestHandler, status: int, headers: dict[str, str], payload: bytes
) -> None:
    request.send_response(status)
    for name, value in headers.items():
        request.send_header(name, value)
    request.send_header("Content-Length", str(len(payload)))
    request.end_headers()
    request.wfile.write(payload)


@pytest.fixture
def isolated_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Process environment for the factory's git: no developer or Codespaces config, an
    ambient credential helper, the governor's GITHUB_TOKEN, App credentials, and git's
    command trace and temp files under `tmp_path` so the leak scan sees them."""
    home = tmp_path / "home"
    home.mkdir()
    helper = home / "ambient-credential-helper"
    helper.write_text(AMBIENT_HELPER, encoding="utf-8")
    helper.chmod(0o755)
    gitconfig = home / ".gitconfig"
    gitconfig.write_text(
        "[user]\n\tname = Fixture Bot\n\temail = fixture@example.test\n"
        f"[credential]\n\thelper = {helper}\n",
        encoding="utf-8",
    )
    scratch = tmp_path / "tmp"
    scratch.mkdir()
    for name in CLEARED_ENV:
        monkeypatch.delenv(name, raising=False)
    for name, value in {
        "HOME": str(home),
        "GIT_CONFIG_GLOBAL": str(gitconfig),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_TRACE": str(tmp_path / "git-trace.log"),
        "NO_PROXY": "127.0.0.1,localhost",
        "no_proxy": "127.0.0.1,localhost",
        "TMPDIR": str(scratch),
        "GITHUB_TOKEN": AMBIENT_TOKEN,
        "FACTORY_GITHUB_APP_ID": APP_ID,
        "FACTORY_GITHUB_APP_PRIVATE_KEY": app_key().pem,
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    yield tmp_path


def _app(
    monkeypatch: pytest.MonkeyPatch, app: RecordedApp | None = None
) -> tuple[RecordedApp, RecordedGitHub]:
    """App endpoints plus recorded REST data, so `claim`'s reads work whether they reach
    the substituted FakeGitHub or a real agent adapter."""
    recorded, data = app or RecordedApp(), RecordedGitHub()
    patch_transport(monkeypatch, lambda request: recorded.handle(request) or data.handler(request))
    return recorded, data


def _issue(repo: RepoBuilder, slug: str) -> str:
    order_id = f"wo-20261007-{slug}"
    repo.issue_order(order(order_id, owned_paths=[f"apps/demo/{order_id}/**"]))
    return order_id


def _set_identity_mode(repo: RepoBuilder, mode: str) -> None:
    text = (repo.path / "factory.toml").read_text(encoding="utf-8")
    repo.write("factory.toml", text.replace('mode = "recorded"', f'mode = "{mode}"'))
    assert repo.settings.identity.mode == mode


def _claim(factory_cli: FactoryCli, repo: RepoBuilder, order_id: str) -> CliResult:
    return factory_cli("claim", order_id, "--actor-model", "claude-opus-5.5", repo=repo.path)


def _origin_files(repo: RepoBuilder, branch: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(repo.origin), "ls-tree", "-r", "--name-only", f"refs/heads/{branch}"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.split()


def _files_holding(root: Path, tokens: Iterable[str]) -> dict[str, list[str]]:
    """Persistence check: files left under `root` that hold a token, a JWT or key material."""
    found = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            kinds = secret_kinds(path.read_bytes(), tokens)
            if kinds:
                found[f"file {path.relative_to(root)}"] = kinds
    return found


def _leaks(texts: dict[str, str], tokens: Iterable[str]) -> dict[str, list[str]]:
    return {name: kinds for name, text in texts.items() if (kinds := secret_kinds(text, tokens))}


def _regular(fd: int) -> bool:
    try:
        return stat.S_ISREG(os.fstat(fd).st_mode)
    except (OSError, ValueError):
        return False


def _fd_name(fd: int) -> str:
    try:
        return os.readlink(f"/proc/self/fd/{fd}")
    except OSError:
        return f"fd {fd}"


class _RecordingFile:
    """A writable regular file whose payloads are recorded before they reach the file."""

    def __init__(self, handle: Any, name: str, record: Callable[[str, Any], None]) -> None:
        self._handle = handle
        self._name = name
        self._record = record

    def write(self, data: Any) -> Any:
        self._record(self._name, data)
        return self._handle.write(data)

    def writelines(self, lines: Iterable[Any]) -> None:
        listed = list(lines)
        for line in listed:
            self._record(self._name, line)
        self._handle.writelines(listed)

    def __enter__(self) -> Self:
        self._handle.__enter__()
        return self

    def __exit__(self, *exc: object) -> Any:
        return self._handle.__exit__(*exc)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._handle)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._handle, name)


class CredentialObserver:
    """What the factory hands the OS, or raises, while the test runs (Python level only):

    - payloads written to regular files through `open` / `io.open` (so `Path.write_*`,
      `os.fdopen` and `tempfile` too) and `os.write`, kept even when the file is deleted;
    - every child-process argv (`subprocess.Popen`, so `run` / `check_output` too);
    - the exception chain in flight (`repr` + formatted traceback) whenever a command turns
      a failure into a `CommandError`.

    Pipes are not files: a token handed to a child on stdin, or in its environment, is
    not a write here.
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.writes: dict[str, bytearray] = {}
        self.argv: list[str] = []
        self.exceptions: list[str] = []
        self._install(monkeypatch)

    def _record(self, name: str, data: Any) -> None:
        chunk = data.encode("utf-8", "replace") if isinstance(data, str) else bytes(data)
        self.writes.setdefault(name, bytearray()).extend(chunk)

    def _install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        observer = self
        original_open, original_write = io.open, os.write
        original_popen, original_init = subprocess.Popen, CommandError.__init__

        def observed_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
            handle = original_open(file, mode, *args, **kwargs)
            if any(flag in mode for flag in "wax+") and _regular(handle.fileno()):
                name = _fd_name(file) if isinstance(file, int) else os.fsdecode(file)
                return _RecordingFile(handle, name, observer._record)
            return handle

        def observed_write(fd: int, data: Any) -> int:
            if _regular(fd):
                observer._record(_fd_name(fd), data)
            return original_write(fd, data)

        class ObservedPopen(original_popen):  # type: ignore[misc, valid-type]
            def __init__(self, args: Any, *rest: Any, **kwargs: Any) -> None:
                if not isinstance(args, str | bytes | os.PathLike):
                    args = list(args)
                listed = args if isinstance(args, list) else [args]
                observer.argv.append(" ".join(os.fsdecode(part) for part in listed))
                super().__init__(args, *rest, **kwargs)

        def observed_init(error: CommandError, *args: Any, **kwargs: Any) -> None:
            current = sys.exc_info()[1]
            if current is not None:
                formatted = "".join(traceback.format_exception(current))
                observer.exceptions.append(f"{current!r}\n{formatted}")
            original_init(error, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", observed_open)
        monkeypatch.setattr(io, "open", observed_open)
        monkeypatch.setattr(os, "write", observed_write)
        monkeypatch.setattr(subprocess, "Popen", ObservedPopen)
        monkeypatch.setattr(CommandError, "__init__", observed_init)

    def leaks(self, tokens: Iterable[str]) -> dict[str, list[str]]:
        tokens = list(tokens)
        found = {}
        for name, data in self.writes.items():
            if kinds := secret_kinds(bytes(data), tokens):
                found[f"write {name}"] = kinds
        for index, argv in enumerate(self.argv):
            if kinds := secret_kinds(argv, tokens):
                found[f"argv #{index} ({argv.split(' ', 1)[0]})"] = kinds
        for index, text in enumerate(self.exceptions):
            if kinds := secret_kinds(text, tokens):
                found[f"exception #{index}"] = kinds
        return found


@pytest.fixture
def observer(isolated_git: Path, monkeypatch: pytest.MonkeyPatch) -> CredentialObserver:
    return CredentialObserver(monkeypatch)


def _no_leaks(
    observer: CredentialObserver, root: Path, texts: dict[str, str], tokens: Iterable[str]
) -> None:
    """The secrets (tokens, every App JWT, the whole private key) reached no write, argv,
    exception chain, output, log, or file left under `root`."""
    tokens = list(tokens)
    found = {**observer.leaks(tokens), **_leaks(texts, tokens), **_files_holding(root, tokens)}
    assert found == {}


def test_push_runs_as_the_app_only_in_verified_mode_and_leaves_no_token_behind(
    repo: RepoBuilder,
    factory_cli: FactoryCli,
    isolated_git: Path,
    observer: CredentialObserver,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Recorded mode pushes exactly as today (ambient git credentials, no mint). Verified
    mode pushes with the installation token through the helper, ahead of any ambient
    helper. No token, App JWT or key material reaches a write (even a deleted temp file),
    a child argv, a file left behind (git config, credential store, trace), the history,
    the CLI output or the logs."""
    caplog.set_level(logging.DEBUG)
    recorded_order, verified_order = _issue(repo, "recorded-push"), _issue(repo, "verified-push")
    app, data = _app(monkeypatch)
    with GitHttpOrigin(repo.root, {AMBIENT, APP_CREDENTIAL}) as origin:
        repo.git("remote", "set-url", "origin", origin.url)

        recorded = _claim(factory_cli, repo, recorded_order)
        assert recorded.exit_code == exit_codes.OK, recorded.stderr
        assert set(origin.presented) == {AMBIENT}, "recorded mode pushes as it does today"
        assert app.requests == [], "recorded mode never mints an App token"

        origin.presented.clear()
        data.requests.clear()
        _set_identity_mode(repo, "verified")
        result = _claim(factory_cli, repo, verified_order)
        assert result.exit_code == exit_codes.OK, result.stderr
        assert set(origin.presented) == {APP_CREDENTIAL}, origin.presented
        assert AMBIENT_TOKEN not in [credential(r) for r in data.requests]

    assert f"bus/orders/{verified_order}/claim.yaml" in _origin_files(repo, f"wo/{verified_order}")
    texts = {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "logs": caplog.text,
        "history": repo.git("log", "--all", "-p"),
        "git config": repo.git("config", "--list", "--show-origin"),
    }
    _no_leaks(observer, isolated_git, texts, [INSTALLATION_TOKEN, *app.jwts])


@pytest.mark.parametrize("cause", ["mint-refused", "app-not-installed", "no-app-credentials"])
def test_verified_push_without_an_app_token_fails_closed_and_keeps_secrets_out(
    cause: str,
    repo: RepoBuilder,
    factory_cli: FactoryCli,
    isolated_git: Path,
    observer: CredentialObserver,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Orchestrator ruling 2026-10-07: in verified mode, a refused mint (401), an
    installation lookup 404, or missing App credentials is an external error (exit 4) with
    no fallback to GITHUB_TOKEN or ambient git credentials; no App JWT or key material
    reaches the exception chain, a write, an argv, the output, the logs or a file."""
    caplog.set_level(logging.DEBUG)
    order_id = _issue(repo, cause)
    recorded = {
        "mint-refused": RecordedApp(mint_status=401),
        "app-not-installed": RecordedApp(installed=False),
        "no-app-credentials": RecordedApp(),
    }[cause]
    if cause == "no-app-credentials":
        monkeypatch.delenv("FACTORY_GITHUB_APP_ID")
        monkeypatch.delenv("FACTORY_GITHUB_APP_PRIVATE_KEY")
    app, data = _app(monkeypatch, recorded)
    _set_identity_mode(repo, "verified")
    with GitHttpOrigin(repo.root, {AMBIENT, APP_CREDENTIAL}) as origin:
        repo.git("remote", "set-url", "origin", origin.url)
        result = _claim(factory_cli, repo, order_id)
    assert result.exit_code == exit_codes.EXTERNAL, (result.exit_code, result.stderr)
    assert origin.presented == [], "no fallback to ambient git credentials"
    assert AMBIENT_TOKEN not in [credential(r) for r in data.requests], "no GITHUB_TOKEN"
    assert not app.mints or cause == "mint-refused", [r.url.path for r in app.requests]
    texts = {"stdout": result.stdout, "stderr": result.stderr, "logs": caplog.text}
    _no_leaks(observer, isolated_git, texts, app.jwts)


def test_refused_push_keeps_the_installation_token_out_of_the_error(
    repo: RepoBuilder,
    factory_cli: FactoryCli,
    isolated_git: Path,
    observer: CredentialObserver,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A push origin refuses after authenticating as the App fails as an external error;
    no token, App JWT or key material reaches its exception chain, git's stderr, the
    output, a write, an argv, the logs or a file."""
    caplog.set_level(logging.DEBUG)
    order_id = _issue(repo, "push-refused")
    app, _ = _app(monkeypatch)
    _set_identity_mode(repo, "verified")
    with GitHttpOrigin(repo.root, {AMBIENT, APP_CREDENTIAL}, refuse_pushes=True) as origin:
        repo.git("remote", "set-url", "origin", origin.url)
        result = _claim(factory_cli, repo, order_id)
    assert result.exit_code == exit_codes.EXTERNAL, (result.exit_code, result.stderr)
    assert APP_CREDENTIAL in origin.presented, origin.presented
    texts = {"stdout": result.stdout, "stderr": result.stderr, "logs": caplog.text}
    _no_leaks(observer, isolated_git, texts, [INSTALLATION_TOKEN, *app.jwts])


# --- T-AT1: every CLI call site picks the provider of its role -------------------------------

AGENT, CI = "agent", "ci"
CALC = "apps/demo/app/calc.py"


class Providers:
    """Distinguishable CI (`DEPS.github`) and agent (`DEPS.agent_github`, amendment-01)
    providers. Both hand out the same FakeGitHub, so only the provider asked for differs."""

    def __init__(self, github: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
        self.github = github
        self.calls: list[str] = []
        monkeypatch.setattr(DEPS, "github", self._provider(CI))
        monkeypatch.setattr(DEPS, "agent_github", self._provider(AGENT), raising=False)

    def _provider(self, role: str) -> Callable[[Settings, EnvSettings], GitHubPort]:
        def provide(settings: Settings, env: EnvSettings) -> GitHubPort:
            self.calls.append(role)
            return self.github

        return provide


@dataclass(frozen=True)
class Command:
    argv: tuple[str, ...]
    role: str
    pushes: bool
    branch: str = "main"
    ok: frozenset[int] = frozenset({exit_codes.OK})


def _reviewable(repo: RepoBuilder, slug: str) -> str:
    """An order claimed, handed off and run-complete on its branch."""
    order_id = f"wo-20261007-{slug}"
    repo.issue_order(order(order_id, owned_paths=[CALC], checks=["diff-within-owned-paths"]))
    repo.add_event(order_id, message("claim", order_id=order_id))
    work = {CALC: "def add(a, b):\n    return a + b\n"}
    repo.add_event(order_id, message("handoff", order_id=order_id), extra_files=work)
    repo.add_event(order_id, message("run_complete", order_id=order_id))
    return order_id


def _stage_every_command(repo: RepoBuilder, tmp_path: Path) -> list[Command]:
    """Fixture state for each GitHub-using or pushing command, on a file origin."""
    repo.add_demo_feature()
    # Verified mode makes `branch-protection-require-pr` (run by `handoff`) require
    # code-owner review in the ruleset snapshot, as T065 sets it on main.
    snapshot = repo.path / "deploy/github/branch-protection.json"
    text = snapshot.read_text(encoding="utf-8")
    assert '"require_code_owner_review": false' in text
    snapshot.write_text(
        text.replace('"require_code_owner_review": false', '"require_code_owner_review": true'),
        encoding="utf-8",
    )
    repo.commit("ruleset requires code-owner review")
    repo.push("main")
    claim_id, release_id = _issue(repo, "cs-claim"), _issue(repo, "cs-release")
    handoff_id = "wo-20261007-cs-handoff"
    repo.issue_order(order(handoff_id, owned_paths=[CALC], checks=["diff-within-owned-paths"]))
    work = {CALC: "def add(a, b):\n    return a + b\n"}
    repo.add_event(handoff_id, message("claim", order_id=handoff_id), extra_files=work)
    repo.checkout(f"wo/{handoff_id}")
    repo.write_message(message("handoff", order_id=handoff_id))
    repo.commit("handoff")
    repo.checkout("main")
    pr_id, verdict_id = _reviewable(repo, "cs-pr"), _reviewable(repo, "cs-verdict")
    verdict = tmp_path / "verdict.yaml"
    head = repo.head_sha(f"wo/{verdict_id}")
    fields = {
        "actor_model": "gpt-5.6-sol",
        "reviewer_model": "gpt-5.6-sol",
        "reviewer_family": "openai",
        "inputs": [{"path": f"bus/orders/{verdict_id}/order.yaml", "sha": head}],
    }
    verdict.write_text(yaml_text(message("verdict", order_id=verdict_id, **fields)), "utf-8")
    gated = repo.make_pr(f"wo/{verdict_id}")
    # Untracked inputs last: RepoBuilder commits with `git add -A`.
    issue_id = "wo-20261007-cs-issue"
    repo.write_message(order(issue_id, owned_paths=[f"apps/demo/{issue_id}/**"]))
    decision = repo.write_message(message("decision_request", decision_id="cs-web-view"))
    model = ("--actor-model", "claude-opus-5.5")
    return [
        Command(("order", "issue", issue_id), AGENT, pushes=True),
        Command(("claim", claim_id, *model), AGENT, pushes=True),
        Command(("release", release_id, "--reason", "abandoned", *model), AGENT, pushes=True),
        Command(("handoff", handoff_id), AGENT, pushes=True, branch=f"wo/{handoff_id}"),
        Command(("pr", "open", pr_id), AGENT, pushes=True, branch=f"wo/{pr_id}"),
        Command(
            ("verdict", verdict_id, "--file", str(verdict)),
            AGENT,
            pushes=True,
            branch=f"wo/{verdict_id}",
        ),
        Command(("bus", "pr", "--message", decision), AGENT, pushes=True),
        Command(
            ("gate", "run", "--gate", "diff-within-owned-paths", "--pr", str(gated.number)),
            CI,
            pushes=False,
            ok=frozenset({exit_codes.OK, exit_codes.GATE_FAILURE}),
        ),
        Command(
            ("gate", "evidence", "--base", "main", "--head", "main", "--out", str(tmp_path / "ev")),
            CI,
            pushes=False,
        ),
    ]


def test_every_cli_call_site_uses_the_provider_and_push_credentials_of_its_role(
    fake_github: FakeGitHub,
    factory_cli: FactoryCli,
    isolated_git: Path,
    observer: CredentialObserver,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Orchestrator ruling + amendment-01, in verified mode. Agent commands (order issue,
    claim, release, handoff, pr open, verdict, bus pr) never ask `DEPS.github`, and each
    push authenticates as the App, never with ambient git credentials. The trusted CI
    commands (`gate run`, `gate evidence`) never ask `DEPS.agent_github`, never mint and
    never push."""
    caplog.set_level(logging.DEBUG)
    repo = RepoBuilder(isolated_git / "fixture", github=fake_github, concurrency_cap=10)
    commands = _stage_every_command(repo, isolated_git)
    providers = Providers(fake_github, monkeypatch)
    app, _ = _app(monkeypatch)
    _set_identity_mode(repo, "verified")
    problems: list[str] = []
    outputs: dict[str, str] = {}
    with GitHttpOrigin(repo.root, {AMBIENT, APP_CREDENTIAL}) as origin:
        repo.git("remote", "set-url", "origin", origin.url)
        for command in commands:
            name = " ".join(command.argv[:2])
            repo.checkout(command.branch)
            providers.calls.clear()
            origin.presented.clear()
            minted = len(app.mints)
            result = factory_cli(*command.argv, repo=repo.path)
            outputs[f"{name} output"] = result.stdout + result.stderr
            if result.exit_code not in command.ok:
                problems.append(f"{name}: exit {result.exit_code}: {result.stderr.strip()[:300]}")
            wrong = CI if command.role == AGENT else AGENT
            if wrong in providers.calls:
                problems.append(f"{name}: asked the {wrong} provider")
            if command.role == CI and len(app.mints) > minted:
                problems.append(f"{name}: minted an App token")
            pushed_as = sorted({user for user, _ in origin.presented})
            if command.pushes and pushed_as != [APP_CREDENTIAL[0]]:
                problems.append(f"{name}: pushed as {pushed_as}, not the App")
            if not command.pushes and pushed_as:
                problems.append(f"{name}: pushed as {pushed_as}")
            repo.checkout("main")
    assert problems == [], "\n".join(problems)
    _no_leaks(
        observer, isolated_git, {**outputs, "logs": caplog.text}, [INSTALLATION_TOKEN, *app.jwts]
    )
