"""Slice A: `factory status`, `factory decisions`, `factory scorecard` (stubs at CP0)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from factory.cli.common import JsonOpt, RepoOpt, not_implemented


def status(json_out: JsonOpt = False, repo: RepoOpt = Path(".")) -> None:
    """Print the board derived from git, PR, and check reality."""
    not_implemented("status")


def decisions(json_out: JsonOpt = False, repo: RepoOpt = Path(".")) -> None:
    """Print open decision requests (the governor's batch)."""
    not_implemented("decisions")


def scorecard(
    sprint: Annotated[str | None, typer.Option("--sprint", help="Sprint id.")] = None,
    json_out: JsonOpt = False,
    repo: RepoOpt = Path("."),
) -> None:
    """Compute the scorecard from run events, verdicts, corrections, overrides."""
    not_implemented("scorecard")
