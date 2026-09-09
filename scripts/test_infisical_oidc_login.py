"""Tests for scripts/infisical_oidc_login.py (mocked HTTP; no live Infisical)."""

from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import infisical_oidc_login as oidc  # noqa: E402


def test_exchange_oidc_returns_access_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/api/v1/auth/oidc-auth/login")
        return httpx.Response(200, json={"accessToken": "infisical-short-lived"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    token = oidc.exchange_oidc_jwt(
        identity_id="id-123",
        jwt="github-jwt",
        domain="https://app.infisical.com",
        client=client,
    )
    assert token == "infisical-short-lived"
    client.close()


def test_exchange_oidc_fail_closed_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "denied"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(oidc.OidcLoginError, match="Infisical OIDC login failed"):
        oidc.exchange_oidc_jwt(
            identity_id="id-123",
            jwt="bad",
            domain="https://app.infisical.com",
            client=client,
        )
    client.close()


def test_main_refuses_without_identity(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("INFISICAL_MACHINE_IDENTITY_ID", raising=False)
    code = oidc.main([])
    assert code == 1
    assert "identity" in capsys.readouterr().err.lower()


def test_main_prints_token_only(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("INFISICAL_MACHINE_IDENTITY_ID", "id-xyz")
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_URL", "https://example.test/oidc")
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "req-tok")

    def handler(request: httpx.Request) -> httpx.Response:
        if "example.test" in str(request.url):
            return httpx.Response(200, json={"value": "gh-jwt"})
        return httpx.Response(200, json={"accessToken": "vault-tok"})

    monkeypatch.setattr(oidc, "_http_client", lambda: httpx.Client(transport=httpx.MockTransport(handler)))
    code = oidc.main([])
    assert code == 0
    out = capsys.readouterr().out.strip()
    assert out == "vault-tok"
