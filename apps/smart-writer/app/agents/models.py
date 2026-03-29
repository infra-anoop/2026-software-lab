"""Schema-first models for the Smart Writer pipeline (values, rubrics, assessment, final state)."""

from __future__ import annotations

from typing import Annotated, List, Literal, Sequence, TypedDict

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from app.agents.canonical_library_ids import library_value_id

# --- Defaults (align with ARCHITECTURE.md) ---

DEFAULT_MIN_VALUES = 5
DEFAULT_MAX_VALUES = 8
DIMENSIONS_PER_VALUE = 5
MAX_SCORE_PER_DIMENSION = 5
RUBRIC_MAX_TOTAL = DIMENSIONS_PER_VALUE * MAX_SCORE_PER_DIMENSION  # 25

DEFAULT_MAX_WRITER_ITERATIONS = 10
DEFAULT_PLATEAU_WINDOW = 2
DEFAULT_PLATEAU_EPSILON_DOMAIN = 0.5
DEFAULT_PLATEAU_EPSILON_CRAFT = 0.5
DEFAULT_PLATEAU_EPSILON_GROUNDING = 0.05

DEFAULT_GROUNDING_SCORE_TARGET = 0.9

# Value-track targets (design §7.6) — domain vs craft when craft is enabled.
DEFAULT_DOMAIN_AGGREGATE_TARGET = 18.0
DEFAULT_DOMAIN_PER_VALUE_FLOOR = 12.0
DEFAULT_CRAFT_AGGREGATE_TARGET = 20.0
DEFAULT_CRAFT_PER_VALUE_FLOOR = 15.0
DEFAULT_CRAFT_WEIGHT_MASS = 0.35

# Backward name for tests importing old constant — same scale as domain aggregate (0–25 mean).
DEFAULT_PLATEAU_EPSILON = DEFAULT_PLATEAU_EPSILON_DOMAIN

ValueProvenance = Literal["designer_craft", "library_canonical", "task_derived"]

# Evidence injection caps (chars); tune with evals (design §14.5).
MAX_EVIDENCE_CHUNKS = 24
MAX_EVIDENCE_TOTAL_CHARS = 28_000
MAX_CHUNK_CHARS = 6_000
GROUNDING_ASSESSOR_RAW_INPUT_CAP = 12_000


class ValueDefinition(BaseModel):
    """One writing quality the pipeline will optimize for.

    Provenance is **derived** (Option B): set exactly one of ``craft_key`` (craft template),
    ``canonical_id`` (canonical domain library), or neither (task-derived decoder). Do not
    store a separate provenance enum alongside these — use the computed ``provenance`` property.
    """

    value_id: str = Field(description="Stable id, e.g. V1, V2, …")
    name: str = Field(description="Short name of the value.")
    description: str = Field(description="What this value means for this writing task.")
    raw_weight: float = Field(
        default=1.0,
        gt=0.0,
        description="Strictly positive; decoder-suggested for domain, template default for craft.",
    )
    weight: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Final normalized weight after compose_values (sums to 1 across all values).",
    )
    craft_key: str | None = Field(
        default=None,
        description="When set, designer craft template row; mutually exclusive with canonical_id.",
    )
    canonical_id: str | None = Field(
        default=None,
        description="When set, canonical domain library entry; mutually exclusive with craft_key.",
    )

    @field_validator("raw_weight")
    @classmethod
    def cap_raw_weight(cls, v: float) -> float:
        if v > 10.0:
            return 10.0
        if v <= 0.0:
            return 1e-6
        return v

    @model_validator(mode="after")
    def craft_and_canonical_mutex(self) -> ValueDefinition:
        if self.craft_key is not None and self.canonical_id is not None:
            raise ValueError("craft_key and canonical_id are mutually exclusive")
        return self

    @model_validator(mode="after")
    def library_value_id_option_a(self) -> ValueDefinition:
        """When ``canonical_id`` is set, ``value_id`` must be ``LIB_<canonical_id>`` (Option A)."""
        if self.canonical_id is not None:
            expected = library_value_id(self.canonical_id)
            if self.value_id != expected:
                raise ValueError(
                    "library_canonical row: value_id must equal library_value_id(canonical_id); "
                    f"expected {expected!r}, got {self.value_id!r}"
                )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def provenance(self) -> ValueProvenance:
        if self.craft_key is not None:
            return "designer_craft"
        if self.canonical_id is not None:
            return "library_canonical"
        return "task_derived"


