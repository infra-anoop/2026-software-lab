"""LangGraph orchestration: decode values → build rubrics → writer ↔ assess → merge until stop."""

from __future__ import annotations

import asyncio
import os
import logging
from typing import Any, Literal, TypedDict

import logfire
from langgraph.graph import END, StateGraph

from app.agents.assessor import run_assess_one
from app.agents.canonical_library import library_rubric_map_from_entries
from app.agents.library_match import (
    get_library_match_margin,
    get_library_match_threshold,
    get_library_max_matches,
    run_library_match,
)
from app.agents.compose_values import compose_values
from app.agents.craft_values import CRAFT_RUBRIC_VERSION
from app.agents.feedback_merge import (
    craft_aggregate,
    domain_aggregate,
    merge_value_and_grounding_feedback,
    weighted_mean_aggregate,
)
from app.agents.grounding_assessor import run_grounding_assess
from app.agents.models import (
    AssessorResult,
    BuiltRubrics,
    CanonicalValueEntry,
    ComposedValues,
    DecodedValues,
    DocumentOutline,
    ResearchPlan,
    ValueDefinition,
    ValueRubric,
    validate_decoded_domain_slot_count,
    DEFAULT_CRAFT_AGGREGATE_TARGET,
    DEFAULT_CRAFT_PER_VALUE_FLOOR,
    DEFAULT_DOMAIN_AGGREGATE_TARGET,
    DEFAULT_DOMAIN_PER_VALUE_FLOOR,
    DEFAULT_GROUNDING_SCORE_TARGET,
    DEFAULT_MAX_WRITER_ITERATIONS,
    DEFAULT_PLATEAU_EPSILON_CRAFT,
    DEFAULT_PLATEAU_EPSILON_DOMAIN,
    DEFAULT_PLATEAU_EPSILON_GROUNDING,
    DEFAULT_PLATEAU_WINDOW,
    EvidenceBundle,
    GroundingAssessment,
)
from app.agents.research_planning import run_research_planning, sanitize_research_planning_output
from app.agents.rubric_builder import run_build_rubrics
from app.agents.rubric_digest import build_rubric_digest_for_planner
from app.agents.value_decoder import run_decode_values
from app.agents.writer import run_writer
from app.config import MAX_CONCURRENT_LLM_CAP, get_max_concurrent_llm
from app.llm.retry import reset_workflow_run_id, set_workflow_run_id
from app.db.client import get_supabase_client
from app.db.null_repo import NullRepo
from app.db.repo import RunRepo
from app.db.supabase_repo import SupabaseRepo
from app.prompts.loader import (
    default_prompt_profile_id,
    get_program_metadata,
    resolve_prompt_parameters_for_run,
    resolve_research_planning_enabled,
)
from app.prompts.models import PromptParameters
from app.retrieval.bundle_builder import RetrievalMode, build_bundle_from_prompt

_repo: RunRepo | None = None
_logger = logging.getLogger(__name__)


def get_repo() -> RunRepo:
    global _repo
    if _repo is None:
        client = get_supabase_client()
        _repo = SupabaseRepo(client) if client else NullRepo()
    return _repo


class AgentState(TypedDict, total=False):
    raw_input: str
    reference_material: str | None
    retrieval_mode: str
    # Canonical library (match_canonical_library → compose_values → build_rubrics); optional until wired.
    library_enabled: bool
    library_max_matches: int | None
    library_match_threshold: float | None
    library_domain_count: int
    library_domain_rows: Any
    library_rubric_by_value_id: Any
    canonical_library_entries: Any
    canonical_ids_used: list[str]
    library_version_aggregate: str | None
    library_matches: list[Any]
    library_resolution_notes: str | None
    decoded_raw: DecodedValues
    composed_values: ComposedValues
    craft_enabled: bool
    rubrics: BuiltRubrics
    evidence_bundle: EvidenceBundle
    retrieval_query: str
    draft: str
    merged_feedback: str
    last_assessments: list[AssessorResult]
    last_grounding_assessment: GroundingAssessment | None
    iterations: int
    max_iterations: int
    aggregate_value_score: float
    aggregate_history: list[float]
    domain_aggregate_history: list[float]
    craft_aggregate_history: list[float]
    grounding_score_history: list[float]
    plateau_window: int
    plateau_epsilon_domain: float
    plateau_epsilon_craft: float
    plateau_epsilon_grounding: float
    grounding_enabled: bool
    assess_parallel: bool
    max_concurrent_llm: int
    run_id: str
    step: int
    history: list[tuple[Any, ...]]
    # Versioned prompt program (semantic priority #4); optional keys default via coercion in nodes.
    prompt_parameters: dict[str, Any]
    prompt_program_id: str
    prompt_program_version: str
    prompt_profile_id: str | None
    # Research / document planning (semantic priority #5)
    research_planning_requested: bool | None
    research_planning_effective: bool
    research_plan: ResearchPlan | None
    document_outline: DocumentOutline | None
    research_planning_skipped_reason: str | None
    force_research_planning: bool


def _coerce_prompt_parameters(state: AgentState) -> PromptParameters:
    raw = state.get("prompt_parameters")
    if isinstance(raw, dict):
        try:
            return PromptParameters.model_validate(raw)
        except Exception:
            return PromptParameters()
    return PromptParameters()


def _prompt_program_id(state: AgentState) -> str | None:
    pid = state.get("prompt_program_id")
    return str(pid).strip() if isinstance(pid, str) and str(pid).strip() else None


