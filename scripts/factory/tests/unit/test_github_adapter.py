"""T019 — GitHub REST adapter against recorded responses in github_recorded/.

T036b — the agent adapter authenticates with the GitHub App installation token in verified
mode; the CI adapter keeps GITHUB_TOKEN.
"""

from __future__ import annotations

import base64
import functools
import importlib
import json
import logging
import re
import traceback
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, NamedTuple

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from factory.api import CheckRun, GitHubPort, PullRequest, PullRequestReview
from factory.config.settings import EnvSettings, IdentityConfig, Settings, load_env
from factory.identity.app_token import AppTokenError
from tests.fixtures.repo_builder import RepoBuilder
from tests.unit.test_api import assert_commit_status_read_after_write

RECORDED = Path(__file__).resolve().parents[1] / "fixtures" / "github_recorded"
HEAD = "wo/wo-20261007-recorded"
SHA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
TOKEN = "ghs_test_recorded"
REPO_PATH = "/repos/fixture/demo"
APP_ID = "12345"


def load_rest() -> Any:
    try:
        return importlib.import_module("factory.github.rest")
    except ImportError as exc:
        pytest.fail(f"factory.github.rest is not implemented: {exc}")


def recorded(name: str) -> Any:
    return json.loads((RECORDED / name).read_text(encoding="utf-8"))


class RecordedGitHub:
    """Recorded REST responses plus a commit-status store fed only by captured POSTs."""

    def __init__(self, *, seed_recorded_statuses: bool = True) -> None:
        self.requests: list[httpx.Request] = []
        self.statuses: dict[str, dict[str, dict[str, Any]]] = {}
        if seed_recorded_statuses:
            combined = recorded("combined_status.json")
            self.statuses[combined["sha"]] = {s["context"]: s for s in combined["statuses"]}

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if request.method == "GET" and path.endswith("/pulls"):
            return httpx.Response(200, json=recorded("pulls_by_head.json"))
        if request.method == "GET" and path.endswith("/reviews"):
            return httpx.Response(200, json=recorded("pull_reviews.json"))
        if request.method == "GET" and path.startswith(f"{REPO_PATH}/pulls/"):
            number = path.removeprefix(f"{REPO_PATH}/pulls/")
            for item in recorded("pulls_by_head.json"):
                if str(item["number"]) == number:
                    return httpx.Response(200, json=item)
        if request.method == "GET" and path.endswith("/check-runs"):
            return httpx.Response(200, json=recorded("check_runs.json"))
        if request.method == "GET" and path.startswith(f"{REPO_PATH}/commits/"):
            sha = path.removeprefix(f"{REPO_PATH}/commits/").removesuffix("/status")
            if path.endswith("/status") and "/" not in sha:
                listed = list(self.statuses.get(sha, {}).values())
                state = "pending" if not listed else listed[-1]["state"]
                return httpx.Response(
                    200,
                    json={"state": state, "sha": sha, "statuses": listed},
                )
        if request.method == "POST" and path.endswith("/pulls"):
            return httpx.Response(201, json=recorded("create_pull.json"))
        if request.method == "POST" and path.startswith(f"{REPO_PATH}/statuses/"):
            sha = path.removeprefix(f"{REPO_PATH}/statuses/")
            body = json.loads(request.content)
            written = {
                "context": body.get("context", "default"),
                "state": body["state"],
                "description": body.get("description", ""),
                "target_url": body.get("target_url"),
            }
            self.statuses.setdefault(sha, {})[written["context"]] = written
            return httpx.Response(201, json=written)
        return httpx.Response(404, json={"message": f"unrecorded {request.method} {path}"})


def build_port(
    repo: RepoBuilder, monkeypatch: pytest.MonkeyPatch, recorder: RecordedGitHub | None = None
) -> GitHubPort:
    rest = load_rest()
    build = getattr(rest, "build_github", None)
    assert callable(build), "factory.github.rest must export build_github(settings, env)"
    transport = httpx.MockTransport((recorder or RecordedGitHub()).handler)
    original = httpx.Client

    def client_with_transport(*args: Any, **kwargs: Any) -> httpx.Client:
        kwargs.setdefault("transport", transport)
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", client_with_transport)
    env = load_env({"GITHUB_TOKEN": TOKEN})
    assert isinstance(env, EnvSettings)
    port = build(repo.settings, env)
    assert isinstance(port, GitHubPort)
    return port


