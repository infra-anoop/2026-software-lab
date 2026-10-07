"""Lifecycle derivation (data-model § Lifecycle): git + PR + checks -> `LifecycleSnapshot`.

Nothing here writes: state is recomputed from `origin/wo/*` branches, `main`'s bus, and
`GitHubPort` every time. `factory status` fetches before calling this.
"""

from __future__ import annotations

import posixpath
from datetime import UTC, datetime, timedelta
from pathlib import Path

from factory.api import (
    CommitStatus,
    GitHubPort,
    LifecycleSnapshot,
    OrderLifecycle,
    OrderState,
    PullRequest,
)
from factory.bus.models import Claim, Override, Release, Verdict
from factory.config.settings import Settings, load_settings
from factory.gates.drift.catalog_linkage import CATALOG_NAME, catalog_rows
from factory.gates.drift.catalog_linkage import GATE as LINKAGE_GATE
from factory.gates.registry import load_registry
from factory.lifecycle.view import BusView, OrderRecord, load_view
from factory.orders import git

STATUS_PREFIX = "factory/"
FAILED_STATUSES = frozenset({"failure", "error"})


def pick_pr(prs: list[PullRequest]) -> PullRequest | None:
    """The PR that decides state: merged first, then open, then the newest closed one."""
    for wanted in (lambda p: p.merged, lambda p: p.open):
        found = [p for p in prs if wanted(p)]
        if found:
            return max(found, key=lambda p: p.number)
    return max(prs, key=lambda p: p.number) if prs else None


def latest_verdict(record: OrderRecord) -> Verdict | None:
    verdicts = record.of_kind(Verdict)
    return verdicts[-1] if verdicts else None


def head_catalog_ids(repo: Path, sha: str) -> set[str] | None:
    """Row ids of every `acceptance.md` in the tree of `sha`; None when `sha` is not local."""
    if not git.object_exists(repo, f"{sha}^{{commit}}"):
        return None
    listing = git.run_git(repo, "ls-tree", "-r", "-z", sha).decode("utf-8", errors="replace")
    ids: set[str] = set()
    for record in listing.split("\0"):
        if not record:
            continue
        meta, path = record.split("\t", 1)
        if meta.split(" ")[1] != "blob" or posixpath.basename(path) != CATALOG_NAME:
            continue
        text = git.run_git(repo, "cat-file", "blob", f"{sha}:{path}").decode(errors="replace")
        ids.update(row.cells["id"].strip().strip("`") for row in catalog_rows(text))
    return ids


def required_checks_green(
    record: OrderRecord, statuses: list[CommitStatus], catalog_ids: set[str]
) -> tuple[bool, list[str]]:
    """Every id in `checks` is satisfied by the status of the gate that judges it.

    A catalog row id (in `catalog_ids`, classified first) is judged by
    `catalog-test-linkage`; any other id must be a gate in the installed registry and is
    judged by its own `factory/<gate>` status; an id that is neither is never satisfied.
    A judging status counts when green, or failed and overridden for that gate.
    Returns (green, ids still missing). An empty `checks` list is never green (FR-011).
    """
    checks = record.order.checks
    if not checks:
        return False, []
    gate_ids = set(load_registry().ids())
    by_context = {s.context: s.state for s in statuses}
    overridden = {o.gate for o in record.of_kind(Override)}
    missing = []
    for check_id in checks:
        if check_id in catalog_ids:
            gate = LINKAGE_GATE
        elif check_id in gate_ids:
            gate = check_id
        else:
            missing.append(check_id)
            continue
        state = by_context.get(f"{STATUS_PREFIX}{gate}")
        if state == "success" or (state in FAILED_STATUSES and gate in overridden):
            continue
        missing.append(check_id)
    return not missing, missing


def is_stale(record: OrderRecord, settings: Settings, now: datetime) -> bool:
    window = timedelta(minutes=settings.stale_multiplier * record.order.size_minutes)
    return now - record.tip_time > window


def is_blocked(record: OrderRecord, view: BusView) -> bool:
    if view.open_dependencies(record.order):
        return True
    return bool(record.blocker_questions()) and record.order_id not in view.answered_orders()


def derive_order(
    record: OrderRecord,
    view: BusView,
    github: GitHubPort,
    settings: Settings,
    now: datetime,
    *,
    repo: Path | None = None,
) -> OrderLifecycle:
    """`repo` is the checkout whose objects hold the PR head; without it no `checks` id is
    recognised as a catalog row (the row stays unsatisfied). With it, a PR head missing
    from `repo` satisfies no check (catalog-first needs the head tree)."""
    prs = github.list_prs_by_head(record.branch)
    pr = pick_pr(prs)
    claimed = record.one(Claim) is not None
    released = record.one(Release) is not None
    overlays: list[OrderState] = []

    if record.on_main or (pr is not None and pr.merged):
        state = OrderState.MERGED
    elif released or (pr is not None and not pr.open):
        state = OrderState.RELEASED
    elif pr is not None:
        verdict = latest_verdict(record)
        if verdict is None:
            state = OrderState.IN_REVIEW
        elif verdict.decision == "reject":
            state = OrderState.REJECTED
        else:
            catalog_ids = head_catalog_ids(repo, pr.head_sha) if repo is not None else set()
            green = False
            if catalog_ids is not None:
                statuses = github.list_commit_statuses(pr.head_sha)
                green, _ = required_checks_green(record, statuses, catalog_ids)
            state = OrderState.ACCEPTED if green else OrderState.IN_REVIEW
    elif claimed:
        state = OrderState.CLAIMED
        if is_stale(record, settings, now):
            overlays.append(OrderState.STALE)
    else:
        state = OrderState.ISSUED

    if state not in {OrderState.MERGED, OrderState.RELEASED} and is_blocked(record, view):
        overlays.append(OrderState.BLOCKED_ON_GOVERNOR)

    return OrderLifecycle(
        order_id=record.order_id,
        branch=record.branch,
        state=state,
        overlays=overlays,
        pr_number=pr.number if pr is not None else None,
        owned_paths=list(record.order.owned_paths),
    )


def derive_from_view(
    view: BusView,
    github: GitHubPort,
    settings: Settings,
    now: datetime,
    *,
    repo: Path | None = None,
) -> LifecycleSnapshot:
    orders = [
        derive_order(record, view, github, settings, now, repo=repo)
        for _, record in sorted(view.orders.items())
    ]
    return LifecycleSnapshot(generated_at=now, orders=orders)


def derive_snapshot(
    repo: Path,
    github: GitHubPort,
    *,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> LifecycleSnapshot:
    """Every order's derived state at `now` (default: the current UTC time)."""
    config = settings or load_settings(repo)
    view = load_view(Path(repo), config)
    return derive_from_view(view, github, config, now or datetime.now(UTC), repo=Path(repo))
