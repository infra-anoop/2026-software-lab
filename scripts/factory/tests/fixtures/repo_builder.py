"""Seeded fixture repos for gate, CLI, and seed tests (tasks.md T012). Frozen at CP0.

`RepoBuilder` creates a temp bare `origin` plus a working clone on `main`, writes a
fixture `factory.toml`, and offers helpers to write messages, commit, branch, push,
issue orders on `wo/<order-id>` branches, open fake PRs, and build base/head pairs.
"""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

import yaml
from pydantic import BaseModel

from factory import PROJECT_DIR
from factory.api import GateContext, PullRequest
from factory.bus.models import ORDER_SCOPED_KINDS, parse_message
from factory.bus.store import expected_path, load_all
from factory.config.settings import Settings, load_settings
from tests.fixtures.fake_github import FakeGitHub

MESSAGES_DIR = Path(__file__).resolve().parent / "messages"
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
SAMPLE_ORDER_ID = "wo-20261005-red-first-gate"
SAMPLE_DECISION_ID = "board-web-view"
GOVERNOR_LOGIN = "fixture-governor"
REPO_ROOT = PROJECT_DIR.parents[1]
REPO_JARGON = load_settings(REPO_ROOT).decision_lint.jargon

FIXTURE_TOML = """\
bus_dir = "bus"
spec_roots = ["specs"]
app_roots = ["apps"]
rule_paths = [".specify/memory/constitution.md", "AGENTS.md", "scripts/factory/gates.yaml"]
concurrency_cap = {concurrency_cap}
autonomy_horizon_minutes = {autonomy_horizon_minutes}
stale_multiplier = 3
governor_login = "{governor_login}"

[families]
claude = "anthropic"
gpt = "openai"
gemini = "google"

[identity]
mode = "{identity_mode}"

[github]
repository = "fixture/demo"
api_url = "https://api.github.test"

[decision_lint]
jargon = {jargon}
"""

DEMO_SPEC = """\
# Feature: demo

## Open Decisions

| id | shape_locked | content_open | who | before | status | arch_impact | fidelity |
|----|--------------|--------------|-----|--------|--------|-------------|----------|
| **D1** | The demo app has one deploy host | Which host | human | Before deploy | **locked** (2026-10-01) — **Railway** | content-only | letter |
"""  # noqa: E501

# Inputs the repo-level gates read from `main` and the head (amend-08, CP0 fixture
# amendment): the real gate registry and `main` ruleset snapshot, and stand-ins for the
# lab validators, whose real inputs (app registry, Railway manifests, secrets schema) are
# outside the factory's scope.
LAB_COPIED_FILES = ("scripts/factory/gates.yaml", "deploy/github/branch-protection.json")
LAB_VALIDATOR_STAND_IN = """\
\"\"\"Fixture stand-in for a lab validator: takes `--repo-root`, finds nothing wrong.\"\"\"
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--repo-root")
parser.parse_args()
"""
LAB_VALIDATORS = ("scripts/validate_secrets_schema.py", "scripts/validate_deploy_env.py")

DEMO_TASKS = """\
# Tasks: demo

- [ ] T001 [P] Add `add()` to `apps/demo/app/calc.py`
- [ ] T002 [OD:D1] Deploy the demo app on Railway via `deploy/railway/demo.toml`
"""

DEMO_ACCEPTANCE = """\
# Acceptance catalog — demo

| id | class | intents | severity | when | shall | how | evidence |
|----|-------|---------|----------|------|-------|-----|----------|
| demo.adds | SC-001 | I-D1 | must | two integers | add returns their sum | auto | planned |
"""


def load_sample(kind: str) -> dict[str, Any]:
    """A deep copy of the sample message of `kind` from `fixtures/messages/`."""
    data = yaml.safe_load((MESSAGES_DIR / SAMPLE_FILES[kind]).read_text(encoding="utf-8"))
    return copy.deepcopy(data)


