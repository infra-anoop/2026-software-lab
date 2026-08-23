"""Centralized env loading and validation for CLI/HTTP entrypoints.

Smart Writer fan-out (many rubric + assessor calls) can hit OpenAI **tokens-per-minute (TPM)**
limits if too many completions overlap. The knob below is the **canonical default** in code.

Where this default is also mirrored for local dev (keep in sync when you change it):
  - This file: ``DEFAULT_MAX_CONCURRENT_LLM`` (single source of truth for Python).
  - ``apps/smart-writer/.env.example`` — copy to ``.env`` locally; ``.env`` is gitignored.

A unified app config layer (file + precedence) is planned; see ``docs/TODO-smart-writer.md``.

Override anytime: ``export SMART_WRITER_MAX_CONCURRENT_LLM=2`` (higher throughput if your tier allows).
Env var name (note spelling): ``SMART_WRITER_MAX_CONCURRENT_LLM`` — not ``...COMCURRENT...``.
"""
from functools import lru_cache
import sys
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, create_model
from pydantic_settings import BaseSettings, SettingsConfigDict

# ``app/`` → smart-writer app root (where ``pyproject.toml`` and ``.env`` live).
_SMART_WRITER_ROOT = Path(__file__).resolve().parent.parent

# Cattle rule: names live in git. REQUIRED_ENV_NAMES / ALL_ENV_NAMES are parsed by
# ``scripts/validate_deploy_env.py`` (string-literal tuples only).
REQUIRED_ENV_NAMES: tuple[str, ...] = ("OPENAI_API_KEY",)
ALL_ENV_NAMES: tuple[str, ...] = (
    "OPENAI_API_KEY",
    "SMART_WRITER_MODEL",
    "SMART_WRITER_MODEL_DECODER",
    "SMART_WRITER_MODEL_RUBRIC",
    "SMART_WRITER_MODEL_PLANNER",
    "SMART_WRITER_MODEL_WRITER",
    "SMART_WRITER_MODEL_ASSESSOR",
    "SMART_WRITER_MODEL_GROUNDING",
    "SMART_WRITER_TEMPERATURE_DECODER",
    "SMART_WRITER_TEMPERATURE_RUBRIC",
    "SMART_WRITER_TEMPERATURE_PLANNER",
    "SMART_WRITER_TEMPERATURE_WRITER",
    "SMART_WRITER_TEMPERATURE_ASSESSOR",
    "SMART_WRITER_TEMPERATURE_GROUNDING",
    "SMART_WRITER_MAX_TOKENS_DECODER",
    "SMART_WRITER_MAX_TOKENS_RUBRIC",
    "SMART_WRITER_MAX_TOKENS_PLANNER",
    "SMART_WRITER_MAX_TOKENS_WRITER",
    "SMART_WRITER_MAX_TOKENS_ASSESSOR",
    "SMART_WRITER_MAX_TOKENS_GROUNDING",
    "SMART_WRITER_MAX_CONCURRENT_LLM",
    "SMART_WRITER_LLM_RETRY_MAX_ATTEMPTS",
    "SMART_WRITER_LLM_RETRY_BASE_SEC",
    "SMART_WRITER_LLM_RETRY_MAX_SEC",
    "SMART_WRITER_AUDIT_TIMEOUT_SEC",
    "SMART_WRITER_AUDIT_SECRET",
    "SMART_WRITER_JOB_CONCURRENCY",
    "SMART_WRITER_JOB_QUEUE_MAX",
    "SMART_WRITER_AUDIT_RATE_LIMIT_PER_MIN",
    "SMART_WRITER_VALUE_WEIGHTS",
    "SMART_WRITER_CRAFT_KEYS",
    "SMART_WRITER_CRAFT_ENABLED",
    "SMART_WRITER_CRAFT_WEIGHT_MASS",
    "SMART_WRITER_EMBEDDING_MODEL",
    "SMART_WRITER_EMBEDDING_BATCH_SIZE",
    "SMART_WRITER_EMBEDDING_TIMEOUT_SEC",
    "SMART_WRITER_EMBEDDING_ON_FAILURE",
    "SMART_WRITER_CANONICAL_LIBRARY_PATH",
    "SMART_WRITER_LIBRARY_MATCH_THRESHOLD",
    "SMART_WRITER_LIBRARY_MATCH_MARGIN",
    "SMART_WRITER_LIBRARY_MAX_MATCHES",
    "SMART_WRITER_LIBRARY_REFRESH_ANCHORS",
    "SMART_WRITER_PROMPTS_DIR",
    "SMART_WRITER_PROMPT_PROGRAM_VERSION",
    "SMART_WRITER_PROMPT_PROGRAM",
    "SMART_WRITER_PROMPT_AUDIENCE",
    "SMART_WRITER_PROMPT_WRITING_REGISTER",
    "SMART_WRITER_PROMPT_LENGTH_TARGET",
    "SMART_WRITER_PROMPT_RISK_TOLERANCE",
    "SMART_WRITER_PROMPT_FORMALITY",
    "SMART_WRITER_PROMPT_PROFILE",
    "SMART_WRITER_RESEARCH_PLANNING_DEFAULT",
    "SMART_WRITER_PLANNING_MIN_CHARS",
    "SMART_WRITER_GROUNDING_TARGET",
    "SMART_WRITER_DOMAIN_AGGREGATE_TARGET",
    "SMART_WRITER_DOMAIN_PER_VALUE_FLOOR",
    "SMART_WRITER_CRAFT_AGGREGATE_TARGET",
    "SMART_WRITER_CRAFT_PER_VALUE_FLOOR",
    "SMART_WRITER_MAX_URL_FETCHES",
    "SMART_WRITER_SEARCH_PROVIDER",
    "TAVILY_API_KEY",
    "SMART_WRITER_FETCH_DOMAIN_BLOCKLIST",
    "SUPABASE_URL",
    "SUPABASE_SECRET_KEY",
    "LOGFIRE_TOKEN",
)

