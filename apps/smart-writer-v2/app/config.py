"""Centralized env loading for Smart Writer V2.

Cattle rule: names live in git. REQUIRED_ENV_NAMES / ALL_ENV_NAMES are parsed by
``scripts/validate_deploy_env.py`` (string-literal tuples only).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, create_model
from pydantic_settings import BaseSettings, SettingsConfigDict

_APP_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_ENV_NAMES: tuple[str, ...] = ("OPENAI_API_KEY",)
ALL_ENV_NAMES: tuple[str, ...] = (
    "OPENAI_API_KEY",
    "SMART_WRITER_V2_AUDIT_SECRET",
    "TAVILY_API_KEY",
    "LOGFIRE_TOKEN",
)

DEFAULT_JOB_CONCURRENCY = 1
DEFAULT_JOB_QUEUE_MAX = 4
DEFAULT_JOB_TIMEOUT_SEC = 300.0


class _SettingsBase(BaseSettings):
    """pydantic-settings: code defaults → app-root ``.env`` → process env (process wins)."""

    model_config = SettingsConfigDict(
        env_file=_APP_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
        populate_by_name=True,
    )


def _settings_field_specs(names: tuple[str, ...]) -> dict:
    return {
        name.lower(): (
            str,
            Field(default="", alias=name, validation_alias=name),
        )
        for name in names
    }


Settings = create_model(
    "Settings",
    __base__=_SettingsBase,
    **_settings_field_specs(ALL_ENV_NAMES),
)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings snapshot. Tests must call ``get_settings.cache_clear()`` after env patches."""
    return Settings()


def _settings_str(env_name: str, default: str = "") -> str:
    """Read a Settings field by canonical env name; empty/unset → ``default``."""
    raw = getattr(get_settings(), env_name.lower(), "")
    text = str(raw or "").strip()
    return text if text else default


def get_openai_api_key() -> str | None:
    """Return OPENAI_API_KEY or None if unset."""
    raw = _settings_str("OPENAI_API_KEY")
    return raw or None


def get_audit_secret() -> str | None:
    """Shared secret for mutating/job routes. ``None`` if unset (fail closed at the API)."""
    raw = _settings_str("SMART_WRITER_V2_AUDIT_SECRET")
    return raw or None


def get_tavily_api_key() -> str | None:
    """Return TAVILY_API_KEY or None."""
    raw = _settings_str("TAVILY_API_KEY")
    return raw or None


def get_job_timeout_sec() -> float | None:
    """Wall-clock seconds for in-process jobs; ``None`` means no server-side timeout."""
    return DEFAULT_JOB_TIMEOUT_SEC
