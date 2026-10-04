"""T002 — typed `factory.toml` loader and environment settings."""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.config.settings import ConfigError, load_env, load_settings
from tests.fixtures.cli_runner import FactoryCli
from tests.fixtures.repo_builder import RepoBuilder, order

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


def test_packet_command_from_the_uv_project_dir_discovers_the_repo(
    factory_cli: FactoryCli, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(REPO_ROOT / "scripts/factory")
    result = factory_cli("check", "schema", "--path", "tests/fixtures/messages/")
    assert result.exit_code == 0, result.stderr


def test_discovery_walks_up_to_the_nearest_factory_toml(
    repo: RepoBuilder, factory_cli: FactoryCli, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo.write_message(order("wo-20261006-discover", progress="50%"), validate=False)
    nested = repo.path / "apps/demo/app"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    result = factory_cli("check", "schema")
    assert result.exit_code == 1, result.stderr
    assert "wo-20261006-discover" in result.stdout


def test_discovery_stops_at_the_git_root(
    tmp_path: Path, factory_cli: FactoryCli, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "factory.toml").write_text(
        (REPO_ROOT / "factory.toml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    inner = tmp_path / "checkout"
    (inner / ".git").mkdir(parents=True)
    (inner / "sub").mkdir()
    monkeypatch.chdir(inner / "sub")
    result = factory_cli("check", "schema")
    assert result.exit_code == 3
    assert "factory.toml" in result.stderr


def test_explicit_repo_wins_over_discovery(
    tmp_path: Path, factory_cli: FactoryCli, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(REPO_ROOT / "scripts/factory")
    assert factory_cli("check", "schema", repo=tmp_path).exit_code == 3


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
