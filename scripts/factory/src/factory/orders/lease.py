"""`order issue`, `claim`, `release`: git is the lease authority.

Issue creates `wo/<order-id>` from `origin/main` with the order file as its only commit.
Claim and release are fast-forward pushes of one event file; two racing claims build on
the same branch tip, so the remote accepts exactly one of them.

Capacity is read from git only: an order holds a slot from its claim until a release
event or until its order file lands on `main`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from factory.bus.models import Claim, Release, WorkOrder
from factory.bus.store import BusError, load_file
from factory.config.settings import Settings
from factory.lifecycle.view import BusView, OrderRecord, load_messages, load_view
from factory.orders import git
from factory.orders.errors import External, Refused, Usage
from factory.orders.messages import build, path_of, to_yaml, utc_stamp
from factory.orders.paths import overlapping


@dataclass(frozen=True)
class Pushed:
    order_id: str
    branch: str
    sha: str
    path: str


def fetch_or_fail(repo: Path) -> None:
    try:
        git.fetch(repo)
    except git.GitError as exc:
        raise External(f"cannot reach origin: {exc}") from exc


def push_or_fail(repo: Path, sha: str, branch: str, *, lost: str) -> None:
    try:
        git.push(repo, sha, branch)
    except git.PushRejected as exc:
        raise Refused(lost) from exc
    except git.GitError as exc:
        raise External(f"push to origin failed: {exc}") from exc


def waiting_prompts(view: BusView, order: WorkOrder) -> list[str]:
    return [request.prompt for request in view.open_dependencies(order)]


def _refuse_if_waiting(view: BusView, order: WorkOrder) -> None:
    prompts = waiting_prompts(view, order)
    if prompts:
        lines = "\n".join(f"- {prompt}" for prompt in prompts)
        raise Refused(f"This work waits on your decision:\n{lines}", details={"questions": prompts})


def issue_order(repo: Path, settings: Settings, order_id: str) -> Pushed:
    relative = f"{settings.bus_dir}/orders/{order_id}/order.yaml"
    if not (repo / relative).is_file():
        raise Refused(f"no order file at {relative}; scaffold it with `factory order new`")
    try:
        order = load_file(repo, None, relative, settings).message
    except BusError as exc:
        raise Refused(f"the order file is invalid: {exc}") from exc
    if not isinstance(order, WorkOrder) or order.id != order_id:
        raise Refused(f"{relative} is not order {order_id}")
    if not order.checks:
        raise Refused(
            "the order lists no checks, so it could never be accepted; name the gates it must"
            " pass under checks"
        )
    fetch_or_fail(repo)
    main = git.main_ref(repo)
    if main is None:
        raise External("origin has no main branch to issue from")
    view = BusView(main_ref=main, main_messages=load_messages(repo, main, settings))
    _refuse_if_waiting(view, order)
    branch = git.order_branch(order_id)
    if git.rev_parse(repo, git.remote_ref(branch)):
        raise Refused(f"{order_id} is already issued")
    base = git.git_text(repo, "rev-parse", main)
    sha = git.commit_files(
        repo, base, {relative: (repo / relative).read_bytes()}, f"order: {order_id}"
    )
    push_or_fail(repo, sha, branch, lost=f"{order_id} was issued by someone else first")
    git.advance_local_branch(repo, branch, sha)
    return Pushed(order_id=order_id, branch=branch, sha=sha, path=relative)


def _issued(view: BusView, order_id: str) -> OrderRecord:
    record = view.orders.get(order_id)
    if record is None or record.ref != git.remote_ref(git.order_branch(order_id)):
        raise Refused(f"{order_id} is not issued (no origin/wo/{order_id} with an order file)")
    if record.on_main:
        raise Refused(f"{order_id} has already landed on main")
    return record


def holds_slot(record: OrderRecord) -> bool:
    return record.one(Claim) is not None and record.one(Release) is None and not record.on_main


def _append(repo: Path, record: OrderRecord, relative: str, content: bytes, subject: str) -> str:
    base = git.git_text(repo, "rev-parse", record.ref)
    return git.commit_files(repo, base, {relative: content}, subject)


def claim_order(
    repo: Path,
    settings: Settings,
    order_id: str,
    *,
    actor_model: str | None,
    worker_runtime: str,
    now: datetime,
) -> Pushed:
    if not actor_model:
        raise Usage("say which model is claiming with --actor-model")
    fetch_or_fail(repo)
    view = load_view(repo, settings)
    record = _issued(view, order_id)
    if record.one(Claim) is not None:
        released = record.one(Release) is not None
        raise Refused(
            f"{order_id} was claimed and released; issue a new order"
            if released
            else f"{order_id} is already claimed"
        )
    _refuse_if_waiting(view, record.order)
    if record.blocker_questions() and order_id not in view.answered_orders():
        raise Refused(f"{order_id} waits on the governor: {record.blocker_questions()[0]}")
    active = [r for r in view.orders.values() if r.order_id != order_id and holds_slot(r)]
    cap = settings.concurrency_cap
    if len(active) >= cap:
        names = ", ".join(sorted(r.order_id for r in active))
        raise Refused(f"concurrency cap {cap} reached ({len(active)} active: {names})")
    for other in active:
        clashes = overlapping(list(record.order.owned_paths), list(other.order.owned_paths))
        if clashes:
            mine, theirs = clashes[0]
            raise Refused(f"owned paths overlap active order {other.order_id}: {mine} vs {theirs}")
    claim = build(
        {
            "schema_version": 1,
            "kind": "claim",
            "id": f"{order_id}.claim",
            "created": utc_stamp(now),
            "actor": "worker",
            "actor_model": actor_model,
            "claimed_at": utc_stamp(now),
            "worker_runtime": worker_runtime,
            "refs": [order_id],
        },
        settings,
    )
    relative = path_of(claim, settings)
    sha = _append(repo, record, relative, to_yaml(claim), f"claim: {order_id}")
    push_or_fail(repo, sha, record.branch, lost=f"{order_id} was claimed by someone else first")
    git.advance_local_branch(repo, record.branch, sha)
    return Pushed(order_id=order_id, branch=record.branch, sha=sha, path=relative)


def release_order(
    repo: Path,
    settings: Settings,
    order_id: str,
    *,
    reason: str,
    actor_model: str,
    now: datetime,
) -> Pushed:
    fetch_or_fail(repo)
    view = load_view(repo, settings)
    record = _issued(view, order_id)
    if record.one(Release) is not None:
        raise Refused(f"{order_id} is already released")
    release = build(
        {
            "schema_version": 1,
            "kind": "release",
            "id": f"{order_id}.release",
            "created": utc_stamp(now),
            "actor": "orchestrator",
            "actor_model": actor_model,
            "reason": reason,
            "refs": [order_id],
        },
        settings,
    )
    if not isinstance(release, Release):
        raise Usage("not a release event")
    relative = path_of(release, settings)
    sha = _append(repo, record, relative, to_yaml(release), f"release: {order_id}")
    push_or_fail(repo, sha, record.branch, lost=f"{order_id} moved on origin; try again")
    git.advance_local_branch(repo, record.branch, sha)
    return Pushed(order_id=order_id, branch=record.branch, sha=sha, path=relative)
