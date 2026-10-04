"""T052 — `verdict.reviewer-family-differs`, `verdict.inputs-isolated`, `message.override`.

Verdict gates judge the order's latest verdict (highest `verdict-NN`) at head
(FR-011, FR-011a, I-P3): the reviewer family is derived from `reviewer_model` through
`factory.toml [families]` and must equal the declared `reviewer_family` and differ from
the family of the handoff's `author_model`; every input must be a path that exists in
git at its sha. A PR with no verdict (or no handoff) is not reviewed and is blocked.

`message.override` (governor-only, I-M1/I-P9) checks the override messages this PR adds:
the gate is registered, `gate_class` equals the registry class, a governor-only gate is
overridden only by `actor: governor`, and `pr` matches the PR being checked.
"""

from __future__ import annotations

from typing import Any

from factory.api import GateContext
from tests.fixtures.repo_builder import RepoBuilder, message, yaml_text
from tests.unit.gates.pr.helpers import (
    ORDER_DIR,
    ORDER_ID,
    assert_blocks,
    assert_passes,
    oid,
    order_for,
)

FAMILY = "verdict.reviewer-family-differs"
ISOLATED = "verdict.inputs-isolated"
OVERRIDE = "message.override"
AUTHOR = "claude-opus-5.5"
PR = 7


def verdict(nn: int, base_sha: str, **fields: Any) -> dict[str, Any]:
    fields.setdefault("inputs", [{"path": "README.md", "sha": base_sha}])
    data = message("verdict", order_id=ORDER_ID, **fields)
    data["id"] = f"{ORDER_ID}.verdict-{nn:02d}"
    return data


def reviewed_pr(
    repo: RepoBuilder,
    verdicts: list[dict[str, Any]] | None = None,
    *,
    handoff: bool = True,
) -> GateContext:
    files: dict[str, str | None] = {f"{ORDER_DIR}/order.yaml": yaml_text(order_for(ORDER_ID))}
    if handoff:
        data = message("handoff", order_id=ORDER_ID, author_model=AUTHOR, actor_model=AUTHOR)
        files[f"{ORDER_DIR}/handoff.yaml"] = yaml_text(data)
    for data in verdicts or []:
        suffix = data["id"].split(".", 1)[1]
        files[f"{ORDER_DIR}/{suffix}.yaml"] = yaml_text(data)
    pair = repo.base_head_pair({}, files, head_branch=f"wo/{ORDER_ID}")
    return repo.gate_context(pair, pr_number=PR, order_id=ORDER_ID)


def main_sha(repo: RepoBuilder) -> str:
    return repo.head_sha("main")


# --- verdict.reviewer-family-differs ------------------------------------------------------


def test_family_passes_for_other_family_reviewer(repo: RepoBuilder) -> None:
    ctx = reviewed_pr(repo, [verdict(1, main_sha(repo))])
    assert_passes(FAMILY, ctx)


def test_family_blocks_same_family_reviewer(repo: RepoBuilder) -> None:
    same = verdict(
        1,
        main_sha(repo),
        actor_model="claude-sonnet-5",
        reviewer_model="claude-sonnet-5",
        reviewer_family="anthropic",
    )
    assert_blocks(FAMILY, reviewed_pr(repo, [same]), "anthropic")


def test_family_blocks_mislabelled_family(repo: RepoBuilder) -> None:
    """The family comes from the model name, not from the reviewer's own label."""
    mislabelled = verdict(
        1,
        main_sha(repo),
        actor_model="claude-sonnet-5",
        reviewer_model="claude-sonnet-5",
        reviewer_family="openai",
    )
    assert_blocks(FAMILY, reviewed_pr(repo, [mislabelled]), "claude-sonnet-5")


def test_family_blocks_unknown_reviewer_family(repo: RepoBuilder) -> None:
    unknown = verdict(
        1, main_sha(repo), actor_model="llama-4", reviewer_model="llama-4", reviewer_family="meta"
    )
    assert_blocks(FAMILY, reviewed_pr(repo, [unknown]), "llama-4")


def test_family_blocks_pr_without_verdict(repo: RepoBuilder) -> None:
    assert_blocks(FAMILY, reviewed_pr(repo, []), ORDER_ID)


def test_family_blocks_pr_without_handoff(repo: RepoBuilder) -> None:
    ctx = reviewed_pr(repo, [verdict(1, main_sha(repo))], handoff=False)
    assert_blocks(FAMILY, ctx, ORDER_ID)


