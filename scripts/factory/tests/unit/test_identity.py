"""T032 — recorded vs verified governor identity, and GitHub App token minting."""

from __future__ import annotations

import base64
import importlib
import json
import subprocess
from datetime import UTC, datetime, timedelta
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


def _openssl(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["openssl", *args], check=False, capture_output=True)


def _test_rsa_keypair(tmp_path: Path) -> tuple[str, Path]:
    """A throwaway 2048-bit App key: (private PEM text, public PEM path)."""
    pem = tmp_path / "app.pem"
    pub = tmp_path / "app.pub.pem"
    assert _openssl("genrsa", "-out", str(pem), "2048").returncode == 0
    assert _openssl("rsa", "-in", str(pem), "-pubout", "-out", str(pub)).returncode == 0
    return pem.read_text(encoding="utf-8"), pub


def _b64url_decode(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


def _rs256_valid(signing_input: bytes, signature: bytes, public_pem: Path) -> bool:
    data = public_pem.with_name("jwt.input")
    sig = public_pem.with_name("jwt.sig")
    data.write_bytes(signing_input)
    sig.write_bytes(signature)
    verify = ("dgst", "-sha256", "-verify", str(public_pem), "-signature", str(sig), str(data))
    return _openssl(*verify).returncode == 0


RECORDED_EXPIRES_AT = datetime(2026, 10, 7, 17, 0, tzinfo=UTC)
MINT_NOW = RECORDED_EXPIRES_AT - timedelta(hours=1)


def _mint_against_recording(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, now: datetime
) -> tuple[Any, list[httpx.Request], Path]:
    token_mod = load_app_token()
    mint = getattr(token_mod, "mint_installation_token", None)
    assert callable(mint), "factory.identity.app_token must export mint_installation_token"
    key, public_pem = _test_rsa_keypair(tmp_path)
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
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
    minted = mint(
        app_id=env.app_id,
        private_key=env.app_private_key.get_secret_value() if env.app_private_key else key,
        installation_id="67890",
        api_url="https://api.github.test",
        now=now,
    )
    return minted, requests, public_pem


def test_app_token_mints_rs256_jwt_and_exchanges_recorded_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    minted, requests, public_pem = _mint_against_recording(tmp_path, monkeypatch, now=MINT_NOW)

    assert len(requests) == 1, [f"{r.method} {r.url}" for r in requests]
    request = requests[0]
    assert request.method == "POST"
    assert request.url.host == "api.github.test"
    assert request.url.path == "/app/installations/67890/access_tokens"
    auth = request.headers.get("Authorization", "")
    assert auth.startswith("Bearer "), auth
    jwt = auth.removeprefix("Bearer ").strip()
    segments = jwt.split(".")
    assert len(segments) == 3, "GitHub App JWT must have three segments"

    header = json.loads(_b64url_decode(segments[0]))
    claims = json.loads(_b64url_decode(segments[1]))
    assert header.get("alg") == "RS256", header
    assert str(claims.get("iss")) == "12345", claims
    iat, exp = claims.get("iat"), claims.get("exp")
    assert isinstance(iat, int) and isinstance(exp, int), claims
    now = int(MINT_NOW.timestamp())
    assert now - 60 <= iat <= now, f"iat must be backdated at most 60 s: iat={iat} now={now}"
    assert now < exp <= now + 600, f"exp must be within 10 minutes: exp={exp} now={now}"

    signing_input = f"{segments[0]}.{segments[1]}".encode()
    signature = _b64url_decode(segments[2])
    assert _rs256_valid(signing_input, signature, public_pem), "JWT signature does not verify"
    tampered = f"{segments[0]}.{segments[1]}x".encode()
    assert not _rs256_valid(tampered, signature, public_pem), "verifier accepted a tampered JWT"

    assert minted.token == RECORDED_TOKEN
    assert minted.expires_at == RECORDED_EXPIRES_AT


def test_app_token_refuses_recorded_token_already_expired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    late = RECORDED_EXPIRES_AT + timedelta(seconds=1)
    with pytest.raises(Exception, match="(?i)expire"):
        _mint_against_recording(tmp_path, monkeypatch, now=late)


def test_installation_token_repr_and_str_hide_the_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T036b: a minted token printed, logged or put in an error shows no token value."""
    minted, _, _ = _mint_against_recording(tmp_path, monkeypatch, now=MINT_NOW)
    shown = {"repr": repr(minted), "str": str(minted), "format": f"{minted}"}
    assert [name for name, text in shown.items() if RECORDED_TOKEN in text] == []