def _prompt_profile_id(state: AgentState) -> str | None:
    rid = state.get("prompt_profile_id")
    return str(rid).strip() if isinstance(rid, str) and str(rid).strip() else None


def _planning_min_chars() -> int:
    raw = os.getenv("SMART_WRITER_PLANNING_MIN_CHARS", "200")
    try:
        return max(1, int(str(raw).strip(), 10))
    except ValueError:
        return 200


def _initial_research_planning_skip_reason(
    *,
    effective: bool,
    raw_input: str,
    reference_material: str | None,
    force_research_planning: bool,
) -> str | None:
    if not effective:
        return "disabled"
    if force_research_planning:
        return None
    lim = _planning_min_chars()
    raw = (raw_input or "").strip()
    if len(raw) < lim and not (reference_material or "").strip():
        return "short_prompt_heuristic"
    return None


def _should_run_research_planning(state: AgentState) -> bool:
    if not state.get("research_planning_effective", False):
        return False
    if state.get("research_planning_skipped_reason") == "short_prompt_heuristic":
        return False
    return True


def route_after_build_rubrics(
    state: AgentState,
) -> Literal["research_planning", "retrieve_evidence", "writer"]:
    """Single router after rubrics: planning (optional) → retrieve or writer (§5.2)."""
    if _should_run_research_planning(state):
        return "research_planning"
    if state.get("grounding_enabled", False):
        return "retrieve_evidence"
    return "writer"


def route_after_research_planning(state: AgentState) -> Literal["retrieve_evidence", "writer"]:
    if state.get("grounding_enabled", False):
        return "retrieve_evidence"
    return "writer"


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(str(raw).strip())
    except ValueError:
        return default


def _grounding_target_threshold() -> float:
    return _env_float("SMART_WRITER_GROUNDING_TARGET", DEFAULT_GROUNDING_SCORE_TARGET)


def _domain_targets_met(assessments: list[AssessorResult], composed: ComposedValues) -> bool:
    by_id = {a.value_id: a for a in assessments}
    agg_t = _env_float("SMART_WRITER_DOMAIN_AGGREGATE_TARGET", DEFAULT_DOMAIN_AGGREGATE_TARGET)
    floor = _env_float("SMART_WRITER_DOMAIN_PER_VALUE_FLOOR", DEFAULT_DOMAIN_PER_VALUE_FLOOR)
    if domain_aggregate(assessments, composed) < agg_t:
        return False
    for v in composed.values:
        if v.provenance not in ("task_derived", "library_canonical"):
            continue
        if by_id[v.value_id].total < floor:
            return False
    return True


def _craft_targets_met(assessments: list[AssessorResult], composed: ComposedValues) -> bool:
    if not any(v.provenance == "designer_craft" for v in composed.values):
        return True
    by_id = {a.value_id: a for a in assessments}
    agg_t = _env_float("SMART_WRITER_CRAFT_AGGREGATE_TARGET", DEFAULT_CRAFT_AGGREGATE_TARGET)
    floor = _env_float("SMART_WRITER_CRAFT_PER_VALUE_FLOOR", DEFAULT_CRAFT_PER_VALUE_FLOOR)
    if craft_aggregate(assessments, composed) < agg_t:
        return False
    for v in composed.values:
        if v.provenance != "designer_craft":
            continue
        if by_id[v.value_id].total < floor:
            return False
    return True


def _grounding_targets_met(state: AgentState, ga: GroundingAssessment | None) -> bool:
    if not state.get("grounding_enabled", False):
        return True
    if ga is None:
        return False
    return ga.grounding_score >= _grounding_target_threshold()


def _targets_met(state: AgentState) -> bool:
    assessments = state.get("last_assessments") or []
    composed = state.get("composed_values")
    if not assessments or composed is None:
        return False
    ga = state.get("last_grounding_assessment")
    return (
        _domain_targets_met(assessments, composed)
        and _craft_targets_met(assessments, composed)
        and _grounding_targets_met(state, ga)
    )


def _domain_plateau(state: AgentState) -> bool:
    hist = state.get("domain_aggregate_history", [])
    pw = state.get("plateau_window", DEFAULT_PLATEAU_WINDOW)
    eps = state.get("plateau_epsilon_domain", DEFAULT_PLATEAU_EPSILON_DOMAIN)
    return len(hist) > pw and (hist[-1] - hist[-1 - pw]) < eps


def _craft_plateau(state: AgentState) -> bool:
    if not state.get("craft_enabled", False):
        return True
    hist = state.get("craft_aggregate_history", [])
    pw = state.get("plateau_window", DEFAULT_PLATEAU_WINDOW)
    eps = state.get("plateau_epsilon_craft", DEFAULT_PLATEAU_EPSILON_CRAFT)
    return len(hist) > pw and (hist[-1] - hist[-1 - pw]) < eps


def _grounding_plateau(state: AgentState) -> bool:
    """True when grounding improvement is flat over ``plateau_window`` (or grounding off)."""
    if not state.get("grounding_enabled", False):
        return True
    gh = state.get("grounding_score_history", [])
    pw = state.get("plateau_window", DEFAULT_PLATEAU_WINDOW)
    eps = state.get("plateau_epsilon_grounding", DEFAULT_PLATEAU_EPSILON_GROUNDING)
    # Insufficient history: not a grounding plateau yet (avoid blocking value-only plateau in tests).
    if len(gh) <= pw:
        return False
    return (gh[-1] - gh[-1 - pw]) < eps