# ---------------------------------------------------------------------------
# Default OpenAI model id when no env override is set (all roles, or fallback).
# Override globally: ``SMART_WRITER_MODEL``; per phase: ``SMART_WRITER_MODEL_DECODER``,
# ``SMART_WRITER_MODEL_RUBRIC``, ``SMART_WRITER_MODEL_WRITER``, ``SMART_WRITER_MODEL_ASSESSOR``.
# Optional generation: ``SMART_WRITER_TEMPERATURE_<ROLE>``, ``SMART_WRITER_MAX_TOKENS_<ROLE>``
# with role suffix ``DECODER``, ``RUBRIC``, ``WRITER``, ``ASSESSOR`` — see ``app.agents.llm_settings``.
# ---------------------------------------------------------------------------
DEFAULT_LLM_MODEL = "openai:gpt-4o"

# ---------------------------------------------------------------------------
# OpenAI concurrency default for smart-writer (rubric + assessor phases).
# ``1`` = safest for low TPM tiers; increase to 2–4 only after checking rate limits.
# ---------------------------------------------------------------------------
DEFAULT_MAX_CONCURRENT_LLM = 1
MAX_CONCURRENT_LLM_CAP = 16

# ---------------------------------------------------------------------------
# LLM retries (429 / transient 5xx / connection errors). See ``app.llm.retry``.
# ---------------------------------------------------------------------------
DEFAULT_LLM_RETRY_MAX_ATTEMPTS = 5
DEFAULT_LLM_RETRY_BASE_SEC = 1.0
DEFAULT_LLM_RETRY_MAX_SEC = 60.0

# ---------------------------------------------------------------------------
# HTTP audit *job* wall-clock limit. ``0`` = no limit (operator override).
# Default is conservative so a forgotten env cannot run an unbounded graph.
# ---------------------------------------------------------------------------
DEFAULT_AUDIT_TIMEOUT_SEC = 300.0
AUDIT_TIMEOUT_CAP_SEC = 3600.0
HTTP_MAX_ITERATIONS = 8
DEFAULT_JOB_CONCURRENCY = 1
DEFAULT_JOB_QUEUE_MAX = 4
DEFAULT_AUDIT_RATE_LIMIT_PER_MIN = 5


