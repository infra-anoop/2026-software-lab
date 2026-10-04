"""T032 — recorded vs verified governor identity, and GitHub App token minting."""

from __future__ import annotations

import importlib
import json
import subprocess
from pathlib import Path
from typing import Any

import httpx
import pytest

from factory.api import IdentityPort, PullRequest
from factory.bus.models import parse_message
from factory.config.settings import load_env
from tests.fixtures.fake_github import FakeGitHub
from tests.fixtures.repo_builder import GOVERNOR_LOGIN, RepoBuilder, message

RECORDED = Path(__file__).resolve().parents[1] / "fixtures" / "github_recorded"
RECORDED_TOKEN = json.loads((RECORDED / "app_access_token.json").read_text(encoding="utf-8"))[
    "token"
]


def load_adapter() -> Any:
    try:
        return importlib.import_module("factory.identity.adapter")
    except ImportError as exc:
        pytest.fail(f"factory.identity.adapter is not implemented: {exc}")


def load_app_token() -> Any:
    try:
        return importlib.import_module("factory.identity.app_token")
    except ImportError as exc:
        pytest.fail(f"factory.identity.app_token is not implemented: {exc}")


def _governor_message() -> Any:
    return parse_message(
        message(
            "override",
            actor="governor",
            actor_model=None,
            gate="red-first-proof",
            pr=1,
            reason="Base suite broken; verified red by hand.",
            gate_class="drift",
        )
    )


def test_recorded_mode_marks_governor_unverified(repo: RepoBuilder) -> None:
    adapter_mod = load_adapter()
    build = getattr(adapter_mod, "build_identity", None)
    assert callable(build), "factory.identity.adapter must export build_identity"
    github = FakeGitHub()
    identity = build(repo.settings, github)
    assert isinstance(identity, IdentityPort)
    assert repo.settings.identity.mode == "recorded"
    assert identity.is_governor_verified(_governor_message(), None) is False


def test_verified_mode_requires_governor_approving_review(tmp_path: Path) -> None:
    repo = RepoBuilder(tmp_path / "verified", identity_mode="verified")
    adapter_mod = load_adapter()
    build = getattr(adapter_mod, "build_identity", None)
    assert callable(build)
    github = repo.github
    pr = github.add_pr("bus/2026-10-07-lock", head_sha="c" * 40)
    identity = build(repo.settings, github)
    msg = _governor_message()
    assert identity.is_governor_verified(msg, pr) is False

    github.add_review(pr.number, login=GOVERNOR_LOGIN, review_state="APPROVED")
    assert identity.is_governor_verified(msg, pr) is True

    other = PullRequest(
        number=99,
        head_ref="bus/other",
        head_sha="d" * 40,
        base_ref="main",
        open=True,
        merged=False,
    )
    github.prs[99] = other
    github.add_review(99, login="not-the-governor", review_state="APPROVED")
    assert identity.is_governor_verified(msg, other) is False


def _test_rsa_pem(tmp_path: Path) -> str:
    pem = tmp_path / "app.pem"
    subprocess.run(
        ["openssl", "genrsa", "-out", str(pem), "2048"],
        check=True,
        capture_output=True,
    )
    return pem.read_text(encoding="utf-8")


def test_app_token_mints_jwt_and_exchanges_recorded_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    token_mod = load_app_token()
    mint = getattr(token_mod, "mint_installation_token", None)
    assert callable(mint), "factory.identity.app_token must export mint_installation_token"
    key = _test_rsa_pem(tmp_path)
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["auth"] = request.headers.get("Authorization", "")
        assert request.method == "POST"
        assert "/app/installations/" in request.url.path
        assert request.url.path.endswith("/access_tokens")
        assert captured["auth"].startswith("Bearer ")
        jwt = captured["auth"].removeprefix("Bearer ").strip()
        assert jwt.count(".") == 2, "GitHub App JWT must have three segments"
        payload = json.loads((RECORDED / "app_access_token.json").read_text())
        return httpx.Response(201, json=payload)

    original = httpx.Client

    def client_with_transport(*args: Any, **kwargs: Any) -> httpx.Client:
        kwargs.setdefault("transport", httpx.MockTransport(handler))
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", client_with_transport)
    env = load_env(
        {
            "FACTORY_GITHUB_APP_ID": "12345",
            "FACTORY_GITHUB_APP_PRIVATE_KEY": key,
        }
    )
    token = mint(
        app_id=env.app_id,
        private_key=env.app_private_key.get_secret_value() if env.app_private_key else key,
        installation_id="67890",
        api_url="https://api.github.test",
    )
    assert token == RECORDED_TOKEN
    assert captured["path"].endswith("/access_tokens")
