"""Process-local conversation store (MVP; restart loses state)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

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
    """User URL or upload pointer (uploads deferred P7)."""

    uri: str
    label: str | None = None
    kind: MaterialKind = "link"


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

    def reset(self) -> None:
        """Drop all conversations (tests)."""
        self._conversations.clear()
        self._run_state.clear()

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


STORE = InMemoryStore()
