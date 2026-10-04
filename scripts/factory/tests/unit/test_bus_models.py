"""T015 — bus message models: every constraint quoted in tasks.md T006."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from factory.bus import models as bus_models
from factory.bus.models import KIND_MODELS, MESSAGE_KINDS, Lock, parse_message

MESSAGES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "messages"
SAMPLE_FILES = {
    "order": "order.yaml",
    "amendment": "amendment.yaml",
    "handoff": "handoff.yaml",
    "verdict": "verdict.yaml",
    "decision_request": "decision-request.yaml",
    "decision_lock": "decision-lock.yaml",
    "correction": "correction.yaml",
    "override": "override.yaml",
    "claim": "claim.yaml",
    "release": "release.yaml",
    "run_complete": "run-complete.yaml",
}
FORBIDDEN_KEYS = ["status", "state", "done", "progress"]


def sample(kind: str) -> dict[str, Any]:
    data = yaml.safe_load((MESSAGES_DIR / SAMPLE_FILES[kind]).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return copy.deepcopy(data)


def rejects(data: dict[str, Any], **kwargs: Any) -> str:
    with pytest.raises(ValidationError) as excinfo:
        parse_message(data, **kwargs)
    return str(excinfo.value)


# --- envelope -----------------------------------------------------------------


def test_kinds_are_exactly_the_data_model_enum() -> None:
    assert set(MESSAGE_KINDS) == set(SAMPLE_FILES)
    assert set(KIND_MODELS) == set(SAMPLE_FILES)


@pytest.mark.parametrize("kind", sorted(SAMPLE_FILES))
def test_every_sample_message_validates(kind: str) -> None:
    message = parse_message(sample(kind))
    assert message.kind == kind
    assert type(message) is KIND_MODELS[kind]


def test_schema_version_must_be_1() -> None:
    data = sample("order")
    data["schema_version"] = 2
    rejects(data)


def test_unknown_kind_rejected() -> None:
    data = sample("order")
    data["kind"] = "status_update"
    rejects(data)


@pytest.mark.parametrize("actor", ["bot", "human", ""])
def test_actor_enum(actor: str) -> None:
    data = sample("claim")
    data["actor"] = actor
    rejects(data)


@pytest.mark.parametrize("actor", ["orchestrator", "worker", "reviewer"])
def test_actor_model_required_for_non_governor(actor: str) -> None:
    data = sample("override")
    data["actor"] = actor
    del data["actor_model"]
    assert "actor_model" in rejects(data)


def test_governor_needs_no_actor_model() -> None:
    data = sample("decision_lock")
    assert "actor_model" not in data
    assert parse_message(data).actor == "governor"


def test_created_must_be_timezone_aware_utc() -> None:
    data = sample("order")
    data["created"] = "2026-10-05T14:00:00"
    rejects(data)
    data["created"] = "2026-10-05T14:00:00+02:00"
    rejects(data)


# --- FR-003: forbidden keys anywhere ---------------------------------------------


@pytest.mark.parametrize("key", FORBIDDEN_KEYS)
@pytest.mark.parametrize("kind", sorted(SAMPLE_FILES))
def test_forbidden_key_at_top_level(kind: str, key: str) -> None:
    data = sample(kind)
    data[key] = "in_review"
    assert key in rejects(data)


@pytest.mark.parametrize("key", FORBIDDEN_KEYS)
def test_forbidden_key_nested_in_model(key: str) -> None:
    data = sample("order")
    data["locks"][0][key] = True
    assert key in rejects(data)


@pytest.mark.parametrize("key", FORBIDDEN_KEYS)
def test_forbidden_key_nested_in_free_mapping(key: str) -> None:
    data = sample("amendment")
    data["values"]["stop_conditions"] = [{key: "x"}]
    assert key in rejects(data)


@pytest.mark.parametrize("key", FORBIDDEN_KEYS)
def test_forbidden_key_deep_in_list(key: str) -> None:
    data = sample("decision_request")
    data["options"][1]["consequences"][key] = "open"
    assert key in rejects(data)


# --- extra="forbid" ---------------------------------------------------------------


@pytest.mark.parametrize("kind", sorted(SAMPLE_FILES))
def test_extra_top_level_key_rejected(kind: str) -> None:
    data = sample(kind)
    data["notes_for_later"] = "x"
    rejects(data)


def test_extra_key_in_nested_lock_rejected() -> None:
    data = sample("order")
    data["locks"][0]["owner"] = "governor"
    rejects(data)


def test_extra_key_in_nested_finding_rejected() -> None:
    data = sample("verdict")
    data["findings"][0]["blocking"] = True
    rejects(data)


# --- WorkOrder --------------------------------------------------------------------


def test_goal_at_most_three_sentences() -> None:
    data = sample("order")
    data["goal"] = "One. Two. Three."
    parse_message(data)
    data["goal"] = "One. Two. Three. Four."
    assert "goal" in rejects(data)


def test_owned_paths_non_empty() -> None:
    data = sample("order")
    data["owned_paths"] = []
    assert "owned_paths" in rejects(data)


def test_stop_conditions_non_empty() -> None:
    data = sample("order")
    data["stop_conditions"] = []
    assert "stop_conditions" in rejects(data)


def test_size_minutes_at_most_default_horizon() -> None:
    data = sample("order")
    data["size_minutes"] = 60
    parse_message(data)
    data["size_minutes"] = 61
    assert "size_minutes" in rejects(data)


def test_size_minutes_at_most_configured_horizon() -> None:
    data = sample("order")
    data["size_minutes"] = 45
    parse_message(data, autonomy_horizon_minutes=45)
    assert "size_minutes" in rejects(data, autonomy_horizon_minutes=30)


@pytest.mark.parametrize("size", [0, -5])
def test_size_minutes_positive(size: int) -> None:
    data = sample("order")
    data["size_minutes"] = size
    rejects(data)


def test_worker_runtime_enum() -> None:
    data = sample("order")
    data["worker_runtime"] = "laptop"
    rejects(data)


def test_lock_fidelity_enum() -> None:
    data = sample("order")
    data["locks"][0]["fidelity"] = "approx"
    rejects(data)


def test_waived_lock_requires_waiver_ref() -> None:
    data = sample("order")
    data["locks"][0]["fidelity"] = "waived"
    assert "waiver_ref" in rejects(data)
    data["locks"][0]["waiver_ref"] = "board-web-view.lock"
    parse_message(data)


@pytest.mark.parametrize("tokens", [[], [""], ["  "], ["70%", " "]])
def test_letter_lock_requires_non_empty_letter_tokens(tokens: list[str]) -> None:
    data = sample("order")
    data["locks"][0]["letter_tokens"] = tokens
    assert "letter_tokens" in rejects(data)


def test_intent_lock_may_omit_letter_tokens() -> None:
    data = sample("order")
    data["locks"][0].update(fidelity="intent", letter_tokens=[])
    parse_message(data)


def test_lock_substitutes_are_optional() -> None:
    assert "substitutes" in Lock.model_fields, "Lock has no substitutes field"
    data = sample("order")
    assert parse_message(data).locks[0].substitutes == []
    data["locks"][0]["substitutes"] = ["60%", "best effort"]
    assert parse_message(data).locks[0].substitutes == ["60%", "best effort"]


@pytest.mark.parametrize("substitutes", [["70%"], [""], ["  "]])
def test_lock_substitutes_must_be_distinct_non_blank(substitutes: list[str]) -> None:
    assert "substitutes" in Lock.model_fields, "Lock has no substitutes field"
    data = sample("order")
    data["locks"][0]["substitutes"] = substitutes
    assert "substitutes" in rejects(data)


def test_lock_direction_is_optional() -> None:
    assert "direction" in Lock.model_fields, "Lock has no direction field"
    data = sample("order")
    assert parse_message(data).locks[0].direction is None
    for direction in ("min", "max"):
        data["locks"][0]["direction"] = direction
        assert parse_message(data).locks[0].direction == direction


def test_lock_direction_enum() -> None:
    assert "direction" in Lock.model_fields, "Lock has no direction field"
    data = sample("order")
    data["locks"][0]["direction"] = "up"
    assert "direction" in rejects(data)


@pytest.mark.parametrize(
    ("fidelity", "tokens"),
    [
        ("letter", ["railway"]),
        ("letter", ["between 2 and 5"]),
        ("intent", ["70%"]),
    ],
    ids=["no_number", "two_numbers", "not_letter"],
)
def test_lock_direction_needs_a_numeric_letter_token(fidelity: str, tokens: list[str]) -> None:
    """`direction` only means something for a letter token holding exactly one number."""
    assert "direction" in Lock.model_fields, "Lock has no direction field"
    data = sample("order")
    data["locks"][0].update(fidelity=fidelity, letter_tokens=tokens, direction="min")
    assert "direction" in rejects(data)


@pytest.mark.parametrize(
    ("token", "numeric"),
    [
        ("70%", True),
        ("cap 3", True),
        ("max_attempts: 2", True),
        ("$5", True),
        ("gpt-5.6", True),
        ("railway", False),
        ("between 2 and 5", False),
    ],
)
def test_numeric_letter_token(token: str, numeric: bool) -> None:
    is_numeric_token = getattr(bus_models, "is_numeric_token", None)
    assert is_numeric_token is not None, "bus models export no is_numeric_token"
    assert is_numeric_token(token) is numeric


def test_amendment_values_validated_like_order_fields() -> None:
    data = sample("amendment")
    data["values"]["size_minutes"] = 90
    assert "size_minutes" in rejects(data)


def test_amendment_supersedes_must_match_values_and_order_fields() -> None:
    data = sample("amendment")
    data["supersedes"] = ["size_minutes"]
    rejects(data)
    data = sample("amendment")
    data["supersedes"].append("colour")
    data["values"]["colour"] = "blue"
    rejects(data)


# --- Verdict ----------------------------------------------------------------------


@pytest.mark.parametrize("severity", ["blocker", "debate", "later", "nit"])
def test_finding_severity_allowed(severity: str) -> None:
    data = sample("verdict")
    data["findings"][0]["severity"] = severity
    parse_message(data)


@pytest.mark.parametrize("severity", ["major", "minor", "info"])
def test_finding_severity_rejected(severity: str) -> None:
    data = sample("verdict")
    data["findings"][0]["severity"] = severity
    rejects(data)


@pytest.mark.parametrize("tag", ["product", "process", "arch"])
def test_finding_tag_allowed(tag: str) -> None:
    data = sample("verdict")
    data["findings"][0]["tag"] = tag
    parse_message(data)


@pytest.mark.parametrize("tag", ["security", "style"])
def test_finding_tag_rejected(tag: str) -> None:
    data = sample("verdict")
    data["findings"][0]["tag"] = tag
    rejects(data)


def test_verdict_decision_enum() -> None:
    data = sample("verdict")
    data["decision"] = "approve"
    rejects(data)


@pytest.mark.parametrize("path", ["https://chat.example/thread/1", "/home/vscode/transcript.jsonl"])
def test_verdict_inputs_are_repo_paths(path: str) -> None:
    data = sample("verdict")
    data["inputs"][0]["path"] = path
    rejects(data)


def test_verdict_input_sha_is_hex() -> None:
    data = sample("verdict")
    data["inputs"][0]["sha"] = "HEAD"
    rejects(data)


def test_bootstrap_verdict_lists_manual_equivalents() -> None:
    data = sample("verdict")
    data["manual_equivalents"] = []
    assert "manual_equivalents" in rejects(data)


# --- Handoff ----------------------------------------------------------------------


def test_handoff_deviations_key_required() -> None:
    data = sample("handoff")
    del data["deviations"]
    assert "deviations" in rejects(data)
    data["deviations"] = []
    parse_message(data)


def test_handoff_open_question_classes() -> None:
    data = sample("handoff")
    data["open_questions"][0]["class"] = "blocker_governor"
    parse_message(data)
    data["open_questions"][0]["class"] = "urgent"
    rejects(data)


def test_handoff_summary_at_most_ten_lines() -> None:
    data = sample("handoff")
    data["summary"] = "\n".join(f"line {i}" for i in range(11))
    assert "summary" in rejects(data)


def test_handoff_author_model_required() -> None:
    data = sample("handoff")
    del data["author_model"]
    rejects(data)


# --- Override ---------------------------------------------------------------------


@pytest.mark.parametrize("reason", ["", "   ", "\n"])
def test_override_reason_non_empty(reason: str) -> None:
    data = sample("override")
    data["reason"] = reason
    assert "reason" in rejects(data)


def test_governor_only_override_needs_governor_actor() -> None:
    data = sample("override")
    data["gate_class"] = "governor-only"
    rejects(data)
    data["actor"] = "governor"
    del data["actor_model"]
    parse_message(data)


# --- Decision request ---------------------------------------------------------------


def test_arch_impact_options_need_consequences() -> None:
    data = sample("decision_request")
    del data["options"][0]["consequences"]
    assert "consequences" in rejects(data)
    data["arch_impact"] = False
    parse_message(data)


def test_decision_request_owner_is_governor() -> None:
    data = sample("decision_request")
    data["owner"] = "orchestrator"
    rejects(data)


# --- Run events ---------------------------------------------------------------------


def test_release_reason_enum() -> None:
    data = sample("release")
    data["reason"] = "finished"
    rejects(data)


def test_run_complete_counts_non_negative() -> None:
    data = sample("run_complete")
    data["governor_interrupts"] = -1
    rejects(data)


# --- id patterns --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "good", "bad"),
    [
        ("order", "wo-20261005-red-first-gate", "wo-2026105-red-first-gate"),
        ("order", "wo-20261005-x", "WO-20261005-x"),
        ("order", "wo-20261231-a1-b2", "wo-20261399-bad-date"),
        ("amendment", "wo-20261005-red-first-gate.amend-01", "wo-20261005-red-first-gate.amend-1"),
        ("verdict", "wo-20261005-red-first-gate.verdict-02", "wo-20261005-red-first-gate.verdict"),
        ("override", "wo-20261005-red-first-gate.override-10", "wo-20261005-red-first-gate.ovr-10"),
        ("correction", "corr-20261005-thin-substitute", "corr-2026-10-05-thin"),
        ("handoff", "wo-20261005-red-first-gate.handoff", "wo-20261005-red-first-gate.handoff-01"),
        ("claim", "wo-20261005-red-first-gate.claim", "red-first-gate.claim"),
        ("release", "wo-20261005-red-first-gate.release", "wo-20261005-red-first-gate.released"),
        (
            "run_complete",
            "wo-20261005-red-first-gate.run-complete",
            "wo-20261005-red-first-gate.run_complete",
        ),
        ("decision_lock", "board-web-view.lock", "board-web-view"),
    ],
)
def test_id_patterns(kind: str, good: str, bad: str) -> None:
    data = sample(kind)
    data["id"] = good
    assert parse_message(data).id == good
    data["id"] = bad
    assert "id" in rejects(data)
