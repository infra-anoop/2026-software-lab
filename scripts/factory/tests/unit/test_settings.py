"""T002 — typed `factory.toml` loader and environment settings."""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.config.settings import ConfigError, load_env, load_settings

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_repo_config_carries_the_governor_locks() -> None:
    settings = load_settings(REPO_ROOT)
    assert settings.concurrency_cap == 3
    assert settings.autonomy_horizon_minutes == 60
    assert settings.stale_multiplier == 3
    assert settings.bus_dir == "bus"
    assert settings.families["gpt"] == "openai"
    assert settings.identity.mode == "recorded"
    assert "scripts/factory/gates.yaml" in settings.rule_paths


@pytest.mark.parametrize(
    ("model", "family"),
    [
        ("gpt-5.6-codex", "openai"),
        ("claude-opus-5.5", "anthropic"),
        ("Gemini-3-pro", "google"),
        ("llama-4", None),
    ],
)
def test_family_of(model: str, family: str | None) -> None:
    assert load_settings(REPO_ROOT).family_of(model) == family


def test_missing_config_is_a_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_settings(tmp_path)


def test_unknown_key_is_a_config_error(tmp_path: Path) -> None:
    text = (REPO_ROOT / "factory.toml").read_text(encoding="utf-8")
    (tmp_path / "factory.toml").write_text(text + '\nstatus = "green"\n', encoding="utf-8")
    with pytest.raises(ConfigError):
        load_settings(tmp_path)


def test_load_env_reads_only_named_variables() -> None:
    env = load_env(
        {
            "GITHUB_TOKEN": "ghs_x",
            "GITHUB_REPOSITORY": "o/r",
            "FACTORY_GITHUB_APP_ID": "123",
            "FACTORY_GITHUB_APP_PRIVATE_KEY": "-----BEGIN-----",
        }
    )
    assert env.github_token is not None and env.github_token.get_secret_value() == "ghs_x"
    assert env.github_repository == "o/r"
    assert env.app_id == "123"
    assert env.app_private_key is not None
    assert "ghs_x" not in repr(env)
    assert load_env({}).github_token is None
