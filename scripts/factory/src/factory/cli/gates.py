"""Slice C: `factory override`, `gate run`, `hook`, `retro` (stubs at CP0)."""

from __future__ import annotations

from typing import Annotated

import typer

from factory.cli.common import JsonOpt, RepoOpt, not_implemented


def override(
    order_id: Annotated[str, typer.Argument(help="Order id.")],
    gate: Annotated[str, typer.Option("--gate", help="Gate id to override.")],
    reason: Annotated[str, typer.Option("--reason", help="Why the override is justified.")],
    actor: Annotated[
        str, typer.Option("--actor", help="governor | orchestrator.")
    ] = "orchestrator",
    actor_model: Annotated[
        str | None, typer.Option("--actor-model", help="Model of a non-governor actor.")
    ] = None,
    pr: Annotated[int | None, typer.Option("--pr", help="PR number.")] = None,
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Write an override message for a failing gate."""
    not_implemented("override")


def gate_run(
    gate: Annotated[list[str] | None, typer.Option("--gate", help="Gate id (repeatable).")] = None,
    pr: Annotated[int | None, typer.Option("--pr", help="PR number.")] = None,
    base: Annotated[str | None, typer.Option("--base", help="Base ref.")] = None,
    head: Annotated[str | None, typer.Option("--head", help="Head ref.")] = None,
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Run registered gates; print per-intent results."""
    not_implemented("gate run")


def hook(
    name: Annotated[str, typer.Argument(help="Hook name (contracts/hooks.md).")],
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Cursor hook entrypoint: stdin JSON -> stdout JSON."""
    not_implemented("hook")


def retro(
    since: Annotated[str, typer.Option("--since", help="Git ref where Wave 1 started.")],
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Run P1 gates retroactively on merged Wave 1 PRs; write a report."""
    not_implemented("retro")
