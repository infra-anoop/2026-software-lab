"""T051 — registry and repo gates: `gate.fail-mode-category`, `hook-has-ci-twin`,
`branch-protection-require-pr`, and the wrapped existing lab checks (T059).

Repo gates read their inputs from the head commit: the registry at
`scripts/factory/gates.yaml` and the hooks at `.cursor/hooks.json`. The head registry is
the source of truth: when it is missing or unreadable the gate blocks and names the path
(no fallback to the installed registry — T* round 1, T-C2).

Hook twins (contracts/hooks.md): each hook in `.cursor/hooks.json` is a factory hook
command (`.cursor/hooks/factory-hook.sh <name>`, amendment A1), and the registry has a
row `id: <name>` whose `hook_twin_of` names an existing CI gate (a row that is not itself
a hook row).

Branch protection (I-P10, T066/T101): `deploy/github/branch-protection.json` is the GitHub
REST "get a repository ruleset" body for the ruleset protecting `main` (governor
2026-10-06: a repository ruleset, not classic branch protection). It must be an active
branch ruleset applying to `main` (`~DEFAULT_BRANCH`, as live, or `refs/heads/main`) with
an empty bypass list and the rules
`pull_request`, `required_status_checks`, `non_fast_forward` and `deletion`. The required
checks hold the summary context `factory/gates` (T107, governor 2026-10-06, `PLAN_DELTA.md`
Round 5), not one `factory/<gate-id>` context per P1 CI gate, and every
entry has `integration_id` equal to typed config `github.actions_app_id`, the GitHub
Actions integration (delta P* P9, T094): an entry without a source, with `-1` (any source)
or with another app's id fails. Code-owner review is required only once `identity.mode` is
`verified` (T065: the factory's App authors PRs, so the governor can approve them).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from factory.api import GateContext
from factory.cli import exit_codes
from factory.config.settings import GitHubConfig
from factory.gates.registry import REGISTRY_PATH
from tests.fixtures.cli_runner import FactoryCli
from tests.fixtures.repo_builder import LAB_VALIDATORS, REPO_ROOT, RepoBuilder
from tests.unit.gates.pr.helpers import assert_blocks, assert_passes, raw_context

REGISTRY = "scripts/factory/gates.yaml"
HOOKS = ".cursor/hooks.json"
SNAPSHOT = "deploy/github/branch-protection.json"
IMPORTABLE = "factory.api:run_gate"


def row(gate_id: str, **fields: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": gate_id,
        "class": "drift",
        "category": "drift",
        "intents": ["I-G5"],
        "ci_job": "factory-gates",
        "priority": "P1",
        "scope": "repo",
        "entrypoint": IMPORTABLE,
    }
    data.update(fields)
    return {key: value for key, value in data.items() if value is not None}


def registry_text(*rows: dict[str, Any]) -> str:
    return yaml.safe_dump({"schema_version": 1, "gates": list(rows)}, sort_keys=False)


def hooks_text(**events: list[str]) -> str:
    hooks = {
        event: [{"command": command} for command in commands] for event, commands in events.items()
    }
    return json.dumps({"version": 1, "hooks": hooks}, indent=2)


def factory_hook(name: str) -> str:
    return f".cursor/hooks/factory-hook.sh {name}"


CI_GATE = row(
    "branch-protection-require-pr", **{"class": "governor-only", "category": "irreversible"}
)
SHELL_GUARD = row("shell-guard", hook_twin_of="branch-protection-require-pr", scope="changed_lines")


def drop_from_main(repo: RepoBuilder, *paths: str) -> None:
    """Remove lab inputs the fixture plants by default, for tests of their absence."""
    repo.checkout("main")
    for path in paths:
        repo.delete(path)
    repo.commit("drop lab inputs")
    repo.push("main")


def head_with(repo: RepoBuilder, files: dict[str, str | None]) -> GateContext:
    pair = repo.base_head_pair({}, files)
    return raw_context(repo, pair)


# --- gate.fail-mode-category --------------------------------------------------------------


def test_fail_mode_passes_on_valid_registry(repo: RepoBuilder) -> None:
    ctx = head_with(repo, {REGISTRY: registry_text(CI_GATE, SHELL_GUARD)})
    assert_passes("gate.fail-mode-category", ctx)


@pytest.mark.parametrize(
    ("gate_class", "category"),
    [("governor-only", "drift"), ("drift", "secrets"), ("drift", "spend"), ("advisory", "drift")],
)
def test_fail_mode_blocks_class_category_mismatch(
    repo: RepoBuilder, gate_class: str, category: str
) -> None:
    bad = row("bad-gate", **{"class": gate_class, "category": category})
    ctx = head_with(repo, {REGISTRY: registry_text(CI_GATE, bad)})
    assert_blocks("gate.fail-mode-category", ctx, "bad-gate")


def test_fail_mode_blocks_missing_head_registry(repo: RepoBuilder) -> None:
    drop_from_main(repo, REGISTRY)
    ctx = head_with(repo, {"README.md": "# edited\n"})
    assert_blocks("gate.fail-mode-category", ctx, REGISTRY)


def test_fail_mode_blocks_registry_deleted_at_head(repo: RepoBuilder) -> None:
    pair = repo.base_head_pair({REGISTRY: registry_text(CI_GATE)}, {REGISTRY: None})
    assert_blocks("gate.fail-mode-category", raw_context(repo, pair), REGISTRY)


def test_fail_mode_blocks_unreadable_head_registry(repo: RepoBuilder) -> None:
    ctx = head_with(repo, {REGISTRY: "schema_version: 1\ngates: [unclosed\n"})
    assert_blocks("gate.fail-mode-category", ctx, REGISTRY)


def test_check_registry_cli_fails_without_registry(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    drop_from_main(repo, REGISTRY)
    result = factory_cli("check", "registry", repo=repo.path)
    assert result.exit_code == exit_codes.GATE_FAILURE, result
    assert REGISTRY in result.stdout + result.stderr


def test_check_registry_cli_fails_on_disallowed_category(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    repo.write(REGISTRY, registry_text(row("bad-gate", **{"class": "governor-only"})))
    result = factory_cli("check", "registry", repo=repo.path)
    assert result.exit_code == exit_codes.GATE_FAILURE, result
    assert "bad-gate" in result.stdout + result.stderr


def test_check_registry_cli_fails_on_unimportable_entrypoint(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    repo.write(REGISTRY, registry_text(row("ghost", entrypoint="factory.gates.nowhere:run")))
    result = factory_cli("check", "registry", repo=repo.path)
    assert result.exit_code == exit_codes.GATE_FAILURE, result
    assert "factory.gates.nowhere:run" in result.stdout + result.stderr


def test_check_registry_cli_passes_on_valid_fixture_registry(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    repo.write(REGISTRY, registry_text(CI_GATE, SHELL_GUARD))
    result = factory_cli("check", "registry", repo=repo.path)
    assert result.exit_code == exit_codes.OK, result


# --- hook-has-ci-twin ---------------------------------------------------------------------


def test_hook_twin_passes_when_every_hook_is_twinned(repo: RepoBuilder) -> None:
    spawn = row("spawn-guard", hook_twin_of="spawn-concurrency-cap")
    cap = row("spawn-concurrency-cap", scope="pr")
    files: dict[str, str | None] = {
        REGISTRY: registry_text(CI_GATE, SHELL_GUARD, cap, spawn),
        HOOKS: hooks_text(
            beforeShellExecution=[factory_hook("shell-guard")],
            subagentStart=[factory_hook("spawn-guard")],
        ),
    }
    assert_passes("hook-has-ci-twin", head_with(repo, files))


def test_hook_twin_passes_without_hooks_file(repo: RepoBuilder) -> None:
    ctx = head_with(repo, {REGISTRY: registry_text(CI_GATE)})
    assert_passes("hook-has-ci-twin", ctx)


def test_hook_twin_blocks_hook_without_registry_row(repo: RepoBuilder) -> None:
    files: dict[str, str | None] = {
        REGISTRY: registry_text(CI_GATE, SHELL_GUARD),
        HOOKS: hooks_text(
            beforeShellExecution=[factory_hook("shell-guard")],
            postToolUse=[factory_hook("owned-path-warn")],
        ),
    }
    assert_blocks("hook-has-ci-twin", head_with(repo, files), "owned-path-warn")


def test_hook_twin_blocks_row_without_twin(repo: RepoBuilder) -> None:
    files: dict[str, str | None] = {
        REGISTRY: registry_text(CI_GATE, row("shell-guard")),
        HOOKS: hooks_text(beforeShellExecution=[factory_hook("shell-guard")]),
    }
    assert_blocks("hook-has-ci-twin", head_with(repo, files), "shell-guard")


def test_hook_twin_blocks_twin_that_is_not_registered(repo: RepoBuilder) -> None:
    files: dict[str, str | None] = {
        REGISTRY: registry_text(row("shell-guard", hook_twin_of="no-such-ci-gate")),
        HOOKS: hooks_text(beforeShellExecution=[factory_hook("shell-guard")]),
    }
    assert_blocks("hook-has-ci-twin", head_with(repo, files), "no-such-ci-gate")


def test_hook_twin_blocks_twin_that_is_another_hook(repo: RepoBuilder) -> None:
    owned = row("owned-path-warn", hook_twin_of="shell-guard")
    files: dict[str, str | None] = {
        REGISTRY: registry_text(CI_GATE, SHELL_GUARD, owned),
        HOOKS: hooks_text(
            beforeShellExecution=[factory_hook("shell-guard")],
            postToolUse=[factory_hook("owned-path-warn")],
        ),
    }
    assert_blocks("hook-has-ci-twin", head_with(repo, files), "owned-path-warn")


def test_hook_twin_blocks_hook_that_is_not_a_factory_hook(repo: RepoBuilder) -> None:
    files: dict[str, str | None] = {
        REGISTRY: registry_text(CI_GATE, SHELL_GUARD),
        HOOKS: hooks_text(afterFileEdit=[".cursor/hooks/format.sh"]),
    }
    assert_blocks("hook-has-ci-twin", head_with(repo, files), ".cursor/hooks/format.sh")


def test_hook_twin_blocks_hooks_without_head_registry(repo: RepoBuilder) -> None:
    drop_from_main(repo, REGISTRY)
    files: dict[str, str | None] = {
        HOOKS: hooks_text(beforeShellExecution=[factory_hook("shell-guard")]),
    }
    assert_blocks("hook-has-ci-twin", head_with(repo, files), REGISTRY)


def test_hook_twin_blocks_unreadable_hooks_file(repo: RepoBuilder) -> None:
    files: dict[str, str | None] = {REGISTRY: registry_text(CI_GATE), HOOKS: "{not json"}
    assert_blocks("hook-has-ci-twin", head_with(repo, files), HOOKS)


def test_check_hooks_cli_fails_on_untwinned_hook(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    repo.write(REGISTRY, registry_text(CI_GATE))
    repo.write(HOOKS, hooks_text(stop=[factory_hook("decision-in-chat")]))
    result = factory_cli("check", "hooks", repo=repo.path)
    assert result.exit_code == exit_codes.GATE_FAILURE, result
    assert "decision-in-chat" in result.stdout + result.stderr


def test_check_hooks_cli_passes_on_twinned_hook(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    repo.write(REGISTRY, registry_text(CI_GATE, SHELL_GUARD))
    repo.write(HOOKS, hooks_text(beforeShellExecution=[factory_hook("shell-guard")]))
    result = factory_cli("check", "hooks", repo=repo.path)
    assert result.exit_code == exit_codes.OK, result


# --- branch-protection-require-pr ---------------------------------------------------------


SUMMARY = "factory/gates"


def required_contexts() -> list[str]:
    """The T107 target: the two workflow checks and the one `factory/gates` summary."""
    return ["Factory tests", "Verify Source / verify", SUMMARY]


def actions_app_id() -> int:
    """Typed config `github.actions_app_id`: the GitHub Actions integration (P9)."""
    configured = getattr(GitHubConfig(repository="fixture/demo"), "actions_app_id", None)
    assert isinstance(configured, int), "typed config `github.actions_app_id` is missing"
    return configured


def pinned(contexts: list[str], integration_id: int | None = None) -> dict[str, Any]:
    """The `required_status_checks` rule, every context pinned to one source app (P9)."""
    source = actions_app_id() if integration_id is None else integration_id
    return {
        "type": "required_status_checks",
        "parameters": {
            "strict_required_status_checks_policy": False,
            "do_not_enforce_on_create": False,
            "required_status_checks": [{"context": c, "integration_id": source} for c in contexts],
        },
    }


def pull_request_rule(*, code_owner_review: bool = False) -> dict[str, Any]:
    return {
        "type": "pull_request",
        "parameters": {
            "required_approving_review_count": 0,
            "dismiss_stale_reviews_on_push": False,
            "required_reviewers": [],
            "require_code_owner_review": code_owner_review,
            "require_last_push_approval": False,
            "required_review_thread_resolution": False,
            "require_extra_approval_for_unattributed_changes": False,
        },
    }


def snapshot(**changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "name": "main-protection",
        "target": "branch",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
        "bypass_actors": [],
        "rules": [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            pull_request_rule(),
            pinned(required_contexts()),
        ],
    }
    body.update(changes)
    return body


def without_rule(body: dict[str, Any], rule_type: str) -> dict[str, Any]:
    body["rules"] = [rule for rule in body["rules"] if rule["type"] != rule_type]
    return body


def with_rule(body: dict[str, Any], replacement: dict[str, Any]) -> dict[str, Any]:
    body["rules"] = [
        replacement if rule["type"] == replacement["type"] else rule for rule in body["rules"]
    ]
    return body


def required_checks(body: dict[str, Any]) -> list[dict[str, Any]]:
    for rule in body["rules"]:
        if rule["type"] == "required_status_checks":
            checks: list[dict[str, Any]] = rule["parameters"]["required_status_checks"]
            return checks
    raise AssertionError("no required_status_checks rule")


def protection_ctx(
    repo: RepoBuilder, body: dict[str, Any] | None, *, with_registry: bool = True
) -> GateContext:
    """Head carries the real registry, so the required P1 set is read from the head."""
    files: dict[str, str | None] = {"README.md": "# edited\n"}
    if with_registry:
        files[REGISTRY] = REGISTRY_PATH.read_text(encoding="utf-8")
    if body is not None:
        files[SNAPSHOT] = json.dumps(body, indent=2)
    return head_with(repo, files)


def test_branch_protection_passes_on_expected_ruleset(repo: RepoBuilder) -> None:
    """Recorded identity (before T065): code-owner review off still passes."""
    assert_passes("branch-protection-require-pr", protection_ctx(repo, snapshot()))


def test_branch_protection_passes_on_the_committed_snapshot(repo: RepoBuilder) -> None:
    committed = json.loads((REPO_ROOT / SNAPSHOT).read_text(encoding="utf-8"))
    assert_passes("branch-protection-require-pr", protection_ctx(repo, committed))


def test_branch_protection_blocks_without_head_registry(repo: RepoBuilder) -> None:
    drop_from_main(repo, REGISTRY)
    ctx = protection_ctx(repo, snapshot(), with_registry=False)
    assert_blocks("branch-protection-require-pr", ctx, REGISTRY)


def test_branch_protection_blocks_missing_snapshot(repo: RepoBuilder) -> None:
    drop_from_main(repo, SNAPSHOT)
    assert_blocks("branch-protection-require-pr", protection_ctx(repo, None), SNAPSHOT)


def test_branch_protection_blocks_when_pr_not_required(repo: RepoBuilder) -> None:
    body = without_rule(snapshot(), "pull_request")
    assert_blocks("branch-protection-require-pr", protection_ctx(repo, body), "pull request")


ADMIN_ROLE = {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}
AGENT_APP = {"actor_id": 424242, "actor_type": "Integration", "bypass_mode": "pull_request"}


def test_branch_protection_blocks_admin_bypass(repo: RepoBuilder) -> None:
    body = snapshot(bypass_actors=[ADMIN_ROLE])
    ctx = protection_ctx(repo, body)
    assert_blocks("branch-protection-require-pr", ctx, "RepositoryRole 5")


def test_branch_protection_blocks_bypass_allowance(repo: RepoBuilder) -> None:
    body = snapshot(bypass_actors=[AGENT_APP])
    ctx = protection_ctx(repo, body)
    assert_blocks("branch-protection-require-pr", ctx, "Integration 424242")


@pytest.mark.parametrize("rule_type", ["non_fast_forward", "deletion"])
def test_branch_protection_blocks_without_branch_rule(repo: RepoBuilder, rule_type: str) -> None:
    body = without_rule(snapshot(), rule_type)
    assert_blocks("branch-protection-require-pr", protection_ctx(repo, body), rule_type)


@pytest.mark.parametrize(
    ("label", "changes"),
    [
        ("another branch", {"conditions": {"ref_name": {"include": ["refs/heads/dev"]}}}),
        (
            "main excluded",
            {"conditions": {"ref_name": {"include": ["~ALL"], "exclude": ["refs/heads/main"]}}},
        ),
        (
            "default branch excluded",
            {"conditions": {"ref_name": {"include": ["~ALL"], "exclude": ["~DEFAULT_BRANCH"]}}},
        ),
        ("no conditions", {"conditions": None}),
        ("tag ruleset", {"target": "tag"}),
        ("evaluate only", {"enforcement": "evaluate"}),
        ("disabled", {"enforcement": "disabled"}),
    ],
)
def test_branch_protection_blocks_ruleset_not_enforced_on_main(
    repo: RepoBuilder, label: str, changes: dict[str, Any]
) -> None:
    assert_blocks("branch-protection-require-pr", protection_ctx(repo, snapshot(**changes)))


@pytest.mark.parametrize("include", ["refs/heads/main", "~DEFAULT_BRANCH", "~ALL"])
def test_branch_protection_passes_when_ruleset_includes_main(
    repo: RepoBuilder, include: str
) -> None:
    """`main` is this repo's default branch, so `~DEFAULT_BRANCH` (the live form) targets it."""
    body = snapshot(conditions={"ref_name": {"include": [include], "exclude": []}})
    assert_passes("branch-protection-require-pr", protection_ctx(repo, body))


