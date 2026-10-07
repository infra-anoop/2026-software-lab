"""GitHub App installation tokens (1 hour) and a repo-local git credential helper.

The App JWT is RS256-signed with PyJWT (research.md § GitHub App JWT signing). Values
come from typed settings (`EnvSettings.app_id` / `app_private_key`); nothing here reads
the environment. No token, JWT or key reaches an error message or a `repr`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx
import jwt
from pydantic import SecretStr

JWT_BACKDATE = timedelta(seconds=60)
JWT_LIFETIME = timedelta(minutes=9)
REFRESH_MARGIN = timedelta(minutes=5)
TIMEOUT_SECONDS = 30.0
API_VERSION = "2022-11-28"


class AppTokenError(Exception):
    """The installation token could not be minted, or came back already expired."""


@dataclass(frozen=True)
class InstallationToken:
    token: str = field(repr=False)
    expires_at: datetime


def app_jwt(*, app_id: str, private_key: str, now: datetime) -> str:
    """A GitHub App JWT: `iat` backdated 60 s for clock skew, `exp` under 10 minutes."""
    payload = {
        "iss": str(app_id),
        "iat": int((now - JWT_BACKDATE).timestamp()),
        "exp": int((now + JWT_LIFETIME).timestamp()),
    }
    try:
        return jwt.encode(payload, private_key, algorithm="RS256")
    except (ValueError, TypeError, jwt.PyJWTError):
        raise AppTokenError("the GitHub App private key cannot sign a JWT") from None


def _app_request(api_url: str, method: str, path: str, token: str, action: str) -> httpx.Response:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": API_VERSION,
    }
    try:
        with httpx.Client(base_url=api_url.rstrip("/"), timeout=TIMEOUT_SECONDS) as client:
            response = client.request(method, path, headers=headers)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        raise AppTokenError(f"{action} failed: HTTP {status} from {method} {path}") from None
    except httpx.HTTPError as exc:
        raise AppTokenError(f"{action} failed: {type(exc).__name__}") from None
    return response


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
    path = f"/app/installations/{installation_id}/access_tokens"
    body = _app_request(api_url, "POST", path, token, "minting an installation token").json()
    expires_at = datetime.fromisoformat(str(body["expires_at"]).replace("Z", "+00:00"))
    if expires_at <= moment:
        raise AppTokenError(f"installation token already expired at {expires_at.isoformat()}")
    return InstallationToken(token=str(body["token"]), expires_at=expires_at.astimezone(UTC))


def find_installation_id(
    *, app_id: str, private_key: str, repository: str, api_url: str, now: datetime
) -> str:
    """The App's installation on `owner/repo` (`GET /repos/{owner}/{repo}/installation`).

    A 404 (the App is not installed there) is a mint failure like any other.
    """
    token = app_jwt(app_id=app_id, private_key=private_key, now=now)
    path = f"/repos/{repository}/installation"
    body = _app_request(api_url, "GET", path, token, "finding the App installation").json()
    return str(body["id"])


class InstallationTokenSource:
    """The installation token for one repository, minted in-process on first use and
    reused until only `REFRESH_MARGIN` of its hour is left.

    Raises `AppTokenError` at construction when App credentials are missing, and from
    `token()` when the lookup or the mint fails; there is no fallback credential.
    """

    def __init__(
        self,
        *,
        app_id: str | None,
        private_key: SecretStr | None,
        repository: str,
        api_url: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not app_id or private_key is None:
            raise AppTokenError(
                "identity.mode is verified but FACTORY_GITHUB_APP_ID or"
                " FACTORY_GITHUB_APP_PRIVATE_KEY is not set"
            )
        self._app_id = app_id
        self._private_key = private_key
        self._repository = repository
        self._api_url = api_url
        self._clock = clock or (lambda: datetime.now(UTC))
        self._installation_id: str | None = None
        self._current: InstallationToken | None = None

    def __repr__(self) -> str:
        return f"InstallationTokenSource(repository={self._repository!r})"

    def token(self) -> str:
        now = self._clock()
        current = self._current
        if current is None or current.expires_at - now <= REFRESH_MARGIN:
            key = self._private_key.get_secret_value()
            if self._installation_id is None:
                self._installation_id = find_installation_id(
                    app_id=self._app_id,
                    private_key=key,
                    repository=self._repository,
                    api_url=self._api_url,
                    now=now,
                )
            current = mint_installation_token(
                app_id=self._app_id,
                private_key=key,
                installation_id=self._installation_id,
                api_url=self._api_url,
                now=now,
            )
            self._current = current
        return current.token


def git_credential_response(token: InstallationToken) -> str:
    """Answer for git's credential-helper protocol (`git credential fill`) on github.com."""
    return f"username=x-access-token\npassword={token.token}\n"
