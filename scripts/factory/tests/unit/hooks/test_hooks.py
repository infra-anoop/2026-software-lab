"""T053 — Cursor hooks (contracts/hooks.md): `spawn-guard`, `shell-guard`,
`owned-path-warn`, `decision-in-chat`.

Each hook reads the Cursor hook JSON on stdin and prints the Cursor hook response on
stdout (always one JSON object). Payload fields follow the Cursor client:
`beforeShellExecution` {command, cwd}, `subagentStart` {task, subagent_type,
subagent_model, git_branch}, `afterFileEdit` {file_path (absolute), edits}, `stop`
{status, loop_count, transcript_path}. Transcripts are JSONL lines
`{"role", "message": {"content": [{"type": "text", "text"}]}}`.

- `shell-guard` denies with `permission: "deny"` and exit 2 (Cursor's block code).
- `spawn-guard` is advisory (FR-008 waive): always `permission: "allow"`, warning in
  `user_message`.
- `owned-path-warn` warns in `agent_message`; `decision-in-chat` warns in
  `followup_message`. Both exit 0.

Hooks are offline: they read the working tree and last-fetched refs, never the network,
and answer in < 300 ms (in process here; end to end for the `.cursor/hooks.json`
command below).
"""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest

from factory.cli import exit_codes
from tests.fixtures.cli_runner import CliResult, FactoryCli
from tests.fixtures.repo_builder import REPO_ROOT, RepoBuilder, message, order, yaml_text

DAY = "20261006"
BUDGET_SECONDS = 0.3
HOOK_COMMAND = "uv run --project scripts/factory factory hook {name}"
CONTRACT_HOOKS = {
    "subagentStart": "spawn-guard",
    "beforeShellExecution": "shell-guard",
    "afterFileEdit": "owned-path-warn",
    "stop": "decision-in-chat",
}


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
    factory_cli: FactoryCli, repo: RepoBuilder, command: str
) -> tuple[CliResult, dict[str, Any]]:
    data = payload(
        "beforeShellExecution", repo.path, command=command, cwd=str(repo.path), sandbox=False
    )
    return call_hook(factory_cli, repo.path, "shell-guard", data)


def assert_denied(factory_cli: FactoryCli, repo: RepoBuilder, command: str) -> None:
    result, response = shell(factory_cli, repo, command)
    assert response.get("permission") == "deny", f"{command!r} was not denied: {response}"
    assert result.exit_code == exit_codes.REFUSED, result
    reason = warning(response, "user_message") + warning(response, "agent_message")
    assert reason.strip(), f"deny without a reason: {response}"


def assert_allowed(factory_cli: FactoryCli, repo: RepoBuilder, command: str) -> None:
    result, response = shell(factory_cli, repo, command)
    assert response.get("permission") == "allow", f"{command!r} was not allowed: {response}"
    assert result.exit_code == exit_codes.OK, result


