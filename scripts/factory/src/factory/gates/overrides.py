"""Override resolution (contracts/gates.md § Override resolution; FR-020/021).

A failing gate looks for `bus/orders/<order-id>/override-NN.yaml` with `gate: <id>` at
the PR head. The registry class decides, never the class written in the message:

- `drift`: an override by `orchestrator` or `governor` with a reason is honored.
- `governor-only`: only `actor: governor`; when `identity.mode` is `verified`, the
  `IdentityPort` must also verify the message.

An override naming another PR than the one being checked is not honored.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from factory.bus.models import Message, Override, order_id_of
from factory.config.settings import Settings
from factory.gates.registry import Gate

DRIFT_OVERRIDERS = frozenset({"orchestrator", "governor"})


@dataclass(frozen=True)
class HonoredOverride:
    message: Override
    verified: bool

    def summary(self) -> dict[str, object]:
        return {
            "id": self.message.id,
            "actor": self.message.actor,
            "reason": self.message.reason,
            "verified": self.verified,
        }


def order_overrides(messages: list[Message], order_id: str | None) -> list[Override]:
    """The order's override messages in `override-NN` order."""
    if order_id is None:
        return []
    own = [m for m in messages if isinstance(m, Override) and order_id_of(m.id) == order_id]
    return sorted(own, key=lambda m: m.id)


def honored_overrides(
    gate: Gate,
    overrides: list[Override],
    *,
    settings: Settings,
    pr_number: int | None,
    verify: Callable[[Override], bool],
) -> list[HonoredOverride]:
    honored = []
    for message in overrides:
        if message.gate != gate.id or not message.reason.strip():
            continue
        if pr_number is not None and message.pr != pr_number:
            continue
        if gate.gate_class == "drift":
            if message.actor in DRIFT_OVERRIDERS:
                honored.append(HonoredOverride(message, verified=False))
            continue
        if message.actor != "governor":
            continue
        if settings.identity.mode == "verified":
            if verify(message):
                honored.append(HonoredOverride(message, verified=True))
        else:
            honored.append(HonoredOverride(message, verified=False))
    return honored
