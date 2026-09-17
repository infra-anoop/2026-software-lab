"""Contract-facing Pydantic models (data-model.md)."""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

ProducingMode = Literal["generate", "revise"]
CitationMode = Literal["panel", "inline", "footnotes", "combo"]
WebSignal = Literal["used", "none_declared", "disabled"]
ClaimStatus = Literal["grounded", "uncertain"]
SourceKind = Literal["user_material", "web"]
SourceBundle = Literal["materials", "web"]
MaterialKind = Literal["link", "upload"]


class ClaimProvenance(BaseModel):
    """Claim span/quote → source_id | uncertain (P4)."""

    claim_id: str = Field(default_factory=lambda: f"cl_{uuid4().hex[:8]}")
    excerpt: str = Field(description="Quote or span from body (org/funder-specific assertion)")
    source_id: str | None = Field(
        default=None,
        description="Set when grounded; uncertain ⇒ omit or mark in prose; null source_id",
    )
    status: ClaimStatus


class SourceRecord(BaseModel):
    """User material or retrieved web snippet."""

    source_id: str
    kind: SourceKind
    bundle: SourceBundle
    uri: str | None = None
    title: str | None = None
    excerpt: str | None = None
    retrieved_at: str | None = None


class MaterialRef(BaseModel):
    """User URL or upload pointer (uploads deferred P7)."""

    uri: str
    label: str | None = None
    kind: MaterialKind = "link"


class ArtifactVersion(BaseModel):
    """Complete user-visible writing output."""

    artifact_id: str
    conversation_id: str
    parent_artifact_id: str | None = Field(
        default=None,
        description="Set on revise; null on fresh generate",
    )
    producing_mode: ProducingMode
    body: str
    citation_mode: CitationMode = Field(
        default="panel",
        description="Default panel when sources exist (F7)",
    )
    source_ids: list[str] = Field(default_factory=list)
    claims: list[ClaimProvenance] = Field(default_factory=list)
    materials_bundle_ids: list[str] = Field(default_factory=list)
    web_bundle_ids: list[str] = Field(default_factory=list)
    web_signal: WebSignal
    created_at: str
    sources: list[SourceRecord] = Field(default_factory=list)


class InferOutput(BaseModel):
    """Schema-first infer node (PydanticAI result_type)."""

    who: str | None = None
    whom: str | None = None
    ask: str | None = None
    why_funder: str | None = None
    evidence: str | None = None
    humor_enabled: bool = False
    web_research_enabled: bool = True
    property_ranking: list[str] = Field(default_factory=list)
    search_query: str = ""


class WriterOutput(BaseModel):
    """Schema-first write node."""

    body: str


class ProvenanceOutput(BaseModel):
    """Schema-first provenance node."""

    claims: list[ClaimProvenance] = Field(default_factory=list)
