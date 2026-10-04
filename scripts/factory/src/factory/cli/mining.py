"""US7 (Wave 2): `factory correction new`, `factory sprint close` (stubs at CP0)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from factory.cli.common import JsonOpt, RepoOpt, not_implemented


def correction_new(
    target: Annotated[str, typer.Option("--target", help="Order, PR, or message id.")],
    what: Annotated[str, typer.Option("--what", help="What was wrong.")],
    tag: Annotated[str, typer.Option("--tag", help="drift | routing | smell | scope | other.")],
    links_to: Annotated[
        str | None, typer.Option("--links-to", help="Pattern or correction id it repeats.")
    ] = None,
    json_out: JsonOpt = False,
    repo: RepoOpt = Path("."),
) -> None:
    """Record a governor correction; a repeat link emits a rule/check proposal order."""
    not_implemented("correction new")


def sprint_close(
    sprint: Annotated[str, typer.Option("--sprint", help="Sprint id.")],
    json_out: JsonOpt = False,
    repo: RepoOpt = Path("."),
) -> None:
    """Refuse unless the post-mortem exists and dispositions every correction."""
    not_implemented("sprint close")