def verified_repo(tmp_path: Path) -> RepoBuilder:
    """T065 done: the factory's App authors PRs and `identity.mode` is `verified`."""
    return RepoBuilder(tmp_path / "verified", identity_mode="verified")


def test_branch_protection_blocks_without_code_owner_review_once_identity_verified(
    tmp_path: Path,
) -> None:
    ctx = protection_ctx(verified_repo(tmp_path), snapshot())
    assert_blocks("branch-protection-require-pr", ctx, "code-owner review")


def test_branch_protection_passes_with_code_owner_review_once_identity_verified(
    tmp_path: Path,
) -> None:
    body = with_rule(snapshot(), pull_request_rule(code_owner_review=True))
    assert_passes("branch-protection-require-pr", protection_ctx(verified_repo(tmp_path), body))


def test_branch_protection_blocks_without_the_gates_summary_status(repo: RepoBuilder) -> None:
    contexts = [c for c in required_contexts() if c != SUMMARY]
    body = with_rule(snapshot(), pinned(contexts))
    ctx = protection_ctx(repo, body)
    assert_blocks("branch-protection-require-pr", ctx, SUMMARY)


# P9: every required context names the GitHub Actions integration as source.

UNPINNED = SUMMARY


def unpin(body: dict[str, Any], **check: Any) -> dict[str, Any]:
    for entry in required_checks(body):
        if entry["context"] == UNPINNED:
            entry.pop("integration_id")
            entry.update(check)
    return body


