"""FastAPI worker: health, ready, preview gate, conversations.

Endpoints:
  GET  /health              — liveness (public)
  GET  /ready               — OPENAI_API_KEY present; no upstream call
  POST /v1/conversations    — create conversation (preview gate)
"""

from __future__ import annotations

import hmac
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from lab_shared.jobs import JobRunner
from pydantic import BaseModel

from app.config import (
    DEFAULT_JOB_CONCURRENCY,
    DEFAULT_JOB_QUEUE_MAX,
    get_audit_secret,
    get_job_timeout_sec,
    get_openai_api_key,
)
from app.store import STORE

AUDIT_SECRET_HEADER = "X-Audit-Secret"


async def _execute_job(payload: dict[str, Any]) -> dict[str, Any]:
    """Placeholder until generate/revise graphs (US1)."""
    return {"ok": True, "payload": payload}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the in-process job worker. Health does not touch this."""
    runner = JobRunner(
        execute=_execute_job,
        timeout_sec=get_job_timeout_sec,
        concurrency=DEFAULT_JOB_CONCURRENCY,
        queue_max=DEFAULT_JOB_QUEUE_MAX,
    )
    app.state.job_runner = runner
    await runner.start()
    yield
    await runner.stop()


app = FastAPI(title="Smart Writer V2", version="0.1.0", lifespan=lifespan)


def require_preview_secret(
    x_audit_secret: str | None = Header(default=None, alias=AUDIT_SECRET_HEADER),
) -> None:
    """Reject missing/wrong secret with 401; unset env with 503 (fail closed)."""
    expected = get_audit_secret()
    if expected is None:
        raise HTTPException(
            status_code=503,
            detail="SMART_WRITER_V2_AUDIT_SECRET is not configured",
        )
    provided = x_audit_secret or ""
    try:
        matched = hmac.compare_digest(provided, expected)
    except (TypeError, ValueError):
        matched = False
    if not matched:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Audit-Secret")


class ConversationCreated(BaseModel):
    """POST /v1/conversations response."""

    conversation_id: str


@app.get("/health")
def health() -> dict[str, bool]:
    """Liveness. No secrets, no OpenAI."""
    return {"ok": True}


@app.get("/ready", response_model=None)
def ready() -> dict[str, str | bool] | JSONResponse:
    """Config present. Does not call OpenAI."""
    if get_openai_api_key() is None:
        return JSONResponse(
            status_code=503,
            content={"ok": False, "openai_api_key": "missing"},
        )
    return {"ok": True, "openai_api_key": "set"}


@app.post("/v1/conversations", response_model=ConversationCreated)
def create_conversation(_: None = Depends(require_preview_secret)) -> ConversationCreated:
    """Create an in-memory conversation."""
    conversation = STORE.create_conversation()
    return ConversationCreated(conversation_id=conversation.conversation_id)
