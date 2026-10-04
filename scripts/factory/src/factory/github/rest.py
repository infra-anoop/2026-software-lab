"""`GitHubPort` over the GitHub REST API (httpx). The only module that calls GitHub (I-A4)."""

from __future__ import annotations

from typing import Any

import httpx

from factory.api import (
    CheckRun,
    CommitStatus,
    CommitStatusValue,
    GitHubPort,
    PullRequest,
    PullRequestReview,
)
from factory.config.settings import EnvSettings, Settings

API_VERSION = "2022-11-28"
PAGE_SIZE = 100
TIMEOUT_SECONDS = 30.0


class GitHubError(Exception):
    """GitHub was unreachable or answered with an error."""


def _pr(data: dict[str, Any]) -> PullRequest:
    return PullRequest(
        number=int(data["number"]),
        head_ref=data["head"]["ref"],
        head_sha=data["head"]["sha"],
        base_ref=data["base"]["ref"],
        title=data.get("title") or "",
        body=data.get("body") or "",
        open=data.get("state") == "open",
        merged=data.get("merged_at") is not None,
        author_login=(data.get("user") or {}).get("login") or "",
        html_url=data.get("html_url") or "",
    )


def _review(data: dict[str, Any]) -> PullRequestReview:
    return PullRequestReview(
        id=int(data["id"]),
        user_login=(data.get("user") or {}).get("login") or "",
        review_state=data["state"],
        commit_id=data.get("commit_id") or "",
        submitted_at=data.get("submitted_at"),
    )


def _check_run(data: dict[str, Any]) -> CheckRun:
    return CheckRun(
        name=data["name"],
        head_sha=data["head_sha"],
        run_status=data["status"],
        conclusion=data.get("conclusion"),
    )


def _status(data: dict[str, Any]) -> CommitStatus:
    return CommitStatus(
        context=data.get("context") or "default",
        state=data["state"],
        description=data.get("description") or "",
        target_url=data.get("target_url"),
    )


class RestGitHub:
    """REST client for one repository (`owner/name`)."""

    def __init__(self, *, repository: str, api_url: str, token: str | None) -> None:
        self.repository = repository
        self.owner = repository.split("/", 1)[0]
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.Client(
            base_url=api_url.rstrip("/"), headers=headers, timeout=TIMEOUT_SECONDS
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self._client.request(method, f"/repos/{self.repository}{path}", **kwargs)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:200]
            raise GitHubError(
                f"GitHub {method} {path}: HTTP {exc.response.status_code} {detail}"
            ) from exc
        except httpx.HTTPError as exc:
            raise GitHubError(f"GitHub {method} {path}: {exc}") from exc
        return response.json()

    def list_prs_by_head(self, head_branch: str) -> list[PullRequest]:
        params = {"head": f"{self.owner}:{head_branch}", "state": "all", "per_page": PAGE_SIZE}
        prs = [_pr(item) for item in self._request("GET", "/pulls", params=params)]
        return [pr for pr in prs if pr.head_ref == head_branch]

    def pr_reviews(self, pr_number: int) -> list[PullRequestReview]:
        params = {"per_page": PAGE_SIZE}
        return [
            _review(item)
            for item in self._request("GET", f"/pulls/{pr_number}/reviews", params=params)
        ]

    def check_runs(self, sha: str) -> list[CheckRun]:
        body = self._request("GET", f"/commits/{sha}/check-runs", params={"per_page": PAGE_SIZE})
        return [_check_run(item) for item in body.get("check_runs", [])]

    def create_pr(self, head_branch: str, base_branch: str, title: str, body: str) -> PullRequest:
        payload = {"head": head_branch, "base": base_branch, "title": title, "body": body}
        return _pr(self._request("POST", "/pulls", json=payload))

    def set_commit_status(
        self,
        sha: str,
        context: str,
        value: CommitStatusValue,
        description: str,
        target_url: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {"context": context, "state": value, "description": description}
        if target_url is not None:
            payload["target_url"] = target_url
        self._request("POST", f"/statuses/{sha}", json=payload)

    def list_commit_statuses(self, sha: str) -> list[CommitStatus]:
        body = self._request("GET", f"/commits/{sha}/status", params={"per_page": PAGE_SIZE})
        latest: dict[str, CommitStatus] = {}
        for item in body.get("statuses", []):
            status = _status(item)
            latest.setdefault(status.context, status)
        return list(latest.values())


def build_github(settings: Settings, env: EnvSettings) -> GitHubPort:
    """The adapter `factory.cli.common.DEPS.github` loads by default."""
    token = env.github_token.get_secret_value() if env.github_token else None
    return RestGitHub(
        repository=settings.github.repository,
        api_url=env.github_api_url or settings.github.api_url,
        token=token,
    )
