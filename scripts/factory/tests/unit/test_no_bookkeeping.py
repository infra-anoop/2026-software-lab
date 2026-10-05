"""T020 — commits that only rewrite status or SHAs inside bus/ are counted.

Catalog: `history.no_bookkeeping`.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable

import pytest

from tests.fixtures.repo_builder import RepoBuilder, message, order, yaml_text

DAY = "20261007"


def oid(slug: str) -> str:
    return f"wo-{DAY}-{slug}"


def load_counter() -> Callable[..., int]:
    try:
        module = importlib.import_module("factory.metrics.history")
    except ImportError as exc:
        pytest.fail(f"factory.metrics.history is not implemented: {exc}")
    counter = getattr(module, "count_bookkeeping_commits", None)
    assert callable(counter), "factory.metrics.history must export count_bookkeeping_commits"
    return counter


def test_status_only_bus_rewrite_is_counted(repo: RepoBuilder) -> None:
    order_id = oid("bookkeep")
    repo.issue_order(order(order_id, owned_paths=[f"apps/demo/{order_id}/**"]))
    repo.add_event(order_id, message("claim", order_id=order_id))
    start = repo.current_branch()
    repo.checkout(f"wo/{order_id}")
    path = f"bus/orders/{order_id}/order.yaml"
    original = (repo.path / path).read_text(encoding="utf-8")
    # A bookkeeping edit: only status/SHA-shaped fields inside bus/. The file is
    # invalid as a message; the counter looks at the diff, not schema.
    repo.write(path, original + "status: claimed\nhead_sha: deadbeef\n")
    repo.commit("chore: sync bus status")
    repo.push()
    repo.checkout(start)

    count = load_counter()(repo.path, since="main")
    assert count >= 1


def test_real_work_commit_is_not_counted(repo: RepoBuilder) -> None:
    order_id = oid("real-work")
    repo.issue_order(order(order_id, owned_paths=[f"apps/demo/{order_id}/**"]))
    start = repo.current_branch()
    repo.checkout(f"wo/{order_id}")
    repo.write("apps/demo/app/calc.py", "def add(a, b):\n    return a + b\n")
    repo.commit("feat: add()")
    repo.push()
    repo.checkout(start)

    count = load_counter()(repo.path, since="main")
    assert count == 0


def test_event_append_is_not_bookkeeping(repo: RepoBuilder) -> None:
    order_id = oid("append")
    repo.issue_order(order(order_id, owned_paths=[f"apps/demo/{order_id}/**"]))
    repo.add_event(order_id, message("claim", order_id=order_id))
    count = load_counter()(repo.path, since="main")
    assert count == 0
    assert yaml_text(message("claim", order_id=order_id))
