"""T031 — scorecard from events, verdicts, overrides, corrections, decision locks.

Catalogs: `scorecard.computed`, `wave1.timebox`.
"""

from __future__ import annotations

import importlib
import json
import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from types import ModuleType
from typing import Any

import pytest

from factory.cli import exit_codes
from factory.gates.registry import load_registry
from tests.fixtures.cli_runner import FactoryCli
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
@pytest.mark.usefixtures("p1_implemented")
def test_scorecard_wave1_exit_when_every_order_merged(
    repo: RepoBuilder,
    factory_cli: FactoryCli,
    exit_at: datetime,
    exit_date: str,
    working_days: int,
    within: bool,
) -> None:
    _seed_completed_wave(repo, exit_at)
    _p1_statuses(repo, repo.head_sha("main"))
    card = _cli_card(factory_cli, repo)
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


# --- PR-A5: SC-013 Wave 1 exit -----------------------------------------------------------
# Wave 1 exits only when all three hold (amendment-05):
#   (a) every Wave 1 order has a run record (run_complete), an accepted latest verdict, and has
#       landed on main;
#   (b) every `priority: P1` row in gates.yaml is implemented: its entrypoint resolves;
#   (c) the main commit at the exit point (the last Wave 1 landing) has a `success`
#       `factory/<gate-id>` commit status for every P1 gate, read through the GitHub port.
# Wave 1 cohort: orders issued before `bus/postmortems/wave1-retro.yaml` first lands on main
# (every order while no retro has landed). Sprint S: orders whose `refs` include
# `notes/sprints/S.md`. Both are provisional (orchestrator) and up for T* review.

P1_GATES = [gate for gate in load_registry().gates if gate.priority == "P1"]
GATED = "red-first-proof"
SPRINT = "2026-10-sprint-02"
OTHER_SPRINT = "2026-11-sprint-03"
WAVE1_RETRO = "bus/postmortems/wave1-retro.yaml"
FIFTH_DAY_EXIT = datetime(2026, 10, 7, 17, 0, tzinfo=UTC)


def _stub_gate(ctx: object) -> None:
    raise AssertionError("the scorecard resolves P1 entrypoints; it never runs gates")


@pytest.fixture
def p1_implemented(monkeypatch: pytest.MonkeyPatch) -> None:
    """Condition (b) true: every P1 entrypoint resolves to a stub module in `sys.modules`.

    Test environment only; slices B and C own the real gate modules.
    """
    modules: dict[str, ModuleType] = {}
    for gate in P1_GATES:
        module = modules.setdefault(gate.module, ModuleType(gate.module))
        setattr(module, gate.function, _stub_gate)
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)


def _p1_statuses(
    repo: RepoBuilder, sha: str, *, missing: str | None = None, failing: str | None = None
) -> None:
    """Condition (c): a `factory/<gate-id>` status on `sha` for every P1 gate."""
    for gate in P1_GATES:
        if gate.id == missing:
            continue
        value = "failure" if gate.id == failing else "success"
        repo.github.set_commit_status(sha, f"factory/{gate.id}", value, "fixture")


def _sprint_ref(sprint: str) -> str:
    return f"notes/sprints/{sprint}.md"


def _order_fields(order_id: str, refs: list[str] | None) -> dict[str, Any]:
    fields: dict[str, Any] = {"feature": FEATURE, "owned_paths": [f"apps/demo/{order_id}/**"]}
    if refs is not None:
        fields["refs"] = refs
    return fields


def _run_order(
    repo: RepoBuilder,
    slug: str,
    issued: datetime,
    landed: datetime | None,
    *,
    run_record: bool = True,
    verdicts: tuple[str, ...] = ("accept",),
    refs: list[str] | None = None,
) -> str:
    """Issue, claim, (run record), verdicts in order, then land on main at `landed`."""
    order_id = oid(slug)
    repo.issue_order(order(order_id, **_order_fields(order_id, refs)), when=issued)
    repo.add_event(order_id, message("claim", order_id=order_id), when=issued)
    if run_record:
        repo.add_event(
            order_id,
            message("run_complete", order_id=order_id, wall_minutes=30),
            when=issued + timedelta(hours=1),
        )
    if verdicts:
        pr = repo.make_pr(f"wo/{order_id}", open=False, merged=landed is not None)
        for n, decision in enumerate(verdicts, start=1):
            repo.add_event(
                order_id,
                message(
                    "verdict",
                    order_id=order_id,
                    id=f"{order_id}.verdict-{n:02d}",
                    decision=decision,
                    inputs=[{"path": f"bus/orders/{order_id}/order.yaml", "sha": pr.head_sha}],
                ),
                when=issued + timedelta(hours=1 + n),
            )
    if landed is not None:
        _land(repo, order_id, landed)
    return order_id


