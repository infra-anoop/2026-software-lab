"""Unit tests for scripts/disk_hygiene.py (no Docker/Nix mutation)."""

from __future__ import annotations

import stat
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import disk_hygiene as hygiene  # noqa: E402


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


def test_apply_allowed_in_ci(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _make_fake_bin(tmp_path, "nix-collect-garbage")
    _make_fake_bin(tmp_path, "docker")
    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("GITHUB_ACTIONS", "1")
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool = False, **_kwargs):  # noqa: ARG001
        calls.append(list(cmd))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(hygiene.subprocess, "run", fake_run)
    code = hygiene.main(["--apply", "--path", str(tmp_path)])
    assert code == 0
    # status probe + nix-gc + apply probe + docker prune
    assert len(calls) == 4
    assert calls[1][0].endswith("nix-collect-garbage")
    prune = calls[3]
    assert "prune" in prune and "-af" in prune


def test_apply_runs_available_tools(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _make_fake_bin(tmp_path, "nix-collect-garbage")
    _make_fake_bin(tmp_path, "docker")
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool = False, **_kwargs):  # noqa: ARG001
        calls.append(list(cmd))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(hygiene.subprocess, "run", fake_run)
    code = hygiene.main(["--apply", "--path", str(tmp_path)])
    assert code == 0
    assert any(c[0].endswith("nix-collect-garbage") for c in calls)
    prune = next(c for c in calls if "prune" in c)
    assert prune[0].endswith("docker")
    assert "-af" in prune


def test_apply_skips_docker_when_daemon_down(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _make_fake_bin(tmp_path, "nix-collect-garbage")
    _make_fake_bin(tmp_path, "docker")
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool = False, **_kwargs):  # noqa: ARG001
        calls.append(list(cmd))
        if len(cmd) >= 2 and cmd[1] == "info":
            return SimpleNamespace(returncode=1)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(hygiene.subprocess, "run", fake_run)
    code = hygiene.main(["--apply", "--path", str(tmp_path)])
    assert code == 0
    assert any(c[0].endswith("nix-collect-garbage") for c in calls)
    assert not any("prune" in c for c in calls)


def test_best_effort_suppresses_nonzero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _make_fake_bin(tmp_path, "nix-collect-garbage")
    _make_fake_bin(tmp_path, "docker")

    def fake_run(cmd: list[str], check: bool = False, **_kwargs):  # noqa: ARG001
        if len(cmd) >= 2 and cmd[1] == "info":
            return SimpleNamespace(returncode=0)
        if cmd and str(cmd[0]).endswith("nix-collect-garbage"):
            return SimpleNamespace(returncode=1)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(hygiene.subprocess, "run", fake_run)
    assert hygiene.main(["--apply", "--path", str(tmp_path)]) == 1
    assert hygiene.main(["--apply", "--best-effort", "--path", str(tmp_path)]) == 0