def test_list_prs_by_head_maps_recorded_payload(
    repo: RepoBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    port = build_port(repo, monkeypatch)
    prs = port.list_prs_by_head(HEAD)
    assert len(prs) == 1
    pr = prs[0]
    assert isinstance(pr, PullRequest)
    assert pr.number == 7
    assert pr.head_ref == HEAD
    assert pr.head_sha == SHA
    assert pr.open is True
    assert pr.merged is False
    assert pr.author_login == "factory-app[bot]"


def test_get_pr_maps_recorded_payload_and_missing_is_none(
    repo: RepoBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    port = build_port(repo, monkeypatch)
    pr = port.get_pr(7)
    assert isinstance(pr, PullRequest)
    assert pr.number == 7
    assert pr.head_ref == HEAD
    assert pr.head_sha == SHA
    assert port.get_pr(999) is None


def test_pr_reviews_maps_recorded_payload(
    repo: RepoBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    port = build_port(repo, monkeypatch)
    reviews = port.pr_reviews(7)
    assert len(reviews) == 1
    review = reviews[0]
    assert isinstance(review, PullRequestReview)
    assert review.user_login == "fixture-governor"
    assert review.review_state == "APPROVED"


def test_check_runs_maps_recorded_payload(
    repo: RepoBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    port = build_port(repo, monkeypatch)
    runs = port.check_runs(SHA)
    assert {run.name for run in runs} == {"factory-tests", "verify"}
    running = next(run for run in runs if run.name == "factory-tests")
    assert isinstance(running, CheckRun)
    assert running.run_status == "in_progress"
    assert running.conclusion is None


def test_list_commit_statuses_maps_recorded_payload(
    repo: RepoBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    port = build_port(repo, monkeypatch)
    statuses = port.list_commit_statuses(SHA)
    by_context = {item.context: item for item in statuses}
    assert by_context["factory/red-first-proof"].state == "pending"
    assert by_context["factory/test-seam-ban"].state == "success"


def test_create_pr_maps_recorded_payload(
    repo: RepoBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    port = build_port(repo, monkeypatch)
    pr = port.create_pr(
        "wo/wo-20261007-new-pr",
        "main",
        "wo-20261007-new-pr",
        "Order: wo-20261007-new-pr\nIntents: I-G2",
    )
    assert pr.number == 8
    assert pr.head_ref == "wo/wo-20261007-new-pr"
    assert "wo-20261007-new-pr" in pr.body


def test_set_commit_status_posts_exact_request(
    repo: RepoBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorder = RecordedGitHub(seed_recorded_statuses=False)
    port = build_port(repo, monkeypatch, recorder)
    port.set_commit_status(
        SHA, "factory/order-fidelity-declared", "failure", "lock D1 undeclared", "https://ci.test/9"
    )
    posts = [r for r in recorder.requests if r.method == "POST"]
    assert len(posts) == 1, [f"{r.method} {r.url.path}" for r in recorder.requests]
    post = posts[0]
    assert post.url.host == "api.github.test"
    assert post.url.path == f"{REPO_PATH}/statuses/{SHA}"
    assert post.headers.get("Authorization") in {f"Bearer {TOKEN}", f"token {TOKEN}"}
    assert json.loads(post.content) == {
        "context": "factory/order-fidelity-declared",
        "state": "failure",
        "description": "lock D1 undeclared",
        "target_url": "https://ci.test/9",
    }


def test_adapter_commit_status_round_trip(
    repo: RepoBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The REST adapter passes the port conformance helper: reads return what POSTs wrote."""
    recorder = RecordedGitHub(seed_recorded_statuses=False)
    port = build_port(repo, monkeypatch, recorder)
    assert_commit_status_read_after_write(port)
    posted = [r.url.path for r in recorder.requests if r.method == "POST"]
    assert posted == [
        f"{REPO_PATH}/statuses/{SHA}",
        f"{REPO_PATH}/statuses/{SHA}",
        f"{REPO_PATH}/statuses/{SHA}",
        f"{REPO_PATH}/statuses/{'b' * 40}",
    ], posted


# --- T036b: GitHub App installation token -----------------------------------------------

INSTALLATION_TOKEN = recorded("app_access_token.json")["token"]
CI_BUILDER = "build_github"
AGENT_BUILDER = "build_agent_github"


class AppKey(NamedTuple):
    pem: str
    public_pem: str
    key_line: str


@functools.cache
def app_key() -> AppKey:
    """A throwaway App private key (PKCS#1 PEM, the form GitHub issues), made once per run."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()
    public_pem = (
        key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    return AppKey(pem=pem, public_pem=public_pem, key_line=pem.splitlines()[5])


def app_env(*, with_app: bool = True) -> EnvSettings:
    values = {"GITHUB_TOKEN": TOKEN}
    if with_app:
        values |= {"FACTORY_GITHUB_APP_ID": APP_ID, "FACTORY_GITHUB_APP_PRIVATE_KEY": app_key().pem}
    return load_env(values)


KEY_WINDOW = 16
_BASE64_RUN = re.compile(rb"[A-Za-z0-9+/]{%d,}" % KEY_WINDOW)


@functools.cache
def _key_windows() -> frozenset[bytes]:
    lines = [line for line in app_key().pem.splitlines() if line and not line.startswith("-----")]
    body = "".join(lines).encode()
    return frozenset(body[i : i + KEY_WINDOW] for i in range(len(body) - KEY_WINDOW + 1))


def secret_kinds(data: str | bytes, tokens: Iterable[str]) -> list[str]:
    """Which secrets `data` holds: a token or JWT from `tokens` (verbatim, or as the
    base64 `x-access-token:<token>` Basic credential), or any 16-character window of the
    throwaway private key's base64 body."""
    raw = data.encode() if isinstance(data, str) else data
    kinds = []
    for token in tokens:
        basic = base64.b64encode(f"x-access-token:{token}".encode())
        if token.encode() in raw or basic in raw:
            kinds.append(f"token {token[:8]}…")
    windows = _key_windows()
    for match in _BASE64_RUN.finditer(raw):
        run = match.group()
        if any(run[i : i + KEY_WINDOW] in windows for i in range(len(run) - KEY_WINDOW + 1)):
            kinds.append("private key")
            break
    return kinds


def credential(request: httpx.Request) -> str:
    """The credential a request carried (`Bearer x` / `token x` -> `x`)."""
    value = request.headers.get("Authorization", "")
    for scheme in ("Bearer ", "token "):
        if value.startswith(scheme):
            return value.removeprefix(scheme)
    return value


class RecordedApp:
    """Recorded GitHub App endpoints: the repository's installation and token minting.

    Mint `i` answers with `tokens[i]` (the last one repeats) expiring `lifetimes[i]` from
    `clock()` (the real clock by default): the recorded `expires_at` is re-based so the
    recording never goes stale.
    """

    def __init__(
        self,
        *,
        installation_id: int | None = None,
        tokens: tuple[str, ...] = (INSTALLATION_TOKEN,),
        lifetimes: tuple[timedelta, ...] = (timedelta(hours=1),),
        mint_status: int = 201,
        installed: bool = True,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.installation_id = installation_id
        self.tokens = tokens
        self.lifetimes = lifetimes
        self.mint_status = mint_status
        self.installed = installed
        self.clock = clock
        self.requests: list[httpx.Request] = []

    @property
    def mints(self) -> list[httpx.Request]:
        return [r for r in self.requests if r.url.path.startswith("/app/installations/")]

    @property
    def jwts(self) -> list[str]:
        return [credential(r) for r in self.requests]

    def handle(self, request: httpx.Request) -> httpx.Response | None:
        path = request.url.path
        lookup = path.startswith("/repos/") and path.endswith("/installation")
        if request.method == "GET" and lookup:
            self.requests.append(request)
            if not self.installed:
                return httpx.Response(
                    404,
                    json={
                        "message": "Not Found",
                        "documentation_url": "https://docs.github.com/rest",
                    },
                )
            body = recorded("repo_installation.json")
            if self.installation_id is not None:
                body["id"] = self.installation_id
                body["access_tokens_url"] = (
                    f"https://api.github.test/app/installations/{self.installation_id}/access_tokens"
                )
            return httpx.Response(200, json=body)
        if (
            request.method == "POST"
            and path.startswith("/app/installations/")
            and path.endswith("/access_tokens")
        ):
            self.requests.append(request)
            if self.mint_status != 201:
                return httpx.Response(
                    self.mint_status,
                    json={
                        "message": "A JSON web token could not be decoded",
                        "documentation_url": "https://docs.github.com/rest",
                    },
                )
            index = len(self.mints) - 1
            body = recorded("app_access_token.json")
            body["token"] = self.tokens[min(index, len(self.tokens) - 1)]
            lifetime = self.lifetimes[min(index, len(self.lifetimes) - 1)]
            body["expires_at"] = (self.clock() + lifetime).strftime("%Y-%m-%dT%H:%M:%SZ")
            return httpx.Response(201, json=body)
        return None


def patch_transport(
    monkeypatch: pytest.MonkeyPatch, handler: Callable[[httpx.Request], httpx.Response]
) -> None:
    """Every `httpx.Client` made from here on answers through `handler` (latest wins)."""
    original = httpx.Client

    def client_with_transport(*args: Any, **kwargs: Any) -> httpx.Client:
        kwargs.setdefault("transport", httpx.MockTransport(handler))
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", client_with_transport)


def verified(settings: Settings) -> Settings:
    return settings.model_copy(update={"identity": IdentityConfig(mode="verified")})


def port_over(
    settings: Settings,
    env: EnvSettings,
    monkeypatch: pytest.MonkeyPatch,
    app: RecordedApp,
    data: Callable[[httpx.Request], httpx.Response],
    *,
    builder: str = AGENT_BUILDER,
    **options: Any,
) -> GitHubPort:
    build = getattr(load_rest(), builder, None)
    assert callable(build), f"factory.github.rest must export {builder}(settings, env)"
    patch_transport(monkeypatch, lambda request: app.handle(request) or data(request))
    port = build(settings, env, **options)
    assert isinstance(port, GitHubPort)
    return port


def test_credentials_follow_the_role_ci_keeps_github_token_agents_use_the_app(
    repo: RepoBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Orchestrator ruling 2026-10-07: the CI gate path (`build_github`, which `factory gate
    run` / `gate evidence` load to post `factory/*` statuses under D8) keeps GITHUB_TOKEN in
    either mode and never mints. The agent path (`build_agent_github`) keeps GITHUB_TOKEN in
    recorded mode, sends the installation token in verified mode, and without App
    credentials fails closed before any request: no fallback to GITHUB_TOKEN."""
    legs = [
        (CI_BUILDER, repo.settings, TOKEN),
        (CI_BUILDER, verified(repo.settings), TOKEN),
        (AGENT_BUILDER, repo.settings, TOKEN),
        (AGENT_BUILDER, verified(repo.settings), INSTALLATION_TOKEN),
    ]
    for builder, settings, expected in legs:
        leg = f"{builder}, mode={settings.identity.mode}"
        app, data = RecordedApp(), RecordedGitHub()
        port = port_over(settings, app_env(), monkeypatch, app, data.handler, builder=builder)
        port.list_prs_by_head(HEAD)
        assert [credential(r) for r in data.requests] == [expected], leg
        minted = expected == INSTALLATION_TOKEN
        assert bool(app.mints) is minted, f"{leg}: {[r.url.path for r in app.requests]}"

    app, data = RecordedApp(), RecordedGitHub()
    with pytest.raises((load_rest().GitHubError, AppTokenError)):
        port = port_over(
            verified(repo.settings), app_env(with_app=False), monkeypatch, app, data.handler
        )
        port.list_prs_by_head(HEAD)
    assert data.requests == [], "no request may fall back to GITHUB_TOKEN"
    assert app.requests == []


def test_verified_mode_finds_the_installation_from_the_repository_with_an_app_jwt(
    repo: RepoBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The installation id comes from `GET /repos/{owner}/{repo}/installation` (no config)."""
    app = RecordedApp(installation_id=424242)
    port = port_over(verified(repo.settings), app_env(), monkeypatch, app, RecordedGitHub().handler)
    port.get_pr(7)
    calls = [(r.method, r.url.path) for r in app.requests]
    assert calls == [
        ("GET", f"{REPO_PATH}/installation"),
        ("POST", "/app/installations/424242/access_tokens"),
    ], calls
    for request in app.requests:
        assert request.headers["Authorization"].startswith("Bearer ")
        claims = jwt.decode(credential(request), app_key().public_pem, algorithms=["RS256"])
        assert str(claims["iss"]) == APP_ID, claims


REFRESH_MARGIN = timedelta(minutes=5)


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def test_installation_token_is_reused_while_fresh_and_refreshed_at_the_margin(
    repo: RepoBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With an injected clock (`build_agent_github(settings, env, clock=...)`), a 1-hour
    token is reused 30 minutes in, and once only REFRESH_MARGIN (5 minutes) is left it is
    replaced before the next authenticated request."""
    start = datetime.now(UTC).replace(microsecond=0)
    clock = FakeClock(start)
    first, second = INSTALLATION_TOKEN, f"{INSTALLATION_TOKEN}_refreshed"
    app = RecordedApp(tokens=(first, second), clock=clock)
    data = RecordedGitHub()
    port = port_over(
        verified(repo.settings), app_env(), monkeypatch, app, data.handler, clock=clock
    )
    port.pr_reviews(7)
    clock.now = start + timedelta(minutes=30)
    port.pr_reviews(7)
    assert len(app.mints) == 1, "a fresh token is reused"
    clock.now = start + timedelta(hours=1) - REFRESH_MARGIN
    port.pr_reviews(7)
    assert [credential(r) for r in data.requests] == [first, first, second]
    assert len(app.mints) == 2, [r.url.path for r in app.requests]


def _error_texts(error: BaseException) -> dict[str, str]:
    return {
        "str": str(error),
        "repr": repr(error),
        "traceback": "".join(traceback.format_exception(error)),
    }


def test_failing_api_call_and_failing_mint_keep_secrets_out_of_errors_and_logs(
    repo: RepoBuilder,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A refused API call leaks no installation token, and a refused mint no App JWT or
    private key, into the exception chain (`str`, `repr`, formatted traceback), the port's
    `repr`, the logs or the output."""
    caplog.set_level(logging.DEBUG)
    seen: list[httpx.Request] = []

    def refuse(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(403, json={"message": "Resource not accessible by integration"})

    app = RecordedApp()
    port = port_over(verified(repo.settings), app_env(), monkeypatch, app, refuse)
    with pytest.raises(load_rest().GitHubError) as caught:
        port.create_pr("wo/wo-20261007-new-pr", "main", "title", "body")
    assert [credential(r) for r in seen] == [INSTALLATION_TOKEN]
    texts = {**_error_texts(caught.value), "port repr": repr(port)}

    refused = RecordedApp(mint_status=401)
    port = port_over(verified(repo.settings), app_env(), monkeypatch, refused, refuse)
    with pytest.raises((load_rest().GitHubError, AppTokenError)) as failed_mint:
        port.get_pr(7)
    assert refused.mints, "the mint was attempted"
    texts |= {f"mint {name}": text for name, text in _error_texts(failed_mint.value).items()}
    captured = capsys.readouterr()
    texts |= {"logs": caplog.text, "output": captured.out + captured.err}
    secrets = [INSTALLATION_TOKEN, *app.jwts, *refused.jwts]
    leaked = {name: kinds for name, text in texts.items() if (kinds := secret_kinds(text, secrets))}
    assert leaked == {}
