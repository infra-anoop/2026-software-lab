"""Scorecard (catalogs `scorecard.computed`, `wave1.timebox`).

Inputs: run-complete events, verdicts and overrides on order branches; decision requests,
locks and corrections on `main`; for the Wave 1 exit, commit statuses through `GitHubPort`.

Scope: with a sprint, only orders whose effective `refs` include `notes/sprints/<S>.md`.
Wave 1 cohort: orders in scope issued before `<bus>/postmortems/wave1-retro.yaml` first
landed on `main` (every order in scope while no retro has landed). Wave 1 starts at the
cohort's first issue commit and exits (SC-013) at the `main` commit of its last landing,
only when (a) every cohort order has a run record, an accepted latest verdict, and has
landed; (b) every P1 gate's entrypoint resolves; and (c) that commit has a `success`
`factory/<gate-id>` status for every P1 gate.
"""

from __future__ import annotations

import importlib
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from factory.api import GitHubPort
from factory.bus.models import Correction, Override, RunComplete, Verdict
from factory.config.settings import Settings, load_settings
from factory.gates.registry import Gate, load_registry
from factory.lifecycle.derive import STATUS_PREFIX, latest_verdict
from factory.lifecycle.view import BusView, OrderRecord, load_view
from factory.metrics.history import count_bookkeeping_commits
from factory.orders import git

WAVE1_TIMEBOX_WORKING_DAYS = 5
WAVE1_RETRO = "postmortems/wave1-retro.yaml"

Landing = tuple[str, datetime]


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


def sprint_ref(sprint: str) -> str:
    return f"notes/sprints/{sprint}.md"


def in_scope(record: OrderRecord, sprint: str | None) -> bool:
    return sprint is None or sprint_ref(sprint) in record.order.refs


def issued_at(repo: Path, record: OrderRecord, settings: Settings) -> datetime | None:
    commits = git.added_commits(repo, record.ref, _order_path(settings, record.order_id))
    return min(when for _, when in commits) if commits else None


def _first_landing(repo: Path, view: BusView, path: str) -> Landing | None:
    """The first-parent `main` commit that first added `path`."""
    if view.main_ref is None:
        return None
    commits = git.added_commits(repo, view.main_ref, path, first_parent=True)
    return min(commits, key=lambda commit: commit[1]) if commits else None


def landed_at(repo: Path, view: BusView, record: OrderRecord, settings: Settings) -> Landing | None:
    if not record.on_main:
        return None
    return _first_landing(repo, view, _order_path(settings, record.order_id))


def _first_verdicts(records: list[OrderRecord]) -> list[Verdict]:
    firsts = []
    for record in records:
        verdicts = record.of_kind(Verdict)
        if verdicts:
            firsts.append(verdicts[0])
    return firsts


def _resolves(gate: Gate) -> bool:
    """The gate's entrypoint imports (resolution only; the scorecard never runs a gate)."""
    try:
        return callable(getattr(importlib.import_module(gate.module), gate.function))
    except (ImportError, AttributeError):
        return False


def _p1_green(sha: str, github: GitHubPort | None) -> bool:
    """(b) every P1 gate resolves and (c) has a `success` status on `sha`."""
    gates = [gate for gate in load_registry().gates if gate.priority == "P1"]
    if github is None or not all(_resolves(gate) for gate in gates):
        return False
    states = {status.context: status.state for status in github.list_commit_statuses(sha)}
    return all(states.get(f"{STATUS_PREFIX}{gate.id}") == "success" for gate in gates)


def _cohort_exit(
    repo: Path, view: BusView, cohort: list[OrderRecord], settings: Settings
) -> Landing | None:
    """(a): the last landing, once every cohort order has run, been accepted, and landed."""
    landings = []
    for record in cohort:
        verdict = latest_verdict(record)
        if record.one(RunComplete) is None or verdict is None or verdict.decision != "accept":
            return None
        landing = landed_at(repo, view, record, settings)
        if landing is None:
            return None
        landings.append(landing)
    return max(landings, key=lambda landing: landing[1]) if landings else None


def _wave1(
    repo: Path,
    view: BusView,
    records: list[OrderRecord],
    settings: Settings,
    github: GitHubPort | None,
) -> dict[str, Any]:
    retro = _first_landing(repo, view, f"{settings.bus_dir}/{WAVE1_RETRO}")
    issued = {record.order_id: issued_at(repo, record, settings) for record in records}
    cohort = [
        record
        for record in records
        if (when := issued[record.order_id]) is not None and (retro is None or when < retro[1])
    ]
    starts = [when for record in cohort if (when := issued[record.order_id]) is not None]
    start = min(starts) if starts else None
    landing = _cohort_exit(repo, view, cohort, settings)
    end = landing[1] if landing is not None and _p1_green(landing[0], github) else None
    days = working_day_number(start.date(), end.date()) if start and end else None
    return {
        "wave1_start": start.isoformat() if start else None,
        "wave1_exit": end.isoformat() if end else None,
        "wave1_working_days": days,
        "wave1_within_timebox": days <= WAVE1_TIMEBOX_WORKING_DAYS if days else None,
    }


def scorecard_from_view(
    repo: Path,
    view: BusView,
    settings: Settings,
    *,
    github: GitHubPort | None = None,
    sprint: str | None = None,
) -> dict[str, Any]:
    """Order-derived metrics cover the sprint's orders; `main`-derived ones the whole bus."""
    records = [record for record in view.orders.values() if in_scope(record, sprint)]
    runs = {
        record.order_id: run for record in records if (run := record.one(RunComplete)) is not None
    }
    corrections = [m for m in view.main_messages if isinstance(m, Correction)]
    drift_targets = {c.target for c in corrections if c.tag == "drift"}
    firsts = _first_verdicts(records)
    requests = view.requests()
    locks = view.locks()
    points = Counter(
        requests[decision_id].feature for decision_id in locks if decision_id in requests
    )
    overrides = [o for r in records for o in r.of_kind(Override)]
    costs = [run.cost_usd for run in runs.values() if run.cost_usd is not None]
    card: dict[str, Any] = {
        "orders": len(records),
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
    card.update(_wave1(repo, view, records, settings, github))
    return card


def compute_scorecard(
    repo: Path,
    *,
    settings: Settings | None = None,
    github: GitHubPort | None = None,
    sprint: str | None = None,
) -> dict[str, Any]:
    """Without `github`, SC-013 (c) cannot be confirmed, so `wave1_exit` stays null."""
    config = settings or load_settings(repo)
    view = load_view(Path(repo), config)
    return scorecard_from_view(Path(repo), view, config, github=github, sprint=sprint)
