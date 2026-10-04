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

Branch protection (I-P10, T066): `deploy/github/branch-protection.json` is the GitHub
REST "get branch protection" body for `main`. It must require a PR, enforce it for
admins with no bypass allowances, require code-owner review, and require a
`factory/<gate-id>` status for every P1 CI gate in the registry.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
import yaml

from factory.api import GateContext
from factory.cli import exit_codes
from factory.gates.registry import REGISTRY_PATH, load_registry
from tests.fixtures.cli_runner import FactoryCli
from tests.fixtures.repo_builder import RepoBuilder
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


def required_contexts() -> list[str]:
    return [
        f"factory/{gate.id}"
        for gate in load_registry().gates
        if gate.priority == "P1" and gate.hook_twin_of is None
    ]


def snapshot(**changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "required_status_checks": {"strict": True, "contexts": required_contexts()},
        "enforce_admins": {"enabled": True},
        "required_pull_request_reviews": {
            "require_code_owner_reviews": True,
            "required_approving_review_count": 0,
            "bypass_pull_request_allowances": {"users": [], "teams": [], "apps": []},
        },
        "restrictions": None,
    }
    body.update(changes)
    return body


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


def test_branch_protection_passes_on_expected_snapshot(repo: RepoBuilder) -> None:
    assert_passes("branch-protection-require-pr", protection_ctx(repo, snapshot()))


def test_branch_protection_blocks_without_head_registry(repo: RepoBuilder) -> None:
    ctx = protection_ctx(repo, snapshot(), with_registry=False)
    assert_blocks("branch-protection-require-pr", ctx, REGISTRY)


def test_branch_protection_blocks_missing_snapshot(repo: RepoBuilder) -> None:
    assert_blocks("branch-protection-require-pr", protection_ctx(repo, None), SNAPSHOT)


def test_branch_protection_blocks_when_pr_not_required(repo: RepoBuilder) -> None:
    body = snapshot(required_pull_request_reviews=None)
    assert_blocks("branch-protection-require-pr", protection_ctx(repo, body))


def test_branch_protection_blocks_admin_bypass(repo: RepoBuilder) -> None:
    body = snapshot(enforce_admins={"enabled": False})
    assert_blocks("branch-protection-require-pr", protection_ctx(repo, body))


def test_branch_protection_blocks_bypass_allowance(repo: RepoBuilder) -> None:
    body = snapshot()
    body["required_pull_request_reviews"]["bypass_pull_request_allowances"]["users"] = [
        {"login": "some-agent"}
    ]
    assert_blocks("branch-protection-require-pr", protection_ctx(repo, body), "some-agent")


def test_branch_protection_blocks_without_code_owner_review(repo: RepoBuilder) -> None:
    body = snapshot()
    body["required_pull_request_reviews"]["require_code_owner_reviews"] = False
    assert_blocks("branch-protection-require-pr", protection_ctx(repo, body))


def test_branch_protection_blocks_missing_required_gate_status(repo: RepoBuilder) -> None:
    contexts = [c for c in required_contexts() if c != "factory/bus.immutable"]
    body = snapshot(required_status_checks={"strict": True, "contexts": contexts})
    ctx = protection_ctx(repo, body)
    assert_blocks("branch-protection-require-pr", ctx, "factory/bus.immutable")


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
    pair = repo.base_head_pair({}, {"README.md": "# edited\n"})
    assert_blocks(gate_id, raw_context(repo, pair))


def test_uv_sync_locked_passes_without_apps(repo: RepoBuilder) -> None:
    pair = repo.base_head_pair({}, {"README.md": "# edited\n"})
    assert_passes("uv-sync-locked", raw_context(repo, pair))


def test_uv_sync_locked_blocks_app_without_lock(repo: RepoBuilder) -> None:
    pyproject = '[project]\nname = "demo"\nversion = "0.1.0"\nrequires-python = ">=3.12"\n'
    pair = repo.base_head_pair({"apps/demo/pyproject.toml": pyproject}, {"README.md": "# edited\n"})
    assert_blocks("uv-sync-locked", raw_context(repo, pair), "apps/demo")
