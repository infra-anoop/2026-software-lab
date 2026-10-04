"""T012 — the shared fixture builder does what slices rely on."""

from __future__ import annotations

from datetime import UTC, datetime

from tests.fixtures.repo_builder import RepoBuilder, message, order

ORDER_ID = "wo-20261006-builder"


def test_issue_order_first_commit_adds_only_the_order(repo: RepoBuilder) -> None:
    branch = repo.issue_order(order(ORDER_ID))
    assert branch == f"wo/{ORDER_ID}"
    assert repo.current_branch() == "main"
    added = repo.git("diff", "--name-only", "origin/main", f"origin/{branch}")
    assert added == f"bus/orders/{ORDER_ID}/order.yaml"
    assert repo.head_sha("origin/main") == repo.head_sha("main")


def test_add_event_with_commit_date(repo: RepoBuilder) -> None:
    repo.issue_order(order(ORDER_ID))
    when = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)
    sha = repo.add_event(ORDER_ID, message("claim", order_id=ORDER_ID), when=when)
    assert int(repo.git("show", "-s", "--format=%ct", sha)) == int(when.timestamp())
    assert int(repo.git("show", "-s", "--format=%at", sha)) == int(when.timestamp())
    assert repo.head_sha(f"origin/wo/{ORDER_ID}") == sha


def test_base_head_pair_and_gate_context(repo: RepoBuilder) -> None:
    pair = repo.base_head_pair(
        {"apps/demo/app/x.py": "A = 1\n"},
        {"apps/demo/app/x.py": None, "apps/demo/app/y.py": "B = 2\n"},
        head_branch=f"wo/{ORDER_ID}",
    )
    changed = repo.git("diff", "--name-status", pair.base_sha, pair.head_sha).splitlines()
    assert changed == ["D\tapps/demo/app/x.py", "A\tapps/demo/app/y.py"]
    ctx = repo.gate_context(pair, order_id=ORDER_ID, pr_number=7)
    assert ctx.repo_path == repo.path
    assert ctx.order_id == ORDER_ID
    assert ctx.bus_snapshot == []


def test_make_pr_uses_branch_head(repo: RepoBuilder) -> None:
    branch = repo.issue_order(order(ORDER_ID))
    pr = repo.make_pr(branch)
    assert pr.head_sha == repo.head_sha(branch)
    assert repo.github.list_prs_by_head(branch) == [pr]
