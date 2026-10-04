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
from factory.cli.common import (
    CommandError,
    JsonOpt,
    RepoOpt,
    emit,
    not_implemented,
    resolve_repo,
)
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
    repo: RepoOpt = None,
) -> None:
    """Validate every bus file and fail when the generated JSON Schemas are stale."""
    root = resolve_repo(repo)
    settings = load_settings(root)
    written = [str(p) for p in write_schemas()] if write else []
    problems = stale_schemas(SCHEMA_DIR)
    if path:
        for directory in path:
            problems += validate_message_dir(
                directory, autonomy_horizon_minutes=settings.autonomy_horizon_minutes
            )
    else:
        problems += validate_bus(root, settings)
    text = "\n".join([*(f"wrote {p}" for p in written), *problems]) or "schema ok"
    report = {"problems": problems, "written": written}
    if problems:
        if not json_out:
            typer.echo(text)
        raise CommandError(exit_codes.GATE_FAILURE, f"{len(problems)} schema problem(s)", report)
    emit("check schema", as_json=json_out, text=text, data=report)


def check_hooks(json_out: JsonOpt = False, repo: RepoOpt = None) -> None:
    """Every hook in .cursor/hooks.json has a CI twin in the registry."""
    not_implemented("check hooks")


def check_registry(json_out: JsonOpt = False, repo: RepoOpt = None) -> None:
    """gates.yaml is valid (class/category rule, importable entrypoints)."""
    not_implemented("check registry")


def check_immutability(
    base: Annotated[str, typer.Option("--base", help="Base ref.")] = "origin/main",
    head: Annotated[str, typer.Option("--head", help="Head ref.")] = "HEAD",
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """No existing bus file is modified or deleted between base and head."""
    not_implemented("check immutability")