def _two_order_wave(
    repo: RepoBuilder,
    prefix: str,
    exit_at: datetime,
    *,
    refs: list[str] | None = None,
    **last: Any,
) -> str:
    """Same shape as `_seed_completed_wave`; returns the main commit of the 2nd landing."""
    _run_order(
        repo, f"{prefix}-0", WAVE1_START, WAVE1_START + timedelta(days=1, hours=5), refs=refs
    )
    _run_order(
        repo, f"{prefix}-1", WAVE1_START + timedelta(days=1, hours=6), exit_at, refs=refs, **last
    )
    return repo.head_sha("main")


def _land_wave1_retro(repo: RepoBuilder, when: datetime) -> None:
    repo.checkout("main")
    repo.write(WAVE1_RETRO, "# Phase 9 retro (fixture: only its landing date is read here)\n")
    repo.commit("bus: wave1 retro", when=when)
    repo.push("main")


def _cli_card(factory_cli: FactoryCli, repo: RepoBuilder, *args: str) -> dict[str, Any]:
    result = factory_cli("scorecard", "--json", *args, repo=repo.path)
    assert result.exit_code == exit_codes.OK, f"{result.stdout}\n{result.stderr}"
    data: dict[str, Any] = json.loads(result.stdout)["data"]
    return data


def _assert_not_exited(card: dict[str, Any], why: str) -> None:
    assert card["wave1_exit"] is None, f"{why}: {card['wave1_exit']}"
    assert card.get("wave1_working_days") is None
    assert card.get("wave1_within_timebox") is None


P1_NEGATIVE_CASES = ["status-missing", "status-failure", "status-on-other-commit", "unresolvable"]


