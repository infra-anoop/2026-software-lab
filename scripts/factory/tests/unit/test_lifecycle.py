"""T018 — lifecycle derivation rules (data-model.md § Lifecycle)."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from factory.api import OVERLAY_STATES, GitHubPort, LifecycleSnapshot, OrderState
from tests.fixtures.repo_builder import RepoBuilder, message, order

DAY = "20261007"


def oid(slug: str) -> str:
    return f"wo-{DAY}-{slug}"


def load_derive() -> Callable[..., LifecycleSnapshot]:
    try:
        module = importlib.import_module("factory.lifecycle.derive")
    except ImportError as exc:
        pytest.fail(f"factory.lifecycle.derive is not implemented: {exc}")
    derive = getattr(module, "derive_snapshot", None)
    assert callable(derive), "factory.lifecycle.derive must export derive_snapshot"
    return derive


def snapshot(
    repo: RepoBuilder,
    github: GitHubPort | None = None,
    *,
    now: datetime | None = None,
) -> LifecycleSnapshot:
    derive = load_derive()
    before = repo.git("status", "--porcelain")
    result = derive(repo.path, github or repo.github, settings=repo.settings, now=now)
    assert isinstance(result, LifecycleSnapshot), type(result)
    assert repo.git("status", "--porcelain") == before, "lifecycle must write nothing"
    return result


def by_id(snap: LifecycleSnapshot, order_id: str) -> Any:
    for item in snap.orders:
        if item.order_id == order_id:
            return item
    raise AssertionError(f"{order_id} missing from snapshot: {[o.order_id for o in snap.orders]}")


def test_issued_is_ready_when_not_blocked(repo: RepoBuilder) -> None:
    order_id = oid("issued")
    repo.issue_order(order(order_id, owned_paths=[f"apps/demo/{order_id}/**"]))
    item = by_id(snapshot(repo), order_id)
    assert item.state == OrderState.ISSUED
    assert OrderState.BLOCKED_ON_GOVERNOR not in item.overlays


def test_claimed_without_pr(repo: RepoBuilder) -> None:
    order_id = oid("claimed")
    repo.issue_order(order(order_id, owned_paths=[f"apps/demo/{order_id}/**"]))
    repo.add_event(order_id, message("claim", order_id=order_id))
    item = by_id(snapshot(repo), order_id)
    assert item.state == OrderState.CLAIMED


def test_open_pr_is_in_review(repo: RepoBuilder) -> None:
    order_id = oid("review")
    repo.issue_order(order(order_id, owned_paths=[f"apps/demo/{order_id}/**"]))
    repo.add_event(order_id, message("claim", order_id=order_id))
    repo.make_pr(f"wo/{order_id}")
    item = by_id(snapshot(repo), order_id)
    assert item.state == OrderState.IN_REVIEW
    assert item.pr_number == 1


def test_accepted_needs_verdict_and_green_checks(repo: RepoBuilder) -> None:
    order_id = oid("accepted")
    repo.issue_order(order(order_id, owned_paths=[f"apps/demo/{order_id}/**"]))
    repo.add_event(order_id, message("claim", order_id=order_id))
    repo.add_event(order_id, message("handoff", order_id=order_id))
    pr = repo.make_pr(f"wo/{order_id}")
    repo.github.add_check_run(pr.head_sha, "factory-tests", conclusion="success")
    repo.add_event(
        order_id,
        message(
            "verdict",
            order_id=order_id,
            decision="accept",
            inputs=[{"path": f"bus/orders/{order_id}/order.yaml", "sha": pr.head_sha}],
        ),
    )
    item = by_id(snapshot(repo), order_id)
    assert item.state == OrderState.ACCEPTED


def test_rejected_latest_verdict(repo: RepoBuilder) -> None:
    order_id = oid("rejected")
    repo.issue_order(order(order_id, owned_paths=[f"apps/demo/{order_id}/**"]))
    repo.add_event(order_id, message("claim", order_id=order_id))
    repo.add_event(order_id, message("handoff", order_id=order_id))
    pr = repo.make_pr(f"wo/{order_id}")
    repo.add_event(
        order_id,
        message(
            "verdict",
            order_id=order_id,
            decision="reject",
            inputs=[{"path": f"bus/orders/{order_id}/order.yaml", "sha": pr.head_sha}],
        ),
    )
    item = by_id(snapshot(repo), order_id)
    assert item.state == OrderState.REJECTED


def test_merged_pr(repo: RepoBuilder) -> None:
    order_id = oid("merged")
    repo.issue_order(order(order_id, owned_paths=[f"apps/demo/{order_id}/**"]))
    repo.add_event(order_id, message("claim", order_id=order_id))
    pr = repo.make_pr(f"wo/{order_id}", open=False, merged=True)
    repo.github.merge_pr(pr.number)
    item = by_id(snapshot(repo), order_id)
    assert item.state == OrderState.MERGED


def test_released_by_release_event(repo: RepoBuilder) -> None:
    order_id = oid("released-event")
    repo.issue_order(order(order_id, owned_paths=[f"apps/demo/{order_id}/**"]))
    repo.add_event(order_id, message("claim", order_id=order_id))
    repo.add_event(order_id, message("release", order_id=order_id, reason="abandoned"))
    item = by_id(snapshot(repo), order_id)
    assert item.state == OrderState.RELEASED


def test_released_by_pr_closed_unmerged(repo: RepoBuilder) -> None:
    order_id = oid("closed-unmerged")
    repo.issue_order(order(order_id, owned_paths=[f"apps/demo/{order_id}/**"]))
    repo.add_event(order_id, message("claim", order_id=order_id))
    pr = repo.make_pr(f"wo/{order_id}")
    repo.github.close_pr(pr.number)
    item = by_id(snapshot(repo), order_id)
    assert item.state == OrderState.RELEASED


def test_stale_overlay_after_three_times_size_still_counts_toward_cap(
    repo: RepoBuilder,
) -> None:
    order_id = oid("stale")
    claimed_at = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    repo.issue_order(
        order(order_id, owned_paths=[f"apps/demo/{order_id}/**"], size_minutes=10),
        when=claimed_at - timedelta(minutes=1),
    )
    repo.add_event(
        order_id,
        message(
            "claim",
            order_id=order_id,
            claimed_at=claimed_at.isoformat().replace("+00:00", "Z"),
        ),
        when=claimed_at,
    )
    now = claimed_at + timedelta(minutes=31)  # 3 × 10 + 1
    item = by_id(snapshot(repo, now=now), order_id)
    assert item.state == OrderState.CLAIMED
    assert OrderState.STALE in item.overlays
    assert OrderState.STALE in OVERLAY_STATES

    other = oid("fourth")
    repo.issue_order(order(other, owned_paths=[f"apps/demo/{other}/**"]))
    for n in range(2):
        extra = oid(f"active-{n}")
        repo.issue_order(order(extra, owned_paths=[f"apps/demo/{extra}/**"]))
        repo.add_event(extra, message("claim", order_id=extra))
    snap = snapshot(repo, now=now)
    active = [
        o
        for o in snap.orders
        if o.state in {OrderState.CLAIMED, OrderState.IN_REVIEW} and o.state != OrderState.RELEASED
    ]
    assert any(o.order_id == order_id for o in active), "stale still counts toward the cap"


def test_not_stale_inside_window(repo: RepoBuilder) -> None:
    order_id = oid("fresh")
    claimed_at = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    repo.issue_order(
        order(order_id, owned_paths=[f"apps/demo/{order_id}/**"], size_minutes=10),
        when=claimed_at,
    )
    repo.add_event(
        order_id,
        message(
            "claim",
            order_id=order_id,
            claimed_at=claimed_at.isoformat().replace("+00:00", "Z"),
        ),
        when=claimed_at,
    )
    now = claimed_at + timedelta(minutes=29)
    item = by_id(snapshot(repo, now=now), order_id)
    assert OrderState.STALE not in item.overlays


def test_blocked_on_open_human_decision(repo: RepoBuilder) -> None:
    decision = "pick-host"
    repo.checkout("main")
    repo.write_message(message("decision_request", decision_id=decision, blocking=True))
    repo.commit("open decision")
    repo.push("main")
    order_id = oid("blocked-od")
    repo.issue_order(
        order(
            order_id,
            owned_paths=[f"apps/demo/{order_id}/**"],
            depends_on_decisions=[decision],
        )
    )
    item = by_id(snapshot(repo), order_id)
    assert OrderState.BLOCKED_ON_GOVERNOR in item.overlays


def test_blocked_on_handoff_blocker_question(repo: RepoBuilder) -> None:
    order_id = oid("blocked-q")
    repo.issue_order(order(order_id, owned_paths=[f"apps/demo/{order_id}/**"]))
    repo.add_event(order_id, message("claim", order_id=order_id))
    repo.add_event(
        order_id,
        message(
            "handoff",
            order_id=order_id,
            open_questions=[
                {
                    "question": "Should the demo use the locked host?",
                    "class": "blocker_governor",
                }
            ],
        ),
    )
    item = by_id(snapshot(repo), order_id)
    assert OrderState.BLOCKED_ON_GOVERNOR in item.overlays


def test_ready_queue_is_issued_and_not_claimed_and_not_blocked(repo: RepoBuilder) -> None:
    decision = "pick-host"
    repo.checkout("main")
    repo.write_message(message("decision_request", decision_id=decision, blocking=True))
    repo.commit("open decision")
    repo.push("main")

    ready = oid("ready")
    claimed = oid("not-ready-claimed")
    blocked = oid("not-ready-blocked")
    repo.issue_order(order(ready, owned_paths=[f"apps/demo/{ready}/**"]))
    repo.issue_order(order(claimed, owned_paths=[f"apps/demo/{claimed}/**"]))
    repo.add_event(claimed, message("claim", order_id=claimed))
    repo.issue_order(
        order(
            blocked,
            owned_paths=[f"apps/demo/{blocked}/**"],
            depends_on_decisions=[decision],
        )
    )
    snap = snapshot(repo)
    ready_ids = {
        item.order_id
        for item in snap.orders
        if item.state == OrderState.ISSUED and OrderState.BLOCKED_ON_GOVERNOR not in item.overlays
    }
    assert ready in ready_ids
    assert claimed not in ready_ids
    assert blocked not in ready_ids


def test_derive_accepts_repo_path_type(repo: RepoBuilder) -> None:
    assert isinstance(repo.path, Path)
    snap = snapshot(repo)
    assert isinstance(snap.generated_at, datetime)
    assert snap.orders == []