def test_family_judges_latest_verdict(repo: RepoBuilder) -> None:
    sha = main_sha(repo)
    same = verdict(
        1,
        sha,
        actor_model="claude-sonnet-5",
        reviewer_model="claude-sonnet-5",
        reviewer_family="anthropic",
    )
    assert_passes(FAMILY, reviewed_pr(repo, [same, verdict(2, sha)]))


# --- verdict.inputs-isolated --------------------------------------------------------------


def test_isolated_passes_for_git_paths_at_sha(repo: RepoBuilder) -> None:
    sha = main_sha(repo)
    inputs = [{"path": "README.md", "sha": sha}, {"path": "factory.toml", "sha": sha}]
    assert_passes(ISOLATED, reviewed_pr(repo, [verdict(1, sha, inputs=inputs)]))


def test_isolated_blocks_path_missing_at_sha(repo: RepoBuilder) -> None:
    sha = main_sha(repo)
    inputs = [{"path": "notes/chat-transcript-2026-10-06.md", "sha": sha}]
    ctx = reviewed_pr(repo, [verdict(1, sha, inputs=inputs)])
    assert_blocks(ISOLATED, ctx, "notes/chat-transcript-2026-10-06.md")


def test_isolated_blocks_sha_not_in_repo(repo: RepoBuilder) -> None:
    inputs = [{"path": "README.md", "sha": "0123456789abcdef0123456789abcdef01234567"}]
    ctx = reviewed_pr(repo, [verdict(1, main_sha(repo), inputs=inputs)])
    assert_blocks(ISOLATED, ctx, "0123456789abcdef0123456789abcdef01234567")


def test_isolated_blocks_pr_without_verdict(repo: RepoBuilder) -> None:
    assert_blocks(ISOLATED, reviewed_pr(repo, []), ORDER_ID)


# --- message.override ---------------------------------------------------------------------


def override(nn: int, **fields: Any) -> dict[str, Any]:
    fields.setdefault("pr", PR)
    data = message("override", order_id=ORDER_ID, **fields)
    data["id"] = f"{ORDER_ID}.override-{nn:02d}"
    return data


def overridden_pr(
    repo: RepoBuilder, overrides: list[dict[str, Any]], base_files: dict[str, str] | None = None
) -> GateContext:
    files: dict[str, str | None] = {f"{ORDER_DIR}/order.yaml": yaml_text(order_for(ORDER_ID))}
    for data in overrides:
        suffix = data["id"].split(".", 1)[1]
        files[f"{ORDER_DIR}/{suffix}.yaml"] = yaml_text(data)
    pair = repo.base_head_pair(base_files or {}, files, head_branch=f"wo/{ORDER_ID}")
    return repo.gate_context(pair, pr_number=PR, order_id=ORDER_ID)


def test_override_msg_passes_without_overrides(repo: RepoBuilder) -> None:
    assert_passes(OVERRIDE, overridden_pr(repo, []))


def test_override_msg_passes_for_reasoned_drift_override(repo: RepoBuilder) -> None:
    assert_passes(OVERRIDE, overridden_pr(repo, [override(1)]))


def test_override_msg_passes_for_governor_override_of_governor_only_gate(
    repo: RepoBuilder,
) -> None:
    data = override(
        1, gate="order-blocked-on-open-human-od", gate_class="governor-only", actor="governor"
    )
    data.pop("actor_model", None)
    assert_passes(OVERRIDE, overridden_pr(repo, [data]))


def test_override_msg_blocks_unregistered_gate(repo: RepoBuilder) -> None:
    ctx = overridden_pr(repo, [override(1, gate="no-such-gate")])
    assert_blocks(OVERRIDE, ctx, "no-such-gate")


def test_override_msg_blocks_class_that_disagrees_with_registry(repo: RepoBuilder) -> None:
    """An orchestrator cannot dodge the governor-only rule by labelling the gate drift."""
    data = override(1, gate="order-blocked-on-open-human-od", gate_class="drift")
    ctx = overridden_pr(repo, [data])
    assert_blocks(OVERRIDE, ctx, "order-blocked-on-open-human-od", "governor-only")


def test_override_msg_blocks_override_for_another_pr(repo: RepoBuilder) -> None:
    ctx = overridden_pr(repo, [override(1, pr=42)])
    assert_blocks(OVERRIDE, ctx, "42")


def test_override_msg_ignores_overrides_already_on_base(repo: RepoBuilder) -> None:
    other = oid("merged-earlier")
    old = message("override", order_id=other, pr=3, gate="no-such-gate")
    base = {
        f"bus/orders/{other}/order.yaml": yaml_text(order_for(other)),
        f"bus/orders/{other}/override-01.yaml": yaml_text(old),
    }
    assert_passes(OVERRIDE, overridden_pr(repo, [], base_files=base))
