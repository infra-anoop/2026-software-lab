"""Read model over git: every order branch's bus files plus `main`'s bus (writes nothing)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

from factory.bus.models import (
    Amendment,
    DecisionLock,
    DecisionRequest,
    Envelope,
    Handoff,
    Message,
    WorkOrder,
)
from factory.bus.store import list_bus_paths, load_file
from factory.config.settings import Settings
from factory.orders import git

M = TypeVar("M", bound=Envelope)


@dataclass(frozen=True)
class OrderRecord:
    """One order as git shows it: the effective order and every event in its directory."""

    order_id: str
    ref: str
    order: WorkOrder
    messages: list[Message]
    tip_time: datetime
    on_main: bool

    @property
    def branch(self) -> str:
        return git.order_branch(self.order_id)

    def of_kind(self, model: type[M]) -> list[M]:
        found = [m for m in self.messages if isinstance(m, model)]
        return sorted(found, key=lambda m: m.id)

    def one(self, model: type[M]) -> M | None:
        found = self.of_kind(model)
        return found[0] if found else None

    def blocker_questions(self) -> list[str]:
        handoff = self.one(Handoff)
        if handoff is None:
            return []
        return [
            q.question for q in handoff.open_questions if q.question_class == "blocker_governor"
        ]


@dataclass(frozen=True)
class BusView:
    main_ref: str | None
    main_messages: list[Message] = field(default_factory=list)
    orders: dict[str, OrderRecord] = field(default_factory=dict)

    def requests(self) -> dict[str, DecisionRequest]:
        return {m.id: m for m in self.main_messages if isinstance(m, DecisionRequest)}

    def locks(self) -> dict[str, DecisionLock]:
        return {m.decision_id: m for m in self.main_messages if isinstance(m, DecisionLock)}

    def open_requests(self) -> dict[str, DecisionRequest]:
        locked = self.locks()
        return {key: req for key, req in self.requests().items() if key not in locked}

    def open_dependencies(self, order: WorkOrder) -> list[DecisionRequest]:
        """Open decision requests this order waits on (an unknown id counts as open)."""
        requests = self.requests()
        locked = self.locks()
        out = []
        for decision_id in order.depends_on_decisions:
            if decision_id in locked:
                continue
            out.append(requests.get(decision_id) or _unknown_request(decision_id))
        return out

    def answered_orders(self) -> set[str]:
        """Orders a governor lock on main points back to (their blocker question is answered)."""
        return {ref for lock in self.locks().values() for ref in lock.refs}


def _unknown_request(decision_id: str) -> DecisionRequest:
    return DecisionRequest.model_construct(
        id=decision_id, prompt=f"A governor decision ({decision_id}) has not been recorded yet."
    )


def effective_order(order: WorkOrder, amendments: list[Amendment]) -> WorkOrder:
    """Order + amendments in id order (later amendments win)."""
    values: dict[str, Any] = {}
    for amendment in sorted(amendments, key=lambda a: a.id):
        values.update(amendment.values)
    return order.model_copy(update=values) if values else order


def _order_dir(settings: Settings, order_id: str) -> str:
    return f"{settings.bus_dir}/orders/{order_id}/"


def load_messages(repo: Path, ref: str, settings: Settings, prefix: str = "") -> list[Message]:
    paths = [p for p in list_bus_paths(repo, ref, settings.bus_dir) if p.startswith(prefix)]
    return [load_file(repo, ref, path, settings).message for path in paths]


def load_order(
    repo: Path, ref: str, order_id: str, settings: Settings, *, main_ref: str | None
) -> OrderRecord | None:
    """The order on `ref`, or None when `ref` carries no order file for `order_id`."""
    messages = load_messages(repo, ref, settings, _order_dir(settings, order_id))
    order = next((m for m in messages if isinstance(m, WorkOrder)), None)
    if order is None:
        return None
    amendments = [m for m in messages if isinstance(m, Amendment)]
    order_path = f"{_order_dir(settings, order_id)}order.yaml"
    on_main = main_ref is not None and git.object_exists(repo, f"{main_ref}:{order_path}")
    return OrderRecord(
        order_id=order_id,
        ref=ref,
        order=effective_order(order, amendments),
        messages=messages,
        tip_time=git.commit_time(repo, ref),
        on_main=on_main,
    )


def load_view(repo: Path, settings: Settings) -> BusView:
    """Every order on an `origin/wo/*` branch (or already merged into main) plus main's bus."""
    main = git.main_ref(repo)
    main_messages = load_messages(repo, main, settings) if main else []
    orders: dict[str, OrderRecord] = {}
    for order_id, ref in sorted(git.remote_order_refs(repo).items()):
        record = load_order(repo, ref, order_id, settings, main_ref=main)
        if record is not None:
            orders[order_id] = record
    if main:
        for message in main_messages:
            if isinstance(message, WorkOrder) and message.id not in orders:
                record = load_order(repo, main, message.id, settings, main_ref=main)
                if record is not None:
                    orders[message.id] = record
    return BusView(main_ref=main, main_messages=main_messages, orders=orders)
