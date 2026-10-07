"""`factory check schema` (P0) and `factory check hooks|registry|immutability` (slice C)."""

from __future__ import annotations

import importlib
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
    resolve_repo,
)
from factory.config.settings import load_settings
from factory.gates.pr.bus_immutable import immutability_problems
from factory.gates.registry import Gate
from factory.gates.repo._git import GitError
from factory.gates.repo.fail_mode import REGISTRY_FILE, parse_registry
from factory.gates.repo.hook_twin import HOOKS_FILE, twin_problems


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


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def _report(command: str, problems: list[str], ok_text: str, *, json_out: bool) -> None:
    report = {"problems": problems}
    if problems:
        if not json_out:
            typer.echo("\n".join(problems))
        raise CommandError(exit_codes.GATE_FAILURE, f"{len(problems)} {command} problem(s)", report)
    emit(f"check {command}", as_json=json_out, text=ok_text, data=report)


def _entrypoint_problem(gate: Gate) -> str | None:
    try:
        getattr(importlib.import_module(gate.module), gate.function)
    except (ImportError, AttributeError) as exc:
        return f"{gate.id}: entrypoint {gate.entrypoint} is not importable ({exc})"
    return None


def check_hooks(json_out: JsonOpt = False, repo: RepoOpt = None) -> None:
    """Every hook in .cursor/hooks.json has a CI twin in the registry."""
    root = resolve_repo(repo)
    problems = twin_problems(_read(root / REGISTRY_FILE), _read(root / HOOKS_FILE))
    _report("hooks", problems, "every hook has a CI twin", json_out=json_out)


def check_registry(json_out: JsonOpt = False, repo: RepoOpt = None) -> None:
    """gates.yaml is valid (class/category rule, importable entrypoints)."""
    root = resolve_repo(repo)
    gates, problems = parse_registry(_read(root / REGISTRY_FILE), str(root / REGISTRY_FILE))
    problems += [p for p in map(_entrypoint_problem, gates) if p]
    _report("registry", problems, f"{len(gates)} gates registered", json_out=json_out)


def check_immutability(
    base: Annotated[str, typer.Option("--base", help="Base ref.")] = "origin/main",
    head: Annotated[str, typer.Option("--head", help="Head ref.")] = "HEAD",
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """No existing bus file is modified or deleted between base and head."""
    root = resolve_repo(repo)
    settings = load_settings(root)
    try:
        problems = immutability_problems(root, base, head, settings.bus_dir)
    except GitError as exc:
        raise CommandError(exit_codes.USAGE, str(exc)) from exc
    _report("immutability", problems, "no existing bus file changed", json_out=json_out)
