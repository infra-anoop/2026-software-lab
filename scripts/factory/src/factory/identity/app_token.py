"""GitHub App installation tokens (1 hour) and a repo-local git credential helper.

The App JWT is RS256-signed with PyJWT (research.md § GitHub App JWT signing). Values
come from typed settings (`EnvSettings.app_id` / `app_private_key`); nothing here reads
the environment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
import jwt

JWT_BACKDATE = timedelta(seconds=60)
JWT_LIFETIME = timedelta(minutes=9)
TIMEOUT_SECONDS = 30.0


class AppTokenError(Exception):
    """The installation token could not be minted, or came back already expired."""


@dataclass(frozen=True)
class InstallationToken:
    token: str
    expires_at: datetime


def app_jwt(*, app_id: str, private_key: str, now: datetime) -> str:
    """A GitHub App JWT: `iat` backdated 60 s for clock skew, `exp` under 10 minutes."""
    payload = {
        "iss": str(app_id),
        "iat": int((now - JWT_BACKDATE).timestamp()),
        "exp": int((now + JWT_LIFETIME).timestamp()),
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


def mint_installation_token(
    *,
    app_id: str | None,
    private_key: str,
    installation_id: str,
    api_url: str,
    now: datetime | None = None,
) -> InstallationToken:
    """Exchange an App JWT for an installation access token."""
    if not app_id:
        raise AppTokenError("FACTORY_GITHUB_APP_ID is not set")
    moment = now or datetime.now(UTC)
    token = app_jwt(app_id=app_id, private_key=private_key, now=moment)
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    path = f"/app/installations/{installation_id}/access_tokens"
    try:
        with httpx.Client(base_url=api_url.rstrip("/"), timeout=TIMEOUT_SECONDS) as client:
            response = client.post(path, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise AppTokenError(f"minting an installation token failed: {exc}") from exc
    body = response.json()
    expires_at = datetime.fromisoformat(str(body["expires_at"]).replace("Z", "+00:00"))
    if expires_at <= moment:
        raise AppTokenError(f"installation token already expired at {expires_at.isoformat()}")
    return InstallationToken(token=str(body["token"]), expires_at=expires_at.astimezone(UTC))


def git_credential_response(token: InstallationToken) -> str:
    """Answer for git's credential-helper protocol (`git credential fill`) on github.com."""
    return f"username=x-access-token\npassword={token.token}\n"
