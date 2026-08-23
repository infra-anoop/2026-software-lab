"""Centralized env loading and validation for CLI/HTTP entrypoints."""
from functools import lru_cache
import sys
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, create_model
from pydantic_settings import BaseSettings, SettingsConfigDict

_RESEARCH_AUDITOR_ROOT = Path(__file__).resolve().parent.parent

# Cattle rule: names live in git. REQUIRED_ENV_NAMES / ALL_ENV_NAMES are parsed by
# ``scripts/validate_deploy_env.py`` (string-literal tuples only).
REQUIRED_ENV_NAMES: tuple[str, ...] = ("OPENAI_API_KEY",)
ALL_ENV_NAMES: tuple[str, ...] = (
    "OPENAI_API_KEY",
    "RESEARCH_AUDITOR_MODEL",
    "LOGFIRE_TOKEN",
    "SUPABASE_URL",
    "SUPABASE_SECRET_KEY",
    "RESEARCH_AUDITOR_AUDIT_TIMEOUT_SEC",
    "RESEARCH_AUDITOR_AUDIT_SECRET",
    "RESEARCH_AUDITOR_JOB_CONCURRENCY",
    "RESEARCH_AUDITOR_JOB_QUEUE_MAX",
    "RESEARCH_AUDITOR_AUDIT_RATE_LIMIT_PER_MIN",
)

DEFAULT_RESEARCH_AUDITOR_MODEL = "openai:gpt-4o"

# HTTP audit job wall-clock. ``0`` = no limit (operator override).
DEFAULT_AUDIT_TIMEOUT_SEC = 180.0
AUDIT_TIMEOUT_CAP_SEC = 3600.0
HTTP_MAX_ITERATIONS = 8
DEFAULT_JOB_CONCURRENCY = 1
DEFAULT_JOB_QUEUE_MAX = 4
DEFAULT_AUDIT_RATE_LIMIT_PER_MIN = 5


class _SettingsBase(BaseSettings):
    """pydantic-settings: code defaults → app-root ``.env`` → process env (process wins)."""

    model_config = SettingsConfigDict(
        env_file=_RESEARCH_AUDITOR_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
        populate_by_name=True,
    )


def _settings_field_specs(names: tuple[str, ...], defaults: dict[str, str] | None = None) -> dict:
    d = defaults or {}
    return {
        name.lower(): (
            str,
            Field(default=d.get(name, ""), alias=name, validation_alias=name),
        )
        for name in names
    }


Settings = create_model(
    "Settings",
    __base__=_SettingsBase,
    **_settings_field_specs(
        ALL_ENV_NAMES,
        {"RESEARCH_AUDITOR_MODEL": DEFAULT_RESEARCH_AUDITOR_MODEL},
    ),
)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings snapshot. Tests must call ``get_settings.cache_clear()`` after env patches."""
    return Settings()


def init_env() -> None:
    """Load env: ``apps/research-auditor/.env`` first, then cwd."""
    load_dotenv(_RESEARCH_AUDITOR_ROOT / ".env")
    load_dotenv()
    get_settings.cache_clear()


def require_openai_api_key() -> None:
    """Exit with error message if OPENAI_API_KEY is not set. Call before using agents."""
    key = get_settings().openai_api_key
    if not key or not key.strip():
        print("❌ ERROR: OPENAI_API_KEY not found in environment variables.")
        sys.exit(1)


def _settings_str(env_name: str, default: str = "") -> str:
    """Read a Settings field by canonical env name; empty/unset → ``default``."""
    raw = getattr(get_settings(), env_name.lower(), "")
    text = str(raw or "").strip()
    return text if text else default


def get_audit_timeout_sec() -> float | None:
    """Wall-clock seconds for an HTTP audit job; ``None`` means no timeout."""
    raw = _settings_str("RESEARCH_AUDITOR_AUDIT_TIMEOUT_SEC", str(DEFAULT_AUDIT_TIMEOUT_SEC))
    try:
        v = float(raw)
    except ValueError:
        return None
    if v <= 0:
        return None
    return min(v, AUDIT_TIMEOUT_CAP_SEC)


def get_audit_secret() -> str | None:
    """Shared secret for HTTP audit/jobs. ``None`` if unset (fail closed at the API)."""
    raw = _settings_str("RESEARCH_AUDITOR_AUDIT_SECRET")
    return raw or None


def get_job_concurrency() -> int:
    """In-flight graph cap per process (default 1)."""
    raw = _settings_str("RESEARCH_AUDITOR_JOB_CONCURRENCY", str(DEFAULT_JOB_CONCURRENCY))
    try:
        n = int(raw)
    except ValueError:
        return DEFAULT_JOB_CONCURRENCY
    return max(1, min(n, 4))


def get_job_queue_max() -> int:
    """Max waiting jobs (not including the running graph)."""
    raw = _settings_str("RESEARCH_AUDITOR_JOB_QUEUE_MAX", str(DEFAULT_JOB_QUEUE_MAX))
    try:
        n = int(raw)
    except ValueError:
        return DEFAULT_JOB_QUEUE_MAX
    return max(1, min(n, 32))


def get_audit_rate_limit_per_min() -> int:
    """POST /audit sliding-window limit per process."""
    raw = _settings_str("RESEARCH_AUDITOR_AUDIT_RATE_LIMIT_PER_MIN", str(DEFAULT_AUDIT_RATE_LIMIT_PER_MIN))
    try:
        n = int(raw)
    except ValueError:
        return DEFAULT_AUDIT_RATE_LIMIT_PER_MIN
    return max(1, min(n, 60))
