"""In-process `factory` CLI runner bound to a FakeGitHub. Frozen at CP0."""

from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import NamedTuple

import pytest

from factory.cli.app import run
from factory.cli.common import DEPS
from tests.fixtures.fake_github import FakeGitHub


class CliResult(NamedTuple):
    exit_code: int
    stdout: str
    stderr: str


class FactoryCli:
    """Runs `factory.cli.app.run(argv)`; every GitHub call goes to `github`."""

    def __init__(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
        github: FakeGitHub,
    ) -> None:
        self._capsys = capsys
        self._monkeypatch = monkeypatch
        self.github = github
        monkeypatch.setattr(DEPS, "github", lambda settings, env: github)
        monkeypatch.setattr(DEPS, "agent_github", lambda settings, env: github, raising=False)

    def __call__(self, *args: str, repo: Path | None = None, stdin: str | None = None) -> CliResult:
        argv = list(args)
        if repo is not None:
            argv += ["--repo", str(repo)]
        if stdin is not None:
            self._monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
        self._capsys.readouterr()
        code = run(argv)
        captured = self._capsys.readouterr()
        return CliResult(code, captured.out, captured.err)
