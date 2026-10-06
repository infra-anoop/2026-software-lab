"""Gate `factory-status-test` (T102, PR-C3; I-M4; catalog `board.matches_reality`).

`main`'s lifecycle derivation runs over the head's bus alone, with no GitHub data, and
every order folder on the head bus must be on the derived board exactly once. The head
is only data (D5): bus files are read as git objects at `head_sha`; nothing from the
head is imported, run or checked out.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path, PurePosixPath

from factory.api import (
    CheckRun,
    CommitStatus,
    CommitStatusValue,
    GateContext,
    GateResult,
    PullRequest,
    PullRequestReview,
)
from factory.bus.store import BusError, list_bus_paths
from factory.config.settings import Settings
from factory.lifecycle import derive
from factory.lifecycle.view import BusView, OrderRecord, load_messages, load_order
from factory.orders import git

GATE_ID = "factory-status-test"


class NoGitHub:
    """A `GitHubPort` with no PRs, reviews, checks or statuses: the board from bus data only."""

    def list_prs_by_head(self, head_branch: str) -> list[PullRequest]:
        return []

    def pr_reviews(self, pr_number: int) -> list[PullRequestReview]:
        return []

    def check_runs(self, sha: str) -> list[CheckRun]:
        return []

    def create_pr(self, head_branch: str, base_branch: str, title: str, body: str) -> PullRequest:
        raise RuntimeError(f"{GATE_ID} writes nothing")

    def set_commit_status(
        self,
        sha: str,
        context: str,
        value: CommitStatusValue,
        description: str,
        target_url: str | None = None,
    ) -> None:
        raise RuntimeError(f"{GATE_ID} writes nothing")

    def list_commit_statuses(self, sha: str) -> list[CommitStatus]:
        return []


def passed(note: str) -> GateResult:
    return GateResult(gate_id=GATE_ID, passed=True, messages=[f"{GATE_ID}: {note}"])


def failed(problems: list[str]) -> GateResult:
    return GateResult(
        gate_id=GATE_ID, passed=False, messages=[f"{GATE_ID}: {problem}" for problem in problems]
    )


def order_folders(paths: list[str], bus_dir: str) -> list[str]:
    """Order ids that have a folder `<bus>/orders/<id>/` holding at least one bus file."""
    found = set()
    for path in paths:
        parts = PurePosixPath(path).parts
        if len(parts) >= 4 and parts[0] == bus_dir and parts[1] == "orders":
            found.add(parts[2])
    return sorted(found)


def head_view(repo: Path, head: str, base: str, settings: Settings, ids: list[str]) -> BusView:
    """`main`'s read model over one commit: the head's bus is both `main`'s and the orders'."""
    messages = load_messages(repo, head, settings)
    orders: dict[str, OrderRecord] = {}
    for order_id in ids:
        record = load_order(repo, head, order_id, settings, main_ref=base)
        if record is not None:
            orders[order_id] = record
    return BusView(main_ref=head, main_messages=messages, orders=orders)


def judge(ctx: GateContext) -> list[str]:
    repo, head, settings = ctx.repo_path, ctx.head_sha, ctx.config
    if git.rev_parse(repo, head) is None:
        return [f"head commit {head} is not readable; there is no bus to derive a board from"]
    paths = list_bus_paths(repo, head, settings.bus_dir)
    folders = order_folders(paths, settings.bus_dir)
    view = head_view(repo, head, ctx.base_sha, settings, folders)
    now = git.commit_time(repo, head)
    snapshot = derive.derive_from_view(view, NoGitHub(), settings, now)

    counts = Counter(item.order_id for item in snapshot.orders)
    problems = [
        f"{settings.bus_dir}/orders/{order_id}/ is on the head bus but order {order_id} is not"
        f" on the derived board{'' if order_id in view.orders else ' (its folder holds no order)'}"
        for order_id in folders
        if counts[order_id] == 0
    ]
    problems += [
        f"the derived board shows {order_id} {n} times" for order_id, n in counts.items() if n > 1
    ]
    problems += [
        f"the derived board shows {order_id}, which has no order folder on the head bus"
        for order_id in sorted(counts)
        if order_id not in folders
    ]
    return problems


def run(ctx: GateContext) -> GateResult:
    try:
        problems = judge(ctx)
    except BusError as exc:
        return failed([f"cannot derive the board from the head bus: {exc}"])
    except git.GitError as exc:
        return failed([f"cannot read the head commit {ctx.head_sha}: {exc}"])
    except Exception as exc:  # noqa: BLE001 - fail closed: no exception escapes the gate
        path = getattr(exc, "path", None)
        where = f" in {path}" if path else ""
        return failed(
            [f"cannot derive the board from head {ctx.head_sha}: {type(exc).__name__}{where}"]
        )
    if problems:
        return failed(problems)
    return passed("every order folder on the head bus is on main's derived board")
