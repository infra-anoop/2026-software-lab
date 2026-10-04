"""Shared CLI options and adapter providers. Frozen at CP0.

Command modules build adapters through `DEPS` so contract tests can substitute
`FakeGitHub` (tests replace `DEPS` attributes; non-test code never branches on it).
"""

from __future__ import annotations

import importlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, NoReturn

import typer

from factory.api import GitHubPort, IdentityPort
from factory.cli import exit_codes
from factory.config.settings import ConfigError, EnvSettings, Settings, find_repo_root

JsonOpt = Annotated[bool, typer.Option("--json", help="Machine-readable JSON output.")]
RepoOpt = Annotated[
    Path | None,
    typer.Option(
        "--repo",
        help="Repository root (default: nearest factory.toml from the CWD up to the git root).",
        file_okay=False,
        dir_okay=True,
    ),
]

GITHUB_ADAPTER = "factory.github.rest:build_github"
IDENTITY_ADAPTER = "factory.identity.adapter:build_identity"


def resolve_repo(repo: Path | None) -> Path:
    """`--repo` when given, else the discovered repo root; every command calls this first."""
    return repo if repo is not None else find_repo_root(Path.cwd())


def not_implemented(command: str) -> NoReturn:
    typer.echo(f"factory {command}: not implemented", err=True)
    raise typer.Exit(exit_codes.USAGE)


def emit(payload: dict[str, Any], *, as_json: bool, text: str) -> None:
    typer.echo(json.dumps(payload, indent=2, sort_keys=True, default=str) if as_json else text)


def _load_adapter(spec: str) -> Callable[..., Any]:
    module_name, function_name = spec.split(":", 1)
    try:
        return getattr(importlib.import_module(module_name), function_name)
    except (ImportError, AttributeError) as exc:
        raise ConfigError(f"adapter {spec} is not available ({exc})") from exc


def _default_github(settings: Settings, env: EnvSettings) -> GitHubPort:
    adapter: GitHubPort = _load_adapter(GITHUB_ADAPTER)(settings, env)
    return adapter


def _default_identity(settings: Settings, github: GitHubPort) -> IdentityPort:
    adapter: IdentityPort = _load_adapter(IDENTITY_ADAPTER)(settings, github)
    return adapter


def _utc_now() -> datetime:
    return datetime.now(UTC)


class Deps:
    """Adapter providers used by command modules (slice A supplies the real adapters)."""

    def __init__(self) -> None:
        self.github: Callable[[Settings, EnvSettings], GitHubPort] = _default_github
        self.identity: Callable[[Settings, GitHubPort], IdentityPort] = _default_identity
        self.clock: Callable[[], datetime] = _utc_now


DEPS = Deps()
