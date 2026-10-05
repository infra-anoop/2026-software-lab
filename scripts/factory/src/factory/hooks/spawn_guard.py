"""`spawn-guard` (subagentStart; CI twin `spawn-concurrency-cap`). LOG-ONLY.

Every launch is allowed (governor lock, FR-008 "logged"). An advisory goes to the hooks
output (`user_message`) when the task names no active order (claimed, not released, not
merged) and no existing review packet, or when `concurrency_cap` orders are already
active. Reads local refs only; never fetches.
"""

from __future__ import annotations

import re
from pathlib import Path

from factory.hooks._repo import MAIN_REFS, bus_dir, concurrency_cap, config, git, present

ORDER_ID = re.compile(r"\bwo-\d{8}-[a-z0-9]+(?:-[a-z0-9]+)*\b")
PACKET = re.compile(r"\bnotes/packets/[\w./-]+\.md\b")
WO_REF = re.compile(r"^refs/(?:heads|remotes/[^/]+)/wo/(?P<order_id>[^/\s]+)$")


def _wo_tips(root: Path) -> dict[str, set[str]]:
    out = git(
        root, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads/wo/", "refs/remotes/"
    )
    tips: dict[str, set[str]] = {}
    for line in out.splitlines():
        ref, _, sha = line.partition(" ")
        match = WO_REF.match(ref)
        if match and sha:
            tips.setdefault(match["order_id"], set()).add(sha)
    return tips


def _merged_tips(root: Path) -> set[str]:
    merged: set[str] = set()
    for main in MAIN_REFS:
        out = git(
            root,
            "for-each-ref",
            f"--merged={main}",
            "--format=%(objectname)",
            "refs/heads/wo/",
            "refs/remotes/",
        )
        merged.update(out.split())
    return merged


def active_orders(root: Path, bus: str) -> set[str]:
    """Orders claimed and not released on some `wo/*` tip, whose tips are not all merged."""
    tips = _wo_tips(root)
    merged = _merged_tips(root) if tips else set()
    candidates = {order_id: shas for order_id, shas in tips.items() if not shas <= merged}
    specs = [
        f"{sha}:{bus}/orders/{order_id}/{kind}.yaml"
        for order_id, shas in sorted(candidates.items())
        for sha in sorted(shas)
        for kind in ("claim", "release")
    ]
    found = iter(present(root, specs))
    active: set[str] = set()
    for order_id, shas in sorted(candidates.items()):
        claimed = released = False
        for _ in sorted(shas):
            claimed |= next(found, False)
            released |= next(found, False)
        if claimed and not released:
            active.add(order_id)
    return active


def advisory(task: str, root: Path) -> str:
    settings = config(root)
    named = sorted(set(ORDER_ID.findall(task)))
    packets = [p for p in PACKET.findall(task) if "review" in Path(p).name]
    has_packet = any((root / packet).is_file() for packet in packets)
    active = active_orders(root, bus_dir(settings))
    cap = concurrency_cap(settings)
    notes: list[str] = []
    if not has_packet and not any(order_id in active for order_id in named):
        if named:
            inactive = ", ".join(named)
            notes.append(f"no active order among {inactive} (not claimed, released or merged)")
        elif packets:
            notes.append(f"review packet {', '.join(packets)} does not exist")
        else:
            notes.append("the task names no active order and no review packet")
    if len(active) >= cap:
        notes.append(f"{len(active)} orders are active, at the concurrency cap of {cap}")
    if not notes:
        return ""
    return "spawn-guard (log only, launch allowed): " + "; ".join(notes) + "."


def handle(payload: dict[str, object], root: Path) -> tuple[int, dict[str, str]]:
    task = payload.get("task")
    text = advisory(task if isinstance(task, str) else "", root)
    response = {"permission": "allow"}
    if text:
        response["user_message"] = text
    return 0, response
