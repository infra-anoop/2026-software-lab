"""Frozen cross-slice interfaces (tasks.md T010).

Every name in this module is **frozen at CP0**: slices code against it, and a change
needs an order amendment from the orchestrator. Gate entrypoints registered in
`scripts/factory/gates.yaml` have the signature `(ctx: GateContext) -> GateResult`.
"""

from __future__ import annotations

import importlib
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from factory.bus.models import Message
from factory.config.settings import Settings
from factory.gates.registry import RegistryError, load_registry


class GateEntrypointError(LookupError):
    """Frozen at CP0. The gate id is unregistered or its entrypoint cannot be imported.

    `run_gate` raises this instead of returning a result so callers (the runner, the
    seeds suite) can tell "gate not implemented" apart from "gate ran and failed".
    """


class GateContext(BaseModel):
    """Frozen at CP0. Everything a gate may read; gates write nothing."""

    model_config = ConfigDict(frozen=True)

    repo_path: Path
    base_sha: str
    head_sha: str
    pr_number: int | None = None
    order_id: str | None = None
    config: Settings
    bus_snapshot: list[Message] = Field(default_factory=list)


class GateResult(BaseModel):
    """Frozen at CP0. One gate's outcome; `messages` must name the gate id on failure."""

    model_config = ConfigDict(frozen=True)

    gate_id: str
    passed: bool
    messages: list[str] = Field(default_factory=list)
    intent_ids: list[str] = Field(default_factory=list)


def run_gate(gate_id: str, ctx: GateContext) -> GateResult:
    """Frozen at CP0. Dispatch to the gate's registry entrypoint (no override logic).

    Raises `GateEntrypointError` when the gate is unregistered or not importable.
    """
    try:
        gate = load_registry().get(gate_id)
    except RegistryError as exc:
        raise GateEntrypointError(str(exc)) from exc
    try:
        module = importlib.import_module(gate.module)
        function = getattr(module, gate.function)
    except (ImportError, AttributeError) as exc:
        raise GateEntrypointError(
            f"gate {gate_id!r}: entrypoint {gate.entrypoint} is not importable ({exc})"
        ) from exc
    result = function(ctx)
    if not isinstance(result, GateResult):
        raise TypeError(f"gate {gate_id!r}: entrypoint returned {type(result).__name__}")
    return result


class OrderState(StrEnum):
    """Frozen at CP0. Derived lifecycle states (data-model § Lifecycle).

    `stale` and `blocked_on_governor` are overlays carried in
    `OrderLifecycle.overlays`, never the primary `state`.
    """

    ISSUED = "issued"
    CLAIMED = "claimed"
    IN_REVIEW = "in_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MERGED = "merged"
    RELEASED = "released"
    STALE = "stale"
    BLOCKED_ON_GOVERNOR = "blocked_on_governor"


OVERLAY_STATES = frozenset({OrderState.STALE, OrderState.BLOCKED_ON_GOVERNOR})


class OrderLifecycle(BaseModel):
    """Frozen at CP0. One order's derived state (never stored)."""

    model_config = ConfigDict(frozen=True)

    order_id: str
    branch: str
    state: OrderState
    overlays: list[OrderState] = Field(default_factory=list)
    pr_number: int | None = None
    owned_paths: list[str] = Field(default_factory=list)


class LifecycleSnapshot(BaseModel):
    """Frozen at CP0. Every order's derived state at one moment (input to the board)."""

    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    orders: list[OrderLifecycle] = Field(default_factory=list)


class PullRequest(BaseModel):
    """Frozen at CP0. The PR fields the factory reads (GitHub REST subset)."""

    model_config = ConfigDict(frozen=True)

    number: int
    head_ref: str
    head_sha: str
    base_ref: str
    title: str = ""
    body: str = ""
    open: bool
    merged: bool
    author_login: str = ""
    html_url: str = ""


class PullRequestReview(BaseModel):
    """Frozen at CP0. A PR review (GitHub REST subset)."""

    model_config = ConfigDict(frozen=True)

    id: int
    user_login: str
    review_state: Literal["APPROVED", "CHANGES_REQUESTED", "COMMENTED", "DISMISSED", "PENDING"]
    commit_id: str
    submitted_at: datetime | None = None


class CheckRun(BaseModel):
    """Frozen at CP0. A check run on a commit (GitHub REST subset)."""

    model_config = ConfigDict(frozen=True)

    name: str
    head_sha: str
    run_status: Literal["queued", "in_progress", "completed", "waiting", "requested", "pending"]
    conclusion: (
        Literal[
            "success",
            "failure",
            "neutral",
            "cancelled",
            "skipped",
            "timed_out",
            "action_required",
            "stale",
        ]
        | None
    ) = None


CommitStatusValue = Literal["success", "failure", "error", "pending"]


class CommitStatus(BaseModel):
    """Frozen at CP0. One commit-status context on a sha (GitHub REST subset).

    Commit statuses (`factory/<gate-id>` contexts) and check runs are separate GitHub
    APIs; lifecycle needs both to decide "required checks green".
    """

    model_config = ConfigDict(frozen=True)

    context: str
    state: CommitStatusValue
    description: str = ""
    target_url: str | None = None


@runtime_checkable
class GitHubPort(Protocol):
    """Frozen at CP0. Everything the factory asks of GitHub (adapter: `factory.github.rest`)."""

    def list_prs_by_head(self, head_branch: str) -> list[PullRequest]:
        """PRs (open and closed) whose head is `head_branch` in this repo."""
        ...

    def get_pr(self, number: int) -> PullRequest | None:
        """PR `number` in this repo, or None when there is none (CI mode needs no head branch)."""
        ...

    def pr_reviews(self, pr_number: int) -> list[PullRequestReview]: ...

    def check_runs(self, sha: str) -> list[CheckRun]: ...

    def create_pr(
        self, head_branch: str, base_branch: str, title: str, body: str
    ) -> PullRequest: ...

    def set_commit_status(
        self,
        sha: str,
        context: str,
        value: CommitStatusValue,
        description: str,
        target_url: str | None = None,
    ) -> None: ...

    def list_commit_statuses(self, sha: str) -> list[CommitStatus]:
        """The latest status per context on `sha` (GitHub's combined status); `[]` if none."""
        ...


@runtime_checkable
class IdentityPort(Protocol):
    """Frozen at CP0. Governor identity check (D4-A; recorded-only until the App is live)."""

    def is_governor_verified(self, message: Message, pr: PullRequest | None) -> bool:
        """True only when `message` is a governor action proven by GitHub identity."""
        ...
