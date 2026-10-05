"""`IdentityPort`: is a governor action proven by GitHub identity? (D4-A)

`recorded` mode (until the GitHub App exists) never verifies: governor actions show on
the board as unverified. `verified` mode accepts a governor message only when the PR
that carries it has an APPROVED review by `governor_login`.
"""

from __future__ import annotations

from factory.api import GitHubPort, IdentityPort, PullRequest
from factory.bus.models import Message
from factory.config.settings import Settings


class RecordedIdentity:
    def is_governor_verified(self, message: Message, pr: PullRequest | None) -> bool:
        return False


class VerifiedIdentity:
    def __init__(self, governor_login: str, github: GitHubPort) -> None:
        self.governor_login = governor_login
        self.github = github

    def is_governor_verified(self, message: Message, pr: PullRequest | None) -> bool:
        if message.actor != "governor" or pr is None:
            return False
        return any(
            review.user_login == self.governor_login and review.review_state == "APPROVED"
            for review in self.github.pr_reviews(pr.number)
        )


def build_identity(settings: Settings, github: GitHubPort) -> IdentityPort:
    """The adapter `factory.cli.common.DEPS.identity` loads by default."""
    if settings.identity.mode == "verified":
        return VerifiedIdentity(settings.governor_login, github)
    return RecordedIdentity()