@pytest.mark.parametrize(
    ("label", "source"),
    [
        ("no integration_id", {}),
        ("any source", {"integration_id": -1}),
        ("null", {"integration_id": None}),
    ],
)
def test_branch_protection_blocks_factory_context_without_pinned_source(
    repo: RepoBuilder, label: str, source: dict[str, Any]
) -> None:
    body = unpin(snapshot(), **source)
    assert_blocks("branch-protection-require-pr", protection_ctx(repo, body), UNPINNED)


def test_branch_protection_blocks_factory_context_pinned_to_another_app(
    repo: RepoBuilder,
) -> None:
    body = unpin(snapshot(), integration_id=actions_app_id() + 1)
    assert_blocks("branch-protection-require-pr", protection_ctx(repo, body), UNPINNED)


def test_branch_protection_blocks_context_list_without_sources(repo: RepoBuilder) -> None:
    """No entry names a source at all (`{context}` only: any app may satisfy it)."""
    body = snapshot()
    for entry in required_checks(body):
        entry.pop("integration_id")
    assert_blocks("branch-protection-require-pr", protection_ctx(repo, body), UNPINNED)


def test_branch_protection_compares_with_the_configured_actions_app_id(repo: RepoBuilder) -> None:
    assert "actions_app_id" in GitHubConfig.model_fields, "typed config is missing"
    configured = actions_app_id() + 4242
    toml = (repo.path / "factory.toml").read_text(encoding="utf-8")
    repo.write(
        "factory.toml",
        toml.replace("[github]\n", f"[github]\nactions_app_id = {configured}\n", 1),
    )
    body = with_rule(snapshot(), pinned(required_contexts(), configured))
    assert_passes("branch-protection-require-pr", protection_ctx(repo, body))
    repo.git("branch", "-D", "feature/head")
    repo.git("push", "-q", "origin", "--delete", "feature/head")
    default = snapshot()
    assert_blocks("branch-protection-require-pr", protection_ctx(repo, default), UNPINNED)


