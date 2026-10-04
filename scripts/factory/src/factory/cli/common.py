"""Shared CLI options, output envelope, and adapter providers. Frozen at CP0.

Command modules build adapters through `DEPS` so contract tests can substitute
`FakeGitHub` (tests replace `DEPS` attributes; non-test code never branches on it).
Commands report success with `emit` and failure or refusal by raising `CommandError`,
so `--json` always yields one `JsonEnvelope` (contracts/cli.md § JSON envelope).
"""

from __future__ import annotations

import importlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, NoReturn, Self

import typer
from pydantic import BaseModel, ConfigDict, Field, model_validator

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


class CliError(BaseModel):
    """Frozen at CP0. The `error` body of a failed `JsonEnvelope`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: int = Field(ge=1, le=4)
    message: str = Field(min_length=1)
    details: Any = None


class JsonEnvelope(BaseModel):
    """Frozen at CP0. The one JSON object a command prints on stdout under `--json`.

    `{"ok": true, "command", "data"}` on exit 0; `{"ok": false, "command", "error"}`
    otherwise. `command` is the space-separated command path (`check schema`, `claim`).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: bool
    command: str = Field(min_length=1)
    data: Any = None
    error: CliError | None = None

    @model_validator(mode="after")
    def _one_body(self) -> Self:
        if self.ok == (self.error is not None):
            raise ValueError("error is required exactly when ok is false")
        if not self.ok and self.data is not None:
            raise ValueError("a failed envelope carries error, not data")
        return self

    def render(self) -> str:
        body: dict[str, Any] = {"ok": self.ok, "command": self.command}
        if self.error is None:
            body["data"] = self.data
        else:
            body["error"] = self.error.model_dump(mode="json")
        return json.dumps(body, indent=2, sort_keys=True, default=str)


class CommandError(Exception):
    """Frozen at CP0. A command's failure or refusal.

    `run()` prints `message` on stderr, prints the error envelope under `--json`, and
    exits with `code` (`exit_codes`: 1 gate failure, 2 refused, 3 usage, 4 external).
    """

    def __init__(self, code: int, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.error = CliError(code=code, message=message, details=details)


def not_implemented(command: str) -> NoReturn:
    raise CommandError(exit_codes.USAGE, f"factory {command}: not implemented")


def emit(command: str, *, as_json: bool, text: str, data: Any = None) -> None:
    """Print a successful result: the envelope under `--json`, else `text`."""
    typer.echo(JsonEnvelope(ok=True, command=command, data=data).render() if as_json else text)


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