DENIED_ON_ANY_BRANCH = [
    "git push origin main",
    "git push origin HEAD:main",
    "git push origin refs/heads/main",
    "git push origin wo/wo-20261006-x:refs/heads/main",
    "git push -u origin main",
    "git status && git push origin main",
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

DENIED_ON_MAIN_ONLY = [
    "git commit -m 'quick fix'",
    "git add -A && git commit -m 'quick fix'",
    "git push",
    "git push origin",
    "git push origin HEAD",
]

ALLOWED_ANYWHERE = [
    "ls -la",
    "git status",
    "git log main",
    "git checkout -b wo/wo-20261006-x main",
    "git push origin main-docs",
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


# --- spawn-guard --------------------------------------------------------------------------

REVIEW_PACKET = "notes/packets/2026-10-06-demo-test-review-t.md"


def spawn(factory_cli: FactoryCli, repo: RepoBuilder, task: str) -> str:
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
    assert response.get("permission") == "allow", f"spawn-guard is advisory: {response}"
    return warning(response, "user_message")


def issue(repo: RepoBuilder, order_id: str, *, claimed: bool = True) -> None:
    repo.issue_order(order(order_id, owned_paths=[f"apps/demo/{order_id}/**"]))
    if claimed:
        repo.add_event(order_id, message("claim", order_id=order_id))


def release(repo: RepoBuilder, order_id: str) -> None:
    repo.add_event(order_id, message("release", order_id=order_id))


def worker_task(order_id: str) -> str:
    return f"You are a worker. Read notes/packets/{order_id}.md and implement order {order_id}."


def test_spawn_guard_quiet_for_claimed_order(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    issue(repo, oid("alpha"))
    assert spawn(factory_cli, repo, worker_task(oid("alpha"))) == ""


def test_spawn_guard_warns_without_order_or_review_packet(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    assert spawn(factory_cli, repo, "Refactor the board renderer for me.").strip()


def test_spawn_guard_warns_for_unclaimed_order(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    issue(repo, oid("alpha"), claimed=False)
    assert oid("alpha") in spawn(factory_cli, repo, worker_task(oid("alpha")))


def test_spawn_guard_warns_for_released_order(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    issue(repo, oid("alpha"))
    release(repo, oid("alpha"))
    assert oid("alpha") in spawn(factory_cli, repo, worker_task(oid("alpha")))


def test_spawn_guard_quiet_for_existing_review_packet(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    repo.write(REVIEW_PACKET, "# Review packet\n")
    repo.commit("review packet")
    task = f"You are an independent reviewer. Read {REVIEW_PACKET} and write the verdict."
    assert spawn(factory_cli, repo, task) == ""


def test_spawn_guard_warns_for_missing_review_packet(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    task = f"You are an independent reviewer. Read {REVIEW_PACKET} and write the verdict."
    assert spawn(factory_cli, repo, task).strip()


def test_spawn_guard_warns_at_cap(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
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


def edit(factory_cli: FactoryCli, repo: RepoBuilder, relative: str) -> str:
    data = payload(
        "afterFileEdit",
        repo.path,
        file_path=str(repo.path / relative),
        edits=[{"old_string": "", "new_string": "X = 1\n"}],
    )
    result, response = call_hook(factory_cli, repo.path, "owned-path-warn", data)
    assert result.exit_code == exit_codes.OK, result
    return warning(response, "agent_message")


def on_work_branch(repo: RepoBuilder, owned_paths: list[str]) -> None:
    repo.issue_order(order(WORK, owned_paths=owned_paths))
    repo.add_event(WORK, message("claim", order_id=WORK))
    repo.checkout(f"wo/{WORK}")


def test_owned_path_quiet_inside_owned_paths(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    on_work_branch(repo, ["apps/demo/app/calc.py", "apps/demo/tests/**"])
    assert edit(factory_cli, repo, "apps/demo/app/calc.py") == ""
    assert edit(factory_cli, repo, "apps/demo/tests/unit/test_calc.py") == ""


def test_owned_path_quiet_for_own_bus_dir(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    on_work_branch(repo, ["apps/demo/app/calc.py"])
    assert edit(factory_cli, repo, f"bus/orders/{WORK}/handoff.yaml") == ""


def test_owned_path_warns_outside_owned_paths(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    on_work_branch(repo, ["apps/demo/app/calc.py"])
    text = edit(factory_cli, repo, "deploy/railway/demo.toml")
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


# --- offline and fast ---------------------------------------------------------------------


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
            git_branch="main",
        ),
        "owned-path-warn": payload(
            "afterFileEdit",
            repo.path,
            file_path=str(repo.path / "deploy/railway/demo.toml"),
            edits=[],
        ),
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


@pytest.mark.parametrize("name", sorted(CONTRACT_HOOKS.values()))
def test_hook_runs_offline_within_budget(
    repo: RepoBuilder, factory_cli: FactoryCli, tmp_path: Path, offline: None, name: str
) -> None:
    issue(repo, oid("alpha"))
    repo.git("remote", "set-url", "origin", str(repo.root / "unreachable.git"))
    transcript = write_transcript(tmp_path / "t.jsonl", [("user", "Go."), ("assistant", QUESTION)])
    data = contract_payloads(repo, transcript)[name]
    call_hook(factory_cli, repo.path, name, data)
    started = time.perf_counter()
    call_hook(factory_cli, repo.path, name, data)
    elapsed = time.perf_counter() - started
    assert elapsed < BUDGET_SECONDS, f"{name} took {elapsed * 1000:.0f} ms (budget 300 ms)"


# --- .cursor/hooks.json (the live repo's registration, read only) -------------------------


def live_hooks() -> dict[str, Any]:
    path = REPO_ROOT / ".cursor/hooks.json"
    assert path.is_file(), f"{path} is missing"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), data
    return data


def test_live_hooks_json_registers_every_contract_hook() -> None:
    data = live_hooks()
    assert data.get("version") == 1, data
    hooks = data.get("hooks", {})
    for event, name in CONTRACT_HOOKS.items():
        commands = [entry.get("command") for entry in hooks.get(event, [])]
        assert HOOK_COMMAND.format(name=name) in commands, (event, commands)


@pytest.mark.parametrize(("event", "name"), sorted(CONTRACT_HOOKS.items()))
def test_live_hook_command_answers_within_budget(event: str, name: str, tmp_path: Path) -> None:
    """End to end: the exact `.cursor/hooks.json` command, best of three runs."""
    hooks = live_hooks().get("hooks", {})
    commands = [entry.get("command") for entry in hooks.get(event, [])]
    command = HOOK_COMMAND.format(name=name)
    assert command in commands, (event, commands)
    assert shutil.which("uv"), "uv is not on PATH"
    transcript = write_transcript(tmp_path / "t.jsonl", [("user", "Go."), ("assistant", "Done.")])
    data = {
        "shell-guard": payload(event, REPO_ROOT, command="ls", cwd=str(REPO_ROOT)),
        "spawn-guard": payload(event, REPO_ROOT, task=f"Read {REVIEW_PACKET}.", git_branch="main"),
        "owned-path-warn": payload(
            event, REPO_ROOT, file_path=str(REPO_ROOT / "README.md"), edits=[]
        ),
        "decision-in-chat": payload(
            event, REPO_ROOT, status="completed", loop_count=0, transcript_path=str(transcript)
        ),
    }[name]
    timings = []
    for _ in range(3):
        started = time.perf_counter()
        completed = subprocess.run(
            command.split(),
            cwd=REPO_ROOT,
            input=json.dumps(data),
            capture_output=True,
            text=True,
            check=False,
        )
        timings.append(time.perf_counter() - started)
        assert completed.returncode in (0, 2), completed
        assert isinstance(json.loads(completed.stdout), dict), completed.stdout
    best = min(timings)
    assert best < BUDGET_SECONDS, f"{command} took {best * 1000:.0f} ms at best (budget 300 ms)"