def _value_track_plateau(state: AgentState) -> bool:
    return _domain_plateau(state) and _craft_plateau(state)


def _dual_plateau(state: AgentState) -> bool:
    return _value_track_plateau(state) and _grounding_plateau(state)


def _infer_stop_reason(state: AgentState) -> str:
    it = state.get("iterations", 0)
    max_it = state.get("max_iterations", DEFAULT_MAX_WRITER_ITERATIONS)
    if it >= max_it:
        return "max_iterations"
    if _targets_met(state):
        return "targets_met"
    if _dual_plateau(state):
        return "plateau"
    return "completed"


def route_after_merge(state: AgentState) -> Literal["writer"] | Any:
    if state.get("iterations", 0) >= state.get("max_iterations", DEFAULT_MAX_WRITER_ITERATIONS):
        return END
    if _targets_met(state):
        return END
    if _dual_plateau(state):
        return END
    return "writer"


def _coerce_library_domain_rows(raw: Any) -> list[ValueDefinition] | None:
    if raw is None:
        return None
    if not isinstance(raw, list):
        return None
    out: list[ValueDefinition] = []
    for x in raw:
        if isinstance(x, ValueDefinition):
            out.append(x)
        else:
            out.append(ValueDefinition.model_validate(x))
    return out


def _coerce_library_rubrics(raw: Any) -> dict[str, ValueRubric] | None:
    if raw is None or not isinstance(raw, dict):
        return None
    out: dict[str, ValueRubric] = {}
    for k, v in raw.items():
        if not isinstance(k, str):
            continue
        if isinstance(v, ValueRubric):
            out[k] = v
        else:
            out[k] = ValueRubric.model_validate(v)
    return out


def _coerce_canonical_entries(raw: Any) -> list[CanonicalValueEntry] | None:
    if raw is None:
        return None
    if not isinstance(raw, list):
        return None
    out: list[CanonicalValueEntry] = []
    for x in raw:
        if isinstance(x, CanonicalValueEntry):
            out.append(x)
        else:
            out.append(CanonicalValueEntry.model_validate(x))
    return out


def _resolve_library_rubric_map_for_build(
    state: AgentState,
    composed: ComposedValues,
) -> dict[str, ValueRubric] | None:
    """Merge catalog rubrics from ``canonical_library_entries`` and explicit ``library_rubric_by_value_id``."""
    needed = {v.value_id for v in composed.values if v.provenance == "library_canonical"}
    m: dict[str, ValueRubric] = {}
    entries = _coerce_canonical_entries(state.get("canonical_library_entries"))
    if entries:
        m.update(library_rubric_map_from_entries(entries))
    explicit = _coerce_library_rubrics(state.get("library_rubric_by_value_id"))
    if explicit:
        m.update(explicit)
    if not needed:
        return m if m else None
    missing = needed - m.keys()
    if missing:
        raise ValueError(
            "library_canonical rubrics missing for value_id(s) "
            f"{sorted(missing)}. Set AgentState.canonical_library_entries (from match_canonical_library) "
            "and/or library_rubric_by_value_id."
        )
    return m


async def match_canonical_library_node(state: AgentState) -> dict[str, Any]:
    """Embedding match against seed catalog when ``library_enabled``; else zeroed library fields."""
    run_id = state.get("run_id")
    step = state.get("step", 1)
    enabled = bool(state.get("library_enabled", False))
    input_data: dict[str, Any] = {"library_enabled": enabled}
    try:
        if not enabled:
            out = {
                "library_domain_count": 0,
                "library_domain_rows": [],
                "canonical_library_entries": [],
                "library_matches": [],
                "canonical_ids_used": [],
                "library_version_aggregate": None,
                "library_resolution_notes": None,
            }
            history = list(state.get("history", [])) + [("match_canonical_library", 0)]
            if run_id:
                repo = get_repo()
                with logfire.span("repo.append_turn", agent="match_canonical_library", run_id=run_id, step=step):
                    repo.append_turn(run_id, step, "match_canonical_library", input_data, {"k": 0}, True, None)
            patch: dict[str, Any] = {**out, "history": history}
            if run_id:
                patch["step"] = step + 1
            return patch

        threshold = get_library_match_threshold(override=state.get("library_match_threshold"))
        margin = get_library_match_margin()
        max_m = get_library_max_matches(override=state.get("library_max_matches"))

        raw = await asyncio.to_thread(
            run_library_match,
            state["raw_input"],
            threshold=threshold,
            margin=margin,
            max_matches=max_m,
        )
        lm_raw = raw.get("library_matches") or []
        output_data = {
            "k": raw.get("library_domain_count", 0),
            "canonical_ids_used": raw.get("canonical_ids_used"),
            "library_resolution_notes": raw.get("library_resolution_notes"),
            "matches": [m.model_dump() if hasattr(m, "model_dump") else m for m in lm_raw],
        }
        history = list(state.get("history", [])) + [
            ("match_canonical_library", int(raw.get("library_domain_count", 0) or 0)),
        ]
        if run_id:
            repo = get_repo()
            with logfire.span("repo.append_turn", agent="match_canonical_library", run_id=run_id, step=step):
                repo.append_turn(run_id, step, "match_canonical_library", input_data, output_data, True, None)

        rows = raw.get("library_domain_rows") or []
        entries = raw.get("canonical_library_entries") or []
        out_state: dict[str, Any] = {
            "library_domain_count": int(raw.get("library_domain_count", 0) or 0),
            "library_domain_rows": [v.model_dump() if hasattr(v, "model_dump") else v for v in rows],
            "canonical_library_entries": [e.model_dump() if hasattr(e, "model_dump") else e for e in entries],
            "library_matches": [m.model_dump() if hasattr(m, "model_dump") else m for m in lm_raw],
            "canonical_ids_used": list(raw.get("canonical_ids_used") or []),
            "library_version_aggregate": raw.get("library_version_aggregate"),
            "library_resolution_notes": raw.get("library_resolution_notes"),
            "history": history,
        }
        if run_id:
            out_state["step"] = step + 1
        return out_state
    except Exception as e:
        history = list(state.get("history", [])) + [("match_canonical_library", None)]
        if run_id:
            repo = get_repo()
            with logfire.span("repo.append_turn", agent="match_canonical_library", run_id=run_id, step=step):
                repo.append_turn(run_id, step, "match_canonical_library", input_data, None, False, str(e))
        raise


