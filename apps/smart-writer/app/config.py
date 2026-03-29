"""Centralized env loading and validation for CLI/HTTP entrypoints.

Smart Writer fan-out (many rubric + assessor calls) can hit OpenAI **tokens-per-minute (TPM)**
limits if too many completions overlap. The knob below is the **canonical default** in code.

Where this default is also declared for infrastructure-as-code (keep in sync when you change it):
  - This file: ``DEFAULT_MAX_CONCURRENT_LLM`` (single source of truth for Python).
  - ``apps/smart-writer/.env.example`` — copy to ``.env`` locally; ``.env`` is gitignored.
  - Repo root ``.devcontainer/devcontainer.json`` → ``containerEnv.SMART_WRITER_MAX_CONCURRENT_LLM``
    (Codespaces / dev containers inherit it without a manual export).

Override anytime: ``export SMART_WRITER_MAX_CONCURRENT_LLM=2`` (higher throughput if your tier allows).
Env var name (note spelling): ``SMART_WRITER_MAX_CONCURRENT_LLM`` — not ``...COMCURRENT...``.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# ``app/`` → smart-writer app root (where ``pyproject.toml`` and ``.env`` live).
_SMART_WRITER_ROOT = Path(__file__).resolve().parent.parent

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
# HTTP ``POST /audit`` server-side wall-clock limit. ``0`` or unset = no limit.
# Clients should still use a generous read timeout (multi-minute workflows).
# ---------------------------------------------------------------------------
DEFAULT_AUDIT_TIMEOUT_SEC = 0.0


def init_env() -> None:
    """Load env: ``apps/smart-writer/.env`` first (stable regardless of shell cwd), then cwd.

    Without ``SUPABASE_URL`` + ``SUPABASE_SECRET_KEY`` in that file (or the environment),
    the orchestrator uses ``NullRepo`` — **no rows** are written to Supabase.
    """
    load_dotenv(_SMART_WRITER_ROOT / ".env")
    load_dotenv()


def get_max_concurrent_llm() -> int:
    """Max parallel LLM requests for rubric/assessor phases.

    Reads ``SMART_WRITER_MAX_CONCURRENT_LLM``; if unset, uses ``DEFAULT_MAX_CONCURRENT_LLM``
    (defined above — change that constant to change the durable default).
    """
    raw = os.getenv("SMART_WRITER_MAX_CONCURRENT_LLM", str(DEFAULT_MAX_CONCURRENT_LLM))
    try:
        n = int(raw.strip())
    except ValueError:
        return DEFAULT_MAX_CONCURRENT_LLM
    return max(1, min(n, MAX_CONCURRENT_LLM_CAP))


def require_openai_api_key() -> None:
    """Exit with error message if OPENAI_API_KEY is not set. Call before using agents."""
    key = os.getenv("OPENAI_API_KEY")
    if not key or not key.strip():
        print("❌ ERROR: OPENAI_API_KEY not found in environment variables.")
        sys.exit(1)


def get_llm_retry_config() -> tuple[int, float, float]:
    """Return ``(max_attempts, base_delay_sec, max_delay_cap_sec)`` for LLM retries."""
    raw_n = os.getenv("SMART_WRITER_LLM_RETRY_MAX_ATTEMPTS", str(DEFAULT_LLM_RETRY_MAX_ATTEMPTS))
    try:
        n = int(raw_n.strip())
    except ValueError:
        n = DEFAULT_LLM_RETRY_MAX_ATTEMPTS
    n = max(1, min(n, 12))

    raw_base = os.getenv("SMART_WRITER_LLM_RETRY_BASE_SEC", str(DEFAULT_LLM_RETRY_BASE_SEC))
    try:
        base = float(raw_base.strip())
    except ValueError:
        base = DEFAULT_LLM_RETRY_BASE_SEC
    base = max(0.05, min(base, 120.0))

    raw_cap = os.getenv("SMART_WRITER_LLM_RETRY_MAX_SEC", str(DEFAULT_LLM_RETRY_MAX_SEC))
    try:
        cap = float(raw_cap.strip())
    except ValueError:
        cap = DEFAULT_LLM_RETRY_MAX_SEC
    cap = max(base, min(cap, 300.0))

    return (n, base, cap)


def get_audit_timeout_sec() -> float | None:
    """Wall-clock seconds for ``POST /audit``; ``None`` means no server-side timeout."""
    raw = os.getenv("SMART_WRITER_AUDIT_TIMEOUT_SEC", str(DEFAULT_AUDIT_TIMEOUT_SEC))
    try:
        v = float(str(raw).strip())
    except ValueError:
        return None
    if v <= 0:
        return None
    return min(v, 86400.0)