@pytest.mark.usefixtures("p1_implemented")
@pytest.mark.parametrize("case", P1_NEGATIVE_CASES)
def test_scorecard_wave1_not_exited_unless_every_p1_gate_implemented_and_green(
    repo: RepoBuilder, factory_cli: FactoryCli, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    """Every order is accepted and landed (a), but one P1 gate breaks (b) or (c)."""
    _seed_completed_wave(repo, FIFTH_DAY_EXIT)
    exit_sha = repo.head_sha("main")
    if case == "status-missing":
        _p1_statuses(repo, exit_sha, missing=GATED)
    elif case == "status-failure":
        _p1_statuses(repo, exit_sha, failing=GATED)
    elif case == "status-on-other-commit":
        _p1_statuses(repo, repo.head_sha("main^"))
    else:
        _p1_statuses(repo, exit_sha)
        monkeypatch.setitem(sys.modules, load_registry().get(GATED).module, None)
    card = _cli_card(factory_cli, repo)
    assert str(card["wave1_start"]).startswith("2026-10-01"), card["wave1_start"]
    _assert_not_exited(card, f"{case}: SC-013 needs every P1 gate implemented and green at exit")


PRE_EXIT_CASES = {
    "no-run-record": {"run_record": False},
    "no-verdict": {"verdicts": ()},
    "latest-verdict-reject": {"verdicts": ("accept", "reject")},
}


@pytest.mark.usefixtures("p1_implemented")
@pytest.mark.parametrize("last", list(PRE_EXIT_CASES.values()), ids=list(PRE_EXIT_CASES))
def test_scorecard_wave1_not_exited_until_every_order_has_run_record_and_acceptance(
    repo: RepoBuilder, factory_cli: FactoryCli, last: dict[str, Any]
) -> None:
    """(b) and (c) hold and both orders landed, but the 2nd order breaks (a)."""
    exit_sha = _two_order_wave(repo, "pre", FIFTH_DAY_EXIT, **last)
    _p1_statuses(repo, exit_sha)
    card = _cli_card(factory_cli, repo)
    assert str(card["wave1_start"]).startswith("2026-10-01"), card["wave1_start"]
    _assert_not_exited(card, "SC-013 needs a run record and an accepted latest verdict per order")


@pytest.mark.usefixtures("p1_implemented")
def test_scorecard_cli_wave1_exit_after_rework_accepted(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    """A rejected first verdict followed by an accepted one counts as accepted (latest wins)."""
    exit_sha = _two_order_wave(repo, "rework", FIFTH_DAY_EXIT, verdicts=("reject", "accept"))
    _p1_statuses(repo, exit_sha)
    card = _cli_card(factory_cli, repo)
    assert str(card["wave1_start"]).startswith("2026-10-01"), card["wave1_start"]
    assert str(card["wave1_exit"]).startswith("2026-10-07"), card["wave1_exit"]
    assert card.get("wave1_working_days") == 5
    assert card.get("wave1_within_timebox") is True


@pytest.mark.usefixtures("p1_implemented")
def test_scorecard_wave1_exit_survives_later_orders(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    """Cohort boundary: `bus/postmortems/wave1-retro.yaml` landing on main closes Wave 1.

    Orders issued after the retro landed are not Wave 1 (T070: no Wave 2 order before the
    retro), so an open later order neither erases the exit nor, once landed, moves it.
    """
    exit_sha = _two_order_wave(repo, "w1", FIFTH_DAY_EXIT)
    _p1_statuses(repo, exit_sha)
    _land_wave1_retro(repo, datetime(2026, 10, 8, 12, 0, tzinfo=UTC))
    later = oid("w2-later")
    issued = datetime(2026, 10, 9, 9, 0, tzinfo=UTC)
    repo.issue_order(order(later, **_order_fields(later, None)), when=issued)
    repo.add_event(later, message("claim", order_id=later), when=issued)

    card = _cli_card(factory_cli, repo)
    assert str(card["wave1_exit"]).startswith("2026-10-07"), (
        f"an order issued after the Wave 1 retro is not Wave 1: {card['wave1_exit']}"
    )
    assert card.get("wave1_working_days") == 5
    assert card.get("wave1_within_timebox") is True

    repo.add_event(
        later,
        message("run_complete", order_id=later, wall_minutes=30),
        when=issued + timedelta(hours=1),
    )
    _land(repo, later, datetime(2026, 10, 12, 9, 0, tzinfo=UTC))
    card = _cli_card(factory_cli, repo)
    assert str(card["wave1_exit"]).startswith("2026-10-07"), (
        f"a later order landing must not move the Wave 1 exit: {card['wave1_exit']}"
    )
    assert card.get("wave1_working_days") == 5


@pytest.mark.usefixtures("p1_implemented")
def test_scorecard_sprint_scopes_wave1(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    """Sprint membership: an order is in sprint S when its `refs` include `notes/sprints/S.md`.

    `factory scorecard --sprint S` computes `orders` and every wave1_* field over S's orders only.
    """
    exit_sha = _two_order_wave(repo, "s02", FIFTH_DAY_EXIT, refs=[_sprint_ref(SPRINT)])
    _p1_statuses(repo, exit_sha)
    other = oid("s03-open")
    issued = WAVE1_START + timedelta(days=1)
    repo.issue_order(order(other, **_order_fields(other, [_sprint_ref(OTHER_SPRINT)])), when=issued)
    repo.add_event(other, message("claim", order_id=other), when=issued)

    unscoped = _cli_card(factory_cli, repo)
    assert unscoped["orders"] == 3
    assert unscoped["wave1_exit"] is None, "unscoped, the open sprint-03 order keeps Wave 1 open"

    scoped = _cli_card(factory_cli, repo, "--sprint", SPRINT)
    assert scoped["orders"] == 2, f"--sprint {SPRINT} counts only its orders: {scoped['orders']}"
    assert str(scoped["wave1_start"]).startswith("2026-10-01"), scoped["wave1_start"]
    assert str(scoped["wave1_exit"]).startswith("2026-10-07"), (
        f"--sprint {SPRINT} must ignore the other sprint's open order: {scoped['wave1_exit']}"
    )
    assert scoped.get("wave1_working_days") == 5
    assert scoped.get("wave1_within_timebox") is True

    later_sprint = _cli_card(factory_cli, repo, "--sprint", OTHER_SPRINT)
    assert later_sprint["orders"] == 1
    assert str(later_sprint["wave1_start"]).startswith("2026-10-02"), later_sprint["wave1_start"]
    assert later_sprint["wave1_exit"] is None