class _SettingsBase(BaseSettings):
    """pydantic-settings: code defaults → app-root ``.env`` → process env (process wins)."""

    model_config = SettingsConfigDict(
        env_file=_SMART_WRITER_ROOT / ".env",
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
    **_settings_field_specs(ALL_ENV_NAMES),
)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings snapshot. Tests must call ``get_settings.cache_clear()`` after env patches."""
    return Settings()


def init_env() -> None:
    """Load env: ``apps/smart-writer/.env`` first (stable regardless of shell cwd), then cwd.

    Without ``SUPABASE_URL`` + ``SUPABASE_SECRET_KEY`` in that file (or the environment),
    the orchestrator uses ``NullRepo`` — **no rows** are written to Supabase.
    """
    load_dotenv(_SMART_WRITER_ROOT / ".env")
    load_dotenv()
    get_settings.cache_clear()


def _settings_str(env_name: str, default: str = "") -> str:
    """Read a Settings field by canonical env name; empty/unset → ``default``."""
    raw = getattr(get_settings(), env_name.lower(), "")
    text = str(raw or "").strip()
    return text if text else default


def get_max_concurrent_llm() -> int:
    """Max parallel LLM requests for rubric/assessor phases.

    Reads ``SMART_WRITER_MAX_CONCURRENT_LLM``; if unset, uses ``DEFAULT_MAX_CONCURRENT_LLM``
    (defined above — change that constant to change the durable default).
    """
    raw = _settings_str("SMART_WRITER_MAX_CONCURRENT_LLM", str(DEFAULT_MAX_CONCURRENT_LLM))
    try:
        n = int(raw)
    except ValueError:
        return DEFAULT_MAX_CONCURRENT_LLM
    return max(1, min(n, MAX_CONCURRENT_LLM_CAP))


def require_openai_api_key() -> None:
    """Exit with error message if OPENAI_API_KEY is not set. Call before using agents."""
    key = get_settings().openai_api_key
    if not key or not key.strip():
        print("❌ ERROR: OPENAI_API_KEY not found in environment variables.")
        sys.exit(1)


def get_llm_retry_config() -> tuple[int, float, float]:
    """Return ``(max_attempts, base_delay_sec, max_delay_cap_sec)`` for LLM retries."""
    raw_n = _settings_str("SMART_WRITER_LLM_RETRY_MAX_ATTEMPTS", str(DEFAULT_LLM_RETRY_MAX_ATTEMPTS))
    try:
        n = int(raw_n)
    except ValueError:
        n = DEFAULT_LLM_RETRY_MAX_ATTEMPTS
    n = max(1, min(n, 12))

    raw_base = _settings_str("SMART_WRITER_LLM_RETRY_BASE_SEC", str(DEFAULT_LLM_RETRY_BASE_SEC))
    try:
        base = float(raw_base)
    except ValueError:
        base = DEFAULT_LLM_RETRY_BASE_SEC
    base = max(0.05, min(base, 120.0))

    raw_cap = _settings_str("SMART_WRITER_LLM_RETRY_MAX_SEC", str(DEFAULT_LLM_RETRY_MAX_SEC))
    try:
        cap = float(raw_cap)
    except ValueError:
        cap = DEFAULT_LLM_RETRY_MAX_SEC
    cap = max(base, min(cap, 300.0))

    return (n, base, cap)


def get_audit_timeout_sec() -> float | None:
    """Wall-clock seconds for ``POST /audit``; ``None`` means no server-side timeout."""
    raw = _settings_str("SMART_WRITER_AUDIT_TIMEOUT_SEC", str(DEFAULT_AUDIT_TIMEOUT_SEC))
    try:
        v = float(raw)
    except ValueError:
        return None
    if v <= 0:
        return None
    return min(v, AUDIT_TIMEOUT_CAP_SEC)


def get_audit_secret() -> str | None:
    """Shared secret for HTTP audit/jobs. ``None`` if unset (fail closed at the API)."""
    raw = _settings_str("SMART_WRITER_AUDIT_SECRET")
    return raw or None


def get_job_concurrency() -> int:
    """In-flight graph cap per process (default 1)."""
    raw = _settings_str("SMART_WRITER_JOB_CONCURRENCY", str(DEFAULT_JOB_CONCURRENCY))
    try:
        n = int(raw)
    except ValueError:
        return DEFAULT_JOB_CONCURRENCY
    return max(1, min(n, 4))


def get_job_queue_max() -> int:
    """Max waiting jobs (not including the running graph)."""
    raw = _settings_str("SMART_WRITER_JOB_QUEUE_MAX", str(DEFAULT_JOB_QUEUE_MAX))
    try:
        n = int(raw)
    except ValueError:
        return DEFAULT_JOB_QUEUE_MAX
    return max(1, min(n, 32))


def get_audit_rate_limit_per_min() -> int:
    """POST /audit sliding-window limit per process."""
    raw = _settings_str("SMART_WRITER_AUDIT_RATE_LIMIT_PER_MIN", str(DEFAULT_AUDIT_RATE_LIMIT_PER_MIN))
    try:
        n = int(raw)
    except ValueError:
        return DEFAULT_AUDIT_RATE_LIMIT_PER_MIN
    return max(1, min(n, 60))
