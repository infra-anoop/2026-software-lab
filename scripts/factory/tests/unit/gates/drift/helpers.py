"""Helpers for slice B drift-gate unit tests (tasks.md T039-T040).

Gates run through the frozen `factory.api.run_gate`, so a gate that is not yet
implemented fails by assertion ("not implemented"), never at collection.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from factory.api import GateContext, GateEntrypointError, GateResult, run_gate
from tests.fixtures.repo_builder import BaseHeadPair, RepoBuilder, message, order, yaml_text

DAY = "20261006"
ORDER_ID = f"wo-{DAY}-drift-under-test"
ORDER_DIR = f"bus/orders/{ORDER_ID}"
ORDER_BRANCH = f"wo/{ORDER_ID}"


def oid(slug: str) -> str:
    return f"wo-{DAY}-{slug}"


def run_or_fail(gate_id: str, ctx: GateContext) -> GateResult:
    try:
        result: GateResult | None = run_gate(gate_id, ctx)
    except GateEntrypointError as exc:
        result = None
        reason = str(exc)
    assert result is not None, f"gate {gate_id} is not implemented: {reason}"
    assert result.gate_id == gate_id, result
    return result


def assert_passes(gate_id: str, ctx: GateContext) -> GateResult:
    result = run_or_fail(gate_id, ctx)
    assert result.passed is True, f"{gate_id} blocked a clean change: {result.messages}"
    return result


def assert_blocks(gate_id: str, ctx: GateContext, *needles: str) -> GateResult:
    """The gate fails, names itself, and mentions every needle (case-insensitive)."""
    result = run_or_fail(gate_id, ctx)
    assert result.passed is False, f"{gate_id} let the violation through"
    assert any(gate_id in line for line in result.messages), result.messages
    text = "\n".join(result.messages).lower()
    for needle in needles:
        assert needle.lower() in text, (
            f"{gate_id} message does not mention {needle!r}: {result.messages}"
        )
    return result


def order_for(order_id: str = ORDER_ID, **fields: Any) -> dict[str, Any]:
    """A valid order for the demo feature with no locks, checks, or tasks unless given."""
    fields.setdefault("feature", "demo-feature")
    fields.setdefault("owned_paths", ["apps/demo/app/calc.py"])
    fields.setdefault("locks", [])
    fields.setdefault("checks", [])
    fields.setdefault("tasks", [])
    return order(order_id, **fields)


def amendment_for(order_id: str, number: int, **values: Any) -> dict[str, Any]:
    return message(
        "amendment",
        order_id=order_id,
        id=f"{order_id}.amend-{number:02d}",
        supersedes=sorted(values),
        values=values,
    )


def order_files(order_data: Mapping[str, Any], *amendments: Mapping[str, Any]) -> dict[str, str]:
    """Head files for an order plus its amendments at their layout paths."""
    order_id = str(order_data["id"])
    files = {f"bus/orders/{order_id}/order.yaml": yaml_text(order_data)}
    for amendment in amendments:
        number = str(amendment["id"]).rsplit("-", 1)[1]
        files[f"bus/orders/{order_id}/amendment-{number}.yaml"] = yaml_text(amendment)
    return files


def order_pair(
    repo: RepoBuilder,
    base_files: Mapping[str, str],
    head_files: Mapping[str, str | None],
    order_data: Mapping[str, Any] | None = None,
    *amendments: Mapping[str, Any],
) -> BaseHeadPair:
    """A base/head pair on `wo/<order-id>` whose head adds the order (and amendments)."""
    data = order_data if order_data is not None else order_for()
    head = {**order_files(data, *amendments), **head_files}
    return repo.base_head_pair(dict(base_files), head, head_branch=f"wo/{data['id']}")


def order_ctx(repo: RepoBuilder, pair: BaseHeadPair, order_id: str = ORDER_ID) -> GateContext:
    return repo.gate_context(pair, order_id=order_id, pr_number=1)
