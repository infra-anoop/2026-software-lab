"""Unit tests for scripts/codespace_disk_hygiene.py (no Docker/Nix mutation)."""

from __future__ import annotations

import stat
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import codespace_disk_hygiene as hygiene  # noqa: E402


def _make_fake_bin(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def test_dry_run_exits_zero_with_fixture_path(tmp_path: Path) -> None:
    _make_fake_bin(tmp_path, "nix-collect-garbage")
    _make_fake_bin(tmp_path, "docker")
    code = hygiene.main(["--dry-run", "--path", str(tmp_path)])
    assert code == 0


def test_dry_run_exits_zero_when_tools_missing(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    code = hygiene.main(["--dry-run", "--path", str(empty)])
    assert code == 0


def test_apply_refused_in_ci(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _make_fake_bin(tmp_path, "nix-collect-garbage")
    _make_fake_bin(tmp_path, "docker")
    monkeypatch.setenv("CI", "true")
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    code = hygiene.main(["--apply", "--path", str(tmp_path)])
    assert code == 2


def test_apply_refused_when_github_actions(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _make_fake_bin(tmp_path, "nix-collect-garbage")
    _make_fake_bin(tmp_path, "docker")
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("GITHUB_ACTIONS", "1")
    code = hygiene.main(["--apply", "--path", str(tmp_path)])
    assert code == 2


def test_apply_runs_available_tools(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _make_fake_bin(tmp_path, "nix-collect-garbage")
    _make_fake_bin(tmp_path, "docker")
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool = False):  # noqa: ARG001
        calls.append(list(cmd))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(hygiene.subprocess, "run", fake_run)
    code = hygiene.main(["--apply", "--path", str(tmp_path)])
    assert code == 0
    assert len(calls) == 2
    assert calls[0][0].endswith("nix-collect-garbage")
    assert calls[1][0].endswith("docker")


def test_is_ci_environment_reads_dict() -> None:
    assert hygiene.is_ci_environment({"CI": "true"}) is True
    assert hygiene.is_ci_environment({"GITHUB_ACTIONS": "yes"}) is True
    assert hygiene.is_ci_environment({}) is False
