"""Settings catalog matches ALL_ENV_NAMES / REQUIRED_ENV_NAMES."""

import pytest

from app.config import ALL_ENV_NAMES, REQUIRED_ENV_NAMES, Settings, get_settings


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


def test_required_env_names_subset() -> None:
    assert set(REQUIRED_ENV_NAMES) <= set(ALL_ENV_NAMES)
    assert REQUIRED_ENV_NAMES == ("OPENAI_API_KEY",)


def test_openai_key_empty_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()
    assert get_settings().openai_api_key == ""


def test_openai_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", " sk-live ")
    get_settings.cache_clear()
    assert get_settings().openai_api_key == " sk-live "
