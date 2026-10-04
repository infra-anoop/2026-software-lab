"""Slice B: `factory check intent [--coverage]` (stub at CP0)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from factory.cli.common import JsonOpt, RepoOpt, not_implemented


def check_intent(
    coverage: Annotated[
        bool, typer.Option("--coverage", help="Report effective coverage.")
    ] = False,
    json_out: JsonOpt = False,
    repo: RepoOpt = Path("."),
) -> None:
    """Every intent maps to at least one check (presence); optionally effective coverage."""
    not_implemented("check intent")