class RubricDimension(BaseModel):
    """One axis of the 5×5 grid for a single value."""

    name: str = Field(max_length=160, description="Dimension label.")
    description: str = Field(description="What this dimension measures.")
    score_1: str = Field(description="What a score of 1 means on this dimension.")
    score_2: str = Field(description="What a score of 2 means.")
    score_3: str = Field(description="What a score of 3 means.")
    score_4: str = Field(description="What a score of 4 means.")
    score_5: str = Field(description="What a score of 5 means.")


class ValueRubric(BaseModel):
    """Full rubric for one value: five dimensions, each scored 1–5 (total max 25)."""

    value_id: str = Field(description="Must match a decoded value_id.")
    value_name: str = Field(description="Human-readable value name for assessor context.")
    dimensions: Annotated[
        List[RubricDimension],
        Field(min_length=DIMENSIONS_PER_VALUE, max_length=DIMENSIONS_PER_VALUE),
    ]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def max_total(self) -> int:
        return RUBRIC_MAX_TOTAL


class DecodedValues(BaseModel):
    """Output of the value-decoder agent (domain / task_derived values only).

    Length ``d`` is validated per run via :func:`validate_decoded_domain_slot_count` after
    ``k`` library domain rows are chosen: ``max(0, MIN−k) ≤ d ≤ MAX−k`` (**canonical library doc §5.3.1**).
    The list field allows ``0…MAX`` so Pydantic can parse; bounds depend on ``k``.
    """

    values: Annotated[
        List[ValueDefinition],
        Field(
            min_length=0,
            max_length=DEFAULT_MAX_VALUES,
            description="Task-derived domain values only; length d is checked against k separately.",
        ),
    ]
    rationale: str = Field(description="One short paragraph: why these values fit the prompt.")

    @model_validator(mode="after")
    def domain_only_contract(self) -> "DecodedValues":
        seen: set[str] = set()
        for v in self.values:
            if v.value_id in seen:
                raise ValueError(f"Duplicate value_id in decode output: {v.value_id}")
            seen.add(v.value_id)
            if v.value_id.upper().startswith("CRAFT_"):
                raise ValueError(
                    f"value_id {v.value_id!r} uses reserved CRAFT_ prefix; use task-specific ids.",
                )
            if v.value_id.upper().startswith("LIB_"):
                raise ValueError(
                    f"value_id {v.value_id!r} uses reserved LIB_ prefix (canonical library only); "
                    "use task-specific ids.",
                )
            if v.craft_key is not None or v.canonical_id is not None:
                raise ValueError("Decoder must emit task_derived values only (no craft_key or canonical_id).")
        return self


def decoder_domain_slot_bounds(
    library_domain_count: int,
    *,
    min_domain: int = DEFAULT_MIN_VALUES,
    max_domain: int = DEFAULT_MAX_VALUES,
) -> tuple[int, int]:
    """Return ``(d_min, d_max)`` for the decoder given ``k`` library rows (§5.3.1)."""
    k = library_domain_count
    if k < 0 or k > max_domain:
        raise ValueError(f"library_domain_count k must be in [0, {max_domain}]; got {k}")
    d_min = max(0, min_domain - k)
    d_max = max_domain - k
    return d_min, d_max


def validate_decoded_domain_slot_count(
    values: Sequence[ValueDefinition],
    *,
    library_domain_count: int = 0,
    min_domain: int = DEFAULT_MIN_VALUES,
    max_domain: int = DEFAULT_MAX_VALUES,
) -> None:
    """Ensure decoder output length ``d`` satisfies §5.3.1 given ``k`` library rows already selected."""
    k = library_domain_count
    if k < 0 or k > max_domain:
        raise ValueError(f"library_domain_count k must be in [0, {max_domain}]; got {k}")
    d = len(values)
    lo = max(0, min_domain - k)
    hi = max_domain - k
    if not (lo <= d <= hi):
        raise ValueError(
            f"Decoder must emit d domain values in [{lo}, {hi}] when k={k} library rows; got d={d}"
        )


