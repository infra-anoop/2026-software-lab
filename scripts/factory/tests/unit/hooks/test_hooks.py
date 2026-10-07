"""T053 — Cursor hooks (contracts/hooks.md): `spawn-guard`, `shell-guard`,
`owned-path-warn`, `decision-in-chat`.

Each hook reads the Cursor hook JSON on stdin and prints the Cursor hook response on
stdout (always one JSON object). Payload fields follow the Cursor hooks docs:
`beforeShellExecution` {command, cwd}, `subagentStart` {task, subagent_type,
subagent_model, git_branch}, `postToolUse` {tool_name, tool_input {file_path, …},
tool_output, cwd}, `stop` {status, loop_count, transcript_path}. Every payload carries
`workspace_roots`; hooks judge that repository (shell-guard: the repository the command
runs in). Transcripts are JSONL lines `{"role", "message": {"content": [{"type": "text",
"text"}]}}`.

- `shell-guard` denies with `permission: "deny"` and exit 2 (Cursor's block code).
- `spawn-guard` is advisory and log-only (FR-008; governor 2026-10-04, T-C2-1 option B):
  always `permission: "allow"`; the advisory text goes in `user_message`, which Cursor
  records in the Hooks output channel and does not show on allow. These tests pin the
  JSON contract only, not visibility.
- `owned-path-warn` (postToolUse, anchored `Write|Delete` matcher) warns in
  `additional_context`;
  `decision-in-chat` (stop) warns in `followup_message`. Both exit 0.

Hooks are offline: they read the working tree and last-fetched refs, never the network.
Amendment wo-20261004-factory-slice-c.amend-01 (A1): Cursor runs
`.cursor/hooks/factory-hook.sh <name>`, which execs the project venv's lightweight
`factory-hook` console script (`factory.hooks.entry:main`) and falls back to
`uv run --project scripts/factory factory hook <name>` only when the venv is missing.
`factory hook <name>` stays the slow-path equivalent. Budget (contracts/hooks.md, letter):
< 300 ms end to end, median of five runs of the exact command. In process, the fast
path is checked for offline behavior and parity with the CLI, not for a tighter budget.
"""

from __future__ import annotations

import importlib
import io
import json
import re
import shutil
import socket
import statistics
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from typing import Any

import pytest

from factory.cli import exit_codes
from tests.fixtures.cli_runner import CliResult, FactoryCli
from tests.fixtures.repo_builder import REPO_ROOT, RepoBuilder, message, order, yaml_text

DAY = "20261006"
BUDGET_SECONDS = 0.3
E2E_RUNS = 5
WRAPPER = ".cursor/hooks/factory-hook.sh"
HOOK_COMMAND = WRAPPER + " {name}"
VENV_HOOK = "scripts/factory/.venv/bin/factory-hook"
SLOW_PATH = "uv run --project scripts/factory factory hook {name}"
CONTRACT_HOOKS = {
    "subagentStart": "spawn-guard",
    "beforeShellExecution": "shell-guard",
    "postToolUse": "owned-path-warn",
    "stop": "decision-in-chat",
}
# The field each hook fills when it has something to say (the realistic payloads below do).
VISIBLE_FIELD = {
    "shell-guard": "permission",
    "spawn-guard": "user_message",
    "owned-path-warn": "additional_context",
    "decision-in-chat": "followup_message",
}
EXPECTED_EXIT = {
    "shell-guard": exit_codes.REFUSED,
    "spawn-guard": exit_codes.OK,
    "owned-path-warn": exit_codes.OK,
    "decision-in-chat": exit_codes.OK,
}
# The fast path must not pay for the Typer app or for other slices' packages.
HEAVY_MODULES = {"typer", "click", "rich", "httpx"}
HEAVY_PREFIXES = (
    "factory.cli",
    "factory.lifecycle",
    "factory.board",
    "factory.metrics",
    "factory.github",
    "factory.identity",
    "factory.orders",
    "factory.gates.drift",
    "factory.intent",
    "factory.mining",
)


def oid(slug: str) -> str:
    return f"wo-{DAY}-{slug}"


