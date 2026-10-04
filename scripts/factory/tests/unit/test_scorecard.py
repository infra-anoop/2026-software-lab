"""T031 — scorecard from events, verdicts, overrides, corrections, decision locks.

Catalogs: `scorecard.computed`, `wave1.timebox`.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from tests.fixtures.repo_builder import RepoBuilder, message, order

DAY = "20261007"
FEATURE = "demo-feature"


def oid(slug: str) -> str:
    return f"wo-{DAY}-{slug}"


def load_scorecard() -> Callable[..., dict[str, Any]]:
    try:
        module = importlib.import_module("factory.metrics.scorecard")
    except ImportError as exc:
        pytest.fail(f"factory.metrics.scorecard is not implemented: {exc}")
    compute = getattr(module, "compute_scorecard", None)
    assert callable(compute), "factory.metrics.scorecard must export compute_scorecard"
    return compute


def _seed(repo: RepoBuilder) -> None:
    repo.add_demo_feature()
    repo.checkout("main")
    repo.write_message(
        message(
            "decision_request",
            decision_id="pick-host",
            blocking=True,
            feature=FEATURE,
            prompt="Which host should the demo deploy to?",
        )
    )
    repo.write_message(
        message(
            "decision_lock",
            decision_id="pick-host",
            chosen="Railway",
            governor_minutes=4,
        )
    )
    repo.write_message(
        message(
            "correction",
            target=oid("rework"),
            tag="drift",
            what_was_wrong="Worker swapped the named host.",
        )
    )
    repo.commit("scorecard decisions + correction")
    repo.push("main")

    first = oid("first-pass")
    t0 = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
    repo.issue_order(
        order(first, feature=FEATURE, owned_paths=[f"apps/demo/{first}/**"]),
        when=t0,
    )
    repo.add_event(first, message("claim", order_id=first), when=t0)
    repo.add_event(
        first,
        message(
            "run_complete",
            order_id=first,
            wall_minutes=50,
            governor_interrupts=1,
            cost_usd=1.2,
            cost_usd_estimated=True,
            deviations_count=1,
        ),
        when=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
    )
    pr = repo.make_pr(f"wo/{first}", open=False, merged=True)
    repo.github.merge_pr(pr.number)
    repo.add_event(
        first,
        message(
            "verdict",
            order_id=first,
            decision="accept",
            inputs=[{"path": f"bus/orders/{first}/order.yaml", "sha": pr.head_sha}],
        ),
    )
    repo.add_event(
        first,
        message(
            "override",
            order_id=first,
            gate="red-first-proof",
            pr=pr.number,
            reason="Base suite broken; verified red by hand.",
            gate_class="drift",
        ),
    )

    rework = oid("rework")
    repo.issue_order(
        order(rework, feature=FEATURE, owned_paths=[f"apps/demo/{rework}/**"]),
        when=datetime(2026, 10, 2, 9, 0, tzinfo=UTC),
    )
    repo.add_event(rework, message("claim", order_id=rework))
    repo.add_event(
        rework,
        message(
            "run_complete",
            order_id=rework,
            wall_minutes=40,
            governor_interrupts=0,
            cost_usd=0.8,
            deviations_count=0,
        ),
    )
    pr2 = repo.make_pr(f"wo/{rework}")
    repo.add_event(
        rework,
        message(
            "verdict",
            order_id=rework,
            decision="reject",
            inputs=[{"path": f"bus/orders/{rework}/order.yaml", "sha": pr2.head_sha}],
        ),
    )


def test_scorecard_computes_intent_yaml_metrics(repo: RepoBuilder) -> None:
    _seed(repo)
    card = load_scorecard()(repo.path, settings=repo.settings)
    required = {
        "drift",
        "first_pass_acceptance",
        "decision_points_per_feature",
        "governor_minutes",
        "rework_loops",
        "wave1_start",
        "wave1_exit",
    }
    missing = required - set(card)
    assert not missing, f"scorecard missing {missing}: {sorted(card)}"

    # 2 completed runs; 1 has a drift correction → drift = 0.5
    assert card["drift"] == pytest.approx(0.5)
    # 1 accept-first, 1 reject-first → first-pass = 0.5
    assert card["first_pass_acceptance"] == pytest.approx(0.5)
    points = card["decision_points_per_feature"]
    assert isinstance(points, dict)
    assert points.get(FEATURE) == 1
    assert card["governor_minutes"] == pytest.approx(4)
    assert card.get("governor_minutes_estimated") is True
    assert card["rework_loops"] == 1
    start = card["wave1_start"]
    assert str(start).startswith("2026-10-01")
    # Wave 1 has not exited: one order still open / rejected
    assert card["wave1_exit"] is None


WAVE1_START = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)  # Thursday = working day 1


def _git_dates(when: datetime) -> dict[str, str]:
    stamp = when.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S+0000")
    return {"GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}


def _land(repo: RepoBuilder, order_id: str, when: datetime) -> None:
    """Merge `wo/<order-id>` into main at `when` (what a GitHub merge leaves in git)."""
    repo.checkout("main")
    repo.git(
        "merge",
        "--no-ff",
        "-q",
        "-m",
        f"Merge wo/{order_id}",
        f"wo/{order_id}",
        env=_git_dates(when),
    )
    repo.push("main")


def _seed_completed_wave(repo: RepoBuilder, exit_at: datetime) -> None:
    """Two orders, each run complete, accepted, and merged; the second merge is `exit_at`."""
    issues = [WAVE1_START, WAVE1_START + timedelta(days=1, hours=6)]
    landings = [WAVE1_START + timedelta(days=1, hours=5), exit_at]
    for n, (issued_at, landed_at) in enumerate(zip(issues, landings, strict=True)):
        order_id = oid(f"wave-{n}")
        repo.issue_order(
            order(order_id, feature=FEATURE, owned_paths=[f"apps/demo/{order_id}/**"]),
            when=issued_at,
        )
        repo.add_event(order_id, message("claim", order_id=order_id), when=issued_at)
        repo.add_event(
            order_id,
            message("run_complete", order_id=order_id, wall_minutes=30),
            when=issued_at + timedelta(hours=1),
        )
        pr = repo.make_pr(f"wo/{order_id}", open=False, merged=True)
        repo.add_event(
            order_id,
            message(
                "verdict",
                order_id=order_id,
                decision="accept",
                inputs=[{"path": f"bus/orders/{order_id}/order.yaml", "sha": pr.head_sha}],
            ),
            when=issued_at + timedelta(hours=2),
        )
        _land(repo, order_id, landed_at)


# Working days count the start day as day 1 and skip Saturday/Sunday (SC-013: 5 working days).
# Thu 1 Oct = 1, Fri 2 = 2, Mon 5 = 3, Tue 6 = 4, Wed 7 = 5, Thu 8 = 6.
EXIT_CASES = {
    "fifth-working-day": (datetime(2026, 10, 7, 17, 0, tzinfo=UTC), "2026-10-07", 5, True),
    "sixth-working-day": (datetime(2026, 10, 8, 9, 0, tzinfo=UTC), "2026-10-08", 6, False),
}


@pytest.mark.parametrize(
    ("exit_at", "exit_date", "working_days", "within"),
    list(EXIT_CASES.values()),
    ids=list(EXIT_CASES),
)
def test_scorecard_wave1_exit_when_every_order_merged(
    repo: RepoBuilder, exit_at: datetime, exit_date: str, working_days: int, within: bool
) -> None:
    _seed_completed_wave(repo, exit_at)
    card = load_scorecard()(repo.path, settings=repo.settings)
    assert str(card["wave1_start"]).startswith("2026-10-01"), card["wave1_start"]
    assert card["wave1_exit"] is not None, "every order merged: Wave 1 has exited"
    assert str(card["wave1_exit"]).startswith(exit_date), card["wave1_exit"]
    assert card.get("wave1_working_days") == working_days, card.get("wave1_working_days")
    assert card.get("wave1_within_timebox") is within


def test_scorecard_includes_fr035_run_totals(repo: RepoBuilder) -> None:
    _seed(repo)
    card = load_scorecard()(repo.path, settings=repo.settings)
    assert card.get("wall_minutes") == pytest.approx(90)
    assert card.get("governor_interrupts") == 1
    assert card.get("overrides") == 1 or card.get("override_count") == 1
    assert card.get("deviations") == 1 or card.get("deviations_count") == 1
    assert card.get("cost_usd") == pytest.approx(2.0)
    assert card.get("cost_usd_estimated") is True
