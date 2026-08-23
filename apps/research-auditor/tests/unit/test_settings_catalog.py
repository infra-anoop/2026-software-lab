"""Settings catalog and RESEARCH_AUDITOR_MODEL."""

import pytest

from app.config import (
    ALL_ENV_NAMES,
    DEFAULT_RESEARCH_AUDITOR_MODEL,
    REQUIRED_ENV_NAMES,
    Settings,
    get_settings,
)


def _field_env_names() -> set[str]:
    names: set[str] = set()
    for name, field in Settings.model_fields.items():
        alias = field.alias
        if alias is None:
            val = field.validation_alias
            alias = val if isinstance(val, str) else name
        names.add(str(alias))
    return names


def test_settings_aliases_match_all_env_names() -> None:
    assert _field_env_names() == set(ALL_ENV_NAMES)


def test_required_env_names() -> None:
    assert REQUIRED_ENV_NAMES == ("OPENAI_API_KEY",)


def test_research_auditor_model_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RESEARCH_AUDITOR_MODEL", raising=False)
    get_settings.cache_clear()
    assert get_settings().research_auditor_model == DEFAULT_RESEARCH_AUDITOR_MODEL
    assert DEFAULT_RESEARCH_AUDITOR_MODEL == "openai:gpt-4o"


def test_research_auditor_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESEARCH_AUDITOR_MODEL", "openai:gpt-4o-mini")
    get_settings.cache_clear()
    assert get_settings().research_auditor_model == "openai:gpt-4o-mini"
