"""Unit tests for scripts/validate_deploy_env.py (no app imports)."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import validate_deploy_env as vde  # noqa: E402


def test_parse_env_catalog(tmp_path: Path) -> None:
    src = tmp_path / "config.py"
    src.write_text(
        textwrap.dedent(
            """
            REQUIRED_ENV_NAMES: tuple[str, ...] = ("OPENAI_API_KEY",)
            ALL_ENV_NAMES: tuple[str, ...] = (
                "OPENAI_API_KEY",
                "LOGFIRE_TOKEN",
            )
            """
        ),
        encoding="utf-8",
    )
    required, all_names = vde.parse_env_catalog(src)
    assert required == ("OPENAI_API_KEY",)
    assert all_names == ("OPENAI_API_KEY", "LOGFIRE_TOKEN")


def test_empty_required_fails(tmp_path: Path) -> None:
    yml = tmp_path / "app.yml"
    yml.write_text("env:\n  required: []\n", encoding="utf-8")
    errors = vde.validate_env_block(
        yaml_path=yml,
        required_code=("OPENAI_API_KEY",),
        all_code=frozenset({"OPENAI_API_KEY", "LOGFIRE_TOKEN"}),
        block={"required": [], "optional": ["LOGFIRE_TOKEN"]},
    )
    assert any("empty" in e for e in errors)


def test_unknown_optional_fails(tmp_path: Path) -> None:
    yml = tmp_path / "app.yml"
    yml.write_text("x: 1\n", encoding="utf-8")
    errors = vde.validate_env_block(
        yaml_path=yml,
        required_code=("OPENAI_API_KEY",),
        all_code=frozenset({"OPENAI_API_KEY", "LOGFIRE_TOKEN"}),
        block={"required": ["OPENAI_API_KEY"], "optional": ["NOT_A_REAL_NAME"]},
    )
    assert any("NOT_A_REAL_NAME" in e for e in errors)


def test_happy_path_block(tmp_path: Path) -> None:
    yml = tmp_path / "app.yml"
    yml.write_text("env: {}\n", encoding="utf-8")
    errors = vde.validate_env_block(
        yaml_path=yml,
        required_code=("OPENAI_API_KEY",),
        all_code=frozenset({"OPENAI_API_KEY", "LOGFIRE_TOKEN"}),
        block={"required": ["OPENAI_API_KEY"], "optional": ["LOGFIRE_TOKEN"]},
    )
    assert errors == []


def test_validate_repo_happy() -> None:
    errors = vde.validate_repo()
    assert errors == [], errors


def test_main_prints_errors_to_stderr_and_exits_1(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["validate_deploy_env.py"])
    monkeypatch.setattr(
        vde,
        "validate_repo",
        lambda: ["env.optional names not in Settings catalog: ['NOT_A_REAL_NAME']"],
    )
    assert vde.main() == 1
    captured = capsys.readouterr()
    assert "NOT_A_REAL_NAME" in captured.err
    assert captured.err.startswith("deploy env validation error:")
