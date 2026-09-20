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
    "SMART_WRITER_V2_AUDIT_RATE_LIMIT_PER_MIN",
    "SMART_WRITER_V2_MAX_WRITE_JOBS_PER_CONVERSATION",
    "SMART_WRITER_V2_MAX_CLARIFY_TURNS_PER_CONVERSATION",
    "SMART_WRITER_V2_MAX_INNER_ASSESSOR_TURNS",
    "TAVILY_API_KEY",
    "LOGFIRE_TOKEN",
)

DEFAULT_JOB_CONCURRENCY = 1
DEFAULT_JOB_QUEUE_MAX = 4
DEFAULT_JOB_TIMEOUT_SEC = 300.0
DEFAULT_AUDIT_RATE_LIMIT_PER_MIN = 5
# D2 locked (2026-09-20): 3 write jobs / 10 clarifies / 8 inner turns.
DEFAULT_MAX_WRITE_JOBS_PER_CONVERSATION = 3
DEFAULT_MAX_CLARIFY_TURNS_PER_CONVERSATION = 10
DEFAULT_MAX_INNER_ASSESSOR_TURNS = 8


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


def get_audit_rate_limit_per_min() -> int:
    """POST .../messages sliding-window limit per process (B5; create/GET exempt)."""
    raw = _settings_str(
        "SMART_WRITER_V2_AUDIT_RATE_LIMIT_PER_MIN",
        str(DEFAULT_AUDIT_RATE_LIMIT_PER_MIN),
    )
    try:
        return max(0, int(raw))
    except ValueError:
        return DEFAULT_AUDIT_RATE_LIMIT_PER_MIN


def _settings_int(env_name: str, default: int) -> int:
    """Parse a non-negative int Settings field; invalid/empty → ``default``."""
    raw = _settings_str(env_name, str(default))
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def get_max_write_jobs_per_conversation() -> int:
    """Max generate/revise enqueues per conversation (D2 / FR-022)."""
    return _settings_int(
        "SMART_WRITER_V2_MAX_WRITE_JOBS_PER_CONVERSATION",
        DEFAULT_MAX_WRITE_JOBS_PER_CONVERSATION,
    )


def get_max_clarify_turns_per_conversation() -> int:
    """Max clarify assistant turns per conversation (D2 / FR-022)."""
    return _settings_int(
        "SMART_WRITER_V2_MAX_CLARIFY_TURNS_PER_CONVERSATION",
        DEFAULT_MAX_CLARIFY_TURNS_PER_CONVERSATION,
    )


def get_max_inner_assessor_turns() -> int:
    """Max writer↔assessor inner turns per write job (D2/D8).

    Clamped to **8** (T51 / catalog ≤8). Settings may be lower.
    """
    raw = _settings_int(
        "SMART_WRITER_V2_MAX_INNER_ASSESSOR_TURNS",
        DEFAULT_MAX_INNER_ASSESSOR_TURNS,
    )
    return min(8, raw)