async def decode_values_node(state: AgentState) -> dict[str, Any]:
    run_id = state.get("run_id")
    step = state.get("step", 1)
    k_lib = int(state.get("library_domain_count", 0) or 0)
    entries = _coerce_canonical_entries(state.get("canonical_library_entries")) or []
    reserved = [(e.canonical_id, e.name) for e in entries]
    input_data = {"raw_input": state["raw_input"], "library_domain_count": k_lib, "reserved_n": len(reserved)}
    try:
        decoded = await run_decode_values(
            state["raw_input"],
            library_domain_count=k_lib,
            reserved_canonical=reserved,
            prompt_parameters=_coerce_prompt_parameters(state),
            prompt_profile_id=_prompt_profile_id(state),
            prompt_program_id=_prompt_program_id(state),
        )
        validate_decoded_domain_slot_count(decoded.values, library_domain_count=k_lib)
        output_data = decoded.model_dump()
        history = list(state.get("history", [])) + [("decode_values", len(decoded.values))]
        if run_id:
            repo = get_repo()
            with logfire.span("repo.append_turn", agent="decode_values", run_id=run_id, step=step):
                repo.append_turn(run_id, step, "decode_values", input_data, output_data, True, None)
        out: dict[str, Any] = {"decoded_raw": decoded, "history": history}
        if run_id:
            out["step"] = step + 1
        return out
    except Exception as e:
        history = list(state.get("history", [])) + [("decode_values", None)]
        if run_id:
            repo = get_repo()
            with logfire.span("repo.append_turn", agent="decode_values", run_id=run_id, step=step):
                repo.append_turn(run_id, step, "decode_values", input_data, None, False, str(e))
        raise


async def compose_values_node(state: AgentState) -> dict[str, Any]:
    run_id = state.get("run_id")
    step = state.get("step", 1)
    dr = state["decoded_raw"]
    lib_rows = _coerce_library_domain_rows(state.get("library_domain_rows"))
    input_data = {"decoded_raw": dr.model_dump(), "library_domain_rows_n": len(lib_rows or [])}
    try:
        ce = state.get("craft_enabled")
        composed = compose_values(dr, craft_enabled=ce, library_domain_rows=lib_rows)
        has_craft = any(v.provenance == "designer_craft" for v in composed.values)
        output_data = {
            "n_values": len(composed.values),
            "craft_enabled_effective": has_craft,
            "value_ids": [v.value_id for v in composed.values],
        }
        history = list(state.get("history", [])) + [("compose_values", len(composed.values))]
        if run_id:
            repo = get_repo()
            with logfire.span("repo.append_turn", agent="compose_values", run_id=run_id, step=step):
                repo.append_turn(run_id, step, "compose_values", input_data, output_data, True, None)
        out: dict[str, Any] = {
            "composed_values": composed,
            "craft_enabled": has_craft,
            "history": history,
        }
        if run_id:
            out["step"] = step + 1
        return out
    except Exception as e:
        history = list(state.get("history", [])) + [("compose_values", None)]
        if run_id:
            repo = get_repo()
            with logfire.span("repo.append_turn", agent="compose_values", run_id=run_id, step=step):
                repo.append_turn(run_id, step, "compose_values", input_data, None, False, str(e))
        raise


async def build_rubrics_node(state: AgentState) -> dict[str, Any]:
    run_id = state.get("run_id")
    step = state.get("step", 1)
    input_data = {"composed": state["composed_values"].model_dump()}
    try:
        limit = int(state.get("max_concurrent_llm", get_max_concurrent_llm()))
        composed = state["composed_values"]
        lib_rub = _resolve_library_rubric_map_for_build(state, composed)
        built = await run_build_rubrics(
            state["raw_input"],
            composed,
            max_concurrent_llm=limit,
            library_rubric_by_value_id=lib_rub,
            prompt_parameters=_coerce_prompt_parameters(state),
            prompt_profile_id=_prompt_profile_id(state),
            prompt_program_id=_prompt_program_id(state),
        )
        output_data = built.model_dump()
        history = list(state.get("history", [])) + [("build_rubrics", len(built.rubrics))]
        if run_id:
            repo = get_repo()
            with logfire.span("repo.append_turn", agent="rubric_builder", run_id=run_id, step=step):
                repo.append_turn(run_id, step, "build_rubrics", input_data, output_data, True, None)
        out: dict[str, Any] = {"rubrics": built, "history": history}
        if run_id:
            out["step"] = step + 1
        return out
    except Exception as e:
        if run_id:
            repo = get_repo()
            with logfire.span("repo.append_turn", agent="rubric_builder", run_id=run_id, step=step):
                repo.append_turn(run_id, step, "build_rubrics", input_data, None, False, str(e))
        raise


