"""Lifecycle derivation (data-model § Lifecycle): git + PR + checks -> `LifecycleSnapshot`.

Nothing here writes: state is recomputed from `origin/wo/*` branches, `main`'s bus, and
`GitHubPort` every time. `factory status` fetches before calling this.
"""

from __future__ import annotations

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
from factory.lifecycle.view import BusView, OrderRecord, load_view

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


def required_checks_green(
    record: OrderRecord, statuses: list[CommitStatus]
) -> tuple[bool, list[str]]:
    """Every gate in `checks` has a green `factory/<gate>` status, or failed and overridden.

    Returns (green, gates still missing). An empty `checks` list is never green (FR-011).
    """
    checks = record.order.checks
    if not checks:
        return False, []
    by_context = {s.context: s.state for s in statuses}
    overridden = {o.gate for o in record.of_kind(Override)}
    missing = []
    for gate in checks:
        state = by_context.get(f"{STATUS_PREFIX}{gate}")
        if state == "success" or (state in FAILED_STATUSES and gate in overridden):
            continue
        missing.append(gate)
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
) -> OrderLifecycle:
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
            green, _ = required_checks_green(record, github.list_commit_statuses(pr.head_sha))
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
    view: BusView, github: GitHubPort, settings: Settings, now: datetime
) -> LifecycleSnapshot:
    orders = [
        derive_order(record, view, github, settings, now)
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
    return derive_from_view(view, github, config, now or datetime.now(UTC))
