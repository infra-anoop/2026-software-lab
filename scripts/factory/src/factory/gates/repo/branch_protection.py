"""`branch-protection-require-pr` (governor-only, irreversible; I-P10, T066/T101).

`deploy/github/branch-protection.json` is the GitHub REST "get a repository ruleset" body
for the ruleset protecting `main` (governor 2026-10-06: a repository ruleset, not classic
branch protection). At head it must be an active branch ruleset that applies to `main`
(`refs/heads/main`, `~DEFAULT_BRANCH` or `~ALL`, and not excluded), with no bypass actors
and the rules `pull_request`, `required_status_checks`, `non_fast_forward` and `deletion`.
The required checks hold a `factory/<gate-id>` context for every P1 CI gate in the head
registry, and every entry is pinned to the GitHub Actions app (`integration_id` equal to
typed config `github.actions_app_id`), so no other identity can satisfy it (P9).

Code-owner review is required only once `identity.mode` is `verified` (T065): until the
factory's App authors PRs, they are the governor's own and GitHub does not let an author
approve their own PR. A live drift check is P3 (sprint 03, D1).
"""

from __future__ import annotations

import json
from typing import Any

from factory.api import GateContext, GateResult
from factory.gates.repo._git import failed, outcome, show
from factory.gates.repo.fail_mode import head_registry

GATE_ID = "branch-protection-require-pr"
SNAPSHOT_FILE = "deploy/github/branch-protection.json"
MAIN_REF = "refs/heads/main"
# Ruleset ref patterns that select `main`: `main` is this repository's default branch, and
# the live ruleset uses `~DEFAULT_BRANCH`.
INCLUDES_MAIN = {MAIN_REF, "~DEFAULT_BRANCH", "~ALL"}
EXCLUDES_MAIN = {MAIN_REF, "~DEFAULT_BRANCH"}
BRANCH_RULES = {
    "non_fast_forward": "force pushes to main are not blocked",
    "deletion": "deleting main is not blocked",
}


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _rules(body: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Rule type -> its `parameters` (`{}` for rules that take none)."""
    rules: dict[str, dict[str, Any]] = {}
    for rule in body.get("rules") or []:
        if isinstance(rule, dict) and isinstance(rule.get("type"), str):
            rules[rule["type"]] = _mapping(rule.get("parameters"))
    return rules


def _targets_main(body: dict[str, Any]) -> bool:
    ref_name = _mapping(_mapping(body.get("conditions")).get("ref_name"))
    include = set(ref_name.get("include") or [])
    exclude = set(ref_name.get("exclude") or [])
    return bool(include & INCLUDES_MAIN) and not exclude & EXCLUDES_MAIN


def _required_contexts(parameters: dict[str, Any]) -> dict[str, set[object]]:
    """Required context -> the source integration ids named for it (`None`: any source)."""
    sources: dict[str, set[object]] = {}
    for check in parameters.get("required_status_checks") or []:
        if isinstance(check, dict) and isinstance(check.get("context"), str):
            sources.setdefault(check["context"], set()).add(check.get("integration_id"))
    return sources


def _bypass_names(body: dict[str, Any]) -> list[str]:
    return [
        f"{actor.get('actor_type')} {actor.get('actor_id')}"
        if isinstance(actor, dict)
        else str(actor)
        for actor in body.get("bypass_actors") or []
    ]


def snapshot_problems(
    body: Any, required: list[str], actions_app_id: int, *, code_owner_review: bool
) -> list[str]:
    if not isinstance(body, dict):
        return [f"{SNAPSHOT_FILE}: expected a JSON object"]
    problems = []
    if body.get("target") != "branch":
        problems.append(f"{SNAPSHOT_FILE}: not a branch ruleset (target {body.get('target')!r})")
    if body.get("enforcement") != "active":
        problems.append(
            f"{SNAPSHOT_FILE}: ruleset is not enforced (enforcement {body.get('enforcement')!r})"
        )
    if not _targets_main(body):
        problems.append(f"{SNAPSHOT_FILE}: ruleset does not apply to {MAIN_REF}")
    bypass = _bypass_names(body)
    if bypass:
        problems.append(f"{SNAPSHOT_FILE}: ruleset bypass allowed for {', '.join(bypass)}")
    rules = _rules(body)
    if "pull_request" not in rules:
        problems.append(f"{SNAPSHOT_FILE}: main does not require a pull request before merging")
    elif code_owner_review and rules["pull_request"].get("require_code_owner_review") is not True:
        problems.append(f"{SNAPSHOT_FILE}: code-owner review is not required")
    for rule_type, problem in BRANCH_RULES.items():
        if rule_type not in rules:
            problems.append(f"{SNAPSHOT_FILE}: {problem} (no {rule_type} rule)")
    sources = _required_contexts(rules.get("required_status_checks", {}))
    missing = [c for c in required if c not in sources]
    if missing:
        problems.append(f"{SNAPSHOT_FILE}: required status checks miss {', '.join(missing)}")
    unpinned = [c for c in sorted(sources) if sources[c] != {actions_app_id}]
    if unpinned:
        problems.append(
            f"{SNAPSHOT_FILE}: required status checks not pinned to the GitHub Actions app "
            f"(integration_id {actions_app_id}): {', '.join(unpinned)}"
        )
    return problems


def run(ctx: GateContext) -> GateResult:
    gates, registry_problems = head_registry(ctx)
    if not gates:
        return failed(GATE_ID, registry_problems)
    text = show(ctx.repo_path, ctx.head_sha, SNAPSHOT_FILE)
    if text is None:
        return failed(GATE_ID, [f"{SNAPSHOT_FILE}: not found at head (T101 snapshot)"])
    try:
        body: Any = json.loads(text)
    except ValueError as exc:
        return failed(GATE_ID, [f"{SNAPSHOT_FILE}: unreadable JSON ({exc})"])
    required = [
        f"factory/{gate.id}"
        for gate in gates
        if gate.priority == "P1" and gate.hook_twin_of is None
    ]
    problems = snapshot_problems(
        body,
        required,
        ctx.config.github.actions_app_id,
        code_owner_review=ctx.config.identity.mode == "verified",
    )
    return outcome(GATE_ID, problems, "main requires a PR with no bypass")
