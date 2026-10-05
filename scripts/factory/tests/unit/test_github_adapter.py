"""T019 — GitHub REST adapter against recorded responses in github_recorded/."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from factory.api import CheckRun, GitHubPort, PullRequest, PullRequestReview
from factory.config.settings import EnvSettings, load_env
from tests.fixtures.repo_builder import RepoBuilder
from tests.unit.test_api import assert_commit_status_read_after_write

RECORDED = Path(__file__).resolve().parents[1] / "fixtures" / "github_recorded"
HEAD = "wo/wo-20261007-recorded"
SHA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
TOKEN = "ghs_test_recorded"
REPO_PATH = "/repos/fixture/demo"


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
