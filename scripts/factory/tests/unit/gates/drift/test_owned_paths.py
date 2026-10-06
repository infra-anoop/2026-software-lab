"""T039 — `diff-within-owned-paths` (T044; FR-014; contracts/messages.md § Invariants).

Every changed path (added, modified, or deleted; `git diff --no-renames`) must match
the effective order's `owned_paths` (order + amendments in order) or sit under
`bus/orders/<order-id>/`. The seed in `tests/seeds` is the SC-002 subset.
"""

from __future__ import annotations

from factory.api import GateContext
from tests.fixtures.repo_builder import RepoBuilder, message, yaml_text
from tests.unit.gates.drift.helpers import (
    ORDER_DIR,
    ORDER_ID,
    amendment_for,
    assert_blocks,
    assert_passes,
    oid,
    order_ctx,
    order_for,
    order_pair,
)

GATE = "diff-within-owned-paths"
CALC = "def add(a: int, b: int) -> int:\n    return a + b\n"
MANIFEST = "[deploy]\nstartCommand = 'uvicorn app:app'\nhealthcheckPath = '/healthz'\n"


def demo(repo: RepoBuilder) -> RepoBuilder:
    repo.add_demo_feature()
    return repo


def ctx_for(
    repo: RepoBuilder,
    head_files: dict[str, str | None],
    *,
    base_files: dict[str, str] | None = None,
    owned_paths: list[str] | None = None,
    amendments: tuple[dict[str, object], ...] = (),
) -> GateContext:
    data = order_for(owned_paths=owned_paths or ["apps/demo/app/calc.py"])
    pair = order_pair(demo(repo), base_files or {}, head_files, data, *amendments)
    return order_ctx(repo, pair)


def test_passes_when_every_change_is_owned_or_in_own_bus_dir(repo: RepoBuilder) -> None:
    ctx = ctx_for(
        repo,
        {
            "apps/demo/app/calc.py": CALC.replace("a + b", "b + a"),
            "apps/demo/app/stats/mean.py": "def mean(xs: list[float]) -> float:\n    return 0.0\n",
            f"{ORDER_DIR}/claim.yaml": yaml_text(message("claim", order_id=ORDER_ID)),
        },
        owned_paths=["apps/demo/app/calc.py", "apps/demo/app/stats/**"],
    )
    assert_passes(GATE, ctx)


def test_blocks_an_added_unowned_file(repo: RepoBuilder) -> None:
    ctx = ctx_for(
        repo,
        {"apps/demo/app/calc.py": CALC.replace("a + b", "b + a"), "deploy/demo.toml": MANIFEST},
    )
    assert_blocks(GATE, ctx, "deploy/demo.toml")


def test_blocks_a_modified_unowned_file(repo: RepoBuilder) -> None:
    ctx = ctx_for(
        repo,
        {"apps/demo/app/calc.py": CALC.replace("a + b", "b + a"), "README.md": "# edited\n"},
    )
    assert_blocks(GATE, ctx, "README.md")


def test_blocks_a_deleted_unowned_file(repo: RepoBuilder) -> None:
    ctx = ctx_for(
        repo,
        {"deploy/demo.toml": None},
        base_files={"deploy/demo.toml": MANIFEST},
    )
    assert_blocks(GATE, ctx, "deploy/demo.toml")


def test_blocks_a_rename_out_of_unowned_space(repo: RepoBuilder) -> None:
    """Renames off: moving an unowned file into owned space deletes the unowned path.

    With rename detection on, `--name-only` lists only the (owned) destination.
    """
    ctx = ctx_for(
        repo,
        {"deploy/demo.toml": None, "apps/demo/app/demo.toml": MANIFEST},
        base_files={"deploy/demo.toml": MANIFEST},
        owned_paths=["apps/demo/app/**"],
    )
    assert_blocks(GATE, ctx, "deploy/demo.toml")


def test_blocks_another_orders_bus_dir(repo: RepoBuilder) -> None:
    """Only this order's bus directory is implicitly owned."""
    other = oid("someone-else")
    ctx = ctx_for(
        repo,
        {f"bus/orders/{other}/claim.yaml": yaml_text(message("claim", order_id=other))},
    )
    assert_blocks(GATE, ctx, f"bus/orders/{other}/claim.yaml")


def test_glob_does_not_match_a_sibling_prefix(repo: RepoBuilder) -> None:
    """`apps/demo/**` owns `apps/demo/...`, not `apps/demo-admin/...` (no prefix matching)."""
    ctx = ctx_for(
        repo,
        {"apps/demo-admin/app/main.py": "X = 1\n"},
        owned_paths=["apps/demo/**"],
    )
    assert_blocks(GATE, ctx, "apps/demo-admin/app/main.py")


def test_double_star_owns_nested_paths(repo: RepoBuilder) -> None:
    ctx = ctx_for(
        repo,
        {"apps/demo/app/deep/er/still/inside.py": "X = 1\n", "apps/demo/top.py": "Y = 2\n"},
        owned_paths=["apps/demo/**"],
    )
    assert_passes(GATE, ctx)


def test_amendment_extends_owned_paths(repo: RepoBuilder) -> None:
    amendment = amendment_for(
        ORDER_ID, 1, owned_paths=["apps/demo/app/calc.py", "deploy/demo.toml"]
    )
    ctx = ctx_for(repo, {"deploy/demo.toml": MANIFEST}, amendments=(amendment,))
    assert_passes(GATE, ctx)


def test_amendment_replaces_owned_paths_rather_than_adding(repo: RepoBuilder) -> None:
    """The effective order is the latest value, not the union of all values."""
    amendment = amendment_for(ORDER_ID, 1, owned_paths=["apps/demo/app/calc.py"])
    ctx = ctx_for(
        repo,
        {"deploy/demo.toml": MANIFEST},
        owned_paths=["apps/demo/app/calc.py", "deploy/demo.toml"],
        amendments=(amendment,),
    )
    assert_blocks(GATE, ctx, "deploy/demo.toml")


def test_later_amendment_wins(repo: RepoBuilder) -> None:
    first = amendment_for(ORDER_ID, 1, owned_paths=["apps/demo/app/calc.py", "deploy/**"])
    second = amendment_for(ORDER_ID, 2, owned_paths=["apps/demo/app/calc.py"])
    ctx = ctx_for(repo, {"deploy/demo.toml": MANIFEST}, amendments=(first, second))
    assert_blocks(GATE, ctx, "deploy/demo.toml")


def test_blocks_when_the_order_is_missing_at_head(repo: RepoBuilder) -> None:
    """Fail closed: without the order there are no owned paths to honor."""
    demo(repo)
    pair = repo.base_head_pair(
        {}, {"apps/demo/app/calc.py": CALC.replace("a + b", "b + a")}, head_branch="wo/x"
    )
    ctx = repo.gate_context(pair, order_id=oid("never-issued"), pr_number=1)
    assert_blocks(GATE, ctx, oid("never-issued"))
