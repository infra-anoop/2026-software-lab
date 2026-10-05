"""Board = a rendering of the lifecycle snapshot (JSON sections + markdown).

Order sections are exclusive: an order waiting on the governor shows only there; merged
and released orders are on no section. Governor-facing text is plain language (no ids
beyond the order id itself).
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from factory.api import GitHubPort, IdentityPort, LifecycleSnapshot, OrderLifecycle, OrderState
from factory.bus.models import DecisionLock, Override
from factory.lifecycle.derive import pick_pr
from factory.lifecycle.view import BusView

ORDER_SECTIONS = ("in_flight", "blocked", "waiting_on_governor", "ready")
IN_FLIGHT = frozenset({OrderState.CLAIMED, OrderState.IN_REVIEW, OrderState.ACCEPTED})
TERMINAL = frozenset({OrderState.MERGED, OrderState.RELEASED})


def section_of(item: OrderLifecycle) -> str | None:
    if item.state in TERMINAL:
        return None
    if OrderState.BLOCKED_ON_GOVERNOR in item.overlays:
        return "waiting_on_governor"
    if item.state == OrderState.ISSUED:
        return "ready"
    if item.state in IN_FLIGHT:
        return "in_flight"
    return "blocked"


def _checks(github: GitHubPort, item: OrderLifecycle) -> list[dict[str, Any]]:
    prs = github.list_prs_by_head(item.branch)
    pr = pick_pr(prs)
    if pr is None:
        return []
    runs = [
        {"name": run.name, "status": run.run_status, "conclusion": run.conclusion}
        for run in github.check_runs(pr.head_sha)
    ]
    statuses = [
        {"name": status.context, "status": status.state, "description": status.description}
        for status in github.list_commit_statuses(pr.head_sha)
    ]
    return runs + statuses


def _waiting_on(view: BusView, item: OrderLifecycle) -> list[dict[str, Any]]:
    record = view.orders[item.order_id]
    waits: list[dict[str, Any]] = []
    for request in view.open_dependencies(record.order):
        options = [option.label for option in getattr(request, "options", None) or []]
        waits.append(
            {
                "question": request.prompt,
                "options": options,
                "recommended": getattr(request, "recommended", None),
            }
        )
    if item.order_id not in view.answered_orders():
        waits.extend({"question": q} for q in record.blocker_questions())
    return waits


def order_card(
    item: OrderLifecycle, view: BusView, github: GitHubPort, section: str
) -> dict[str, Any]:
    record = view.orders[item.order_id]
    card: dict[str, Any] = {
        "order_id": item.order_id,
        "state": item.state.value,
        "overlays": [overlay.value for overlay in item.overlays],
        "goal": record.order.goal,
        "owned_paths": item.owned_paths,
        "pr_number": item.pr_number,
        "size_minutes": record.order.size_minutes,
    }
    if item.pr_number is not None:
        card["checks"] = _checks(github, item)
    if section == "waiting_on_governor":
        card["waiting_on"] = _waiting_on(view, item)
    return card


def _unverified_governor_actions(
    view: BusView, github: GitHubPort, identity: IdentityPort
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for record in view.orders.values():
        pr = pick_pr(github.list_prs_by_head(record.branch))
        for override in record.of_kind(Override):
            if override.actor == "governor" and not identity.is_governor_verified(override, pr):
                out.append(
                    {
                        "order_id": record.order_id,
                        "kind": "override",
                        "gate": override.gate,
                        "pr": override.pr,
                        "reason": override.reason,
                    }
                )
    for message in view.main_messages:
        if isinstance(message, DecisionLock) and message.actor == "governor":
            if not identity.is_governor_verified(message, None):
                out.append(
                    {
                        "kind": "decision_lock",
                        "decision": message.decision_id,
                        "chosen": message.chosen,
                    }
                )
    return out


def build_board(
    snapshot: LifecycleSnapshot,
    view: BusView,
    github: GitHubPort,
    identity: IdentityPort,
    gate_ids: list[str],
) -> dict[str, Any]:
    board: dict[str, Any] = {"generated_at": snapshot.generated_at.isoformat()}
    for name in ORDER_SECTIONS:
        board[name] = []
    for item in snapshot.orders:
        section = section_of(item)
        if section is not None:
            board[section].append(order_card(item, view, github, section))
    counts = Counter(o.gate for r in view.orders.values() for o in r.of_kind(Override))
    board["overrides_per_gate"] = {gate: counts.get(gate, 0) for gate in gate_ids} | dict(counts)
    board["unverified_governor_actions"] = _unverified_governor_actions(view, github, identity)
    active = [o for o in snapshot.orders if o.state not in TERMINAL | {OrderState.ISSUED}]
    board["capacity"] = {"active": len(active)}
    return board


def _line(card: dict[str, Any]) -> str:
    overlays = f" [{', '.join(card['overlays'])}]" if card["overlays"] else ""
    pr = f" PR #{card['pr_number']}" if card.get("pr_number") else ""
    return f"- {card['order_id']} — {card['state']}{overlays}{pr}: {card['goal']}"


def render_markdown(board: dict[str, Any], cap: int) -> str:
    titles = {
        "in_flight": "In flight",
        "blocked": "Blocked",
        "waiting_on_governor": "Waiting on you",
        "ready": "Ready",
    }
    lines = [f"# Board ({board['capacity']['active']}/{cap} active)", ""]
    for name in ORDER_SECTIONS:
        lines.append(f"## {titles[name]}")
        cards = board[name]
        if not cards:
            lines.append("- (none)")
        for card in cards:
            lines.append(_line(card))
            for wait in card.get("waiting_on", []):
                lines.append(f"  - {wait['question']}")
        lines.append("")
    used = {gate: n for gate, n in board["overrides_per_gate"].items() if n}
    lines.append("## Overrides per gate")
    lines.extend([f"- {gate}: {n}" for gate, n in sorted(used.items())] or ["- (none)"])
    lines.append("")
    lines.append("## Unverified governor actions")
    actions = board["unverified_governor_actions"]
    lines.extend(
        [
            f"- {a.get('order_id') or a.get('decision')}: {a['kind']} {a.get('gate', '')}".rstrip()
            for a in actions
        ]
        or ["- (none)"]
    )
    return "\n".join(lines).rstrip() + "\n"
