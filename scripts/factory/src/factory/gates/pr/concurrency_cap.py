"""`spawn-concurrency-cap` (I-X4, FR-008): the CI twin of the claim cap.

Replays claim events (`claimed_at`) in timestamp order across every `wo/*` branch in the
repository (local and remote-tracking). An order is active from its claim until its
release (`created`) or until its branch tip merges into the base branch. The PR's order
is blocked when it has no claim at head, or when `concurrency_cap` orders were already
active at the moment of its claim. Ties on `claimed_at` are broken by order id.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from factory.api import GateContext, GateResult
from factory.bus.models import Claim, Release
from factory.bus.store import BusError, parse_bus_text
from factory.gates.repo._git import failed, git, passed, read_specs

GATE_ID = "spawn-concurrency-cap"
WO_REF = re.compile(r"^refs/(?:heads|remotes/[^/]+)/wo/(?P<order_id>[^/]+)$")


@dataclass
class OrderEvents:
    order_id: str
    claimed_at: datetime | None = None
    released_at: datetime | None = None
    merged_at: datetime | None = None
    tips: set[str] = field(default_factory=set)

    def active_at(self, moment: datetime) -> bool:
        ended = [t for t in (self.released_at, self.merged_at) if t is not None]
        return self.claimed_at is not None and not any(t <= moment for t in ended)


def work_order_tips(repo: Path) -> dict[str, set[str]]:
    """Order id -> tip shas of its `wo/<order-id>` refs (local and remote-tracking)."""
    out = git(
        repo, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads/wo/", "refs/remotes/"
    )
    tips: dict[str, set[str]] = {}
    for line in out.splitlines():
        name, _, sha = line.partition(" ")
        match = WO_REF.match(name)
        if match:
            tips.setdefault(match["order_id"], set()).add(sha)
    return tips


def _parse(text: str | None, path: str, horizon: int) -> Claim | Release | None:
    if text is None:
        return None
    try:
        message = parse_bus_text(text, path, autonomy_horizon_minutes=horizon)
    except BusError:
        return None
    return message if isinstance(message, Claim | Release) else None


def merge_times(repo: Path, tips: set[str], base: str) -> dict[str, datetime]:
    """Tip sha -> committer time of the base first-parent commit that merged it."""
    first_parent = [
        (sha, int(stamp))
        for sha, stamp in (
            line.split()
            for line in git(repo, "log", "--first-parent", "--format=%H %ct", base).splitlines()
        )
    ]
    on_chain = dict(first_parent)
    times: dict[str, datetime] = {}
    for tip in tips:
        if tip in on_chain:
            times[tip] = datetime.fromtimestamp(on_chain[tip], UTC)
            continue
        descendants = set(git(repo, "rev-list", "--ancestry-path", f"{tip}..{base}").split())
        merges = [stamp for sha, stamp in first_parent if sha in descendants]
        if merges:
            times[tip] = datetime.fromtimestamp(min(merges), UTC)
    return times


def _merged_tips(repo: Path, base: str) -> set[str]:
    out = git(
        repo,
        "for-each-ref",
        f"--merged={base}",
        "--format=%(objectname)",
        "refs/heads/wo/",
        "refs/remotes/",
    )
    return set(out.split())


def replay(ctx: GateContext, order_id: str) -> tuple[datetime | None, list[OrderEvents]]:
    """The PR order's claim time (at head) and every other order's events."""
    repo, bus_dir = ctx.repo_path, ctx.config.bus_dir
    horizon = ctx.config.autonomy_horizon_minutes
    tips = work_order_tips(repo)
    tips.pop(order_id, None)
    orders = {oid: OrderEvents(oid, tips=shas) for oid, shas in tips.items()}
    specs: list[tuple[OrderEvents, str, str]] = []
    for events in orders.values():
        for sha in sorted(events.tips):
            for name in ("claim", "release"):
                path = f"{bus_dir}/orders/{events.order_id}/{name}.yaml"
                specs.append((events, path, f"{sha}:{path}"))
    own_path = f"{bus_dir}/orders/{order_id}/claim.yaml"
    texts = read_specs(repo, [f"{ctx.head_sha}:{own_path}", *(spec for _, _, spec in specs)])
    own = _parse(texts[0], own_path, horizon)
    for (events, path, _), text in zip(specs, texts[1:], strict=True):
        message = _parse(text, path, horizon)
        if isinstance(message, Claim):
            claimed = message.claimed_at
            events.claimed_at = min(filter(None, (events.claimed_at, claimed)))
        elif isinstance(message, Release):
            released = message.created
            events.released_at = min(filter(None, (events.released_at, released)))
    merged = _merged_tips(repo, ctx.base_sha)
    candidates = {sha for e in orders.values() if e.claimed_at for sha in e.tips & merged}
    times = merge_times(repo, candidates, ctx.base_sha) if candidates else {}
    for events in orders.values():
        stamps = [times[sha] for sha in events.tips if sha in times]
        events.merged_at = min(stamps) if stamps else None
    own_claim = own.claimed_at if isinstance(own, Claim) else None
    return own_claim, list(orders.values())


def run(ctx: GateContext) -> GateResult:
    order_id = ctx.order_id
    if order_id is None:
        return passed(GATE_ID, "not a work-order PR")
    cap = ctx.config.concurrency_cap
    claimed_at, others = replay(ctx, order_id)
    if claimed_at is None:
        return failed(
            GATE_ID, [f"order {order_id} has no claim at head; run `factory claim {order_id}`"]
        )
    me = (claimed_at, order_id)
    before = sorted(
        e.order_id
        for e in others
        if e.claimed_at is not None and (e.claimed_at, e.order_id) < me and e.active_at(claimed_at)
    )
    if len(before) >= cap:
        return failed(
            GATE_ID,
            [
                f"order {order_id} was claimed at {claimed_at.isoformat()} while {len(before)}"
                f" orders were already active (cap {cap}): {', '.join(before)}"
            ],
        )
    return passed(
        GATE_ID, f"order {order_id} claimed with {len(before)} active before it (cap {cap})"
    )
