"""Bus reads for gates: messages at a commit, the effective order, an order's messages."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from factory.api import GateContext
from factory.bus.models import Amendment, Message, WorkOrder, order_id_of
from factory.bus.store import BusError, expected_path, list_bus_paths, parse_bus_text
from factory.config.settings import Settings
from factory.gates.repo._git import read_blobs


def load_tolerant(repo: Path, ref: str, settings: Settings) -> list[Message]:
    """Every valid, correctly placed bus message at `ref`; invalid files are skipped.

    `bus.schema` reports the invalid ones; other gates judge what is valid.
    """
    paths = list_bus_paths(repo, ref, settings.bus_dir)
    messages: list[Message] = []
    for path, text in read_blobs(repo, ref, paths).items():
        if text is None:
            continue
        try:
            message = parse_bus_text(
                text, path, autonomy_horizon_minutes=settings.autonomy_horizon_minutes
            )
        except BusError:
            continue
        if str(expected_path(message, settings.bus_dir)) == path:
            messages.append(message)
    return messages


def head_messages(ctx: GateContext) -> list[Message]:
    """The context's bus snapshot, or the head's bus read from git when none was given."""
    if ctx.bus_snapshot:
        return list(ctx.bus_snapshot)
    return load_tolerant(ctx.repo_path, ctx.head_sha, ctx.config)


def order_messages(messages: list[Message], order_id: str) -> list[Message]:
    return [
        m
        for m in messages
        if m.kind not in {"decision_request", "decision_lock", "correction"}
        and order_id_of(m.id) == order_id
    ]


def suffix_number(message_id: str) -> int:
    """`NN` of `<order-id>.<kind>-NN` (0 when the id has no number)."""
    tail = message_id.rsplit("-", 1)[-1]
    return int(tail) if tail.isdigit() else 0


def effective_order(messages: list[Message], order_id: str) -> WorkOrder | None:
    """The order with its amendments applied in `amend-NN` order (data-model § Amendment)."""
    own = order_messages(messages, order_id)
    orders = [m for m in own if isinstance(m, WorkOrder)]
    if not orders:
        return None
    amendments = sorted(
        (m for m in own if isinstance(m, Amendment)), key=lambda m: suffix_number(m.id)
    )
    update: dict[str, Any] = {}
    for amendment in amendments:
        update.update({name: amendment.values[name] for name in amendment.supersedes})
    return orders[0].model_copy(update=update)
