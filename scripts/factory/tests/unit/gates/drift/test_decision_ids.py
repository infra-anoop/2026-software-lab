"""T039 — `decision-request-no-ids` (T047; FR-017; I-B3).

Regexes verbatim from contracts/messages.md (`\\b[TFRPD]\\d+\\b`, `FR-\\d+`, `SC-\\d+`,
`US\\d+`, `§`) plus `factory.toml [decision_lint].jargon`, applied to `prompt` and
`options[].label` of decision requests the change adds. The seeds in `tests/seeds`
cover each regex, each configured term, case, and near misses; this file covers
field scoping, change scoping, and reporting.
"""

from __future__ import annotations

from typing import Any

from factory.api import GateContext
from tests.fixtures.repo_builder import RepoBuilder, message, yaml_text
from tests.unit.gates.drift.helpers import assert_blocks, assert_passes

GATE = "decision-request-no-ids"
PLAIN_PROMPT = "Which host should the demo use on Friday?"
PLAIN_LABELS = ["Keep the current host", "Move to the cheaper host"]


def request(decision_id: str, **fields: Any) -> dict[str, Any]:
    fields.setdefault("prompt", PLAIN_PROMPT)
    labels = fields.pop("labels", PLAIN_LABELS)
    fields.setdefault("options", [{"label": label} for label in labels])
    fields.setdefault("recommended", labels[0])
    fields.setdefault("arch_impact", False)
    return message("decision_request", decision_id=decision_id, **fields)


def request_path(decision_id: str) -> str:
    return f"bus/decisions/{decision_id}/request.yaml"


def decision_ctx(
    repo: RepoBuilder,
    head: dict[str, dict[str, Any]],
    base: dict[str, dict[str, Any]] | None = None,
) -> GateContext:
    pair = repo.base_head_pair(
        {request_path(k): yaml_text(v) for k, v in (base or {}).items()},
        {request_path(k): yaml_text(v) for k, v in head.items()},
    )
    return repo.gate_context(pair)


def test_plain_request_passes(repo: RepoBuilder) -> None:
    assert_passes(GATE, decision_ctx(repo, {"pick-host": request("pick-host")}))


def test_ids_outside_prompt_and_labels_pass(repo: RepoBuilder) -> None:
    """`refs`, `feature`, and option consequences are not governor-facing prose."""
    data = request(
        "pick-host",
        feature="001-factory-v2",
        refs=["T047", "FR-017", "specs/001-factory-v2/spec.md"],
        labels=PLAIN_LABELS,
        options=[
            {"label": PLAIN_LABELS[0]},
            {
                "label": PLAIN_LABELS[1],
                "consequences": {"ops_steps": ["run T065 setup"], "services": ["US3 host"]},
            },
        ],
    )
    assert_passes(GATE, decision_ctx(repo, {"pick-host": data}))


def test_blocks_and_names_every_offender(repo: RepoBuilder) -> None:
    data = request(
        "pick-host",
        prompt="Should the worktree layout change before the demo on Friday?",
        labels=["Keep it", "Adopt SC-002 wording"],
    )
    assert_blocks(GATE, decision_ctx(repo, {"pick-host": data}), "worktree", "SC-002")


def test_blocks_names_the_offending_request_file(repo: RepoBuilder) -> None:
    data = request("pick-host", prompt="Is T042 ready for the demo on Friday?")
    assert_blocks(GATE, decision_ctx(repo, {"pick-host": data}), request_path("pick-host"))


def test_only_requests_added_by_the_change_are_judged(repo: RepoBuilder) -> None:
    """Changed scope: a legacy request on the base is not this change's violation."""
    legacy = request("old-question", prompt="Is T042 ready for the demo on Friday?")
    ctx = decision_ctx(repo, {"pick-host": request("pick-host")}, base={"old-question": legacy})
    assert_passes(GATE, ctx)


def test_one_bad_request_among_clean_ones_blocks(repo: RepoBuilder) -> None:
    bad = request("web-view", prompt="Does the board need a web view for US1 this week?")
    ctx = decision_ctx(repo, {"pick-host": request("pick-host"), "web-view": bad})
    assert_blocks(GATE, ctx, request_path("web-view"))
