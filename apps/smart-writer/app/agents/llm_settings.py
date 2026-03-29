"""Per-role OpenAI model id and optional generation settings from the environment.

Defaults and env var names are documented in ``app.config`` next to
``DEFAULT_MAX_CONCURRENT_LLM``. Set ``SMART_WRITER_MODEL`` for a single default, or
``SMART_WRITER_MODEL_<ROLE>`` (decoder, rubric, planner, writer, assessor, grounding) to override per phase.

Optional: ``SMART_WRITER_TEMPERATURE_<ROLE>``, ``SMART_WRITER_MAX_TOKENS_<ROLE>`` —
if unset, the provider default applies.
"""

from __future__ import annotations

import os
from typing import Any, Literal, TypedDict

from pydantic_ai.settings import ModelSettings

from app.config import DEFAULT_LLM_MODEL

Role = Literal["decoder", "rubric", "planner", "writer", "assessor", "grounding"]

_ENV_MODEL: dict[Role, str] = {
    "decoder": "SMART_WRITER_MODEL_DECODER",
    "rubric": "SMART_WRITER_MODEL_RUBRIC",
    "planner": "SMART_WRITER_MODEL_PLANNER",
    "writer": "SMART_WRITER_MODEL_WRITER",
    "assessor": "SMART_WRITER_MODEL_ASSESSOR",
    "grounding": "SMART_WRITER_MODEL_GROUNDING",
}

_ENV_ROLE_SUFFIX: dict[Role, str] = {
    "decoder": "DECODER",
    "rubric": "RUBRIC",
    "planner": "PLANNER",
    "writer": "WRITER",
    "assessor": "ASSESSOR",
    "grounding": "GROUNDING",
}

_FALLBACK_MODEL_ENV = "SMART_WRITER_MODEL"


def get_llm_model(role: Role) -> str:
    """Resolve model id for ``role``; per-role env overrides ``SMART_WRITER_MODEL``."""
    specific = os.getenv(_ENV_MODEL[role])
    if specific and specific.strip():
        return specific.strip()
    fallback = os.getenv(_FALLBACK_MODEL_ENV, DEFAULT_LLM_MODEL)
    return (fallback.strip() if fallback else "") or DEFAULT_LLM_MODEL


def _optional_float(name: str) -> float | None:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return None
    try:
        return float(str(raw).strip())
    except ValueError:
        return None


def _optional_positive_int(name: str) -> int | None:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return None
    try:
        n = int(str(raw).strip(), 10)
    except ValueError:
        return None
    return n if n > 0 else None


def get_llm_model_settings(role: Role) -> ModelSettings | None:
    """Temperature / max_tokens for ``role``; ``None`` if nothing set."""
    suffix = _ENV_ROLE_SUFFIX[role]
    temperature = _optional_float(f"SMART_WRITER_TEMPERATURE_{suffix}")
    max_tokens = _optional_positive_int(f"SMART_WRITER_MAX_TOKENS_{suffix}")
    kwargs: dict[str, Any] = {}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if not kwargs:
        return None
    return ModelSettings(**kwargs)


class AgentLlmKwargs(TypedDict, total=False):
    """Keyword args for :class:`pydantic_ai.Agent` model configuration."""

    model: str
    model_settings: ModelSettings


def agent_llm_kwargs(role: Role) -> AgentLlmKwargs:
    """Model id and optional ``model_settings`` for constructing an :class:`~pydantic_ai.Agent`."""
    out: AgentLlmKwargs = {"model": get_llm_model(role)}
    ms = get_llm_model_settings(role)
    if ms is not None:
        out["model_settings"] = ms
    return out
