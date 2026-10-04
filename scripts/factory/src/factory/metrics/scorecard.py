"""Scorecard (catalogs `scorecard.computed`, `wave1.timebox`) computed from git alone.

Inputs: run-complete events, verdicts and overrides on order branches; decision requests,
locks and corrections on `main`. Wave 1 starts at the first order's issue commit and exits
when every order has landed on `main` (the last landing commit's date).
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from factory.bus.models import Correction, Override, RunComplete, Verdict
from factory.config.settings import Settings, load_settings
from factory.lifecycle.view import BusView, OrderRecord, load_view
from factory.metrics.history import count_bookkeeping_commits
from factory.orders import git

WAVE1_TIMEBOX_WORKING_DAYS = 5


def working_day_number(start: date, end: date) -> int:
    """`end`'s working-day index counting `start` as day 1 and skipping Sat/Sun."""
    days = 0
    current = start
    while current <= end:
        if current.weekday() < 5:
            days += 1
        current += timedelta(days=1)
    return max(days, 1)


def _share(hits: int, total: int) -> float | None:
    return hits / total if total else None


def _order_path(settings: Settings, order_id: str) -> str:
    return f"{settings.bus_dir}/orders/{order_id}/order.yaml"


def issued_at(repo: Path, record: OrderRecord, settings: Settings) -> datetime | None:
    dates = git.added_dates(repo, record.ref, _order_path(settings, record.order_id))
    return min(dates) if dates else None


def landed_at(
    repo: Path, view: BusView, record: OrderRecord, settings: Settings
) -> datetime | None:
    if view.main_ref is None or not record.on_main:
        return None
    path = _order_path(settings, record.order_id)
    dates = git.added_dates(repo, view.main_ref, path, first_parent=True)
    return min(dates) if dates else None


def _first_verdicts(view: BusView) -> list[Verdict]:
    firsts = []
    for record in view.orders.values():
        verdicts = record.of_kind(Verdict)
        if verdicts:
            firsts.append(verdicts[0])
    return firsts


def _wave1(repo: Path, view: BusView, settings: Settings) -> dict[str, Any]:
    issued = [issued_at(repo, r, settings) for r in view.orders.values()]
    starts = [d for d in issued if d is not None]
    start = min(starts) if starts else None
    landings = [landed_at(repo, view, r, settings) for r in view.orders.values()]
    exited = bool(landings) and all(d is not None for d in landings)
    end = max(d for d in landings if d is not None) if exited else None
    days = working_day_number(start.date(), end.date()) if start and end else None
    return {
        "wave1_start": start.isoformat() if start else None,
        "wave1_exit": end.isoformat() if end else None,
        "wave1_working_days": days,
        "wave1_within_timebox": days <= WAVE1_TIMEBOX_WORKING_DAYS if days else None,
    }


def scorecard_from_view(repo: Path, view: BusView, settings: Settings) -> dict[str, Any]:
    runs = {
        record.order_id: run
        for record in view.orders.values()
        if (run := record.one(RunComplete)) is not None
    }
    corrections = [m for m in view.main_messages if isinstance(m, Correction)]
    drift_targets = {c.target for c in corrections if c.tag == "drift"}
    firsts = _first_verdicts(view)
    requests = view.requests()
    locks = view.locks()
    points = Counter(
        requests[decision_id].feature for decision_id in locks if decision_id in requests
    )
    overrides = [o for r in view.orders.values() for o in r.of_kind(Override)]
    costs = [run.cost_usd for run in runs.values() if run.cost_usd is not None]
    card: dict[str, Any] = {
        "orders": len(view.orders),
        "runs_complete": len(runs),
        "drift": _share(sum(1 for oid in runs if oid not in drift_targets), len(runs)),
        "first_pass_acceptance": _share(sum(v.decision == "accept" for v in firsts), len(firsts)),
        "rework_loops": sum(v.decision == "reject" for v in firsts),
        "decision_points_per_feature": dict(sorted(points.items())),
        "governor_minutes": sum(lock.governor_minutes for lock in locks.values()),
        "governor_minutes_estimated": True,
        "wall_minutes": sum(run.wall_minutes for run in runs.values()),
        "governor_interrupts": sum(run.governor_interrupts for run in runs.values()),
        "overrides": len(overrides),
        "overrides_per_gate": dict(sorted(Counter(o.gate for o in overrides).items())),
        "deviations": sum(run.deviations_count for run in runs.values()),
        "cost_usd": sum(costs) if costs else None,
        "cost_usd_estimated": any(run.cost_usd_estimated for run in runs.values()),
        "corrections": len(corrections),
    }
    if view.main_ref:
        card["bookkeeping_commits"] = count_bookkeeping_commits(
            repo, since=view.main_ref, bus_dir=settings.bus_dir
        )
    card.update(_wave1(repo, view, settings))
    return card


def compute_scorecard(repo: Path, *, settings: Settings | None = None) -> dict[str, Any]:
    config = settings or load_settings(repo)
    return scorecard_from_view(Path(repo), load_view(Path(repo), config), config)
