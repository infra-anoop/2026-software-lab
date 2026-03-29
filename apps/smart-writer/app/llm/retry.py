"""Exponential backoff with jitter for transient OpenAI / transport failures.

Uses a :class:`contextvars.ContextVar` for ``run_id`` set by :func:`app.orchestrator.run.run_workflow`
so retry spans can correlate with Supabase runs without threading ``run_id`` through every agent.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from contextvars import ContextVar, Token
from typing import TypeVar

import logfire
from openai import APIConnectionError, APIStatusError, APITimeoutError
from pydantic_ai.exceptions import ModelHTTPError

from app.config import get_llm_retry_config

T = TypeVar("T")

_workflow_run_id: ContextVar[str | None] = ContextVar("smart_writer_workflow_run_id", default=None)


def set_workflow_run_id(run_id: str) -> Token:
    """Return a token for :func:`reset_workflow_run_id` (call from ``run_workflow``)."""
    return _workflow_run_id.set(run_id)


def reset_workflow_run_id(token: Token) -> None:
    _workflow_run_id.reset(token)


def get_workflow_run_id() -> str | None:
    return _workflow_run_id.get()


def _is_transient_llm_error(exc: BaseException) -> bool:
    if isinstance(exc, (APIConnectionError, APITimeoutError)):
        return True
    if isinstance(exc, ModelHTTPError):
        return exc.status_code in (429, 500, 502, 503)
    if isinstance(exc, APIStatusError):
        return exc.status_code in (429, 500, 502, 503)
    return False


def _retry_after_seconds(exc: BaseException) -> float | None:
    """Parse ``Retry-After`` from exception chain if present (seconds)."""
    seen: set[int] = set()
    e: BaseException | None = exc
    while e is not None:
        i = id(e)
        if i in seen:
            break
        seen.add(i)
        resp = getattr(e, "response", None)
        if resp is not None:
            headers = getattr(resp, "headers", None)
            if headers is not None:
                ra = headers.get("retry-after") or headers.get("Retry-After")
                if ra is not None:
                    try:
                        return float(ra)
                    except ValueError:
                        return None
        nxt = e.__cause__ if e.__cause__ is not None else e.__context__
        e = nxt
    return None


def _sleep_seconds(attempt: int, exc: BaseException, cfg: tuple[int, float, float]) -> float:
    _, base_sec, cap_sec = cfg
    header_wait = _retry_after_seconds(exc)
    exp = min(cap_sec, base_sec * (2**attempt))
    jitter = random.uniform(0, max(base_sec * 0.25, 0.05))
    delay = exp + jitter
    if header_wait is not None:
        delay = max(delay, min(header_wait, cap_sec))
    return min(delay, cap_sec)


async def with_transient_llm_retry(
    factory: Callable[[], Awaitable[T]],
    *,
    phase: str,
) -> T:
    """Run ``await factory()``; retry on transient 429/5xx and connection timeouts."""
    cfg = get_llm_retry_config()
    max_attempts, _, _ = cfg
    for attempt in range(max_attempts):
        try:
            return await factory()
        except Exception as e:
            if not _is_transient_llm_error(e) or attempt >= max_attempts - 1:
                raise
            wait = _sleep_seconds(attempt, e, cfg)
            rid = get_workflow_run_id()
            with logfire.span(
                "llm.retry_backoff",
                phase=phase,
                attempt=attempt + 1,
                max_attempts=max_attempts,
                wait_sec=round(wait, 3),
                run_id=rid,
            ):
                logfire.warning(
                    "Transient LLM error; retrying",
                    phase=phase,
                    attempt=attempt + 1,
                    error_type=type(e).__name__,
                    run_id=rid,
                )
            await asyncio.sleep(wait)
    assert False, "unreachable: loop always returns or raises"  # pragma: no cover
