"""`order issue`, `claim`, `release`: git is the lease authority.

Issue creates `wo/<order-id>` from `origin/main` with the order file as its only commit.
Claim and release are fast-forward pushes of one event file; two racing claims build on
the same branch tip, so the remote accepts exactly one of them. A claim whose push is
rejected, or finds origin already at its commit, lost the race.

Capacity uses the board's lifecycle derivation (git plus PR reality through `GitHubPort`):
an order holds a slot while it is claimed, in review, accepted or rejected. A release
event or a PR closed unmerged releases it; landing on `main` or a merged PR ends it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from factory.api import GitHubPort, OrderState
from factory.bus.models import Claim, Release, WorkOrder
from factory.bus.store import BusError, load_file
from factory.config.settings import Settings, load_env
from factory.github.rest import GitHubError
from factory.identity.app_token import AppTokenError, InstallationTokenSource
from factory.lifecycle.derive import derive_order
from factory.lifecycle.view import BusView, OrderRecord, load_messages, load_view
from factory.orders import git
from factory.orders.errors import External, Refused, Usage
from factory.orders.messages import build, path_of, to_yaml, utc_stamp
from factory.orders.paths import overlapping

ACTIVE_STATES = frozenset(
    {OrderState.CLAIMED, OrderState.IN_REVIEW, OrderState.ACCEPTED, OrderState.REJECTED}
)


@dataclass(frozen=True)
class Pushed:
    order_id: str
    branch: str
    sha: str
    path: str
    notes: list[str] = field(default_factory=list)


GitToken = Callable[[], str] | None


def git_token(settings: Settings) -> GitToken:
    """Who the order commands' git transport is: None (ambient git credentials) in
    recorded mode; in verified mode the App installation token, minted in-process. Missing
    App credentials are an external error here, before any git command runs."""
    if settings.identity.mode != "verified":
        return None
    env = load_env()
    try:
        source = InstallationTokenSource(
            app_id=env.app_id,
            private_key=env.app_private_key,
            repository=settings.github.repository,
            api_url=env.github_api_url or settings.github.api_url,
        )
    except AppTokenError as exc:
        raise External(f"cannot authenticate to origin as the GitHub App: {exc}") from exc
    return source.token


def _password(token: GitToken) -> str | None:
    if token is None:
        return None
    try:
        return token()
    except AppTokenError as exc:
        raise External(f"cannot authenticate to origin as the GitHub App: {exc}") from exc


def fetch_or_fail(repo: Path, token: GitToken) -> None:
    try:
        git.fetch(repo, password=_password(token))
    except git.GitError as exc:
        raise External(f"cannot reach origin: {exc}") from exc


def push_or_fail(
    repo: Path,
    sha: str,
    branch: str,
    *,
    token: GitToken,
    lost: str,
    first_writer: bool = True,
    advance: bool = True,
) -> list[str]:
    """Push `sha` to origin `branch`, then (`advance`) local `branch`; returns caller notes.

    No local ref moves unless the push landed. With a `token`, the push runs as the App
    and nothing falls back to ambient credentials.
    """
    password = _password(token)
    try:
        git.push(repo, sha, branch, first_writer=first_writer, password=password)
    except git.PushRejected as exc:
        try:
            git.fetch(repo, password=password)
        except git.GitError:
            pass
        raise Refused(lost) from exc
    except git.GitError as exc:
        raise External(f"push to origin failed: {exc}") from exc
    note = git.advance_local_branch(repo, branch, sha) if advance else None
    return [note] if note else []


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
    token = git_token(settings)
    fetch_or_fail(repo, token)
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
    notes = push_or_fail(
        repo, sha, branch, token=token, lost=f"{order_id} was issued by someone else first"
    )
    return Pushed(order_id=order_id, branch=branch, sha=sha, path=relative, notes=notes)


def _issued(view: BusView, order_id: str) -> OrderRecord:
    record = view.orders.get(order_id)
    if record is None or record.ref != git.remote_ref(git.order_branch(order_id)):
        raise Refused(f"{order_id} is not issued (no origin/wo/{order_id} with an order file)")
    if record.on_main:
        raise Refused(f"{order_id} has already landed on main")
    return record


def active_orders(
    view: BusView, github: GitHubPort, settings: Settings, now: datetime, *, besides: str
) -> list[OrderRecord]:
    """Orders other than `besides` that hold a slot, by the board's lifecycle derivation."""
    try:
        return [
            record
            for order_id, record in sorted(view.orders.items())
            if order_id != besides
            and derive_order(record, view, github, settings, now).state in ACTIVE_STATES
        ]
    except GitHubError as exc:
        raise External(f"cannot read pull requests to count active orders: {exc}") from exc


def _append(repo: Path, record: OrderRecord, relative: str, content: bytes, subject: str) -> str:
    base = git.git_text(repo, "rev-parse", record.ref)
    return git.commit_files(repo, base, {relative: content}, subject)


def claim_order(
    repo: Path,
    settings: Settings,
    order_id: str,
    *,
    github: GitHubPort,
    actor_model: str | None,
    worker_runtime: str,
    now: datetime,
) -> Pushed:
    if not actor_model:
        raise Usage("say which model is claiming with --actor-model")
    token = git_token(settings)
    fetch_or_fail(repo, token)
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
    active = active_orders(view, github, settings, now, besides=order_id)
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
    notes = push_or_fail(
        repo,
        sha,
        record.branch,
        token=token,
        lost=f"{order_id} was claimed by someone else first",
    )
    return Pushed(order_id=order_id, branch=record.branch, sha=sha, path=relative, notes=notes)


def release_order(
    repo: Path,
    settings: Settings,
    order_id: str,
    *,
    reason: str,
    actor_model: str,
    now: datetime,
) -> Pushed:
    token = git_token(settings)
    fetch_or_fail(repo, token)
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
    notes = push_or_fail(
        repo, sha, record.branch, token=token, lost=f"{order_id} moved on origin; try again"
    )
    return Pushed(order_id=order_id, branch=record.branch, sha=sha, path=relative, notes=notes)
