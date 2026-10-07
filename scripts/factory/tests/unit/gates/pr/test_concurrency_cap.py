"""T052 — `spawn-concurrency-cap`, the CI twin of the claim cap (catalog
`handoff.concurrency_cap`, merge half; FR-008, I-X4).

The gate replays claim events (`claimed_at`) in timestamp order across every
`wo/*` branch in the repo. An order is active from its claim until its release event
(`created`) or until its branch merges into the base. The PR's order is blocked when
it has no claim, or when `concurrency_cap` (3) orders were already active at the
moment of its claim. This closes the read-then-push race between different orders.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from factory.api import GateContext
from tests.fixtures.repo_builder import BaseHeadPair, RepoBuilder
from tests.unit.gates.pr.helpers import (
    assert_blocks,
    assert_passes,
    at,
    claim_for,
    oid,
    order_for,
    release_for,
)

GATE = "spawn-concurrency-cap"
A, B, C, D = (oid(name) for name in ("alpha", "bravo", "charlie", "delta"))


def issue_and_claim(repo: RepoBuilder, order_id: str, claimed: datetime | None) -> None:
    repo.issue_order(order_for(order_id), when=at(8))
    if claimed is not None:
        repo.add_event(order_id, claim_for(order_id, claimed), when=claimed)


def release(repo: RepoBuilder, order_id: str, when: datetime) -> None:
    repo.add_event(order_id, release_for(order_id, when), when=when)


def merge_into_main(repo: RepoBuilder, order_id: str, when: datetime) -> None:
    repo.checkout("main")
    date = when.strftime("%Y-%m-%dT%H:%M:%S+0000")
    repo.git(
        "merge",
        "--no-ff",
        "-q",
        "-m",
        f"Merge wo/{order_id}",
        f"wo/{order_id}",
        env={"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date},
    )
    repo.push("main")


def ctx_for(repo: RepoBuilder, order_id: str, pr_number: int = 9) -> GateContext:
    pair = BaseHeadPair(repo.head_sha("main"), repo.head_sha(f"wo/{order_id}"), f"wo/{order_id}")
    return repo.gate_context(pair, pr_number=pr_number, order_id=order_id)


def test_cap_passes_third_active_order(repo: RepoBuilder) -> None:
    issue_and_claim(repo, A, at(9))
    issue_and_claim(repo, B, at(10))
    issue_and_claim(repo, D, at(11))
    assert_passes(GATE, ctx_for(repo, D))


def test_cap_blocks_fourth_claim(repo: RepoBuilder) -> None:
    issue_and_claim(repo, A, at(9))
    issue_and_claim(repo, B, at(10))
    issue_and_claim(repo, C, at(11))
    issue_and_claim(repo, D, at(12))
    assert_blocks(GATE, ctx_for(repo, D), D, "3")


def test_cap_blocks_pr_without_claim(repo: RepoBuilder) -> None:
    issue_and_claim(repo, D, None)
    assert_blocks(GATE, ctx_for(repo, D), D)


def test_cap_counts_release_before_the_claim(repo: RepoBuilder) -> None:
    issue_and_claim(repo, A, at(9))
    issue_and_claim(repo, B, at(10))
    issue_and_claim(repo, C, at(11))
    release(repo, A, at(11, 30))
    issue_and_claim(repo, D, at(12))
    assert_passes(GATE, ctx_for(repo, D))


def test_cap_ignores_release_after_the_claim(repo: RepoBuilder) -> None:
    issue_and_claim(repo, A, at(9))
    issue_and_claim(repo, B, at(10))
    issue_and_claim(repo, C, at(11))
    issue_and_claim(repo, D, at(12))
    release(repo, A, at(13))
    assert_blocks(GATE, ctx_for(repo, D), D)


def test_cap_frees_capacity_when_an_order_merged_before_the_claim(repo: RepoBuilder) -> None:
    issue_and_claim(repo, A, at(9))
    issue_and_claim(repo, B, at(10))
    issue_and_claim(repo, C, at(11))
    merge_into_main(repo, A, at(11, 30))
    issue_and_claim(repo, D, at(12))
    assert_passes(GATE, ctx_for(repo, D))


@pytest.mark.parametrize(
    ("order_id", "passes"),
    [(C, True), (D, False)],
    ids=["third-by-one-second-passes", "fourth-by-one-second-blocked"],
)
def test_cap_orders_racing_claims_by_timestamp(
    repo: RepoBuilder, order_id: str, passes: bool
) -> None:
    """Two claims one second apart: only the later one exceeded the cap."""
    issue_and_claim(repo, A, at(9))
    issue_and_claim(repo, B, at(10))
    issue_and_claim(repo, D, at(11, 0, 1))
    issue_and_claim(repo, C, at(11, 0, 0))
    ctx = ctx_for(repo, order_id)
    if passes:
        assert_passes(GATE, ctx)
    else:
        assert_blocks(GATE, ctx, D)
