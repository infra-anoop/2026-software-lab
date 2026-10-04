"""Slice A: order, claim, release, handoff, PR, verdict, bus PR commands (stubs at CP0)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from factory.cli.common import JsonOpt, RepoOpt, not_implemented

OrderIdArg = Annotated[str, typer.Argument(help="Order id (wo-YYYYMMDD-<slug>).")]


def order_new(
    feature: Annotated[str, typer.Option("--feature", help="Feature folder under specs/.")],
    from_task: Annotated[list[str], typer.Option("--from-task", help="Task id (repeatable).")],
    slug: Annotated[str | None, typer.Option("--slug", help="Order id slug.")] = None,
    size_minutes: Annotated[
        int | None, typer.Option("--size-minutes", help="Size estimate in minutes.")
    ] = None,
    lock: Annotated[
        list[str] | None,
        typer.Option("--lock", help="Fidelity for a touched named lock: ID=letter|intent|waived."),
    ] = None,
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Scaffold an order file from tasks locally and validate it."""
    not_implemented("order new")


def order_issue(order_id: OrderIdArg, json_out: JsonOpt = False, repo: RepoOpt = None) -> None:
    """Create wo/<order-id> from main with the order as its first commit; push."""
    not_implemented("order issue")


def claim(
    order_id: OrderIdArg,
    actor_model: Annotated[
        str | None, typer.Option("--actor-model", help="Claiming worker's model.")
    ] = None,
    worker_runtime: Annotated[
        str, typer.Option("--worker-runtime", help="local_subagent | cloud_agent.")
    ] = "local_subagent",
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Fast-forward push of the claim event to wo/<order-id>."""
    not_implemented("claim")


def release(
    order_id: OrderIdArg,
    reason: Annotated[str, typer.Option("--reason", help="abandoned | superseded | blocked.")],
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Append a release event; frees capacity."""
    not_implemented("release")


def handoff(order_id: OrderIdArg, json_out: JsonOpt = False, repo: RepoOpt = None) -> None:
    """Validate the handoff and run-complete event on the order branch."""
    not_implemented("handoff")


def pr_open(order_id: OrderIdArg, json_out: JsonOpt = False, repo: RepoOpt = None) -> None:
    """Open PR wo/<order-id> -> main; body links order and intents."""
    not_implemented("pr open")


def verdict(
    order_id: OrderIdArg,
    file: Annotated[Path, typer.Option("--file", help="Verdict YAML file.")],
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Validate a verdict (family, isolation inputs) and commit it to the branch."""
    not_implemented("verdict")


def bus_pr(
    message: Annotated[list[Path], typer.Option("--message", help="Message file (repeatable).")],
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Open a bus PR for decision, correction, or post-mortem messages."""
    not_implemented("bus pr")
