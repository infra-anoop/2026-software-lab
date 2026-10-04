"""`factory check schema` (P0) and `factory check hooks|registry|immutability` (slice C)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from factory.bus.schema import (
    SCHEMA_DIR,
    stale_schemas,
    validate_bus,
    validate_message_dir,
    write_schemas,
)
from factory.cli import exit_codes
from factory.cli.common import JsonOpt, RepoOpt, emit, not_implemented
from factory.config.settings import load_settings


def check_schema(
    path: Annotated[
        list[Path] | None,
        typer.Option("--path", help="Validate loose message files under PATH instead of the bus."),
    ] = None,
    write: Annotated[
        bool, typer.Option("--write", help="Regenerate scripts/factory/schemas/ first.")
    ] = False,
    json_out: JsonOpt = False,
    repo: RepoOpt = Path("."),
) -> None:
    """Validate every bus file and fail when the generated JSON Schemas are stale."""
    settings = load_settings(repo)
    written = [str(p) for p in write_schemas()] if write else []
    problems = stale_schemas(SCHEMA_DIR)
    if path:
        for directory in path:
            target = directory if directory.is_absolute() else repo / directory
            problems += validate_message_dir(
                target, autonomy_horizon_minutes=settings.autonomy_horizon_minutes
            )
    else:
        problems += validate_bus(repo, settings)
    text = "\n".join([*(f"wrote {p}" for p in written), *problems]) or "schema ok"
    emit(
        {"ok": not problems, "problems": problems, "written": written}, as_json=json_out, text=text
    )
    if problems:
        raise typer.Exit(exit_codes.GATE_FAILURE)


def check_hooks(json_out: JsonOpt = False, repo: RepoOpt = Path(".")) -> None:
    """Every hook in .cursor/hooks.json has a CI twin in the registry."""
    not_implemented("check hooks")


def check_registry(json_out: JsonOpt = False, repo: RepoOpt = Path(".")) -> None:
    """gates.yaml is valid (class/category rule, importable entrypoints)."""
    not_implemented("check registry")


def check_immutability(
    base: Annotated[str, typer.Option("--base", help="Base ref.")] = "origin/main",
    head: Annotated[str, typer.Option("--head", help="Head ref.")] = "HEAD",
    json_out: JsonOpt = False,
    repo: RepoOpt = Path("."),
) -> None:
    """No existing bus file is modified or deleted between base and head."""
    not_implemented("check immutability")
