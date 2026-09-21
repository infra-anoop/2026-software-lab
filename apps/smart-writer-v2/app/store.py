"""Process-local conversation store (MVP; restart loses state)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from app.models import ArtifactVersion

CitationMode = Literal["panel", "inline", "footnotes", "combo"]
MessageRole = Literal["user", "assistant", "system"]
MaterialKind = Literal["link", "upload"]


def utc_now_iso() -> str:
    """UTC timestamp for store records (ISO-8601)."""
    return datetime.now(UTC).isoformat()


@dataclass
class IntentSlots:
    """Grant beachhead slots (Who, Whom, Ask, WhyFunder, Evidence)."""

    who: str | None = None
    whom: str | None = None
    ask: str | None = None
    why_funder: str | None = None
    evidence: str | None = None


@dataclass
class MaterialRef:
    """User URL or upload pointer (D7 uploads use content_ref + UploadStore)."""

    uri: str | None = None
    label: str | None = None
    kind: MaterialKind = "link"
    material_id: str | None = None
    mime: str | None = None
    byte_len: int | None = None
    content_ref: str | None = None


@dataclass
class UploadRecord:
    """Process-local upload bytes (data-model UploadStore row)."""

    content_ref: str
    conversation_id: str
    data: bytes
    mime: str
    created_at: str


class UploadStore:
    """In-memory bytes keyed by opaque content_ref (D7). Restart loses bytes."""

    def __init__(self) -> None:
        self._by_ref: dict[str, UploadRecord] = {}

    def reset(self) -> None:
        """Drop all upload bytes (tests / process residual)."""
        self._by_ref.clear()

    def put(self, conversation_id: str, data: bytes, mime: str) -> UploadRecord:
        """Store bytes; return the record (content_ref is the opaque key)."""
        content_ref = f"upl_{uuid4().hex}"
        record = UploadRecord(
            content_ref=content_ref,
            conversation_id=conversation_id,
            data=data,
            mime=mime,
            created_at=utc_now_iso(),
        )
        self._by_ref[content_ref] = record
        return record

    def get(self, content_ref: str) -> UploadRecord | None:
        """Return an upload record or None."""
        return self._by_ref.get(content_ref)


@dataclass
class InternalRunState:
    """Invisible structured state updated from free-form inference (FR-017)."""

    conversation_id: str
    intent_slots: IntentSlots = field(default_factory=IntentSlots)
    property_ranking: list[str] = field(default_factory=list)
    humor_enabled: bool = False
    web_research_enabled: bool = True
    materials: list[MaterialRef] = field(default_factory=list)
    citation_mode_pref: CitationMode | None = None
    last_artifact_id: str | None = None
    grant_beachhead: bool = True
    # D2 outer spend counters (per conversation).
    write_job_count: int = 0
    clarify_turn_count: int = 0


@dataclass
class Message:
    """One chat turn."""

    message_id: str
    conversation_id: str
    role: MessageRole
    text: str
    created_at: str


@dataclass
class Conversation:
    """One chat session."""

    conversation_id: str
    created_at: str
    updated_at: str
    messages: list[Message] = field(default_factory=list)


class InMemoryStore:
    """In-process maps. Not shared across Railway instances."""

    def __init__(self) -> None:
        self._conversations: dict[str, Conversation] = {}
        self._run_state: dict[str, InternalRunState] = {}
        self._artifacts: dict[str, ArtifactVersion] = {}
        self.uploads = UploadStore()

    def reset(self) -> None:
        """Drop all conversations and upload bytes (tests)."""
        self._conversations.clear()
        self._run_state.clear()
        self._artifacts.clear()
        self.uploads.reset()

    def create_conversation(self) -> Conversation:
        """Allocate a conversation and default InternalRunState."""
        conversation_id = str(uuid4())
        now = utc_now_iso()
        conversation = Conversation(
            conversation_id=conversation_id,
            created_at=now,
            updated_at=now,
        )
        self._conversations[conversation_id] = conversation
        self._run_state[conversation_id] = InternalRunState(conversation_id=conversation_id)
        return conversation

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Return a conversation or None."""
        return self._conversations.get(conversation_id)

    def get_run_state(self, conversation_id: str) -> InternalRunState | None:
        """Return internal run state or None."""
        return self._run_state.get(conversation_id)

    def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        text: str,
    ) -> Message:
        """Append a message and bump conversation updated_at."""
        conversation = self._conversations[conversation_id]
        message = Message(
            message_id=str(uuid4()),
            conversation_id=conversation_id,
            role=role,
            text=text,
            created_at=utc_now_iso(),
        )
        conversation.messages.append(message)
        conversation.updated_at = message.created_at
        return message

    def set_intent_slots(self, conversation_id: str, slots: IntentSlots) -> None:
        """Replace intent slots on run state."""
        state = self._run_state[conversation_id]
        state.intent_slots = slots

    def set_property_ranking(self, conversation_id: str, ranking: list[str]) -> None:
        """Replace closed property ranking (T049). Not exposed on GET conversation."""
        state = self._run_state[conversation_id]
        state.property_ranking = list(ranking)

    def set_web_research_enabled(self, conversation_id: str, enabled: bool) -> None:
        """T030: store disable flag. Not exposed on GET conversation."""
        state = self._run_state[conversation_id]
        state.web_research_enabled = enabled

    def set_grant_beachhead(self, conversation_id: str, enabled: bool) -> None:
        """T060: grant vs non-grant smoke. Not exposed on GET conversation (T2)."""
        state = self._run_state[conversation_id]
        state.grant_beachhead = enabled

    def increment_write_job_count(self, conversation_id: str) -> int:
        """Bump D2 write-job counter after a successful enqueue; return new count."""
        state = self._run_state[conversation_id]
        state.write_job_count += 1
        return state.write_job_count

    def increment_clarify_turn_count(self, conversation_id: str) -> int:
        """Bump D2 clarify-turn counter after a clarify response; return new count."""
        state = self._run_state[conversation_id]
        state.clarify_turn_count += 1
        return state.clarify_turn_count

    def set_last_artifact_id(self, conversation_id: str, artifact_id: str) -> None:
        """Point the conversation at the latest ArtifactVersion (T028)."""
        state = self._run_state[conversation_id]
        state.last_artifact_id = artifact_id

    def save_artifact(self, conversation_id: str, artifact: ArtifactVersion) -> None:
        """Persist ArtifactVersion and move last_artifact_id (T037)."""
        self._artifacts[artifact.artifact_id] = artifact
        self.set_last_artifact_id(conversation_id, artifact.artifact_id)

    def get_artifact(self, artifact_id: str) -> ArtifactVersion | None:
        """Return a stored artifact or None."""
        return self._artifacts.get(artifact_id)


STORE = InMemoryStore()
