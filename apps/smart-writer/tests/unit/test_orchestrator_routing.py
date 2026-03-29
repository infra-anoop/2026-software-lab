"""Unit tests for stop reason and conditional routing (no LangGraph execution)."""

from langgraph.graph import END

from app.agents.models import (
    DEFAULT_MAX_WRITER_ITERATIONS,
    DEFAULT_PLATEAU_EPSILON_DOMAIN,
    DEFAULT_PLATEAU_WINDOW,
    AssessorResult,
    ComposedValues,
    GroundingAssessment,
    ValueDefinition,
)
from app.orchestrator.run import (
    _infer_stop_reason,
    route_after_build_rubrics,
    route_after_merge,
    route_after_research_planning,
)


def _domain_composed_five() -> ComposedValues:
    return ComposedValues(
        values=[
            ValueDefinition(
                value_id=f"V{i}",
                name="n",
                description="d",
                raw_weight=1.0,
                weight=0.2,
            )
            for i in range(1, 6)
        ]
    )


def test_infer_stop_reason_max_iterations_first() -> None:
    state = {
        "iterations": 10,
        "max_iterations": 10,
        "domain_aggregate_history": [15.0, 16.0],
    }
    assert _infer_stop_reason(state) == "max_iterations"


def test_infer_stop_reason_plateau_when_gain_small() -> None:
    """Plateau uses ``hist[-1] - hist[-1-pw]`` on domain aggregate (0–25 mean)."""
    state = {
        "iterations": 3,
        "max_iterations": 10,
        "domain_aggregate_history": [15.0, 15.0, 15.0],
        "plateau_window": 2,
        "plateau_epsilon_domain": 0.5,
        "craft_enabled": False,
    }
    assert _infer_stop_reason(state) == "plateau"


def test_infer_stop_reason_completed_when_no_condition() -> None:
    state = {
        "iterations": 1,
        "max_iterations": 10,
        "domain_aggregate_history": [12.0],
    }
    assert _infer_stop_reason(state) == "completed"


def test_infer_stop_reason_history_too_short_for_plateau() -> None:
    """``len(hist) > pw`` is false with only two scores and default ``pw=2``."""
    state = {
        "iterations": 2,
        "max_iterations": 10,
        "domain_aggregate_history": [18.0, 19.0],
        "plateau_window": DEFAULT_PLATEAU_WINDOW,
        "plateau_epsilon_domain": DEFAULT_PLATEAU_EPSILON_DOMAIN,
        "craft_enabled": False,
    }
    assert _infer_stop_reason(state) == "completed"


def test_route_after_merge_stops_at_max_iterations() -> None:
    state = {
        "iterations": 3,
        "max_iterations": 3,
        "domain_aggregate_history": [10.0, 12.0, 14.0],
    }
    assert route_after_merge(state) == END


def test_route_after_merge_plateau_exits() -> None:
    state = {
        "iterations": 2,
        "max_iterations": 10,
        "domain_aggregate_history": [15.0, 15.0, 15.0],
        "plateau_window": DEFAULT_PLATEAU_WINDOW,
        "plateau_epsilon_domain": DEFAULT_PLATEAU_EPSILON_DOMAIN,
        "craft_enabled": False,
    }
    assert route_after_merge(state) == END


def test_route_after_merge_continues_to_writer() -> None:
    state = {
        "iterations": 1,
        "max_iterations": DEFAULT_MAX_WRITER_ITERATIONS,
        "domain_aggregate_history": [12.0, 16.0],
        "plateau_window": DEFAULT_PLATEAU_WINDOW,
        "plateau_epsilon_domain": DEFAULT_PLATEAU_EPSILON_DOMAIN,
        "craft_enabled": False,
    }
    assert route_after_merge(state) == "writer"


def test_route_defaults_match_module_constants() -> None:
    """Explicit defaults in ``route_after_merge`` align with models defaults."""
    minimal = {
        "iterations": 1,
        "domain_aggregate_history": [16.0, 17.0],
    }
    assert minimal.get("max_iterations", DEFAULT_MAX_WRITER_ITERATIONS) == DEFAULT_MAX_WRITER_ITERATIONS
    out = route_after_merge(minimal)
    assert out == "writer"


def _five_high_assessments() -> list[AssessorResult]:
    return [
        AssessorResult(
            value_id=f"V{i}",
            dimension_scores=[5, 5, 5, 5, 5],
            keep=["k"],
            change=["c"],
        )
        for i in range(1, 6)
    ]


def test_infer_stop_reason_targets_met() -> None:
    state = {
        "iterations": 2,
        "max_iterations": 10,
        "grounding_enabled": True,
        "composed_values": _domain_composed_five(),
        "last_assessments": _five_high_assessments(),
        "last_grounding_assessment": GroundingAssessment(
            grounding_score=0.95,
            summary="ok",
            writer_instructions="",
        ),
        "domain_aggregate_history": [20.0, 25.0],
    }
    assert _infer_stop_reason(state) == "targets_met"


def test_route_after_merge_exits_on_targets_met() -> None:
    state = {
        "iterations": 1,
        "max_iterations": 10,
        "grounding_enabled": True,
        "composed_values": _domain_composed_five(),
        "last_assessments": _five_high_assessments(),
        "last_grounding_assessment": GroundingAssessment(
            grounding_score=0.95,
            summary="ok",
            writer_instructions="",
        ),
        "domain_aggregate_history": [25.0],
    }
    assert route_after_merge(state) == END


def test_route_after_build_rubrics_planning_then_grounding() -> None:
    state = {
        "research_planning_effective": True,
        "research_planning_skipped_reason": None,
        "grounding_enabled": True,
    }
    assert route_after_build_rubrics(state) == "research_planning"


def test_route_after_build_rubrics_skips_planning_when_short_heuristic() -> None:
    state = {
        "research_planning_effective": True,
        "research_planning_skipped_reason": "short_prompt_heuristic",
        "grounding_enabled": True,
    }
    assert route_after_build_rubrics(state) == "retrieve_evidence"


def test_route_after_build_rubrics_disabled_goes_to_writer_without_grounding() -> None:
    state = {
        "research_planning_effective": False,
        "grounding_enabled": False,
    }
    assert route_after_build_rubrics(state) == "writer"


def test_route_after_build_rubrics_disabled_goes_to_retrieve_when_grounding() -> None:
    state = {
        "research_planning_effective": False,
        "grounding_enabled": True,
    }
    assert route_after_build_rubrics(state) == "retrieve_evidence"


def test_route_after_research_planning_retrieve_when_grounding() -> None:
    assert route_after_research_planning({"grounding_enabled": True}) == "retrieve_evidence"


def test_route_after_research_planning_writer_when_no_grounding() -> None:
    assert route_after_research_planning({"grounding_enabled": False}) == "writer"


def test_dual_plateau_requires_craft_history_when_craft_enabled() -> None:
    """When craft is on, value plateau needs both domain and craft flatlines."""
    state = {
        "iterations": 2,
        "max_iterations": 10,
        "craft_enabled": True,
        "domain_aggregate_history": [15.0, 15.0, 15.0],
        "craft_aggregate_history": [12.0, 18.0, 20.0],
        "plateau_window": 2,
        "plateau_epsilon_domain": 0.5,
        "plateau_epsilon_craft": 0.5,
        "grounding_enabled": False,
    }
    assert _infer_stop_reason(state) == "completed"
