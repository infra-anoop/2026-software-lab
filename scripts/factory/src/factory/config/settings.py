"""Typed loader for repo config (`factory.toml`) and process environment.

This module is the only place in the factory that reads the environment (I-A3).
Frozen at CP0: changing a field here needs an order amendment.
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr

CONFIG_FILENAME = "factory.toml"
DEFAULT_AUTONOMY_HORIZON_MINUTES = 60
GITHUB_ACTIONS_APP_ID = 15368
DEFAULT_EVIDENCE_MAX_BYTES = 1024 * 1024


class ConfigError(Exception):
    """`factory.toml` is missing or invalid (CLI exit code 3)."""


class IdentityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: Literal["recorded", "verified"] = "recorded"


class GitHubConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repository: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    api_url: str = "https://api.github.com"
    # The GitHub Actions integration: the only source every required `factory/*` status
    # check may be pinned to (contracts/gates.md § Status source).
    actions_app_id: int = Field(default=GITHUB_ACTIONS_APP_ID, ge=1)


class DecisionLintConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    jargon: list[str] = Field(default_factory=list)


class Settings(BaseModel):
    """Repo config from `factory.toml` (keys per tasks.md T002)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    bus_dir: str = "bus"
    spec_roots: list[str] = Field(default_factory=lambda: ["specs"])
    app_roots: list[str] = Field(default_factory=lambda: ["apps"])
    rule_paths: list[str] = Field(default_factory=list)
    concurrency_cap: int = Field(ge=1)
    autonomy_horizon_minutes: int = Field(ge=1)
    stale_multiplier: int = Field(default=3, ge=1)
    families: dict[str, str] = Field(default_factory=dict)
    governor_login: str = Field(min_length=1)
    identity: IdentityConfig = Field(default_factory=IdentityConfig)
    github: GitHubConfig
    decision_lint: DecisionLintConfig = Field(default_factory=DecisionLintConfig)
    # Largest `factory-evidence.json` the trusted judge reads (contracts/gates.md § Evidence
    # bundle).
    evidence_max_bytes: int = Field(default=DEFAULT_EVIDENCE_MAX_BYTES, ge=1)

    def family_of(self, model_name: str) -> str | None:
        """Family for a model name by longest matching prefix in `[families]`."""
        name = model_name.lower()
        matches = [prefix for prefix in self.families if name.startswith(prefix.lower())]
        if not matches:
            return None
        return self.families[max(matches, key=len)]


class EnvSettings(BaseModel):
    """Values that come from the process environment, never from git."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    github_token: SecretStr | None = None
    github_repository: str | None = None
    github_api_url: str | None = None
    app_id: str | None = None
    app_private_key: SecretStr | None = None


def find_repo_root(start: Path) -> Path:
    """Nearest directory from `start` up to its git root that holds `factory.toml`.

    The walk never leaves the git checkout, so a `factory.toml` above the git root is
    ignored. Raises `ConfigError` when none is found.
    """
    here = start.resolve()
    for directory in (here, *here.parents):
        if (directory / CONFIG_FILENAME).is_file():
            return directory
        if (directory / ".git").exists():
            raise ConfigError(
                f"{CONFIG_FILENAME}: not found from {here} up to git root {directory}"
            )
    raise ConfigError(f"{CONFIG_FILENAME}: not found from {here} (not inside a git checkout)")


def load_settings(repo: Path) -> Settings:
    """Load `<repo>/factory.toml`; raise `ConfigError` when missing or invalid."""
    path = Path(repo) / CONFIG_FILENAME
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"{path}: not found") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    try:
        return Settings.model_validate(raw)
    except ValueError as exc:
        raise ConfigError(f"{path}: {exc}") from exc


def load_env(environ: Mapping[str, str] | None = None) -> EnvSettings:
    """Read the factory's environment variables (defaults to `os.environ`)."""
    env = os.environ if environ is None else environ
    token = env.get("GITHUB_TOKEN")
    key = env.get("FACTORY_GITHUB_APP_PRIVATE_KEY")
    return EnvSettings(
        github_token=SecretStr(token) if token else None,
        github_repository=env.get("GITHUB_REPOSITORY") or None,
        github_api_url=env.get("GITHUB_API_URL") or None,
        app_id=env.get("FACTORY_GITHUB_APP_ID") or None,
        app_private_key=SecretStr(key) if key else None,
    )
