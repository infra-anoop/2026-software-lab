"""`branch-protection-require-pr` (governor-only, irreversible; I-P10, T066).

`deploy/github/branch-protection.json` is the GitHub REST "get branch protection" body for
`main`. At head it must require a pull request, enforce it for admins with no bypass
allowances, require code-owner review, and require a `factory/<gate-id>` status for every
P1 CI gate in the head registry. A live drift check is P3 (sprint 03, D1).
"""

from __future__ import annotations

import json
from typing import Any

from factory.api import GateContext, GateResult
from factory.gates.repo._git import failed, outcome, show
from factory.gates.repo.fail_mode import head_registry

GATE_ID = "branch-protection-require-pr"
SNAPSHOT_FILE = "deploy/github/branch-protection.json"
BYPASS_KINDS = {"users": "login", "teams": "slug", "apps": "slug"}


def _enabled(body: dict[str, Any], key: str) -> bool:
    value = body.get(key)
    return bool(value.get("enabled")) if isinstance(value, dict) else bool(value)


def _required_contexts(body: dict[str, Any]) -> set[str]:
    checks = body.get("required_status_checks")
    if not isinstance(checks, dict):
        return set()
    contexts = {c for c in checks.get("contexts") or [] if isinstance(c, str)}
    contexts |= {
        c["context"] for c in checks.get("checks") or [] if isinstance(c, dict) and "context" in c
    }
    return contexts


def _bypass_names(reviews: dict[str, Any]) -> list[str]:
    allowances = reviews.get("bypass_pull_request_allowances") or {}
    names = []
    for kind, key in BYPASS_KINDS.items():
        for actor in allowances.get(kind) or []:
            label = actor.get(key) or actor.get("name") if isinstance(actor, dict) else actor
            names.append(f"{kind[:-1]} {label}")
    return names


def snapshot_problems(body: Any, required: list[str]) -> list[str]:
    if not isinstance(body, dict):
        return [f"{SNAPSHOT_FILE}: expected a JSON object"]
    problems = []
    reviews = body.get("required_pull_request_reviews")
    if not isinstance(reviews, dict):
        problems.append(f"{SNAPSHOT_FILE}: main does not require a pull request before merging")
    else:
        bypass = _bypass_names(reviews)
        if bypass:
            problems.append(f"{SNAPSHOT_FILE}: PR bypass allowed for {', '.join(bypass)}")
        if reviews.get("require_code_owner_reviews") is not True:
            problems.append(f"{SNAPSHOT_FILE}: code-owner review is not required")
    if not _enabled(body, "enforce_admins"):
        problems.append(f"{SNAPSHOT_FILE}: admins can bypass the PR rule (enforce_admins off)")
    for key in ("allow_force_pushes", "allow_deletions"):
        if key in body and _enabled(body, key):
            problems.append(f"{SNAPSHOT_FILE}: {key} is enabled on main")
    missing = [c for c in required if c not in _required_contexts(body)]
    if missing:
        problems.append(f"{SNAPSHOT_FILE}: required status checks miss {', '.join(missing)}")
    return problems


def run(ctx: GateContext) -> GateResult:
    gates, registry_problems = head_registry(ctx)
    if not gates:
        return failed(GATE_ID, registry_problems)
    text = show(ctx.repo_path, ctx.head_sha, SNAPSHOT_FILE)
    if text is None:
        return failed(GATE_ID, [f"{SNAPSHOT_FILE}: not found at head (T066 snapshot)"])
    try:
        body: Any = json.loads(text)
    except ValueError as exc:
        return failed(GATE_ID, [f"{SNAPSHOT_FILE}: unreadable JSON ({exc})"])
    required = [
        f"factory/{gate.id}"
        for gate in gates
        if gate.priority == "P1" and gate.hook_twin_of is None
    ]
    return outcome(GATE_ID, snapshot_problems(body, required), "main requires a PR with no bypass")
