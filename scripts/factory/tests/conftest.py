"""Shared pytest fixtures (frozen at CP0; helpers live in tests/fixtures/)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.cli_runner import FactoryCli
from tests.fixtures.fake_github import FakeGitHub
from tests.fixtures.repo_builder import RepoBuilder


@pytest.fixture
def fake_github() -> FakeGitHub:
    return FakeGitHub()


@pytest.fixture
def repo(tmp_path: Path, fake_github: FakeGitHub) -> RepoBuilder:
    """A fixture repo: bare origin + working clone on main with a fixture factory.toml."""
    return RepoBuilder(tmp_path / "fixture", github=fake_github)


@pytest.fixture
def factory_cli(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, fake_github: FakeGitHub
) -> FactoryCli:
    """In-process `factory` CLI whose GitHub adapter is `fake_github`."""
    return FactoryCli(capsys, monkeypatch, fake_github)
