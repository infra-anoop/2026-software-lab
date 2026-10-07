"""T018 — lifecycle derivation rules (data-model.md § Lifecycle)."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from factory.api import OVERLAY_STATES, GitHubPort, LifecycleSnapshot, OrderState
from factory.gates.registry import load_registry
from tests.fixtures.repo_builder import DEMO_ACCEPTANCE, RepoBuilder, message, order

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


REQUIRED_CHECKS = ["red-first-proof", "test-seam-ban"]
GREEN_STATUSES = {"red-first-proof": "success", "test-seam-ban": "success"}
GREEN_RUNS = {"factory-tests": ("completed", "success")}

# Required set = a `factory/<gate-id>` commit status for every id in the order's `checks`
# (success, or failed and overridden for that same gate). Other check runs on the PR head
# are not required until branch-protection required checks are readable (T066).
CHECK_CASES = {
    "all-green": (GREEN_STATUSES, GREEN_RUNS, None, OrderState.ACCEPTED),
    "failed-overridden": (
        {**GREEN_STATUSES, "red-first-proof": "failure"},
        GREEN_RUNS,
        "red-first-proof",
        OrderState.ACCEPTED,
    ),
    "status-failed": (
        {**GREEN_STATUSES, "red-first-proof": "failure"},
        GREEN_RUNS,
        None,
        OrderState.IN_REVIEW,
    ),
    "status-pending": (
        {**GREEN_STATUSES, "test-seam-ban": "pending"},
        GREEN_RUNS,
        None,
        OrderState.IN_REVIEW,
    ),
    "status-missing": ({"test-seam-ban": "success"}, GREEN_RUNS, None, OrderState.IN_REVIEW),
    "override-other-gate": (
        {**GREEN_STATUSES, "red-first-proof": "failure"},
        GREEN_RUNS,
        "test-seam-ban",
        OrderState.IN_REVIEW,
    ),
    "unrelated-run-pending": (
        GREEN_STATUSES,
        {**GREEN_RUNS, "advisory-scan": ("in_progress", None)},
        None,
        OrderState.ACCEPTED,
    ),
}


@pytest.mark.parametrize(
    ("statuses", "runs", "overridden", "expected"),
    list(CHECK_CASES.values()),
    ids=list(CHECK_CASES),
)
def test_accepted_needs_verdict_and_full_required_check_set(
    repo: RepoBuilder,
    statuses: dict[str, str],
    runs: dict[str, tuple[str, str | None]],
    overridden: str | None,
    expected: OrderState,
) -> None:
    order_id = oid("accepted")
    repo.issue_order(
        order(order_id, owned_paths=[f"apps/demo/{order_id}/**"], checks=REQUIRED_CHECKS)
    )
    repo.add_event(order_id, message("claim", order_id=order_id))
    repo.add_event(order_id, message("handoff", order_id=order_id))
    pr = repo.make_pr(f"wo/{order_id}")
    for gate, value in statuses.items():
        repo.github.set_commit_status(pr.head_sha, f"factory/{gate}", value, f"{gate}: {value}")
    for name, (run_status, conclusion) in runs.items():
        repo.github.add_check_run(pr.head_sha, name, run_status=run_status, conclusion=conclusion)
    if overridden:
        repo.add_event(
            order_id,
            message(
                "override",
                order_id=order_id,
                gate=overridden,
                pr=pr.number,
                reason="Base suite broken by an unrelated module; verified by hand.",
                gate_class="drift",
            ),
        )
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
    assert item.state == expected


def test_empty_checks_never_accepted(repo: RepoBuilder) -> None:
    """FR-011: acceptance needs check evidence plus a verdict; an empty set is no evidence."""
    order_id = oid("no-checks")
    repo.issue_order(order(order_id, owned_paths=[f"apps/demo/{order_id}/**"], checks=[]))
    repo.add_event(order_id, message("claim", order_id=order_id))
    repo.add_event(order_id, message("handoff", order_id=order_id))
    pr = repo.make_pr(f"wo/{order_id}")
    for gate in REQUIRED_CHECKS:
        repo.github.set_commit_status(pr.head_sha, f"factory/{gate}", "success", "green")
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
    assert item.state == OrderState.IN_REVIEW


# T105 (amendment-06 decision 2): each `checks` kind is satisfied by its own status. A
# registered gate id needs `factory/<gate-id>` (CHECK_CASES above); a catalog row id is
# judged by the `catalog-test-linkage` gate, so its status is `factory/catalog-test-linkage`;
# an id that is neither is never satisfied (data-model § WorkOrder: "each exists").
# The demo catalog (`specs/demo-feature/acceptance.md`) has one row, `demo.adds`.
LINKAGE = "catalog-test-linkage"
CATALOG_ROW = "demo.adds"
UNKNOWN_ID = "demo.adds-typo"


def derived_state(
    repo: RepoBuilder,
    checks: list[str],
    statuses: dict[str, str],
    overrides: tuple[str, ...] = (),
) -> OrderState:
    """State of an accepted-verdict order whose PR head carries `factory/<id>` statuses."""
    registered = set(load_registry().ids())
    assert {*REQUIRED_CHECKS, LINKAGE} <= registered, "fixture gate ids are not registered"
    assert not {CATALOG_ROW, UNKNOWN_ID} & registered, "fixture row ids must not be gates"
    repo.add_demo_feature()
    order_id = oid("check-kinds")
    accept_order(repo, order_id, checks, statuses, overrides)
    state: OrderState = by_id(snapshot(repo), order_id).state
    return state


def accept_order(
    repo: RepoBuilder,
    order_id: str,
    checks: list[str],
    statuses: dict[str, str],
    overrides: tuple[str, ...] = (),
    head_files: dict[str, str] | None = None,
) -> None:
    """Issue `order_id` (plus `head_files`, on its branch only), open its PR, post the
    `factory/<id>` statuses on the PR head and accept it."""
    repo.issue_order(order(order_id, owned_paths=[f"apps/demo/{order_id}/**"], checks=checks))
    if head_files:
        start = repo.current_branch()
        repo.checkout(f"wo/{order_id}")
        for relative, text in head_files.items():
            repo.write(relative, text)
        repo.commit(f"head-only inputs: {order_id}")
        repo.push()
        repo.checkout(start)
    repo.add_event(order_id, message("claim", order_id=order_id))
    repo.add_event(order_id, message("handoff", order_id=order_id))
    pr = repo.make_pr(f"wo/{order_id}")
    for check_id, value in statuses.items():
        repo.github.set_commit_status(pr.head_sha, f"factory/{check_id}", value, value)
    for gate in overrides:
        repo.add_event(
            order_id,
            message(
                "override",
                order_id=order_id,
                gate=gate,
                pr=pr.number,
                reason="Linkage fixed by hand; verified against the catalog.",
                gate_class="drift",
            ),
        )
    repo.add_event(
        order_id,
        message(
            "verdict",
            order_id=order_id,
            decision="accept",
            inputs=[{"path": f"bus/orders/{order_id}/order.yaml", "sha": pr.head_sha}],
        ),
    )


def test_catalog_row_is_satisfied_by_the_catalog_linkage_status(repo: RepoBuilder) -> None:
    statuses = {**GREEN_STATUSES, LINKAGE: "success"}
    state = derived_state(repo, [*REQUIRED_CHECKS, CATALOG_ROW], statuses)
    assert state == OrderState.ACCEPTED, (
        f"row {CATALOG_ROW} with a green factory/{LINKAGE} and no factory/{CATALOG_ROW}"
        f" status should be accepted, got {state}"
    )


@pytest.mark.parametrize("linkage", ["failure", "pending", None], ids=str)
def test_catalog_row_needs_a_green_linkage_status_not_its_own(
    repo: RepoBuilder, linkage: str | None
) -> None:
    statuses = {**GREEN_STATUSES, CATALOG_ROW: "success"}
    if linkage is not None:
        statuses[LINKAGE] = linkage
    state = derived_state(repo, [*REQUIRED_CHECKS, CATALOG_ROW], statuses)
    assert state == OrderState.IN_REVIEW, (
        f"a green factory/{CATALOG_ROW} must not satisfy the row while factory/{LINKAGE}"
        f" is {linkage or 'missing'}; got {state}"
    )


OVERRIDE_CASES = {
    "linkage-overridden": ({LINKAGE: "failure"}, LINKAGE, OrderState.ACCEPTED),
    "row-id-overridden": (
        {LINKAGE: "failure", CATALOG_ROW: "failure"},
        CATALOG_ROW,
        OrderState.IN_REVIEW,
    ),
}


@pytest.mark.parametrize(
    ("failing", "overridden", "expected"), list(OVERRIDE_CASES.values()), ids=list(OVERRIDE_CASES)
)
def test_catalog_row_counts_an_override_of_the_linkage_gate_only(
    repo: RepoBuilder, failing: dict[str, str], overridden: str, expected: OrderState
) -> None:
    """contracts/gates.md § Override resolution: an override names the gate that failed."""
    statuses = {**GREEN_STATUSES, **failing}
    state = derived_state(repo, [*REQUIRED_CHECKS, CATALOG_ROW], statuses, (overridden,))
    assert state == expected, f"override of {overridden} over {failing}: got {state}"


def test_an_id_that_is_neither_a_gate_nor_a_catalog_row_fails_closed(repo: RepoBuilder) -> None:
    statuses = {**GREEN_STATUSES, UNKNOWN_ID: "success", LINKAGE: "success"}
    state = derived_state(repo, [*REQUIRED_CHECKS, UNKNOWN_ID], statuses)
    assert state == OrderState.IN_REVIEW, (
        f"{UNKNOWN_ID} is neither a registered gate nor a catalog row; a green"
        f" factory/{UNKNOWN_ID} must not satisfy it, got {state}"
    )


HEAD_REGISTRY = "scripts/factory/gates.yaml"
HEAD_CATALOG = "specs/demo-feature/acceptance.md"
COLLISION_ID = "pr-links-order"
HEAD_ONLY_GATE = "head-only-gate"
HEAD_ONLY_ROW = "demo.head-only"


def head_registry_with(repo: RepoBuilder, gate_id: str) -> str:
    """The fixture's planted `gates.yaml` plus one more drift gate."""
    text = (repo.path / HEAD_REGISTRY).read_text(encoding="utf-8")
    return text + (
        f"  - id: {gate_id}\n    class: drift\n    category: drift\n    intents: [I-M4]\n"
        "    ci_job: factory-gates\n    priority: P1\n    scope: repo\n"
        "    entrypoint: factory.gates.repo.bus_schema:run\n"
    )