def payload(event: str, repo_path: Path, **fields: Any) -> dict[str, Any]:
    return {
        "conversation_id": "conv-1",
        "generation_id": "gen-1",
        "model": "claude-opus-5.5",
        "hook_event_name": event,
        "workspace_roots": [str(repo_path)],
        **fields,
    }


def parse_response(result: CliResult) -> dict[str, Any]:
    try:
        response = json.loads(result.stdout)
    except ValueError as exc:
        raise AssertionError(
            f"hook stdout is not one JSON object: {result.stdout!r}\nstderr: {result.stderr}"
        ) from exc
    assert isinstance(response, dict), response
    return response


def call_hook(
    factory_cli: FactoryCli, repo_path: Path, name: str, data: dict[str, Any]
) -> tuple[CliResult, dict[str, Any]]:
    result = factory_cli("hook", name, repo=repo_path, stdin=json.dumps(data))
    assert result.exit_code in (exit_codes.OK, exit_codes.REFUSED), (
        f"hook {name} exited {result.exit_code}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    return result, parse_response(result)


def warning(response: dict[str, Any], key: str) -> str:
    value = response.get(key) or ""
    assert isinstance(value, str), response
    return value


# --- shell-guard --------------------------------------------------------------------------


def shell(
    factory_cli: FactoryCli, repo: RepoBuilder, command: str, *, cwd: Path | None = None
) -> tuple[CliResult, dict[str, Any]]:
    """`{repo}` in a table entry stands for the fixture repo's absolute path."""
    command = command.replace("{repo}", str(repo.path))
    data = payload(
        "beforeShellExecution",
        repo.path,
        command=command,
        cwd=str(cwd or repo.path),
        sandbox=False,
    )
    return call_hook(factory_cli, repo.path, "shell-guard", data)


def assert_denied(
    factory_cli: FactoryCli, repo: RepoBuilder, command: str, *, cwd: Path | None = None
) -> None:
    result, response = shell(factory_cli, repo, command, cwd=cwd)
    assert response.get("permission") == "deny", f"{command!r} was not denied: {response}"
    assert result.exit_code == exit_codes.REFUSED, result
    reason = warning(response, "user_message") + warning(response, "agent_message")
    assert reason.strip(), f"deny without a reason: {response}"


def assert_allowed(
    factory_cli: FactoryCli, repo: RepoBuilder, command: str, *, cwd: Path | None = None
) -> None:
    result, response = shell(factory_cli, repo, command, cwd=cwd)
    assert response.get("permission") == "allow", f"{command!r} was not allowed: {response}"
    assert result.exit_code == exit_codes.OK, result


# Every push whose destination ref on the remote is `main` (update, force or delete), however
# it is spelled: refspec forms, option prefixes, wrappers, quoting, chaining, nested shells.
PUSH_TO_MAIN = [
    "git push origin main",
    "git push origin HEAD:main",
    "git push origin refs/heads/main",
    "git push origin wo/wo-20261006-x:refs/heads/main",
    "git push origin main:main",
    "git push origin +HEAD:main",
    "git push origin :main",
    "git push origin :refs/heads/main",
    "git push origin --delete main",
    "git push -d origin main",
    "git push -u origin main",
    "git push origin wo/wo-20261006-x main",
    "git -C {repo} push origin main",
    "git -c push.default=current push origin main",
    "git --no-pager push origin main",
    "/usr/bin/git push origin main",
    "command git push origin main",
    "env git push origin main",
    "GIT_TRACE=1 git push origin main",
    'git push origin "main"',
    "git push 'origin' 'HEAD:main'",
    'git push origin "HEAD:refs/heads/main"',
    "git status && git push origin main",
    "echo ok && git push origin main",
    "cd /tmp && git -C {repo} push origin main",
    "true; git push origin main",
    "false || git push origin main",
    "(git push origin main)",
    "bash -c 'git push origin main'",
    'sh -c "git push origin HEAD:main"',
]

DENIED_ON_ANY_BRANCH = [
    *PUSH_TO_MAIN,
    "pip install requests",
    "pip3 install requests",
    "python -m pip install requests",
    "gh workflow run factory-gates.yml",
    "git push --force origin wo/wo-20261006-x",
    "git push -f origin wo/wo-20261006-x",
    "git push --force-with-lease origin wo/wo-20261006-x",
    "echo 1.2.3.4 host > /etc/hosts",
    "echo 1.2.3.4 host | sudo tee -a /etc/hosts",
    "cp tool /usr/local/bin/tool",
    "mkdir -p ~/.config/tool",
    "echo x >> $HOME/.config/git/config",
    "nix-env -i hello",
    "nix-env -iA nixpkgs.hello",
    "nix-env --install hello",
]

# Commits on, and pushes of, the checked-out branch: denied when that branch is `main`.
DENIED_ON_MAIN_ONLY = [
    "git commit -m 'quick fix'",
    "git add -A && git commit -m 'quick fix'",
    "git -C {repo} commit -m 'quick fix'",
    "git -c user.name=bot commit -m 'quick fix'",
    "command git commit -m 'quick fix'",
    "git commit --amend --no-edit",
    "git push",
    "git push origin",
    "git push origin HEAD",
    "git push -u origin HEAD",
    "git -C {repo} push",
]

# Nearby controls: same tools and words, destination is not `main`, or nothing executes.
ALLOWED_ANYWHERE = [
    "ls -la",
    "git status",
    "git log main",
    "git checkout -b wo/wo-20261006-x main",
    "git push origin main-docs",
    "git push origin feature:feature",
    "git push origin main:refs/heads/wo/wo-20261006-x",
    "git push origin HEAD:wo/wo-20261006-x",
    "git -C {repo} push origin wo/wo-20261006-x",
    "git push origin --delete wo/wo-20261006-x",
    "git fetch origin main",
    "git pull --ff-only origin main",
    'echo "git push origin main"',
    "echo git push origin main > /tmp/notes.txt",
    "# git push origin main",
    'git log --grep "push origin main"',
    'rg -n "git push origin main" docs/',
    "pip list",
    "uv sync --locked",
    "gh pr list",
    'rg -n "pip install" docs/',
    "cat /etc/hosts",
    "ls /usr/bin",
    "echo x > /tmp/scratch.txt",
    "nix develop",
]


@pytest.mark.parametrize("command", DENIED_ON_ANY_BRANCH)
def test_shell_guard_denies_on_work_branch(
    repo: RepoBuilder, factory_cli: FactoryCli, command: str
) -> None:
    repo.branch(f"wo/{oid('x')}")
    assert_denied(factory_cli, repo, command)


@pytest.mark.parametrize("command", DENIED_ON_MAIN_ONLY)
def test_shell_guard_denies_direct_main_writes_on_main(
    repo: RepoBuilder, factory_cli: FactoryCli, command: str
) -> None:
    assert repo.current_branch() == "main"
    assert_denied(factory_cli, repo, command)


@pytest.mark.parametrize("command", DENIED_ON_MAIN_ONLY)
def test_shell_guard_allows_branch_writes_on_work_branch(
    repo: RepoBuilder, factory_cli: FactoryCli, command: str
) -> None:
    repo.branch(f"wo/{oid('x')}")
    assert_allowed(factory_cli, repo, command)


@pytest.mark.parametrize("command", ALLOWED_ANYWHERE)
def test_shell_guard_allows_ordinary_commands_on_main(
    repo: RepoBuilder, factory_cli: FactoryCli, command: str
) -> None:
    assert_allowed(factory_cli, repo, command)


def test_shell_guard_judges_the_branch_of_the_dash_c_repo(
    repo: RepoBuilder, factory_cli: FactoryCli, tmp_path: Path
) -> None:
    """`git -C <repo> commit` from elsewhere: the branch that matters is <repo>'s."""
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    assert repo.current_branch() == "main"
    assert_denied(factory_cli, repo, "git -C {repo} commit -m 'quick fix'", cwd=elsewhere)
    repo.branch(f"wo/{oid('x')}")
    assert_allowed(factory_cli, repo, "git -C {repo} commit -m 'work'", cwd=elsewhere)


def test_shell_guard_judges_the_branch_of_cwd(
    repo: RepoBuilder, factory_cli: FactoryCli, tmp_path: Path
) -> None:
    """A plain `git commit` runs in `cwd`; a non-repo `cwd` is not the fixture's `main`."""
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    assert repo.current_branch() == "main"
    assert_allowed(factory_cli, repo, "git commit -m 'scratch'", cwd=elsewhere)
    assert_denied(factory_cli, repo, "cd {repo} && git commit -m 'quick fix'", cwd=elsewhere)


# --- spawn-guard --------------------------------------------------------------------------

REVIEW_PACKET = "notes/packets/2026-10-06-demo-test-review-t.md"


def spawn(factory_cli: FactoryCli, repo: RepoBuilder, task: str) -> str:
    """The advisory log text (empty when there is nothing to log); the spawn is allowed."""
    data = payload(
        "subagentStart",
        repo.path,
        subagent_id="sub-1",
        subagent_type="generalPurpose",
        task=task,
        subagent_model="gpt-5.6-codex",
        is_parallel_worker=False,
        git_branch=repo.current_branch(),
        tool_call_id="tool-1",
    )
    result, response = call_hook(factory_cli, repo.path, "spawn-guard", data)
    assert result.exit_code == exit_codes.OK, result
    assert response.get("permission") == "allow", (
        f"spawn-guard is log-only and always allows: {response}"
    )
    return warning(response, "user_message")


def issue(repo: RepoBuilder, order_id: str, *, claimed: bool = True) -> None:
    repo.issue_order(order(order_id, owned_paths=[f"apps/demo/{order_id}/**"]))
    if claimed:
        repo.add_event(order_id, message("claim", order_id=order_id))


def release(repo: RepoBuilder, order_id: str) -> None:
    repo.add_event(order_id, message("release", order_id=order_id))


def worker_task(order_id: str) -> str:
    return f"You are a worker. Read notes/packets/{order_id}.md and implement order {order_id}."


def test_spawn_guard_allows_without_log_for_claimed_order(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    issue(repo, oid("alpha"))
    assert spawn(factory_cli, repo, worker_task(oid("alpha"))) == ""


def test_spawn_guard_allows_and_logs_without_order_or_review_packet(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    assert spawn(factory_cli, repo, "Refactor the board renderer for me.").strip()


def test_spawn_guard_allows_and_logs_unclaimed_order(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    issue(repo, oid("alpha"), claimed=False)
    assert oid("alpha") in spawn(factory_cli, repo, worker_task(oid("alpha")))


def test_spawn_guard_allows_and_logs_released_order(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    issue(repo, oid("alpha"))
    release(repo, oid("alpha"))
    assert oid("alpha") in spawn(factory_cli, repo, worker_task(oid("alpha")))


def test_spawn_guard_allows_without_log_for_existing_review_packet(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    repo.write(REVIEW_PACKET, "# Review packet\n")
    repo.commit("review packet")
    task = f"You are an independent reviewer. Read {REVIEW_PACKET} and write the verdict."
    assert spawn(factory_cli, repo, task) == ""


def test_spawn_guard_allows_and_logs_missing_review_packet(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    task = f"You are an independent reviewer. Read {REVIEW_PACKET} and write the verdict."
    assert spawn(factory_cli, repo, task).strip()


def test_spawn_guard_allows_and_logs_at_cap(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    for name in ("alpha", "bravo", "charlie"):
        issue(repo, oid(name))
    text = spawn(factory_cli, repo, worker_task(oid("charlie")))
    assert "3" in text, text


def test_spawn_guard_does_not_count_released_orders(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    for name in ("alpha", "bravo", "charlie"):
        issue(repo, oid(name))
    release(repo, oid("alpha"))
    assert spawn(factory_cli, repo, worker_task(oid("charlie"))) == ""


def test_spawn_guard_does_not_count_merged_orders(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    for name in ("alpha", "bravo", "charlie"):
        issue(repo, oid(name))
    repo.checkout("main")
    repo.git("merge", "--no-ff", "-q", "-m", "merge alpha", f"wo/{oid('alpha')}")
    repo.push("main")
    assert spawn(factory_cli, repo, worker_task(oid("charlie"))) == ""


# --- owned-path-warn ----------------------------------------------------------------------

WORK = oid("calc")


MUTATING_TOOLS = ["Write", "Delete"]


def tool_payload(repo: RepoBuilder, tool_name: str, file_path: str) -> dict[str, Any]:
    """postToolUse as the Cursor client sends it: `Write` {file_path, content} → success,
    `Delete` {file_path} → deleted; other tools carry {file_path} only."""
    tool_input: dict[str, Any] = {"file_path": file_path}
    output: dict[str, Any] = {"file_path": file_path, "success": True}
    if tool_name == "Write":
        tool_input["content"] = "X = 1\n"
    if tool_name == "Delete":
        output = {"file_path": file_path, "deleted": True}
    return payload(
        "postToolUse",
        repo.path,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_output=json.dumps(output),
        tool_use_id="tool-1",
        cwd=str(repo.path),
        duration=12,
    )


def edit(factory_cli: FactoryCli, repo: RepoBuilder, relative: str, *, tool: str = "Write") -> str:
    data = tool_payload(repo, tool, str(repo.path / relative))
    result, response = call_hook(factory_cli, repo.path, "owned-path-warn", data)
    assert result.exit_code == exit_codes.OK, result
    return warning(response, "additional_context")


def on_work_branch(repo: RepoBuilder, owned_paths: list[str]) -> None:
    repo.issue_order(order(WORK, owned_paths=owned_paths))
    repo.add_event(WORK, message("claim", order_id=WORK))
    repo.checkout(f"wo/{WORK}")


@pytest.mark.parametrize("tool", MUTATING_TOOLS)
def test_owned_path_quiet_inside_owned_paths(
    repo: RepoBuilder, factory_cli: FactoryCli, tool: str
) -> None:
    on_work_branch(repo, ["apps/demo/app/calc.py", "apps/demo/tests/**"])
    assert edit(factory_cli, repo, "apps/demo/app/calc.py", tool=tool) == ""
    assert edit(factory_cli, repo, "apps/demo/tests/unit/test_calc.py", tool=tool) == ""


def test_owned_path_quiet_for_own_bus_dir(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    on_work_branch(repo, ["apps/demo/app/calc.py"])
    assert edit(factory_cli, repo, f"bus/orders/{WORK}/handoff.yaml") == ""


@pytest.mark.parametrize("tool", MUTATING_TOOLS)
def test_owned_path_warns_outside_owned_paths(
    repo: RepoBuilder, factory_cli: FactoryCli, tool: str
) -> None:
    on_work_branch(repo, ["apps/demo/app/calc.py"])
    text = edit(factory_cli, repo, "deploy/railway/demo.toml", tool=tool)
    assert "deploy/railway/demo.toml" in text, text
    assert WORK in text, text


def test_owned_path_uses_effective_order(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    on_work_branch(repo, ["apps/demo/app/calc.py"])
    repo.checkout("main")
    amendment = message(
        "amendment",
        order_id=WORK,
        supersedes=["owned_paths"],
        values={"owned_paths": ["apps/demo/app/calc.py", "deploy/**"]},
    )
    repo.add_event(WORK, amendment)
    repo.checkout(f"wo/{WORK}")
    assert edit(factory_cli, repo, "deploy/railway/demo.toml") == ""


def test_owned_path_quiet_on_main(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    assert edit(factory_cli, repo, "deploy/railway/demo.toml") == ""


def test_owned_path_quiet_for_non_mutating_tools(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    on_work_branch(repo, ["apps/demo/app/calc.py"])
    assert edit(factory_cli, repo, "deploy/railway/demo.toml", tool="Read") == ""
    assert edit(factory_cli, repo, "deploy/railway/demo.toml", tool="Write").strip()
    assert edit(factory_cli, repo, "deploy/railway/demo.toml", tool="Delete").strip()


# --- decision-in-chat ---------------------------------------------------------------------


def write_transcript(path: Path, turns: list[tuple[str, str]]) -> Path:
    lines: list[dict[str, Any]] = []
    for role, text in turns:
        lines.append({"role": role, "message": {"content": [{"type": "text", "text": text}]}})
        if role == "assistant":
            tool = {"type": "tool_use", "name": "Shell", "input": {"command": "git status"}}
            lines.append({"role": "assistant", "message": {"content": [tool]}})
    lines.append({"type": "turn_ended", "status": "success"})
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")
    return path


def stop(factory_cli: FactoryCli, repo: RepoBuilder, transcript: Path) -> str:
    data = payload(
        "stop", repo.path, status="completed", loop_count=0, transcript_path=str(transcript)
    )
    result, response = call_hook(factory_cli, repo.path, "decision-in-chat", data)
    assert result.exit_code == exit_codes.OK, result
    return warning(response, "followup_message")


QUESTION = "Tests are green. Should the demo deploy to Railway or to Fly first?"


def new_request_text(decision_id: str) -> str:
    return yaml_text(message("decision_request", decision_id=decision_id))


def test_decision_in_chat_warns_on_question_without_request(
    repo: RepoBuilder, factory_cli: FactoryCli, tmp_path: Path
) -> None:
    transcript = write_transcript(tmp_path / "t.jsonl", [("user", "Go."), ("assistant", QUESTION)])
    assert "decision" in stop(factory_cli, repo, transcript).lower()


def test_decision_in_chat_quiet_when_new_request_written(
    repo: RepoBuilder, factory_cli: FactoryCli, tmp_path: Path
) -> None:
    repo.write("bus/decisions/deploy-host/request.yaml", new_request_text("deploy-host"))
    transcript = write_transcript(tmp_path / "t.jsonl", [("user", "Go."), ("assistant", QUESTION)])
    assert stop(factory_cli, repo, transcript) == ""


def test_decision_in_chat_warns_when_only_old_requests_exist(
    repo: RepoBuilder, factory_cli: FactoryCli, tmp_path: Path
) -> None:
    repo.write("bus/decisions/old-one/request.yaml", new_request_text("old-one"))
    repo.commit("old decision request")
    repo.push("main")
    transcript = write_transcript(tmp_path / "t.jsonl", [("user", "Go."), ("assistant", QUESTION)])
    assert stop(factory_cli, repo, transcript).strip()


def test_decision_in_chat_judges_only_the_final_turn(
    repo: RepoBuilder, factory_cli: FactoryCli, tmp_path: Path
) -> None:
    turns = [
        ("user", "Go."),
        ("assistant", QUESTION),
        ("user", "Railway."),
        ("assistant", "Deployed to Railway. Smoke test passed."),
    ]
    assert stop(factory_cli, repo, write_transcript(tmp_path / "t.jsonl", turns)) == ""


def test_decision_in_chat_ignores_question_marks_in_code(
    repo: RepoBuilder, factory_cli: FactoryCli, tmp_path: Path
) -> None:
    text = "Fixed the parser for `a?b` patterns.\n\n```python\nPATTERN = r'colou?r'\n```\nDone."
    turns = [("user", "Go."), ("assistant", text)]
    assert stop(factory_cli, repo, write_transcript(tmp_path / "t.jsonl", turns)) == ""


def test_decision_in_chat_quiet_without_transcript(
    repo: RepoBuilder, factory_cli: FactoryCli, tmp_path: Path
) -> None:
    assert stop(factory_cli, repo, tmp_path / "missing.jsonl") == ""


# --- fast path: offline, parity with `factory hook` ---------------------------------------


def hook_entry() -> Any:
    try:
        return importlib.import_module("factory.hooks.entry")
    except ModuleNotFoundError as exc:
        raise AssertionError(f"factory.hooks.entry is not implemented: {exc}") from exc


def call_entry(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    name: str,
    data: dict[str, Any],
) -> tuple[int, dict[str, Any]]:
    """`factory-hook <name>` in process: Cursor JSON on stdin, one JSON object on stdout."""
    main = hook_entry().main
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(data)))
    capsys.readouterr()
    code = main([name])
    out = capsys.readouterr().out
    try:
        response = json.loads(out)
    except ValueError as exc:
        raise AssertionError(f"factory-hook {name} stdout is not one JSON object: {out!r}") from exc
    assert isinstance(response, dict), response
    return code, response


def prepared_hook_repo(repo: RepoBuilder, tmp_path: Path) -> dict[str, dict[str, Any]]:
    """Realistic payloads: each hook takes its full path (bus reads, git refs, transcript)."""
    for name in ("alpha", "bravo"):
        issue(repo, oid(name))
    on_work_branch(repo, ["apps/demo/app/calc.py"])
    transcript = write_transcript(tmp_path / "t.jsonl", [("user", "Go."), ("assistant", QUESTION)])
    return contract_payloads(repo, transcript)


def contract_payloads(repo: RepoBuilder, transcript: Path) -> dict[str, dict[str, Any]]:
    return {
        "shell-guard": payload(
            "beforeShellExecution", repo.path, command="git push origin main", cwd=str(repo.path)
        ),
        "spawn-guard": payload(
            "subagentStart",
            repo.path,
            subagent_type="generalPurpose",
            task=worker_task(oid("alpha")),
            git_branch=repo.current_branch(),
        ),
        "owned-path-warn": tool_payload(repo, "Write", str(repo.path / "deploy/railway/demo.toml")),
        "decision-in-chat": payload(
            "stop", repo.path, status="completed", loop_count=0, transcript_path=str(transcript)
        ),
    }


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Any in-process network connection fails the test."""

    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("hook tried to use the network")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def test_hook_entry_imports_neither_the_cli_nor_other_slices() -> None:
    code = "import sys, factory.hooks.entry; print('\\n'.join(sorted(sys.modules)))"
    completed = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert completed.returncode == 0, completed.stderr
    loaded = completed.stdout.split()
    heavy = [m for m in loaded if m in HEAVY_MODULES or m.startswith(HEAVY_PREFIXES)]
    assert heavy == [], f"factory.hooks.entry imports {heavy}"


@pytest.mark.parametrize("name", sorted(CONTRACT_HOOKS.values()))
def test_hook_entry_is_offline_and_matches_the_cli(
    repo: RepoBuilder,
    factory_cli: FactoryCli,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    offline: None,
    name: str,
) -> None:
    data = prepared_hook_repo(repo, tmp_path)[name]
    repo.git("remote", "set-url", "origin", str(repo.root / "unreachable.git"))
    monkeypatch.chdir(tmp_path)
    code, response = call_entry(monkeypatch, capsys, name, data)
    cli_result, cli_response = call_hook(factory_cli, repo.path, name, data)
    assert (code, response) == (cli_result.exit_code, cli_response), (
        f"factory-hook {name} and `factory hook {name}` disagree"
    )
    assert code == EXPECTED_EXIT[name], (code, response)
    assert response.get(VISIBLE_FIELD[name]), f"{name} took its quiet path: {response}"


# --- registration: pyproject console script, wrapper, .cursor/hooks.json -----------------


def test_pyproject_declares_the_lightweight_console_script() -> None:
    project = tomllib.loads((REPO_ROOT / "scripts/factory/pyproject.toml").read_text("utf-8"))
    scripts = project["project"]["scripts"]
    assert scripts.get("factory-hook") == "factory.hooks.entry:main", scripts
    assert scripts.get("factory") == "factory.cli.app:main", scripts


def fake_executable(path: Path, log: Path, stdout: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$0 $*" >> "{log}"\n'
        f'cat > "{log}.stdin"\n'
        f"printf '%s' '{stdout}'\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def wrapper_sandbox(tmp_path: Path, *, with_venv: bool) -> tuple[Path, Path, dict[str, str]]:
    wrapper = REPO_ROOT / WRAPPER
    assert wrapper.is_file(), f"{wrapper} is missing"
    root = tmp_path / "project"
    target = root / WRAPPER
    target.parent.mkdir(parents=True)
    shutil.copy2(wrapper, target)
    log = tmp_path / "calls.log"
    if with_venv:
        fake_executable(root / VENV_HOOK, log, '{"permission": "allow"}')
    fake_bin = tmp_path / "bin"
    fake_executable(fake_bin / "uv", log, '{"permission": "allow"}')
    env = {"PATH": f"{fake_bin}:/usr/bin:/bin", "HOME": str(tmp_path)}
    return root, log, env


def run_wrapper(root: Path, env: dict[str, str], stdin: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        HOOK_COMMAND.format(name="shell-guard"),
        shell=True,
        cwd=root,
        env=env,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def test_wrapper_runs_the_venv_console_script(tmp_path: Path) -> None:
    root, log, env = wrapper_sandbox(tmp_path, with_venv=True)
    completed = run_wrapper(root, env, '{"command": "ls"}')
    assert completed.returncode == 0, completed
    assert json.loads(completed.stdout) == {"permission": "allow"}, completed.stdout
    calls = log.read_text(encoding="utf-8").splitlines()
    assert len(calls) == 1, calls
    program, *args = calls[0].split()
    assert program.endswith(VENV_HOOK), calls
    assert args == ["shell-guard"], calls
    assert Path(f"{log}.stdin").read_text(encoding="utf-8") == '{"command": "ls"}'


def test_wrapper_falls_back_to_uv_run_without_the_venv(tmp_path: Path) -> None:
    root, log, env = wrapper_sandbox(tmp_path, with_venv=False)
    completed = run_wrapper(root, env, '{"command": "ls"}')
    assert completed.returncode == 0, completed
    calls = log.read_text(encoding="utf-8").splitlines()
    assert len(calls) == 1, calls
    program, *args = calls[0].split()
    assert program.endswith("/uv"), calls
    assert args == SLOW_PATH.format(name="shell-guard").split()[1:], calls
    assert Path(f"{log}.stdin").read_text(encoding="utf-8") == '{"command": "ls"}'


def live_hooks() -> dict[str, Any]:
    path = REPO_ROOT / ".cursor/hooks.json"
    assert path.is_file(), f"{path} is missing"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), data
    return data


def live_entries(event: str, name: str) -> list[dict[str, Any]]:
    hooks = live_hooks().get("hooks", {})
    command = HOOK_COMMAND.format(name=name)
    return [entry for entry in hooks.get(event, []) if entry.get("command") == command]


def test_live_hooks_json_registers_every_contract_hook() -> None:
    data = live_hooks()
    assert data.get("version") == 1, data
    for event, name in CONTRACT_HOOKS.items():
        assert len(live_entries(event, name)) == 1, (event, data.get("hooks", {}).get(event))


def test_live_hooks_json_routes_factory_hooks_through_the_wrapper() -> None:
    for event, entries in live_hooks().get("hooks", {}).items():
        for entry in entries:
            command = entry.get("command", "")
            if "factory" in command:
                assert command.startswith(f"{WRAPPER} "), (event, command)
    assert live_entries("afterFileEdit", "owned-path-warn") == []


def test_live_owned_path_warn_matches_exactly_write_and_delete() -> None:
    """Cursor tests the matcher as an unanchored JS regex, so it must anchor itself."""
    (entry,) = live_entries("postToolUse", "owned-path-warn")
    matcher = entry.get("matcher")
    assert matcher, f"owned-path-warn would run after every tool: {entry}"
    for tool in MUTATING_TOOLS:
        assert re.search(matcher, tool), (matcher, tool)
    for tool in ("Read", "Shell", "Grep", "Task", "WriteShellStdin", "MCP:Write", "MCP:Delete"):
        assert not re.search(matcher, tool), (matcher, tool)


@pytest.mark.parametrize(("event", "name"), sorted(CONTRACT_HOOKS.items()))
def test_live_hook_command_answers_within_budget(
    repo: RepoBuilder, tmp_path: Path, event: str, name: str
) -> None:
    """End to end through a shell, as Cursor runs it: median of five runs < 300 ms."""
    assert len(live_entries(event, name)) == 1, (event, name)
    command = HOOK_COMMAND.format(name=name)
    data = json.dumps(prepared_hook_repo(repo, tmp_path)[name])
    timings = []
    for _ in range(E2E_RUNS):
        started = time.perf_counter()
        completed = subprocess.run(
            command,
            shell=True,
            cwd=REPO_ROOT,
            input=data,
            capture_output=True,
            text=True,
            check=False,
        )
        timings.append(time.perf_counter() - started)
        assert completed.returncode == EXPECTED_EXIT[name], completed
        response = json.loads(completed.stdout)
        assert response.get(VISIBLE_FIELD[name]), f"{name} took its quiet path: {response}"
    median = statistics.median(timings)
    assert median < BUDGET_SECONDS, (
        f"{command} median {median * 1000:.0f} ms over {E2E_RUNS} runs (budget 300 ms); "
        f"runs: {[round(t * 1000) for t in timings]}"
    )