# --- existing lab checks wrapped as gates (T059) ------------------------------------------

FAILING_SCRIPT = 'import sys\nprint("unknown secret FOO_TOKEN")\nsys.exit(1)\n'
PASSING_SCRIPT = 'print("ok")\n'


@pytest.mark.parametrize(
    ("gate_id", "script"),
    [
        ("validate-secrets-schema", "scripts/validate_secrets_schema.py"),
        ("validate-deploy-env", "scripts/validate_deploy_env.py"),
    ],
)
def test_existing_check_fails_with_script_output(
    repo: RepoBuilder, gate_id: str, script: str
) -> None:
    pair = repo.base_head_pair({script: FAILING_SCRIPT}, {"README.md": "# edited\n"})
    assert_blocks(gate_id, raw_context(repo, pair), "unknown secret FOO_TOKEN")


@pytest.mark.parametrize(
    ("gate_id", "script"),
    [
        ("validate-secrets-schema", "scripts/validate_secrets_schema.py"),
        ("validate-deploy-env", "scripts/validate_deploy_env.py"),
    ],
)
def test_existing_check_passes_when_script_passes(
    repo: RepoBuilder, gate_id: str, script: str
) -> None:
    pair = repo.base_head_pair({script: PASSING_SCRIPT}, {"README.md": "# edited\n"})
    assert_passes(gate_id, raw_context(repo, pair))


@pytest.mark.parametrize("gate_id", ["validate-secrets-schema", "validate-deploy-env"])
def test_existing_check_fails_when_script_missing(repo: RepoBuilder, gate_id: str) -> None:
    drop_from_main(repo, *LAB_VALIDATORS)
    pair = repo.base_head_pair({}, {"README.md": "# edited\n"})
    assert_blocks(gate_id, raw_context(repo, pair))


def test_uv_sync_locked_passes_without_apps(repo: RepoBuilder) -> None:
    pair = repo.base_head_pair({}, {"README.md": "# edited\n"})
    assert_passes("uv-sync-locked", raw_context(repo, pair))


def test_uv_sync_locked_blocks_app_without_lock(repo: RepoBuilder) -> None:
    pyproject = '[project]\nname = "demo"\nversion = "0.1.0"\nrequires-python = ">=3.12"\n'
    pair = repo.base_head_pair({"apps/demo/pyproject.toml": pyproject}, {"README.md": "# edited\n"})
    assert_blocks("uv-sync-locked", raw_context(repo, pair), "apps/demo")
