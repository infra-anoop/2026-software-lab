"""In-memory `GitHubPort` for tests. Frozen at CP0."""

from __future__ import annotations

from datetime import UTC, datetime

from factory.api import CheckRun, CommitStatusValue, PullRequest, PullRequestReview


class RecordedStatus:
    def __init__(
        self, sha: str, context: str, value: str, description: str, target_url: str | None
    ) -> None:
        self.sha = sha
        self.context = context
        self.value = value
        self.description = description
        self.target_url = target_url


class FakeGitHub:
    """Implements `factory.api.GitHubPort`; tests mutate PRs, reviews, and checks directly."""

    def __init__(self) -> None:
        self.prs: dict[int, PullRequest] = {}
        self.reviews: dict[int, list[PullRequestReview]] = {}
        self.runs: dict[str, list[CheckRun]] = {}
        self.statuses: list[RecordedStatus] = []
        self._next_number = 1
        self._next_review = 1

    # --- GitHubPort -----------------------------------------------------------------

    def list_prs_by_head(self, head_branch: str) -> list[PullRequest]:
        return [pr for pr in self.prs.values() if pr.head_ref == head_branch]

    def pr_reviews(self, pr_number: int) -> list[PullRequestReview]:
        return list(self.reviews.get(pr_number, []))

    def check_runs(self, sha: str) -> list[CheckRun]:
        return list(self.runs.get(sha, []))

    def create_pr(self, head_branch: str, base_branch: str, title: str, body: str) -> PullRequest:
        return self.add_pr(head_branch, head_sha="0" * 40, base=base_branch, title=title, body=body)

    def set_commit_status(
        self,
        sha: str,
        context: str,
        value: CommitStatusValue,
        description: str,
        target_url: str | None = None,
    ) -> None:
        self.statuses.append(RecordedStatus(sha, context, value, description, target_url))

    # --- test helpers ---------------------------------------------------------------

    def add_pr(
        self,
        head_branch: str,
        *,
        head_sha: str,
        base: str = "main",
        title: str = "",
        body: str = "",
        open: bool = True,
        merged: bool = False,
        author_login: str = "factory-app[bot]",
    ) -> PullRequest:
        number = self._next_number
        self._next_number += 1
        pr = PullRequest(
            number=number,
            head_ref=head_branch,
            head_sha=head_sha,
            base_ref=base,
            title=title,
            body=body,
            open=open,
            merged=merged,
            author_login=author_login,
            html_url=f"https://github.test/fixture/demo/pull/{number}",
        )
        self.prs[number] = pr
        return pr

    def merge_pr(self, number: int) -> PullRequest:
        pr = self.prs[number].model_copy(update={"open": False, "merged": True})
        self.prs[number] = pr
        return pr

    def close_pr(self, number: int) -> PullRequest:
        pr = self.prs[number].model_copy(update={"open": False, "merged": False})
        self.prs[number] = pr
        return pr

    def add_review(
        self, pr_number: int, *, login: str, review_state: str = "APPROVED", commit_id: str = ""
    ) -> PullRequestReview:
        review = PullRequestReview.model_validate(
            {
                "id": self._next_review,
                "user_login": login,
                "review_state": review_state,
                "commit_id": commit_id or self.prs[pr_number].head_sha,
                "submitted_at": datetime.now(UTC),
            }
        )
        self._next_review += 1
        self.reviews.setdefault(pr_number, []).append(review)
        return review

    def add_check_run(
        self,
        sha: str,
        name: str,
        *,
        run_status: str = "completed",
        conclusion: str | None = "success",
    ) -> CheckRun:
        run = CheckRun.model_validate(
            {"name": name, "head_sha": sha, "run_status": run_status, "conclusion": conclusion}
        )
        self.runs.setdefault(sha, []).append(run)
        return run