async def research_planning_node(state: AgentState) -> dict[str, Any]:
    """Produce research_plan + document_outline after rubrics; validation failures skip planning (§6.5)."""
    run_id = state.get("run_id")
    step = state.get("step", 1)
    composed = state["composed_values"]
    rubrics = state["rubrics"]
    input_data: dict[str, Any] = {
        "raw_input_len": len(state.get("raw_input") or ""),
        "n_values": len(composed.values),
        "prompt_profile_id": _prompt_profile_id(state),
        "prompt_program_id": _prompt_program_id(state),
    }
    try:
        digest = build_rubric_digest_for_planner(composed, rubrics)
        raw_out = await run_research_planning(
            state["raw_input"],
            composed,
            digest,
            prompt_parameters=_coerce_prompt_parameters(state),
            prompt_profile_id=_prompt_profile_id(state),
            prompt_program_id=_prompt_program_id(state),
        )
        cleaned = sanitize_research_planning_output(raw_out, composed)
        if cleaned is None:
            _logger.warning(
                "research_planning validation failed after sanitize; skipping planning for run_id=%s",
                run_id,
            )
            output_fail = {
                "success": False,
                "error": "planner_validation_failed",
                "preview": raw_out.model_dump() if hasattr(raw_out, "model_dump") else str(raw_out),
            }
            history = list(state.get("history", [])) + [("research_planning", None)]
            if run_id:
                repo = get_repo()
                with logfire.span("repo.append_turn", agent="research_planning", run_id=run_id, step=step):
                    repo.append_turn(run_id, step, "research_planning", input_data, output_fail, False, None)
            patch: dict[str, Any] = {
                "research_plan": None,
                "document_outline": None,
                "research_planning_skipped_reason": "planner_validation_failed",
                "history": history,
            }
            if run_id:
                patch["step"] = step + 1
            return patch

        outline_sections = len(cleaned.outline.sections)
        logfire.info(
            "research_planning.completed",
            run_id=run_id,
            program_id=_prompt_program_id(state),
            outline_section_count=outline_sections,
        )
        output_data = cleaned.model_dump()
        history = list(state.get("history", [])) + [("research_planning", outline_sections)]
        if run_id:
            repo = get_repo()
            with logfire.span("repo.append_turn", agent="research_planning", run_id=run_id, step=step):
                repo.append_turn(run_id, step, "research_planning", input_data, output_data, True, None)
        out: dict[str, Any] = {
            "research_plan": cleaned.research_plan,
            "document_outline": cleaned.outline,
            "research_planning_skipped_reason": None,
            "history": history,
        }
        if run_id:
            out["step"] = step + 1
        return out
    except Exception as e:
        history = list(state.get("history", [])) + [("research_planning", None)]
        if run_id:
            repo = get_repo()
            with logfire.span("repo.append_turn", agent="research_planning", run_id=run_id, step=step):
                repo.append_turn(run_id, step, "research_planning", input_data, None, False, str(e))
        raise


async def retrieve_evidence_node(state: AgentState) -> dict[str, Any]:
    run_id = state.get("run_id")
    step = state.get("step", 1)
    mode_raw = (state.get("retrieval_mode") or "auto").strip().lower()
    mode: RetrievalMode
    if mode_raw in ("auto", "urls_only", "search_only", "none"):
        mode = mode_raw  # type: ignore[assignment]
    else:
        mode = "auto"
    ref = state.get("reference_material")
    input_data = {"retrieval_mode": mode, "has_reference": bool(ref)}
    rp = state.get("research_plan")
    supplemental: list[str] | None = None
    if rp is not None:
        if hasattr(rp, "suggested_research_queries"):
            supplemental = list(rp.suggested_research_queries)
        elif isinstance(rp, dict):
            sq = rp.get("suggested_research_queries") or []
            supplemental = [str(x) for x in sq] if sq else None
    try:
        with logfire.span("retrieval.retrieve", mode=mode):
            bundle, rq = await build_bundle_from_prompt(
                state["raw_input"],
                reference_material=ref,
                mode=mode,
                supplemental_queries=supplemental,
            )
        output_data = {
            "chunk_count": len(bundle.chunks),
            "source_count": len(bundle.sources),
            "retrieval_query": rq,
            "bundle_preview": bundle.model_dump(),
        }
        history = list(state.get("history", [])) + [("retrieve_evidence", len(bundle.chunks))]
        if run_id:
            repo = get_repo()
            with logfire.span("repo.append_turn", agent="retrieve_evidence", run_id=run_id, step=step):
                repo.append_turn(run_id, step, "retrieve_evidence", input_data, output_data, True, None)
        out: dict[str, Any] = {
            "evidence_bundle": bundle,
            "retrieval_query": rq,
            "history": history,
        }
        if run_id:
            out["step"] = step + 1
        return out
    except Exception as e:
        if run_id:
            repo = get_repo()
            with logfire.span("repo.append_turn", agent="retrieve_evidence", run_id=run_id, step=step):
                repo.append_turn(run_id, step, "retrieve_evidence", input_data, None, False, str(e))
        raise


