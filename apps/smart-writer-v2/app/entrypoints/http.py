"""FastAPI worker: health, ready, preview gate, conversations.

Endpoints:
  GET  /health                          — liveness (public)
  GET  /ready                           — OPENAI_API_KEY present; no upstream call
  POST /v1/conversations                — create conversation (preview gate)
  POST /v1/conversations/{id}/messages  — turn router (clarify; no enqueue yet)
  GET  /v1/conversations/{id}           — snapshot (no ArtifactVersion on clarify)
"""

from __future__ import annotations

import hmac
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from lab_shared.jobs import JobRunner
from pydantic import BaseModel, Field

from app.agents.infer_state import (
    clarify_text_for_missing,
    extract_intent_slots,
    merge_intent_slots,
    missing_grant_slots,
)
from app.config import (
    DEFAULT_JOB_CONCURRENCY,
    DEFAULT_JOB_QUEUE_MAX,
    get_audit_secret,
    get_job_timeout_sec,
    get_openai_api_key,
)
from app.store import STORE, MaterialRef, Message

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


class MaterialIn(BaseModel):
    """User-provided material pointer on a turn."""

    uri: str
    label: str | None = None


class MessageTurnIn(BaseModel):
    """POST /v1/conversations/{id}/messages body."""

    text: str
    client_intent: Literal["auto", "regenerate"] = "auto"
    citation_mode: Literal["panel", "inline", "footnotes", "combo"] | None = None
    materials: list[MaterialIn] = Field(default_factory=list)


class AssistantMessageOut(BaseModel):
    """Clarify assistant bubble."""

    message_id: str
    text: str


class ClarifyTurnOut(BaseModel):
    """Sync clarify response (P5). job_id omitted — never enqueue."""

    type: Literal["clarify"] = "clarify"
    assistant_message: AssistantMessageOut


class ConversationMessageOut(BaseModel):
    """One message in a GET snapshot."""

    message_id: str
    role: str
    text: str
    created_at: str


class ConversationSnapshotOut(BaseModel):
    """GET /v1/conversations/{id} — slots redacted; last_artifact_id always present."""

    conversation_id: str
    messages: list[ConversationMessageOut]
    last_artifact_id: str | None


def _require_conversation(conversation_id: str) -> None:
    if STORE.get_conversation(conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")


def _message_out(message: Message) -> ConversationMessageOut:
    return ConversationMessageOut(
        message_id=message.message_id,
        role=message.role,
        text=message.text,
        created_at=message.created_at,
    )


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


@app.get("/v1/conversations/{conversation_id}", response_model=ConversationSnapshotOut)
def get_conversation(
    conversation_id: str,
    _: None = Depends(require_preview_secret),
) -> ConversationSnapshotOut:
    """Client snapshot. Do not dump intent slots or a draft on clarify (T10)."""
    _require_conversation(conversation_id)
    conversation = STORE.get_conversation(conversation_id)
    assert conversation is not None
    state = STORE.get_run_state(conversation_id)
    last_artifact_id = state.last_artifact_id if state is not None else None
    return ConversationSnapshotOut(
        conversation_id=conversation.conversation_id,
        messages=[_message_out(m) for m in conversation.messages],
        last_artifact_id=last_artifact_id,
    )


@app.post("/v1/conversations/{conversation_id}/messages")
def post_message(
    conversation_id: str,
    body: MessageTurnIn,
    _: None = Depends(require_preview_secret),
) -> ClarifyTurnOut:
    """Turn router: grant + missing slots → clarify; never enqueue (T043)."""
    _require_conversation(conversation_id)
    state = STORE.get_run_state(conversation_id)
    assert state is not None
    if body.citation_mode is not None:
        state.citation_mode_pref = body.citation_mode
    for item in body.materials:
        state.materials.append(MaterialRef(uri=item.uri, label=item.label, kind="link"))
    STORE.add_message(conversation_id, "user", body.text)
    inferred = extract_intent_slots(body.text)
    merged = merge_intent_slots(state.intent_slots, inferred)
    STORE.set_intent_slots(conversation_id, merged)
    missing = missing_grant_slots(merged)
    if missing:
        text = clarify_text_for_missing(missing)
        assistant = STORE.add_message(conversation_id, "assistant", text)
        return ClarifyTurnOut(
            assistant_message=AssistantMessageOut(
                message_id=assistant.message_id,
                text=assistant.text,
            )
        )
    # Slots complete: generate enqueue is T028 — do not start a job.
    raise HTTPException(
        status_code=501,
        detail="Generate enqueue is not available until T028",
    )