def message(
    kind: str,
    *,
    order_id: str | None = None,
    decision_id: str | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    """Sample message of `kind`, re-addressed to `order_id` / `decision_id`, with overrides."""
    data = load_sample(kind)
    if order_id and kind in ORDER_SCOPED_KINDS:
        data["id"] = data["id"].replace(SAMPLE_ORDER_ID, order_id)
        data["refs"] = [order_id]
    if decision_id and kind in {"decision_request", "decision_lock"}:
        data["id"] = data["id"].replace(SAMPLE_DECISION_ID, decision_id)
        if kind == "decision_lock":
            data["refs"] = [decision_id]
    data.update(overrides)
    return data


DEMO_ORDER: dict[str, Any] = {
    "feature": "demo-feature",
    "goal": "Add the demo calculator's add function, test first.",
    "intents": ["I-D1"],
    "owned_paths": ["apps/demo/app/calc.py", "apps/demo/tests/**"],
    "checks": ["red-first-proof", "diff-within-owned-paths"],
    "locks": [],
    "tasks": ["T001"],
}


def order(order_id: str, **overrides: Any) -> dict[str, Any]:
    """A valid order for a fixture repo's demo feature (sample order re-addressed to
    `order_id`). Task T001 touches no locked decision, so the order declares no lock."""
    return message("order", order_id=order_id, **{**DEMO_ORDER, **overrides})


class BaseHeadPair(NamedTuple):
    base_sha: str
    head_sha: str
    head_branch: str


def _to_data(data: Mapping[str, Any] | BaseModel) -> dict[str, Any]:
    if isinstance(data, BaseModel):
        dumped: dict[str, Any] = data.model_dump(mode="json", by_alias=True, exclude_none=True)
        return dumped
    return dict(data)


class RepoBuilder:
    """A working clone (`path`) of a bare `origin`, on `main`, with a fixture config."""

    def __init__(
        self,
        root: Path,
        *,
        github: FakeGitHub | None = None,
        concurrency_cap: int = 3,
        autonomy_horizon_minutes: int = 60,
        identity_mode: str = "recorded",
    ) -> None:
        self.root = Path(root)
        self.origin = self.root / "origin.git"
        self.path = self.root / "work"
        self.github = github or FakeGitHub()
        self.root.mkdir(parents=True, exist_ok=True)
        self._git_bin = _git_binary()
        # Isolated from the developer's global/system git config (hooks, signing, ...).
        self._env = {"HOME": str(self.root), "GIT_CONFIG_NOSYSTEM": "1", "LC_ALL": "C"}
        for target in (["--bare", str(self.origin)], [str(self.path)]):
            subprocess.run(
                [self._git_bin, "init", "-q", "-b", "main", *target],
                check=True,
                capture_output=True,
                env=self._env,
            )
        for key, value in {
            "user.name": "Fixture Bot",
            "user.email": "fixture@example.test",
            "commit.gpgsign": "false",
            "tag.gpgsign": "false",
            "core.hooksPath": "/dev/null",
        }.items():
            self.git("config", key, value)
        self.git("remote", "add", "origin", str(self.origin))
        self.write(
            "factory.toml",
            FIXTURE_TOML.format(
                concurrency_cap=concurrency_cap,
                autonomy_horizon_minutes=autonomy_horizon_minutes,
                governor_login=GOVERNOR_LOGIN,
                identity_mode=identity_mode,
                jargon=json.dumps(REPO_JARGON),
            ),
        )
        self.write("README.md", "# fixture repo\n")
        # The sample order's feature: every fixture repo has the spec its orders name.
        self.write("specs/demo-feature/spec.md", DEMO_SPEC)
        self.write("specs/demo-feature/tasks.md", DEMO_TASKS)
        self.plant_lab_inputs()
        self.commit("init")
        self.push("main")

    def plant_lab_inputs(self) -> None:
        """Write the files the repo-level gates read (registry, snapshot, validators)."""
        for relative in LAB_COPIED_FILES:
            self.write(relative, (REPO_ROOT / relative).read_text(encoding="utf-8"))
        for relative in LAB_VALIDATORS:
            self.write(relative, LAB_VALIDATOR_STAND_IN)

    # --- git ------------------------------------------------------------------------

    def git(self, *args: str, env: Mapping[str, str] | None = None) -> str:
        result = subprocess.run(
            [self._git_bin, "-C", str(self.path), *args],
            check=False,
            capture_output=True,
            text=True,
            env={**self._env, **(env or {})},
        )
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout.strip()

    @property
    def settings(self) -> Settings:
        return load_settings(self.path)

    def head_sha(self, ref: str = "HEAD") -> str:
        return self.git("rev-parse", ref)

    def current_branch(self) -> str:
        return self.git("rev-parse", "--abbrev-ref", "HEAD")

    def write(self, relative: str, text: str) -> Path:
        target = self.path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def delete(self, relative: str) -> None:
        (self.path / relative).unlink()

    def commit(
        self, subject: str, *, when: datetime | None = None, allow_empty: bool = False
    ) -> str:
        self.git("add", "-A")
        args = ["commit", "-q", "-m", subject]
        if allow_empty:
            args.append("--allow-empty")
        env = None
        if when is not None:
            stamp = when.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S+0000")
            env = {"GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}
        self.git(*args, env=env)
        return self.head_sha()

    def branch(self, name: str, start: str = "main") -> None:
        self.git("checkout", "-q", "-b", name, start)

    def checkout(self, name: str) -> None:
        self.git("checkout", "-q", name)

    def push(self, branch: str | None = None) -> None:
        self.git("push", "-q", "origin", branch or self.current_branch())

    # --- bus messages -----------------------------------------------------------------

    def write_message(self, data: Mapping[str, Any] | BaseModel, *, validate: bool = True) -> str:
        """Write a message at its layout path; returns the repo-relative path."""
        payload = _to_data(data)
        if validate:
            relative = str(expected_path(parse_message(payload), self.settings.bus_dir))
        else:
            relative = str(_unvalidated_path(payload, self.settings.bus_dir))
        self.write(relative, yaml.safe_dump(payload, sort_keys=False))
        return relative

    def issue_order(self, data: Mapping[str, Any], *, when: datetime | None = None) -> str:
        """Create `wo/<order-id>` from main with the order as its first commit; push."""
        order_id = str(data["id"])
        branch = f"wo/{order_id}"
        start = self.current_branch()
        self.branch(branch, "main")
        self.write_message(data)
        self.commit(f"order: {order_id}", when=when)
        self.push(branch)
        self.checkout(start)
        return branch

    def add_event(
        self,
        order_id: str,
        data: Mapping[str, Any] | BaseModel,
        *,
        when: datetime | None = None,
        validate: bool = True,
        extra_files: Mapping[str, str] | None = None,
    ) -> str:
        """Commit a message (plus optional files) on `wo/<order-id>` and push; returns sha."""
        start = self.current_branch()
        self.checkout(f"wo/{order_id}")
        self.write_message(data, validate=validate)
        for relative, text in (extra_files or {}).items():
            self.write(relative, text)
        sha = self.commit(f"{_to_data(data)['kind']}: {order_id}", when=when)
        self.push()
        self.checkout(start)
        return sha

    def make_pr(
        self,
        head_branch: str,
        *,
        base: str = "main",
        title: str = "",
        body: str = "",
        open: bool = True,
        merged: bool = False,
    ) -> PullRequest:
        """Register a PR for `head_branch` in the FakeGitHub (head sha from the branch)."""
        return self.github.add_pr(
            head_branch,
            head_sha=self.head_sha(head_branch),
            base=base,
            title=title or head_branch,
            body=body,
            open=open,
            merged=merged,
        )

    # --- demo feature + gate inputs -----------------------------------------------------

    def add_demo_feature(self, *, acceptance: bool = True) -> str:
        """Commit `specs/demo-feature/` (locked letter OD D1 = Railway; tasks T001, T002)."""
        start = self.current_branch()
        self.checkout("main")
        self.write("specs/demo-feature/spec.md", DEMO_SPEC)
        self.write("specs/demo-feature/tasks.md", DEMO_TASKS)
        if acceptance:
            self.write("specs/demo-feature/acceptance.md", DEMO_ACCEPTANCE)
        self.write("apps/demo/conftest.py", "")
        self.write("apps/demo/app/__init__.py", "")
        self.write("apps/demo/app/calc.py", "def add(a: int, b: int) -> int:\n    return a + b\n")
        sha = self.commit("demo feature")
        self.push("main")
        self.checkout(start)
        return sha

    def base_head_pair(
        self,
        base_files: Mapping[str, str],
        head_files: Mapping[str, str | None],
        *,
        head_branch: str = "feature/head",
    ) -> BaseHeadPair:
        """Commit `base_files` on main (pushed), then `head_files` on `head_branch`.

        A `None` value in `head_files` deletes that path on head.
        """
        self.checkout("main")
        for relative, text in base_files.items():
            self.write(relative, text)
        base_sha = self.commit("base", allow_empty=True)
        self.push("main")
        self.branch(head_branch, "main")
        for relative, text in head_files.items():
            if text is None:
                self.delete(relative)
            else:
                self.write(relative, text)
        head_sha = self.commit("head", allow_empty=True)
        self.push(head_branch)
        self.checkout("main")
        return BaseHeadPair(base_sha, head_sha, head_branch)

    def gate_context(
        self,
        pair: BaseHeadPair,
        *,
        pr_number: int | None = None,
        order_id: str | None = None,
    ) -> GateContext:
        """A `GateContext` for `pair`, with the bus snapshot loaded at head."""
        settings = self.settings
        return GateContext(
            repo_path=self.path,
            base_sha=pair.base_sha,
            head_sha=pair.head_sha,
            pr_number=pr_number,
            order_id=order_id,
            config=settings,
            bus_snapshot=load_all(self.path, pair.head_sha, settings=settings),
        )


def yaml_text(data: Mapping[str, Any] | BaseModel) -> str:
    return yaml.safe_dump(_to_data(data), sort_keys=False)


def _unvalidated_path(payload: Mapping[str, Any], bus_dir: str) -> Path:
    message_id = str(payload["id"])
    kind = str(payload["kind"])
    if kind in ORDER_SCOPED_KINDS:
        order_id = message_id.split(".", 1)[0]
        name = "order" if kind == "order" else message_id.split(".", 1)[1]
        name = name.replace("amend-", "amendment-", 1)
        return Path(bus_dir) / "orders" / order_id / f"{name}.yaml"
    if kind == "decision_request":
        return Path(bus_dir) / "decisions" / message_id / "request.yaml"
    if kind == "decision_lock":
        return Path(bus_dir) / "decisions" / message_id.removesuffix(".lock") / "lock.yaml"
    return Path(bus_dir) / "corrections" / f"{message_id}.yaml"


def _git_binary() -> str:
    found = shutil.which("git")
    if found is None:
        raise RuntimeError("git is required for fixture repos")
    return found