def head_catalog_with(row_id: str) -> str:
    """The demo catalog plus one more row."""
    row = f"| {row_id} | SC-001 | I-D1 | must | always | holds | auto | planned |\n"
    return DEMO_ACCEPTANCE + row


def test_check_kinds_follow_the_installed_registry_and_the_head_catalog(
    repo: RepoBuilder, tmp_path: Path
) -> None:
    """amendment-01 rulings (T-LC1, T-LC2): gate ids come from the installed registry,
    catalog rows from the PR head's `acceptance.md`, a row wins over a gate with the same
    id, and green linkage never stands in for a registered gate's own status."""
    installed = set(load_registry().ids())
    assert {*REQUIRED_CHECKS, LINKAGE, COLLISION_ID} <= installed
    assert not {HEAD_ONLY_GATE, HEAD_ONLY_ROW} & installed
    repo.add_demo_feature()
    head_registry = head_registry_with(repo, HEAD_ONLY_GATE)
    parsed = tmp_path / "head-gates.yaml"
    parsed.write_text(head_registry, encoding="utf-8")
    assert HEAD_ONLY_GATE in load_registry(parsed).ids(), "the head registry must be valid"

    green = {**GREEN_STATUSES, LINKAGE: "success"}
    rows: dict[str, tuple[list[str], dict[str, str], dict[str, str] | None, OrderState]] = {
        "collision": (
            [*REQUIRED_CHECKS, COLLISION_ID],
            green,
            {HEAD_CATALOG: head_catalog_with(COLLISION_ID)},
            OrderState.ACCEPTED,
        ),
        "head-only-gate": (
            [*REQUIRED_CHECKS, HEAD_ONLY_GATE],
            {**green, HEAD_ONLY_GATE: "success"},
            {HEAD_REGISTRY: head_registry},
            OrderState.IN_REVIEW,
        ),
        "head-only-row": (
            [*REQUIRED_CHECKS, HEAD_ONLY_ROW],
            green,
            {HEAD_CATALOG: head_catalog_with(HEAD_ONLY_ROW)},
            OrderState.ACCEPTED,
        ),
        "gate-without-own-status": (
            REQUIRED_CHECKS,
            {REQUIRED_CHECKS[0]: "success", LINKAGE: "success"},
            None,
            OrderState.IN_REVIEW,
        ),
    }
    for name, (checks, statuses, head_files, _) in rows.items():
        accept_order(repo, oid(f"kinds-{name}"), checks, statuses, head_files=head_files)
    snap = snapshot(repo)
    got = {name: by_id(snap, oid(f"kinds-{name}")).state for name in rows}
    assert got == {name: row[3] for name, row in rows.items()}


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
    active = [o for o in snap.orders if o.state in {OrderState.CLAIMED, OrderState.IN_REVIEW}]
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
