#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "httpx>=0.27",
# ]
# ///
"""Exchange a GitHub Actions OIDC JWT for a short-lived Infisical access token.

Prints the access token to stdout only (callers must mask it). Never logs the JWT
or access token to stderr beyond fail-closed messages.

Env (Actions):
  INFISICAL_MACHINE_IDENTITY_ID  — required (or --identity-id)
  ACTIONS_ID_TOKEN_REQUEST_URL / ACTIONS_ID_TOKEN_REQUEST_TOKEN — GitHub runner
  INFISICAL_DOMAIN — optional (default https://app.infisical.com)
  INFISICAL_OIDC_AUDIENCE — optional audience for GitHub OIDC JWT
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

DEFAULT_DOMAIN = "https://app.infisical.com"


class OidcLoginError(RuntimeError):
    """OIDC exchange failed (safe to print; no tokens)."""


def _err(msg: str) -> None:
    print(f"infisical_oidc_login error: {msg}", file=sys.stderr)


def _http_client() -> httpx.Client:
    return httpx.Client(timeout=30.0)


def _with_audience(request_url: str, audience: str | None) -> str:
    if not audience:
        return request_url
    parts = urlsplit(request_url)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    q["audience"] = audience
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))


def fetch_github_oidc_jwt(
    *,
    request_url: str,
    request_token: str,
    audience: str | None = None,
    client: httpx.Client | None = None,
) -> str:
    """GET GitHub Actions OIDC JWT from the runner request URL."""
    url = _with_audience(request_url, audience)
    own = client is None
    http = client or _http_client()
    try:
        resp = http.get(
            url,
            headers={"Authorization": f"Bearer {request_token}"},
        )
    except httpx.HTTPError as e:
        raise OidcLoginError(f"GitHub OIDC request failed: {e}") from e
    finally:
        if own:
            http.close()

    if resp.status_code >= 400:
        raise OidcLoginError(f"GitHub OIDC HTTP {resp.status_code}")
    try:
        data = resp.json()
    except ValueError as e:
        raise OidcLoginError("GitHub OIDC response was not JSON") from e
    if not isinstance(data, dict):
        raise OidcLoginError("GitHub OIDC JSON must be an object")
    value = data.get("value")
    if not isinstance(value, str) or not value.strip():
        raise OidcLoginError("GitHub OIDC response missing value")
    return value.strip()


def exchange_oidc_jwt(
    *,
    identity_id: str,
    jwt: str,
    domain: str = DEFAULT_DOMAIN,
    client: httpx.Client | None = None,
) -> str:
    """POST Infisical oidc-auth/login; return accessToken only."""
    base = domain.rstrip("/")
    url = f"{base}/api/v1/auth/oidc-auth/login"
    own = client is None
    http = client or _http_client()
    try:
        resp = http.post(
            url,
            json={"identityId": identity_id, "jwt": jwt},
            headers={"Content-Type": "application/json"},
        )
    except httpx.HTTPError as e:
        raise OidcLoginError(f"Infisical OIDC login request failed: {e}") from e
    finally:
        if own:
            http.close()

    if resp.status_code >= 400:
        raise OidcLoginError(
            f"Infisical OIDC login failed HTTP {resp.status_code} (body redacted)"
        )
    try:
        data: Any = resp.json()
    except ValueError as e:
        raise OidcLoginError("Infisical OIDC login response was not JSON") from e
    if not isinstance(data, dict):
        raise OidcLoginError("Infisical OIDC login JSON must be an object")
    # Cloud may nest under data
    nested = data.get("data") if isinstance(data.get("data"), dict) else None
    token = data.get("accessToken") or data.get("token")
    if not token and nested:
        token = nested.get("accessToken") or nested.get("token")
    if not isinstance(token, str) or not token.strip():
        raise OidcLoginError("Infisical OIDC login missing accessToken")
    return token.strip()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Exchange GitHub Actions OIDC JWT for Infisical access token. "
            "Prints token to stdout only. Prefer vars.INFISICAL_MACHINE_IDENTITY_ID; "
            "long-lived INFISICAL_TOKEN is non-preferred."
        )
    )
    p.add_argument(
        "--identity-id",
        default=None,
        help="Machine identity id (default: env INFISICAL_MACHINE_IDENTITY_ID)",
    )
    p.add_argument(
        "--domain",
        default=None,
        help=f"Infisical API host (default: env INFISICAL_DOMAIN or {DEFAULT_DOMAIN})",
    )
    p.add_argument(
        "--audience",
        default=None,
        help="Optional GitHub OIDC audience (default: env INFISICAL_OIDC_AUDIENCE)",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    identity = (args.identity_id or os.environ.get("INFISICAL_MACHINE_IDENTITY_ID", "")).strip()
    if not identity:
        _err(
            "configure Infisical machine identity id "
            "(--identity-id or INFISICAL_MACHINE_IDENTITY_ID)"
        )
        return 1

    domain = (
        args.domain
        or os.environ.get("INFISICAL_DOMAIN", "").strip()
        or DEFAULT_DOMAIN
    )
    audience = (args.audience or os.environ.get("INFISICAL_OIDC_AUDIENCE", "")).strip() or None

    req_url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL", "").strip()
    req_tok = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "").strip()
    if not req_url or not req_tok:
        _err(
            "GitHub OIDC runner env missing "
            "(ACTIONS_ID_TOKEN_REQUEST_URL / ACTIONS_ID_TOKEN_REQUEST_TOKEN); "
            "use this helper from Actions with permissions.id-token: write"
        )
        return 1

    try:
        with _http_client() as client:
            jwt = fetch_github_oidc_jwt(
                request_url=req_url,
                request_token=req_tok,
                audience=audience,
                client=client,
            )
            access = exchange_oidc_jwt(
                identity_id=identity,
                jwt=jwt,
                domain=domain,
                client=client,
            )
    except OidcLoginError as e:
        _err(str(e))
        return 1

    # stdout only — workflow must ::add-mask
    print(access)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
