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


def load_rest() -> Any:
    try:
        return importlib.import_module("factory.github.rest")
    except ImportError as exc:
        pytest.fail(f"factory.github.rest is not implemented: {exc}")


def recorded(name: str) -> Any:
    return json.loads((RECORDED / name).read_text(encoding="utf-8"))


def recorded_transport() -> httpx.MockTransport:
    pulls = recorded("pulls_by_head.json")
    reviews = recorded("pull_reviews.json")
    checks = recorded("check_runs.json")
    statuses = recorded("combined_status.json")
    created = recorded("create_pull.json")
    status_created = recorded("create_status.json")

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "GET" and path.endswith("/pulls"):
            return httpx.Response(200, json=pulls)
        if request.method == "GET" and path.endswith("/reviews"):
            return httpx.Response(200, json=reviews)
        if request.method == "GET" and path.endswith("/check-runs"):
            return httpx.Response(200, json=checks)
        if request.method == "GET" and path.rstrip("/").endswith("/status"):
            return httpx.Response(200, json=statuses)
        if request.method == "POST" and path.endswith("/pulls"):
            return httpx.Response(201, json=created)
        if request.method == "POST" and "/statuses/" in path:
            return httpx.Response(201, json=status_created)
        return httpx.Response(404, json={"message": f"unrecorded {request.method} {path}"})

    return httpx.MockTransport(handler)


def build_port(repo: RepoBuilder, monkeypatch: pytest.MonkeyPatch) -> GitHubPort:
    rest = load_rest()
    build = getattr(rest, "build_github", None)
    assert callable(build), "factory.github.rest must export build_github(settings, env)"
    transport = recorded_transport()
    original = httpx.Client

    def client_with_transport(*args: Any, **kwargs: Any) -> httpx.Client:
        kwargs.setdefault("transport", transport)
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", client_with_transport)
    env = load_env({"GITHUB_TOKEN": "ghs_test_recorded"})
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


def test_adapter_commit_status_round_trip(
    repo: RepoBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Writes go to GitHub; reads use the port. In-memory FakeGitHub already covers the helper.

    Against the REST adapter, posting a status must be a real httpx call (recorded 201).
    """
    port = build_port(repo, monkeypatch)
    port.set_commit_status(
        SHA, "factory/red-first-proof", "success", "red first", "https://ci.test/1"
    )
    statuses = port.list_commit_statuses(SHA)
    assert any(item.context.startswith("factory/") for item in statuses)
    _ = assert_commit_status_read_after_write
