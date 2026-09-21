"""Logfire observability for Smart Writer V2 (D3 / T064).

Init when ``LOGFIRE_TOKEN`` is set; **noop if unset** so the product still runs.
Job spans must not log secrets or raw InternalRunState.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from app.config import get_logfire_token

logger = logging.getLogger(__name__)

_configured = False
_logfire_enabled = False


def configure_observability() -> bool:
    """Configure Logfire + PydanticAI instrumentation when a token is present.

    Returns True if Logfire was configured; False when token is unset (noop).
    """
    global _configured, _logfire_enabled
    if _configured:
        return _logfire_enabled
    token = get_logfire_token()
    if token is None:
        logger.info("Logfire disabled: LOGFIRE_TOKEN not set")
        _configured = True
        _logfire_enabled = False
        return False
    import logfire

    logfire.configure()
    logfire.instrument_pydantic_ai()
    _configured = True
    _logfire_enabled = True
    return True


def reset_observability_for_tests() -> None:
    """Clear configure latch (unit tests only)."""
    global _configured, _logfire_enabled
    _configured = False
    _logfire_enabled = False


@contextmanager
def job_span(*, job_mode: str, conversation_id: str) -> Iterator[None]:
    """Span around one write job. Attributes are ids/mode only — no secrets/state."""
    if not _logfire_enabled:
        yield
        return
    import logfire

    with logfire.span(
        "swv2.write_job",
        job_mode=job_mode,
        conversation_id=conversation_id,
    ):
        yield


def empty_usage() -> dict[str, Any]:
    """Best-effort usage shell when provider totals are unavailable (D3)."""
    return {
        "input_tokens": None,
        "output_tokens": None,
        "estimated_cost_usd": None,
    }
