"""Tests for per-role LLM env resolution (no network)."""

import pytest

from app.config import DEFAULT_LLM_MODEL
from app.agents.llm_settings import (
    agent_llm_kwargs,
    get_llm_model,
    get_llm_model_settings,
)


def test_get_llm_model_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SMART_WRITER_MODEL", raising=False)
    monkeypatch.delenv("SMART_WRITER_MODEL_WRITER", raising=False)
    assert get_llm_model("writer") == DEFAULT_LLM_MODEL


def test_get_llm_model_global_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_MODEL", "openai:gpt-4o-mini")
    monkeypatch.delenv("SMART_WRITER_MODEL_ASSESSOR", raising=False)
    assert get_llm_model("assessor") == "openai:gpt-4o-mini"


def test_get_llm_model_per_role_overrides_global(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_MODEL", "openai:gpt-4o")
    monkeypatch.setenv("SMART_WRITER_MODEL_ASSESSOR", "openai:gpt-4o-mini")
    monkeypatch.setenv("SMART_WRITER_MODEL_GROUNDING", "openai:gpt-4o-mini")
    assert get_llm_model("assessor") == "openai:gpt-4o-mini"
    assert get_llm_model("decoder") == "openai:gpt-4o"
    assert get_llm_model("grounding") == "openai:gpt-4o-mini"


def test_get_llm_model_settings_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SMART_WRITER_TEMPERATURE_WRITER", raising=False)
    monkeypatch.delenv("SMART_WRITER_MAX_TOKENS_WRITER", raising=False)
    assert get_llm_model_settings("writer") is None


def test_get_llm_model_settings_temperature_and_max_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SMART_WRITER_TEMPERATURE_RUBRIC", "0.2")
    monkeypatch.setenv("SMART_WRITER_MAX_TOKENS_RUBRIC", "8192")
    ms = get_llm_model_settings("rubric")
    assert ms is not None
    # pydantic_ai ModelSettings is dict-like (attribute or key access varies by version).
    assert ms["temperature"] == 0.2
    assert ms["max_tokens"] == 8192


def test_get_llm_model_settings_invalid_numbers_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SMART_WRITER_TEMPERATURE_DECODER", "not-a-float")
    monkeypatch.setenv("SMART_WRITER_MAX_TOKENS_DECODER", "-1")
    assert get_llm_model_settings("decoder") is None


def test_agent_llm_kwargs_includes_model_settings_when_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SMART_WRITER_MODEL_WRITER", "openai:gpt-4o")
    monkeypatch.setenv("SMART_WRITER_TEMPERATURE_WRITER", "0.5")
    kw = agent_llm_kwargs("writer")
    assert kw["model"] == "openai:gpt-4o"
    assert kw["model_settings"] is not None
    assert kw["model_settings"]["temperature"] == 0.5
