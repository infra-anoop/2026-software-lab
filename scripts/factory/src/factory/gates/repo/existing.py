"""Existing lab checks wrapped as gates (T059): `validate-secrets-schema`,
`validate-deploy-env`, `uv-sync-locked`.

The two validator scripts run against the head tree, exported to a temporary
directory (gates write nothing to the repository), with the factory's interpreter.
`uv-sync-locked` checks that every app project committed its `uv.lock`.
"""

from __future__ import annotations

import io
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

from factory.api import GateContext, GateResult
from factory.gates.repo._git import exists, failed, ls_tree, outcome

SECRETS_GATE = "validate-secrets-schema"
DEPLOY_ENV_GATE = "validate-deploy-env"
UV_LOCK_GATE = "uv-sync-locked"
SCRIPT_TIMEOUT_SECONDS = 300
OUTPUT_LINES = 20


def _export_head(repo: Path, sha: str, target: Path) -> None:
    archive = subprocess.run(
        ["git", "-C", str(repo), "archive", "--format=tar", sha],
        check=True,
        capture_output=True,
    )
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
        tar.extractall(target, filter="tar")


def _run_script(ctx: GateContext, gate_id: str, script: str) -> GateResult:
    if not exists(ctx.repo_path, ctx.head_sha, script):
        return failed(gate_id, [f"{script} not found at head"])
    with tempfile.TemporaryDirectory(prefix="factory-gate-") as tmp:
        tree = Path(tmp)
        _export_head(ctx.repo_path, ctx.head_sha, tree)
        try:
            completed = subprocess.run(
                [sys.executable, str(tree / script)],
                cwd=tree,
                check=False,
                capture_output=True,
                text=True,
                timeout=SCRIPT_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return failed(gate_id, [f"{script} timed out after {SCRIPT_TIMEOUT_SECONDS} s"])
    output = [line for line in (completed.stdout + completed.stderr).splitlines() if line.strip()]
    tail = output[-OUTPUT_LINES:]
    if completed.returncode != 0:
        return failed(gate_id, [f"{script} exited {completed.returncode}", *tail])
    return GateResult(gate_id=gate_id, passed=True, messages=[f"{gate_id}: {script} passed"])


def validate_secrets_schema(ctx: GateContext) -> GateResult:
    return _run_script(ctx, SECRETS_GATE, "scripts/validate_secrets_schema.py")


def validate_deploy_env(ctx: GateContext) -> GateResult:
    return _run_script(ctx, DEPLOY_ENV_GATE, "scripts/validate_deploy_env.py")


def uv_sync_locked(ctx: GateContext) -> GateResult:
    files = set(ls_tree(ctx.repo_path, ctx.head_sha, *ctx.config.app_roots))
    projects = sorted(
        str(PurePosixPath(path).parent)
        for path in files
        if PurePosixPath(path).name == "pyproject.toml"
        and str(PurePosixPath(path).parent.parent) in ctx.config.app_roots
    )
    problems = [
        f"{project}: pyproject.toml has no committed uv.lock"
        for project in projects
        if f"{project}/uv.lock" not in files
    ]
    return outcome(UV_LOCK_GATE, problems, f"{len(projects)} app project(s) carry uv.lock")
