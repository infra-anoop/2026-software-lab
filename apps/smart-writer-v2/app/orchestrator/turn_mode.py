"""Choose generate vs revise without client-supplied parent ids (T16/T17)."""

from __future__ import annotations

from typing import Literal

WriteMode = Literal["generate", "revise"]


class ReviseWithoutParentError(ValueError):
    """mode=revise but parent id missing or unknown — HTTP 409."""


def resolve_write_mode(
    *,
    client_intent: Literal["auto", "regenerate"],
    last_artifact_id: str | None,
) -> tuple[WriteMode, str | None]:
    """auto + head of chain → revise; regenerate always generate (T036)."""
    if client_intent == "regenerate":
        return "generate", None
    if last_artifact_id:
        return "revise", last_artifact_id
    return "generate", None


def require_revise_parent(
    parent_artifact_id: str | None,
    *,
    parent_exists: bool,
) -> str:
    """Fail closed when revise has no stored parent (error table 409)."""
    if not parent_artifact_id or not parent_exists:
        raise ReviseWithoutParentError("revise requires an existing parent artifact")
    return parent_artifact_id
