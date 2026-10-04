"""Helpers for slice C gate unit tests (tasks.md T051-T052).

Gates run through the frozen `factory.api.run_gate`, so a gate that is not yet
implemented fails by assertion ("not implemented"), never at collection.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from factory.api import GateContext, GateEntrypointError, GateResult, run_gate
from tests.fixtures.repo_builder import BaseHeadPair, RepoBuilder, message, order

DAY = "20261006"
ORDER_ID = f"wo-{DAY}-gate-under-test"
ORDER_DIR = f"bus/orders/{ORDER_ID}"


def oid(slug: str) -> str:
    return f"wo-{DAY}-{slug}"


def at(hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime(2026, 10, 6, hour, minute, second, tzinfo=UTC)


def stamp(when: datetime) -> str:
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


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
    """The gate fails, names itself, and mentions every needle in its messages."""
    result = run_or_fail(gate_id, ctx)
    assert result.passed is False, f"{gate_id} let the violation through"
    assert any(gate_id in line for line in result.messages), result.messages
    text = "\n".join(result.messages)
    for needle in needles:
        assert needle in text, f"{gate_id} message does not mention {needle!r}: {result.messages}"
    return result


def raw_context(
    repo: RepoBuilder,
    pair: BaseHeadPair,
    *,
    pr_number: int | None = None,
    order_id: str | None = None,
) -> GateContext:
    """A context without a parsed bus snapshot (for heads holding invalid bus files)."""
    return GateContext(
        repo_path=repo.path,
        base_sha=pair.base_sha,
        head_sha=pair.head_sha,
        pr_number=pr_number,
        order_id=order_id,
        config=repo.settings,
        bus_snapshot=[],
    )


def order_for(order_id: str, **fields: Any) -> dict[str, Any]:
    fields.setdefault("feature", "demo-feature")
    fields.setdefault("owned_paths", [f"apps/demo/{order_id}/**"])
    return order(order_id, **fields)


def claim_for(order_id: str, when: datetime) -> dict[str, Any]:
    return message("claim", order_id=order_id, created=stamp(when), claimed_at=stamp(when))


def release_for(order_id: str, when: datetime) -> dict[str, Any]:
    return message("release", order_id=order_id, created=stamp(when), reason="abandoned")
