"""Bus message models — fields verbatim from specs/001-factory-v2/data-model.md.

Every message is an immutable YAML file. No message carries a status field: the
keys in `FORBIDDEN_KEYS` are rejected at any depth (FR-003). Frozen at CP0.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Annotated, Any, ClassVar, Literal, Self, get_args

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic.fields import FieldInfo

from factory.config.settings import DEFAULT_AUTONOMY_HORIZON_MINUTES

FORBIDDEN_KEYS = frozenset({"status", "state", "done", "progress"})

MessageKind = Literal[
    "order",
    "amendment",
    "handoff",
    "verdict",
    "decision_request",
    "decision_lock",
    "correction",
    "override",
    "claim",
    "release",
    "run_complete",
]
MESSAGE_KINDS: tuple[str, ...] = get_args(MessageKind)

Actor = Literal["governor", "orchestrator", "worker", "reviewer"]
WorkerRuntime = Literal["local_subagent", "cloud_agent"]
Fidelity = Literal["letter", "intent", "waived"]
Severity = Literal["blocker", "debate", "later", "nit"]
FindingTag = Literal["product", "process", "arch"]
QuestionClass = Literal["blocker_governor", "non_blocking"]
CorrectionTag = Literal["drift", "routing", "smell", "scope", "other"]
GateClass = Literal["drift", "governor-only"]
ReleaseReason = Literal["abandoned", "superseded", "blocked"]

_SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
ORDER_ID = rf"wo-(?P<date>\d{{8}})-{_SLUG}"
CORRECTION_ID = rf"corr-(?P<date>\d{{8}})-{_SLUG}"
DECISION_ID = r"[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*"
ORDER_ID_RE = re.compile(rf"^{ORDER_ID}$")

NonEmptyStr = Annotated[str, Field(min_length=1)]


def find_forbidden_key(data: Any, path: str = "") -> str | None:
    """Dotted path of the first forbidden key anywhere in `data`, else None."""
    if isinstance(data, Mapping):
        for key, value in data.items():
            where = f"{path}.{key}" if path else str(key)
            if key in FORBIDDEN_KEYS:
                return where
            found = find_forbidden_key(value, where)
            if found:
                return found
    elif isinstance(data, list | tuple):
        for index, item in enumerate(data):
            found = find_forbidden_key(item, f"{path}[{index}]")
            if found:
                return found
    return None


def count_sentences(text: str) -> int:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return len([part for part in parts if part.strip()])


def order_id_of(message_id: str) -> str:
    """Order id prefix of an order-scoped message id (`<order-id>.<suffix>`)."""
    return message_id.split(".", 1)[0]


class BusModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class Envelope(BusModel):
    """Common envelope (data-model § Common envelope)."""

    ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r".+")

    schema_version: Literal[1]
    kind: MessageKind
    id: str
    created: AwareDatetime
    actor: Actor
    actor_model: str | None = None
    actor_verified: bool = False
    refs: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _no_status_keys(cls, data: Any) -> Any:
        where = find_forbidden_key(data)
        if where:
            raise ValueError(f"forbidden key {where!r}: bus messages carry no status (FR-003)")
        return data

    @field_validator("created")
    @classmethod
    def _created_is_utc(cls, value: datetime) -> datetime:
        if value.utcoffset() != timedelta(0):
            raise ValueError("created must be UTC")
        return value

    @model_validator(mode="after")
    def _envelope_rules(self) -> Self:
        match = self.ID_PATTERN.match(self.id)
        if not match:
            raise ValueError(f"id {self.id!r} does not match {self.ID_PATTERN.pattern}")
        date = match.groupdict().get("date")
        if date:
            try:
                datetime.strptime(date, "%Y%m%d")
            except ValueError as exc:
                raise ValueError(f"id {self.id!r} has an invalid date {date}") from exc
        if self.actor != "governor" and not self.actor_model:
            raise ValueError(f"actor_model is required when actor is {self.actor!r}")
        return self


# --- WorkOrder ------------------------------------------------------------------------


class Lock(BusModel):
    id: NonEmptyStr
    letter_tokens: list[str]
    fidelity: Fidelity
    waiver_ref: str | None = None
    substitutes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _fidelity_rules(self) -> Self:
        if self.fidelity == "waived" and not (self.waiver_ref and self.waiver_ref.strip()):
            raise ValueError("fidelity 'waived' requires waiver_ref to a governor decision lock")
        if self.fidelity == "letter" and (
            not self.letter_tokens or any(not token.strip() for token in self.letter_tokens)
        ):
            raise ValueError("fidelity 'letter' requires non-empty, non-blank letter_tokens")
        if any(not s.strip() for s in self.substitutes):
            raise ValueError("substitutes must be non-blank")
        tokens = {token.strip().lower() for token in self.letter_tokens}
        if tokens & {s.strip().lower() for s in self.substitutes}:
            raise ValueError("substitutes must not repeat a letter token")
        return self


def _horizon(info: ValidationInfo) -> int:
    context = info.context or {}
    value = context.get("autonomy_horizon_minutes")
    return int(value) if value is not None else DEFAULT_AUTONOMY_HORIZON_MINUTES


def _check_order_field(name: str, value: Any, horizon: int) -> None:
    if name == "goal" and count_sentences(value) > 3:
        raise ValueError("goal must be at most 3 sentences")
    if name in {"owned_paths", "stop_conditions"} and not value:
        raise ValueError(f"{name} must be non-empty")
    if name == "size_minutes" and value > horizon:
        raise ValueError(f"size_minutes {value} exceeds the autonomy horizon ({horizon} minutes)")


class WorkOrderFields(BusModel):
    """Order body fields; shared by `WorkOrder` and `Amendment` value validation."""

    feature: NonEmptyStr
    goal: NonEmptyStr
    intents: list[str]
    owned_paths: list[NonEmptyStr]
    checks: list[str]
    locks: list[Lock]
    size_minutes: int = Field(ge=1)
    stop_conditions: list[NonEmptyStr]
    depends_on_decisions: list[str]
    tasks: list[str] = Field(default_factory=list)
    worker_runtime: WorkerRuntime


def _field_adapter(info: FieldInfo) -> TypeAdapter[Any]:
    if info.metadata:
        return TypeAdapter(Annotated[(info.annotation, *info.metadata)])
    return TypeAdapter(info.annotation)


ORDER_FIELDS: tuple[str, ...] = tuple(WorkOrderFields.model_fields)
_ORDER_FIELD_ADAPTERS: dict[str, TypeAdapter[Any]] = {
    name: _field_adapter(info) for name, info in WorkOrderFields.model_fields.items()
}


class WorkOrder(Envelope, WorkOrderFields):
    """`kind: order`, id `wo-YYYYMMDD-<slug>`."""

    ID_PATTERN: ClassVar[re.Pattern[str]] = ORDER_ID_RE

    kind: Literal["order"]

    @model_validator(mode="after")
    def _order_rules(self, info: ValidationInfo) -> Self:
        horizon = _horizon(info)
        for name in ("goal", "owned_paths", "stop_conditions", "size_minutes"):
            _check_order_field(name, getattr(self, name), horizon)
        return self


class Amendment(Envelope):
    """`kind: amendment`, id `<order-id>.amend-NN`; effective order = order + amendments."""

    ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(rf"^{ORDER_ID}\.amend-\d{{2}}$")

    kind: Literal["amendment"]
    supersedes: list[NonEmptyStr] = Field(min_length=1)
    values: dict[str, Any]

    @model_validator(mode="after")
    def _values_match(self, info: ValidationInfo) -> Self:
        unknown = [name for name in self.supersedes if name not in ORDER_FIELDS]
        if unknown:
            raise ValueError(f"supersedes names fields that are not order fields: {unknown}")
        if set(self.supersedes) != set(self.values):
            raise ValueError("values keys must equal supersedes")
        horizon = _horizon(info)
        for name in self.supersedes:
            value = _ORDER_FIELD_ADAPTERS[name].validate_python(self.values[name])
            _check_order_field(name, value, horizon)
        return self


# --- Handoff --------------------------------------------------------------------------


class CheckRunEntry(BusModel):
    gate_or_test: NonEmptyStr
    result: NonEmptyStr


class Deviation(BusModel):
    what: NonEmptyStr
    why: NonEmptyStr
    conservative_choice: NonEmptyStr


class OpenQuestion(BusModel):
    question: NonEmptyStr
    question_class: QuestionClass = Field(alias="class")


class Handoff(Envelope):
    """`kind: handoff`, id `<order-id>.handoff`. Self-report is not evidence (FR-011)."""

    ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(rf"^{ORDER_ID}\.handoff$")

    kind: Literal["handoff"]
    summary: NonEmptyStr
    checks_run: list[CheckRunEntry] = Field(default_factory=list)
    deviations: list[Deviation]
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    author_model: NonEmptyStr

    @field_validator("summary")
    @classmethod
    def _summary_lines(cls, value: str) -> str:
        if len(value.strip().splitlines()) > 10:
            raise ValueError("summary must be at most 10 lines")
        return value


# --- Verdict --------------------------------------------------------------------------


class Finding(BusModel):
    id: NonEmptyStr
    severity: Severity
    tag: FindingTag
    pattern_id: str | None = None
    text: NonEmptyStr


class VerdictInput(BusModel):
    path: NonEmptyStr
    sha: str = Field(pattern=r"^[0-9a-f]{7,40}$")

    @field_validator("path")
    @classmethod
    def _repo_path(cls, value: str) -> str:
        if "://" in value or value.startswith(("/", "~")):
            raise ValueError("verdict inputs must be repo-relative git paths (FR-011a)")
        return value


class Verdict(Envelope):
    """`kind: verdict`, id `<order-id>.verdict-NN`."""

    ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(rf"^{ORDER_ID}\.verdict-\d{{2}}$")

    kind: Literal["verdict"]
    decision: Literal["accept", "reject"]
    findings: list[Finding] = Field(default_factory=list)
    reviewer_model: NonEmptyStr
    reviewer_family: NonEmptyStr
    inputs: list[VerdictInput]
    bootstrap: bool = False
    manual_equivalents: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def _bootstrap(self) -> Self:
        if self.bootstrap and not self.manual_equivalents:
            raise ValueError("bootstrap verdicts must list manual_equivalents (FR-037)")
        return self


# --- Decisions ------------------------------------------------------------------------


class Consequences(BusModel):
    services: list[str] | None = None
    secrets: list[str] | None = None
    ops_steps: list[str] | None = None
    cost: str | None = None


class DecisionOption(BusModel):
    label: NonEmptyStr
    consequences: Consequences | None = None


class DecisionRequest(Envelope):
    """`kind: decision_request` at `bus/decisions/<decision-id>/request.yaml`."""

    ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(rf"^{DECISION_ID}$")

    kind: Literal["decision_request"]
    owner: Literal["governor"]
    prompt: NonEmptyStr
    options: list[DecisionOption] = Field(min_length=1)
    recommended: NonEmptyStr
    blocking: bool
    feature: NonEmptyStr
    arch_impact: bool = False

    @model_validator(mode="after")
    def _options(self) -> Self:
        labels = [option.label for option in self.options]
        if self.recommended not in labels:
            raise ValueError("recommended must be one of the option labels")
        if self.arch_impact:
            missing = [o.label for o in self.options if o.consequences is None]
            if missing:
                raise ValueError(f"arch_impact options need consequences (I-A10): {missing}")
        return self


class DecisionLock(Envelope):
    """`kind: decision_lock` at `bus/decisions/<decision-id>/lock.yaml`; closes the request."""

    ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(rf"^{DECISION_ID}\.lock$")

    kind: Literal["decision_lock"]
    chosen: NonEmptyStr
    governor_minutes: float = Field(ge=0)
    notes: str | None = None

    @property
    def decision_id(self) -> str:
        return self.id.removesuffix(".lock")


# --- Correction / override ----------------------------------------------------------


class Correction(Envelope):
    """`kind: correction`, id `corr-YYYYMMDD-<slug>`."""

    ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(rf"^{CORRECTION_ID}$")

    kind: Literal["correction"]
    target: NonEmptyStr
    what_was_wrong: NonEmptyStr
    tag: CorrectionTag
    links_to: str | None = None
    link_confirmed: bool | None = None
    proposal_ref: str | None = None


class Override(Envelope):
    """`kind: override`, id `<order-id>.override-NN`."""

    ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(rf"^{ORDER_ID}\.override-\d{{2}}$")

    kind: Literal["override"]
    gate: NonEmptyStr
    pr: int = Field(ge=1)
    reason: str
    gate_class: GateClass

    @field_validator("reason")
    @classmethod
    def _reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("override reason must be non-empty (FR-021)")
        return value

    @model_validator(mode="after")
    def _governor_only(self) -> Self:
        if self.gate_class == "governor-only" and self.actor != "governor":
            raise ValueError("a governor-only gate can only be overridden by actor 'governor'")
        return self


# --- Run events -----------------------------------------------------------------------


class Claim(Envelope):
    """`kind: claim`, id `<order-id>.claim`; a fast-forward push to `wo/<order-id>`."""

    ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(rf"^{ORDER_ID}\.claim$")

    kind: Literal["claim"]
    claimed_at: AwareDatetime
    worker_runtime: WorkerRuntime


class Release(Envelope):
    """`kind: release`, id `<order-id>.release`; frees capacity."""

    ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(rf"^{ORDER_ID}\.release$")

    kind: Literal["release"]
    reason: ReleaseReason


class RunComplete(Envelope):
    """`kind: run_complete`, id `<order-id>.run-complete`."""

    ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(rf"^{ORDER_ID}\.run-complete$")

    kind: Literal["run_complete"]
    wall_minutes: float = Field(ge=0)
    governor_interrupts: int = Field(ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    cost_usd_estimated: bool = True
    deviations_count: int = Field(ge=0)


Message = Annotated[
    WorkOrder
    | Amendment
    | Handoff
    | Verdict
    | DecisionRequest
    | DecisionLock
    | Correction
    | Override
    | Claim
    | Release
    | RunComplete,
    Field(discriminator="kind"),
]

KIND_MODELS: dict[str, type[Envelope]] = {
    "order": WorkOrder,
    "amendment": Amendment,
    "handoff": Handoff,
    "verdict": Verdict,
    "decision_request": DecisionRequest,
    "decision_lock": DecisionLock,
    "correction": Correction,
    "override": Override,
    "claim": Claim,
    "release": Release,
    "run_complete": RunComplete,
}

ORDER_SCOPED_KINDS = frozenset(
    {"order", "amendment", "handoff", "verdict", "override", "claim", "release", "run_complete"}
)

_MESSAGE_ADAPTER: TypeAdapter[Message] = TypeAdapter(Message)


def parse_message(
    data: Mapping[str, Any], *, autonomy_horizon_minutes: int | None = None
) -> Message:
    """Validate one message; raises `pydantic.ValidationError`."""
    context = {"autonomy_horizon_minutes": autonomy_horizon_minutes}
    return _MESSAGE_ADAPTER.validate_python(dict(data), context=context)