class CanonicalValueEntry(BaseModel):
    """One row in the canonical domain library (storage / seed JSON / DB)."""

    canonical_id: str = Field(min_length=1, description="Stable catalog PK.")
    name: str = Field(description="Short display name.")
    short_description: str = Field(description="Assessor-facing copy; maps to ValueDefinition.description.")
    match_text: str = Field(description="Embedding source text (§4.2.1).")
    embedding_model_id: str = Field(
        default="text-embedding-3-small",
        description="Model id used to produce embedding; invalidate when changed.",
    )
    embedding: List[float] | None = Field(
        default=None,
        description="Optional stored vector (e.g. pgvector); omit in P0 JSON + in-memory.",
    )
    rubric: ValueRubric = Field(description="Full 5×5 rubric; value_id should match library_value_id(canonical_id).")
    library_version: int | str = Field(default=1, description="Monotonic version for observability.")
    tags: List[str] = Field(default_factory=list)
    default_raw_weight: float = Field(default=1.0, gt=0.0, le=10.0)
    enabled: bool = True
    created_at: str | None = None
    updated_at: str | None = None

    @model_validator(mode="after")
    def rubric_value_id_matches_canonical(self) -> CanonicalValueEntry:
        expected = library_value_id(self.canonical_id)
        if self.rubric.value_id != expected:
            raise ValueError(
                f"CanonicalValueEntry.rubric.value_id must be {expected!r} for canonical_id={self.canonical_id!r}"
            )
        return self


class LibraryMatch(BaseModel):
    """Per-run diagnostic for one catalog candidate (§4.3)."""

    canonical_id: str
    similarity: float = Field(description="Cosine similarity on L2-normalized vectors, [-1, 1].")
    rank: int = Field(ge=1)
    matched: bool = Field(description="True iff similarity >= τ (and margin gate if enabled).")


class ComposedValues(BaseModel):
    """Craft + domain values after compose_values: every row has final ``weight`` set."""

    values: Annotated[
        List[ValueDefinition],
        Field(
            min_length=1,
            description="Ordered: craft (if any) → library_canonical → task_derived (stable).",
        ),
    ]

    @model_validator(mode="after")
    def weights_present(self) -> "ComposedValues":
        for v in self.values:
            if v.weight is None:
                raise ValueError(f"Missing final weight for value_id={v.value_id}")
        return self


class BuiltRubrics(BaseModel):
    """One rubric per composed value (craft templates + LLM-built domain rubrics)."""

    rubrics: Annotated[
        List[ValueRubric],
        Field(
            min_length=1,
            max_length=64,
            description="One rubric per value in composed_values (same count and ids).",
        ),
    ]

    @model_validator(mode="after")
    def rubrics_match_counts(self) -> "BuiltRubrics":
        for r in self.rubrics:
            if len(r.dimensions) != DIMENSIONS_PER_VALUE:
                raise ValueError(f"Rubric {r.value_id} must have {DIMENSIONS_PER_VALUE} dimensions.")
        return self


class WriterOutput(BaseModel):
    """Structured draft from the writer agent."""

    draft_text: str = Field(min_length=1, description="Full draft for this iteration.")


OutlineEmphasis = Literal["low", "medium", "high"]


class KeyPoint(BaseModel):
    """Planner output: one substantive point tied to a composed value."""

    value_id: str = Field(min_length=1, description="Must match a composed_values entry.")
    text: str = Field(min_length=1, description="The substantive point for that value.")


class ResearchPlan(BaseModel):
    """Pre-draft steering artifact: intent, coverage, and optional retrieval hints."""

    intent_summary: str = Field(description="What the document must accomplish.")
    audience_and_constraints: str = Field(
        description="Echo or refine prompt parameters and explicit user constraints.",
    )
    key_points: Annotated[
        List[KeyPoint],
        Field(default_factory=list, max_length=12),
    ]
    facts_to_include: Annotated[List[str], Field(default_factory=list, max_length=12)]
    open_questions: Annotated[List[str], Field(default_factory=list, max_length=12)]
    risks_or_caveats: Annotated[List[str], Field(default_factory=list, max_length=12)]
    suggested_research_queries: Annotated[List[str], Field(default_factory=list, max_length=8)]
    coverage_checklist: Annotated[List[str], Field(default_factory=list, max_length=12)]


