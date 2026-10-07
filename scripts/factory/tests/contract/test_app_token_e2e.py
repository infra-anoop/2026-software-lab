"""T036b — factory pushes run as the GitHub App in verified mode, and the token stays secret.

`origin` is served over smart HTTP by `git http-backend` behind a local server that wants
HTTP Basic credentials for pushes. An ambient credential helper stands in for the
Codespaces one (it answers with the governor's GITHUB_TOKEN). The App endpoints answer
from `github_recorded/`; the App key is a throwaway made in the test. No real App, key or
network.
"""

from __future__ import annotations

import base64
import logging
import shutil
import subprocess
import tempfile
import threading
from collections.abc import Iterable, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Self

import httpx
import pytest

from factory.cli import exit_codes
from tests.fixtures.cli_runner import CliResult, FactoryCli
from tests.fixtures.repo_builder import RepoBuilder, order
from tests.unit.test_github_adapter import (
    APP_ID,
    INSTALLATION_TOKEN,
    RecordedApp,
    app_key,
    patch_transport,
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


def _app(monkeypatch: pytest.MonkeyPatch, app: RecordedApp | None = None) -> RecordedApp:
    recorded = app or RecordedApp()
    patch_transport(
        monkeypatch,
        lambda request: (
            recorded.handle(request)
            or httpx.Response(404, json={"message": f"unrecorded {request.url.path}"})
        ),
    )
    return recorded


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


def _files_holding(root: Path, secrets: Iterable[str]) -> list[str]:
    needles = [s.encode() for s in secrets]
    needles += [base64.b64encode(f"x-access-token:{s}".encode()) for s in secrets]
    return sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file()
        and not path.is_symlink()
        and any(needle in path.read_bytes() for needle in needles)
    )


def _leaks(texts: dict[str, str], secrets: Iterable[str]) -> list[str]:
    return [name for name, text in texts.items() if any(s in text for s in secrets)]


def test_push_runs_as_the_app_only_in_verified_mode_and_leaves_no_token_behind(
    repo: RepoBuilder,
    factory_cli: FactoryCli,
    isolated_git: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Recorded mode pushes exactly as today (ambient git credentials, no mint). Verified
    mode pushes with the installation token through the helper, ahead of any ambient
    helper, and no token reaches a file (git config, credential store, trace, temp), the
    history, the CLI output or the logs."""
    caplog.set_level(logging.DEBUG)
    recorded_order, verified_order = _issue(repo, "recorded-push"), _issue(repo, "verified-push")
    app = _app(monkeypatch)
    with GitHttpOrigin(repo.root, {AMBIENT, APP_CREDENTIAL}) as origin:
        repo.git("remote", "set-url", "origin", origin.url)

        recorded = _claim(factory_cli, repo, recorded_order)
        assert recorded.exit_code == exit_codes.OK, recorded.stderr
        assert set(origin.presented) == {AMBIENT}, "recorded mode pushes as it does today"
        assert app.requests == [], "recorded mode never mints an App token"

        origin.presented.clear()
        _set_identity_mode(repo, "verified")
        result = _claim(factory_cli, repo, verified_order)
        assert result.exit_code == exit_codes.OK, result.stderr
        assert set(origin.presented) == {APP_CREDENTIAL}, origin.presented

    assert f"bus/orders/{verified_order}/claim.yaml" in _origin_files(repo, f"wo/{verified_order}")
    secrets = [INSTALLATION_TOKEN, app_key().key_line]
    assert _files_holding(isolated_git, secrets) == []
    texts = {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "logs": caplog.text,
        "history": repo.git("log", "--all", "-p"),
        "git config": repo.git("config", "--list", "--show-origin"),
    }
    assert _leaks(texts, secrets) == []


def test_failing_mint_stops_the_push_and_keeps_secrets_out_of_the_error(
    repo: RepoBuilder,
    factory_cli: FactoryCli,
    isolated_git: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verified mode with a mint GitHub refuses: an external error, no push with ambient
    credentials instead, and neither the App JWT nor the key in the error or logs."""
    caplog.set_level(logging.DEBUG)
    order_id = _issue(repo, "mint-fails")
    app = _app(monkeypatch, RecordedApp(mint_status=401))
    _set_identity_mode(repo, "verified")
    with GitHttpOrigin(repo.root, {AMBIENT, APP_CREDENTIAL}) as origin:
        repo.git("remote", "set-url", "origin", origin.url)
        result = _claim(factory_cli, repo, order_id)
    assert result.exit_code == exit_codes.EXTERNAL, (result.exit_code, result.stderr)
    assert origin.presented == [], "no fallback to ambient git credentials"
    assert app.mints, "the mint was attempted"
    secrets = [*app.jwts, app_key().key_line]
    texts = {"stdout": result.stdout, "stderr": result.stderr, "logs": caplog.text}
    assert _leaks(texts, secrets) == []
    assert _files_holding(isolated_git, secrets) == []


def test_refused_push_keeps_the_installation_token_out_of_the_error(
    repo: RepoBuilder,
    factory_cli: FactoryCli,
    isolated_git: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A push origin refuses after authenticating as the App fails as an external error
    whose text (git's stderr included) holds no token."""
    caplog.set_level(logging.DEBUG)
    order_id = _issue(repo, "push-refused")
    _app(monkeypatch)
    _set_identity_mode(repo, "verified")
    with GitHttpOrigin(repo.root, {AMBIENT, APP_CREDENTIAL}, refuse_pushes=True) as origin:
        repo.git("remote", "set-url", "origin", origin.url)
        result = _claim(factory_cli, repo, order_id)
    assert result.exit_code == exit_codes.EXTERNAL, (result.exit_code, result.stderr)
    assert APP_CREDENTIAL in origin.presented, origin.presented
    texts = {"stdout": result.stdout, "stderr": result.stderr, "logs": caplog.text}
    assert _leaks(texts, [INSTALLATION_TOKEN]) == []
    assert _files_holding(isolated_git, [INSTALLATION_TOKEN]) == []
