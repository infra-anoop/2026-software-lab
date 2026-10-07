"""T019 — GitHub REST adapter against recorded responses in github_recorded/.

T036b — in verified mode the adapter authenticates with the GitHub App installation token.
"""

from __future__ import annotations

import functools
import importlib
import json
import logging
import traceback
from collections.abc import Callable
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
    the real clock: the recorded `expires_at` is re-based so the recording never goes stale.
    """

    def __init__(
        self,
        *,
        installation_id: int | None = None,
        tokens: tuple[str, ...] = (INSTALLATION_TOKEN,),
        lifetimes: tuple[timedelta, ...] = (timedelta(hours=1),),
        mint_status: int = 201,
    ) -> None:
        self.installation_id = installation_id
        self.tokens = tokens
        self.lifetimes = lifetimes
        self.mint_status = mint_status
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
            body["expires_at"] = (datetime.now(UTC) + lifetime).strftime("%Y-%m-%dT%H:%M:%SZ")
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
) -> GitHubPort:
    build = getattr(load_rest(), "build_github", None)
    assert callable(build), "factory.github.rest must export build_github(settings, env)"
    patch_transport(monkeypatch, lambda request: app.handle(request) or data(request))
    port = build(settings, env)
    assert isinstance(port, GitHubPort)
    return port


def test_app_installation_token_is_used_only_in_verified_mode_with_app_credentials(
    repo: RepoBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Recorded mode keeps GITHUB_TOKEN even with App credentials set; verified mode with
    them sends the installation token. Verified mode without App credentials is the trusted
    CI job, which posts `factory/*` statuses with its own GITHUB_TOKEN (D8: the App has no
    `statuses: write`), so it keeps GITHUB_TOKEN too."""
    legs = [
        (repo.settings, True, TOKEN, False),
        (verified(repo.settings), True, INSTALLATION_TOKEN, True),
        (verified(repo.settings), False, TOKEN, False),
    ]
    for settings, with_app, expected, mints in legs:
        leg = f"mode={settings.identity.mode}, App credentials={with_app}"
        app, data = RecordedApp(), RecordedGitHub()
        port = port_over(settings, app_env(with_app=with_app), monkeypatch, app, data.handler)
        port.list_prs_by_head(HEAD)
        assert [credential(r) for r in data.requests] == [expected], leg
        assert bool(app.mints) is mints, f"{leg}: {[r.url.path for r in app.requests]}"


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


def test_installation_token_is_reused_while_fresh_and_refreshed_before_expiry(
    repo: RepoBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A token with 2 minutes left is replaced before the next call; a 1-hour one is
    reused (refresh margin over 2 minutes, under an hour)."""
    first, second = INSTALLATION_TOKEN, f"{INSTALLATION_TOKEN}_refreshed"
    app = RecordedApp(tokens=(first, second), lifetimes=(timedelta(minutes=2), timedelta(hours=1)))
    data = RecordedGitHub()
    port = port_over(verified(repo.settings), app_env(), monkeypatch, app, data.handler)
    for _ in range(3):
        port.pr_reviews(7)
    used = [credential(r) for r in data.requests]
    assert used[0] in {first, second}, used
    assert used[1:] == [second, second], used
    assert len(app.mints) == 2, [r.url.path for r in app.requests]


def test_failing_api_call_keeps_the_installation_token_out_of_errors_and_logs(
    repo: RepoBuilder,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    caplog.set_level(logging.DEBUG)
    seen: list[httpx.Request] = []

    def refuse(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(403, json={"message": "Resource not accessible by integration"})

    port = port_over(verified(repo.settings), app_env(), monkeypatch, RecordedApp(), refuse)
    with pytest.raises(load_rest().GitHubError) as caught:
        port.create_pr("wo/wo-20261007-new-pr", "main", "title", "body")
    assert [credential(r) for r in seen] == [INSTALLATION_TOKEN]
    error = caught.value
    captured = capsys.readouterr()
    texts = {
        "str": str(error),
        "repr": repr(error),
        "traceback": "".join(traceback.format_exception(error)),
        "port repr": repr(port),
        "logs": caplog.text,
        "output": captured.out + captured.err,
    }
    assert [name for name, text in texts.items() if INSTALLATION_TOKEN in text] == []