class OutlineSection(BaseModel):
    """One section in the document outline."""

    heading: str = Field(min_length=1, description="Section heading (markdown-friendly).")
    bullets: Annotated[List[str], Field(default_factory=list, max_length=24)]
    estimated_emphasis: OutlineEmphasis | None = None


class DocumentOutline(BaseModel):
    """Ordered outline produced before the first writer iteration."""

    title: str | None = None
    sections: Annotated[List[OutlineSection], Field(min_length=1, max_length=32)]


class ResearchPlanningOutput(BaseModel):
    """Single planner agent call: research plan + outline (schema-first)."""

    research_plan: ResearchPlan
    outline: DocumentOutline


class SourceRef(BaseModel):
    """One logical source in the evidence bundle."""

    source_id: str = Field(description="Stable id within a run.")
    kind: str = Field(description="url | upload | search_hit")
    title: str = Field(default="", description="Human-readable label.")
    url: str | None = Field(default=None, description="Canonical URL when applicable.")
    retrieved_at: str = Field(description="ISO8601 timestamp when the source was retrieved.")
    snippet: str = Field(default="", description="Short preview for UI / logs.")


class EvidenceChunk(BaseModel):
    """Verbatim excerpt tied to a source."""

    chunk_id: str
    source_id: str
    text: str
    char_start: int | None = None
    char_end: int | None = None
    query: str | None = Field(default=None, description="Search query that produced this chunk, if any.")
    provenance: str = Field(
        description="user_supplied | url_fetch | search_hit",
    )


class EvidenceBundle(BaseModel):
    """Retrieval output consumed by writer and grounding assessor."""

    chunks: list[EvidenceChunk] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)
    retrieval_notes: str = Field(default="", description="Coverage gaps or fetch failures.")


GroundingSeverity = str  # MUST_FIX | SHOULD_FIX | NIT


class GroundingIssue(BaseModel):
    severity: GroundingSeverity
    category: str
    excerpt_from_draft: str | None = None
    fix_guidance: str


class GroundingAssessment(BaseModel):
    """Structured output of the grounding assessor (editorial QA, not proof engine)."""

    grounding_score: float = Field(ge=0.0, le=1.0)
    supported_ratio: float = Field(default=1.0, ge=0.0, le=1.0)
    issues: list[GroundingIssue] = Field(default_factory=list)
    summary: str = ""
    writer_instructions: str = Field(
        default="",
        description="Paragraph for merged feedback (same role as value assessor change bullets).",
    )


class AssessorResult(BaseModel):
    """One assessor's scores and feedback for a single value."""

    value_id: str
    dimension_scores: Annotated[
        List[int],
        Field(min_length=DIMENSIONS_PER_VALUE, max_length=DIMENSIONS_PER_VALUE),
    ]
    keep: List[str] = Field(
        min_length=1,
        description="Specific strengths to preserve (concrete, tied to the draft).",
    )
    change: List[str] = Field(
        min_length=1,
        description="Specific revisions needed to improve this value.",
    )
    quotes_from_draft: List[str] = Field(
        default_factory=list,
        description="Optional short excerpts from the draft supporting the assessment.",
    )

    @field_validator("dimension_scores")
    @classmethod
    def scores_in_range(cls, v: List[int]) -> List[int]:
        for s in v:
            if s < 1 or s > MAX_SCORE_PER_DIMENSION:
                raise ValueError(f"Each dimension score must be 1–{MAX_SCORE_PER_DIMENSION}.")
        return v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total(self) -> int:
        return sum(self.dimension_scores)


class FinalState(TypedDict, total=False):
    """Subset of graph state useful for API/CLI consumers (stop_reason set after run_workflow)."""

    raw_input: str
    draft: str
    decoded_raw: DecodedValues
    composed_values: ComposedValues
    rubrics: BuiltRubrics
    last_assessments: List[AssessorResult]
    merged_feedback: str
    aggregate_value_score: float
    aggregate_history: List[float]
    iterations: int
    max_iterations: int
    stop_reason: str