async def writer_node(state: AgentState) -> dict[str, Any]:
    run_id = state.get("run_id")
    step = state.get("step", 1)
    next_iter = state.get("iterations", 0) + 1
    mf_raw = state.get("merged_feedback", "")
    merged = mf_raw.strip() if mf_raw else None
    input_data = {"iteration": next_iter, "has_prior_feedback": merged is not None}
    bundle: EvidenceBundle | None = (
        state.get("evidence_bundle") if state.get("grounding_enabled", False) else None
    )
    rp_raw = state.get("research_plan")
    do_raw = state.get("document_outline")
    rp_plan: ResearchPlan | None = None
    outline: DocumentOutline | None = None
    if rp_raw is not None:
        rp_plan = rp_raw if isinstance(rp_raw, ResearchPlan) else ResearchPlan.model_validate(rp_raw)
    if do_raw is not None:
        outline = do_raw if isinstance(do_raw, DocumentOutline) else DocumentOutline.model_validate(do_raw)
    try:
        out_writer = await run_writer(
            state["raw_input"],
            state["composed_values"],
            state["rubrics"],
            merged,
            next_iter,
            evidence_bundle=bundle,
            research_plan=rp_plan,
            document_outline=outline,
            prompt_parameters=_coerce_prompt_parameters(state),
            prompt_profile_id=_prompt_profile_id(state),
            prompt_program_id=_prompt_program_id(state),
        )
        output_data = out_writer.model_dump()
        iteration = next_iter
        history = list(state.get("history", [])) + [(iteration, "writer", len(out_writer.draft_text))]
        if run_id:
            repo = get_repo()
            with logfire.span("repo.append_turn", agent="writer", run_id=run_id, step=step):
                repo.append_turn(run_id, step, "writer", input_data, output_data, True, None)
        result: dict[str, Any] = {
            "draft": out_writer.draft_text,
            "iterations": iteration,
            "history": history,
        }
        if run_id:
            result["step"] = step + 1
        return result
    except Exception as e:
        history = list(state.get("history", [])) + [(next_iter, "writer", None)]
        if run_id:
            repo = get_repo()
            with logfire.span("repo.append_turn", agent="writer", run_id=run_id, step=step):
                repo.append_turn(run_id, step, "writer", input_data, None, False, str(e))
        raise


async def assess_all_node(state: AgentState) -> dict[str, Any]:
    run_id = state.get("run_id")
    step = state.get("step", 1)
    draft = state["draft"]
    composed = state["composed_values"]
    rubrics = state["rubrics"]
    value_by_id = {v.value_id: v for v in composed.values}
    ge = bool(state.get("grounding_enabled", False))
    bundle = state.get("evidence_bundle") or EvidenceBundle()
    input_data = {"draft_len": len(draft), "n_values": len(rubrics.rubrics), "grounding_enabled": ge}
    try:
        parallel = state.get("assess_parallel", True)
        limit = max(1, int(state.get("max_concurrent_llm", get_max_concurrent_llm())))
        sem = asyncio.Semaphore(limit)

        pp = _coerce_prompt_parameters(state)
        prof = _prompt_profile_id(state)
        pprog = _prompt_program_id(state)

        async def one(rid: str) -> AssessorResult:
            rub = next(r for r in rubrics.rubrics if r.value_id == rid)
            val = value_by_id[rub.value_id]
            if parallel:
                async with sem:
                    return await run_assess_one(
                        rub,
                        val,
                        draft,
                        prompt_parameters=pp,
                        prompt_profile_id=prof,
                        prompt_program_id=pprog,
                    )
            return await run_assess_one(
                rub,
                val,
                draft,
                prompt_parameters=pp,
                prompt_profile_id=prof,
                prompt_program_id=pprog,
            )

        ordered_ids = sorted(r.value_id for r in rubrics.rubrics)

        async def run_values() -> list[AssessorResult]:
            if parallel:
                return await asyncio.gather(*[one(rid) for rid in ordered_ids])
            out: list[AssessorResult] = []
            for rid in ordered_ids:
                out.append(await one(rid))
            return out

        async def run_grounding() -> GroundingAssessment | None:
            return await run_grounding_assess(
                state["raw_input"],
                bundle,
                draft,
                prompt_parameters=pp,
                prompt_profile_id=prof,
                prompt_program_id=pprog,
            )

        if ge:
            results, ga = await asyncio.gather(run_values(), run_grounding())
        else:
            results = await run_values()
            ga = None

        results_list = list(results)
        a_headline = weighted_mean_aggregate(results_list, composed)
        a_dom = domain_aggregate(results_list, composed)
        a_craft = craft_aggregate(results_list, composed)
        hist = list(state.get("aggregate_history", [])) + [a_headline]
        dom_hist = list(state.get("domain_aggregate_history", [])) + [a_dom]
        craft_hist = list(state.get("craft_aggregate_history", [])) + [a_craft]
        g_hist = list(state.get("grounding_score_history", []))
        if ga is not None:
            g_hist.append(float(ga.grounding_score))

        output_data: dict[str, Any] = {
            "aggregate_value_score": a_headline,
            "A_domain": a_dom,
            "A_craft": a_craft,
            "results": [r.model_dump() for r in results],
        }
        if ga is not None:
            output_data["grounding_score"] = ga.grounding_score
            output_data["grounding"] = ga.model_dump()

        history = list(state.get("history", [])) + [
            (state.get("iterations", 0), "assess_all", a_headline),
        ]
        if run_id:
            repo = get_repo()
            with logfire.span("repo.append_turn", agent="assess_all", run_id=run_id, step=step):
                repo.append_turn(run_id, step, "assess_all", input_data, output_data, True, None)
            if ge and ga is not None:
                g_step = step + 1
                with logfire.span("repo.append_turn", agent="grounding_assess", run_id=run_id, step=g_step):
                    repo.append_turn(
                        run_id,
                        g_step,
                        "grounding_assess",
                        {"draft_len": len(draft), "chunk_count": len(bundle.chunks)},
                        {"grounding_score": ga.grounding_score, "summary": ga.summary[:500]},
                        True,
                        None,
                    )

        out: dict[str, Any] = {
            "last_assessments": list(results),
            "last_grounding_assessment": ga,
            "aggregate_value_score": a_headline,
            "aggregate_history": hist,
            "domain_aggregate_history": dom_hist,
            "craft_aggregate_history": craft_hist,
            "grounding_score_history": g_hist,
            "history": history,
        }
        if run_id:
            out["step"] = step + (2 if ge and ga is not None else 1)
        return out
    except Exception as e:
        if run_id:
            repo = get_repo()
            with logfire.span("repo.append_turn", agent="assess_all", run_id=run_id, step=step):
                repo.append_turn(run_id, step, "assess_all", input_data, None, False, str(e))
        raise


