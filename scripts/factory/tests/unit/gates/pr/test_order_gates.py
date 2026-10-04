"""T052 — order-linked PR gates: `pr-links-order`, `order-blocked-on-open-human-od`.

The runner resolves `GateContext.order_id` from the PR head `wo/<order-id>` (None for
any other head). `pr-links-order` (I-P1): a PR needs that order at head, except a bus
PR whose changes are all under `bus/decisions/`, `bus/corrections/`, `bus/postmortems/`.
`order-blocked-on-open-human-od` (governor-only, I-X3): the effective order (order +
amendments) depends on no open decision; a decision is open while it has a request and
no lock, and an unknown decision id cannot be shown closed.
"""

from __future__ import annotations

from tests.fixtures.repo_builder import RepoBuilder, message, yaml_text
from tests.unit.gates.pr.helpers import (
    ORDER_DIR,
    ORDER_ID,
    assert_blocks,
    assert_passes,
    oid,
    order_for,
)

ORDER_FILE = f"{ORDER_DIR}/order.yaml"
DECISION = "pick-host"
REQUEST = f"bus/decisions/{DECISION}/request.yaml"
LOCK = f"bus/decisions/{DECISION}/lock.yaml"


def request_text() -> str:
    return yaml_text(message("decision_request", decision_id=DECISION, blocking=True))


def lock_text() -> str:
    return yaml_text(message("decision_lock", decision_id=DECISION))


# --- pr-links-order -----------------------------------------------------------------------


def test_links_order_passes_for_wo_branch_with_its_order(repo: RepoBuilder) -> None:
    pair = repo.base_head_pair(
        {},
        {ORDER_FILE: yaml_text(order_for(ORDER_ID)), "apps/demo/x.py": "X = 1\n"},
        head_branch=f"wo/{ORDER_ID}",
    )
    assert_passes("pr-links-order", repo.gate_context(pair, pr_number=7, order_id=ORDER_ID))


def test_links_order_blocks_pr_not_from_a_work_order_branch(repo: RepoBuilder) -> None:
    pair = repo.base_head_pair({}, {"apps/demo/x.py": "X = 1\n"}, head_branch="feature/x")
    assert_blocks("pr-links-order", repo.gate_context(pair, pr_number=7, order_id=None))


def test_links_order_blocks_wo_branch_without_its_order(repo: RepoBuilder) -> None:
    pair = repo.base_head_pair({}, {"apps/demo/x.py": "X = 1\n"}, head_branch=f"wo/{ORDER_ID}")
    ctx = repo.gate_context(pair, pr_number=7, order_id=ORDER_ID)
    assert_blocks("pr-links-order", ctx, ORDER_ID)


def test_links_order_blocks_when_only_another_order_exists(repo: RepoBuilder) -> None:
    other = oid("someone-else")
    pair = repo.base_head_pair(
        {},
        {f"bus/orders/{other}/order.yaml": yaml_text(order_for(other))},
        head_branch=f"wo/{ORDER_ID}",
    )
    ctx = repo.gate_context(pair, pr_number=7, order_id=ORDER_ID)
    assert_blocks("pr-links-order", ctx, ORDER_ID)


def test_links_order_passes_for_bus_pr(repo: RepoBuilder) -> None:
    pair = repo.base_head_pair({}, {REQUEST: request_text()}, head_branch="bus/20261006-pick-host")
    assert_passes("pr-links-order", repo.gate_context(pair, pr_number=8, order_id=None))


def test_links_order_blocks_bus_branch_carrying_code(repo: RepoBuilder) -> None:
    pair = repo.base_head_pair(
        {},
        {REQUEST: request_text(), "apps/demo/x.py": "X = 1\n"},
        head_branch="bus/20261006-pick-host",
    )
    assert_blocks("pr-links-order", repo.gate_context(pair, pr_number=8, order_id=None))


# --- order-blocked-on-open-human-od -------------------------------------------------------


def test_open_od_blocks_order_depending_on_open_decision(repo: RepoBuilder) -> None:
    pair = repo.base_head_pair(
        {REQUEST: request_text()},
        {ORDER_FILE: yaml_text(order_for(ORDER_ID, depends_on_decisions=[DECISION]))},
        head_branch=f"wo/{ORDER_ID}",
    )
    ctx = repo.gate_context(pair, pr_number=7, order_id=ORDER_ID)
    assert_blocks("order-blocked-on-open-human-od", ctx, DECISION)


def test_open_od_passes_when_decision_locked(repo: RepoBuilder) -> None:
    pair = repo.base_head_pair(
        {REQUEST: request_text(), LOCK: lock_text()},
        {ORDER_FILE: yaml_text(order_for(ORDER_ID, depends_on_decisions=[DECISION]))},
        head_branch=f"wo/{ORDER_ID}",
    )
    assert_passes(
        "order-blocked-on-open-human-od", repo.gate_context(pair, pr_number=7, order_id=ORDER_ID)
    )


def test_open_od_passes_without_dependencies(repo: RepoBuilder) -> None:
    pair = repo.base_head_pair(
        {REQUEST: request_text()},
        {ORDER_FILE: yaml_text(order_for(ORDER_ID))},
        head_branch=f"wo/{ORDER_ID}",
    )
    assert_passes(
        "order-blocked-on-open-human-od", repo.gate_context(pair, pr_number=7, order_id=ORDER_ID)
    )


def test_open_od_blocks_unknown_decision(repo: RepoBuilder) -> None:
    pair = repo.base_head_pair(
        {},
        {ORDER_FILE: yaml_text(order_for(ORDER_ID, depends_on_decisions=["never-asked"]))},
        head_branch=f"wo/{ORDER_ID}",
    )
    ctx = repo.gate_context(pair, pr_number=7, order_id=ORDER_ID)
    assert_blocks("order-blocked-on-open-human-od", ctx, "never-asked")


def test_open_od_uses_effective_order(repo: RepoBuilder) -> None:
    """An amendment that drops the dependency unblocks the order."""
    amendment = message(
        "amendment",
        order_id=ORDER_ID,
        supersedes=["depends_on_decisions"],
        values={"depends_on_decisions": []},
    )
    pair = repo.base_head_pair(
        {REQUEST: request_text()},
        {
            ORDER_FILE: yaml_text(order_for(ORDER_ID, depends_on_decisions=[DECISION])),
            f"{ORDER_DIR}/amendment-01.yaml": yaml_text(amendment),
        },
        head_branch=f"wo/{ORDER_ID}",
    )
    assert_passes(
        "order-blocked-on-open-human-od", repo.gate_context(pair, pr_number=7, order_id=ORDER_ID)
    )


def test_open_od_blocks_when_amendment_adds_open_dependency(repo: RepoBuilder) -> None:
    amendment = message(
        "amendment",
        order_id=ORDER_ID,
        supersedes=["depends_on_decisions"],
        values={"depends_on_decisions": [DECISION]},
    )
    pair = repo.base_head_pair(
        {REQUEST: request_text()},
        {
            ORDER_FILE: yaml_text(order_for(ORDER_ID)),
            f"{ORDER_DIR}/amendment-01.yaml": yaml_text(amendment),
        },
        head_branch=f"wo/{ORDER_ID}",
    )
    ctx = repo.gate_context(pair, pr_number=7, order_id=ORDER_ID)
    assert_blocks("order-blocked-on-open-human-od", ctx, DECISION)