async def merge_feedback_node(state: AgentState) -> dict[str, Any]:
    run_id = state.get("run_id")
    step = state.get("step", 1)
    assessments = state.get("last_assessments") or []
    composed = state["composed_values"]
    ge = bool(state.get("grounding_enabled", False))
    ga = state.get("last_grounding_assessment") if ge else None
    merged = merge_value_and_grounding_feedback(assessments, ga, composed)
    input_data = {"n_assessments": len(assessments), "grounding": ge}
    output_data = {"merged_preview": merged[:500]}
    history = list(state.get("history", [])) + [("merge_feedback", len(merged))]
    if run_id:
        repo = get_repo()
        with logfire.span("repo.append_turn", agent="merge_feedback", run_id=run_id, step=step):
            repo.append_turn(run_id, step, "merge_feedback", input_data, output_data, True, None)
    out: dict[str, Any] = {"merged_feedback": merged, "history": history}
    if run_id:
        out["step"] = step + 1
    return out


workflow = StateGraph(AgentState)
workflow.add_node("match_canonical_library", match_canonical_library_node)
workflow.add_node("decode_values", decode_values_node)
workflow.add_node("compose_values", compose_values_node)
workflow.add_node("build_rubrics", build_rubrics_node)
workflow.add_node("research_planning", research_planning_node)
workflow.add_node("retrieve_evidence", retrieve_evidence_node)
workflow.add_node("writer", writer_node)
workflow.add_node("assess_all", assess_all_node)
workflow.add_node("merge_feedback", merge_feedback_node)

workflow.set_entry_point("match_canonical_library")
workflow.add_edge("match_canonical_library", "decode_values")
workflow.add_edge("decode_values", "compose_values")
workflow.add_edge("compose_values", "build_rubrics")
workflow.add_conditional_edges(
    "build_rubrics",
    route_after_build_rubrics,
    {
        "research_planning": "research_planning",
        "retrieve_evidence": "retrieve_evidence",
        "writer": "writer",
    },
)
workflow.add_conditional_edges(
    "research_planning",
    route_after_research_planning,
    {
        "retrieve_evidence": "retrieve_evidence",
        "writer": "writer",
    },
)
workflow.add_edge("retrieve_evidence", "writer")
workflow.add_edge("writer", "assess_all")
workflow.add_edge("assess_all", "merge_feedback")
workflow.add_conditional_edges("merge_feedback", route_after_merge)

_compiled_app = workflow.compile()


async def run_workflow(initial_input: dict[str, Any]) -> AgentState:
    """Execute workflow with run/turn persistence; returns final graph state."""
    repo = get_repo()
    topic = initial_input.get("raw_input", "unknown")[:200]
    prog_override = initial_input.get("prompt_program_id")
    program_id_arg = (
        str(prog_override).strip()
        if isinstance(prog_override, str) and str(prog_override).strip()
        else None
    )
    prompt_meta = get_program_metadata(program_id_arg)
    prompt_params = resolve_prompt_parameters_for_run(initial_input)
    prompt_profile = default_prompt_profile_id(initial_input)

    req_in = initial_input.get("research_planning_enabled")
    if req_in is None:
        req_in = initial_input.get("research_planning_requested")
    research_planning_requested: bool | None = req_in if isinstance(req_in, bool) else None
    research_planning_effective = resolve_research_planning_enabled(
        requested=research_planning_requested,
        program_id=prompt_meta.program_id,
        prompt_profile_id=prompt_profile,
    )
    force_research_planning = bool(initial_input.get("force_research_planning", False))
    research_planning_skipped_reason = _initial_research_planning_skip_reason(
        effective=research_planning_effective,
        raw_input=str(initial_input.get("raw_input") or ""),
        reference_material=initial_input.get("reference_material"),
        force_research_planning=force_research_planning,
    )

    with logfire.span("repo.create_run", topic=topic):
        run_id = repo.create_run(topic)

    max_it = int(initial_input.get("max_iterations", DEFAULT_MAX_WRITER_ITERATIONS))
    plateau_window = int(initial_input.get("plateau_window", DEFAULT_PLATEAU_WINDOW))
    plateau_epsilon_domain = float(
        initial_input.get(
            "plateau_epsilon_domain",
            initial_input.get("plateau_epsilon", DEFAULT_PLATEAU_EPSILON_DOMAIN),
        )
    )
    plateau_epsilon_craft = float(
        initial_input.get("plateau_epsilon_craft", DEFAULT_PLATEAU_EPSILON_CRAFT)
    )
    plateau_epsilon_grounding = float(
        initial_input.get("plateau_epsilon_grounding", DEFAULT_PLATEAU_EPSILON_GROUNDING)
    )
    craft_enabled_in = initial_input.get("craft_enabled")
    assess_parallel = bool(initial_input.get("assess_parallel", True))
    grounding_enabled = bool(initial_input.get("grounding_enabled", True))
    retrieval_mode = str(initial_input.get("retrieval_mode") or "auto")
    reference_material = initial_input.get("reference_material")
    if reference_material is not None and not isinstance(reference_material, str):
        reference_material = str(reference_material)

    try:
        max_concurrent_llm = int(
            initial_input.get("max_concurrent_llm", get_max_concurrent_llm())
        )
    except (TypeError, ValueError):
        max_concurrent_llm = get_max_concurrent_llm()
    max_concurrent_llm = max(1, min(max_concurrent_llm, MAX_CONCURRENT_LLM_CAP))

    state_with_run: AgentState = {
        **initial_input,  # type: ignore[misc]
        "run_id": run_id,
        "step": 1,
        "history": [],
        "merged_feedback": "",
        "iterations": 0,
        "max_iterations": max_it,
        "plateau_window": plateau_window,
        "plateau_epsilon_domain": plateau_epsilon_domain,
        "plateau_epsilon_craft": plateau_epsilon_craft,
        "plateau_epsilon_grounding": plateau_epsilon_grounding,
        "assess_parallel": assess_parallel,
        "max_concurrent_llm": max_concurrent_llm,
        "aggregate_history": [],
        "domain_aggregate_history": [],
        "craft_aggregate_history": [],
        "grounding_score_history": [],
        "grounding_enabled": grounding_enabled,
        "retrieval_mode": retrieval_mode,
        "reference_material": reference_material,
        "last_grounding_assessment": None,
        "prompt_parameters": prompt_params.model_dump(),
        "prompt_program_id": prompt_meta.program_id,
        "prompt_program_version": prompt_meta.version,
        "prompt_profile_id": prompt_profile,
        "research_planning_requested": research_planning_requested,
        "research_planning_effective": research_planning_effective,
        "research_plan": None,
        "document_outline": None,
        "research_planning_skipped_reason": research_planning_skipped_reason,
        "force_research_planning": force_research_planning,
    }
    if craft_enabled_in is not None:
        state_with_run["craft_enabled"] = bool(craft_enabled_in)

    token = set_workflow_run_id(run_id)
    try:
        with logfire.set_baggage(run_id=run_id, topic=topic):
            try:
                with logfire.span(
                    "langgraph.ainvoke",
                    run_id=run_id,
                    prompt_program_id=prompt_meta.program_id,
                    prompt_program_version=prompt_meta.version,
                    prompt_profile_id=prompt_profile,
                ):
                    final_state = await _compiled_app.ainvoke(state_with_run)

                stop_reason = _infer_stop_reason(final_state)
                ga = final_state.get("last_grounding_assessment")
                bundle = final_state.get("evidence_bundle")
                source_ids = [s.source_id for s in bundle.sources] if bundle else []
                composed = final_state.get("composed_values")
                rp_final = final_state.get("research_plan")
                do_final = final_state.get("document_outline")
                final_output = {
                    "draft": final_state.get("draft"),
                    "iterations": final_state.get("iterations"),
                    "aggregate_value_score": final_state.get("aggregate_value_score"),
                    "aggregate_history": final_state.get("aggregate_history"),
                    "domain_aggregate_history": final_state.get("domain_aggregate_history"),
                    "craft_aggregate_history": final_state.get("craft_aggregate_history"),
                    "grounding_score": float(ga.grounding_score) if ga else None,
                    "grounding_source_ids": source_ids,
                    "stop_reason": stop_reason,
                    "prompt_program_id": final_state.get("prompt_program_id"),
                    "prompt_program_version": final_state.get("prompt_program_version"),
                    "prompt_parameters": final_state.get("prompt_parameters"),
                    "prompt_profile_id": final_state.get("prompt_profile_id"),
                    "craft_rubric_version": CRAFT_RUBRIC_VERSION,
                    "decoded_raw": final_state.get("decoded_raw").model_dump()
                    if final_state.get("decoded_raw")
                    else None,
                    "composed_values": composed.model_dump() if composed else None,
                    "last_assessments": [a.model_dump() for a in final_state.get("last_assessments") or []],
                    "canonical_ids_used": list(final_state.get("canonical_ids_used") or []),
                    "library_version_aggregate": final_state.get("library_version_aggregate"),
                    "library_resolution_notes": final_state.get("library_resolution_notes"),
                    "research_planning_requested": final_state.get("research_planning_requested"),
                    "research_planning_effective": final_state.get("research_planning_effective"),
                    "research_planning_skipped_reason": final_state.get("research_planning_skipped_reason"),
                    "research_plan": rp_final.model_dump() if rp_final is not None else None,
                    "document_outline": do_final.model_dump() if do_final is not None else None,
                }
                with logfire.span("repo.finalize_run", run_id=run_id, status="completed"):
                    repo.finalize_run(run_id, "completed", final_output=final_output)
                return final_state
            except Exception as e:
                with logfire.span("repo.finalize_run", run_id=run_id, status="failed"):
                    repo.finalize_run(run_id, "failed", error=str(e))
                raise
    finally:
        reset_workflow_run_id(token)


workflow_app = _compiled_app
