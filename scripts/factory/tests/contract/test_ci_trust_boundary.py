"""T094 — PR-C1 trusted-base CI (spec D5; D7 Wave 1; delta P* P12).

Contract: contracts/gates.md § CI topology and trust boundary (Workflows, Head as data,
Which gates run, Gate changes take effect after merge, Execution-derived gates, Evidence
bundle, Red-first strength, Artifact provenance, Privileged environment, PR identity,
Shell interpolation, Banned); contracts/cli.md § CI mode.

Replaces the three T059 workflow assertions formerly in test_gate_run.py
(`test_workflow_gate_run_on_the_pr_is_not_allowed_to_fail`,
`test_workflow_can_post_commit_statuses`, `test_workflow_publishes_the_board_in_the_job_summary`):
under D5 the gate step runs in the `workflow_run` job, takes the PR number and head SHA
from the event through `env:`, and is the only job holding `statuses: write`.

Workflows are judged by what the runner and the shell would do, not by text: `run` blocks
are tokenized into simple commands, and `$VAR` arguments are resolved through `env:`.
The trusted job is held to an allowlist (verdict-07 T-C4-1): its steps must equal an
enumerated set of SHA-pinned actions and `run` commands, compared as parsed argv, with
allowlisted keys and env names. Anything else fails, so wrappers (`env`, `command`),
nested shells and git global options need no rule of their own.

Fail-closed reasons named by the red-first judge (each a substring of its message):
`missing` (no bundle), the unexpected file name (wrong or extra file), `unreadable` (not
UTF-8 / not JSON), `size limit`, `schema`, `head_sha`, `crashed`, and the node id of a
test the bundle wrongly lists or omits.
"""

from __future__ import annotations

import importlib
import json
import re
import shlex
import sys
import types
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

from factory.api import PullRequest
from factory.cli import exit_codes
from factory.cli.common import DEPS
from factory.gates.registry import REGISTRY_PATH, load_registry
from tests.fixtures.cli_runner import CliResult, FactoryCli
from tests.fixtures.fake_github import FakeGitHub
from tests.fixtures.repo_builder import BaseHeadPair, RepoBuilder, order, yaml_text
from tests.unit.gates.pr.helpers import assert_blocks, assert_passes, raw_context

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[4]
WORKFLOWS = REPO_ROOT / ".github/workflows"
EVIDENCE_WORKFLOW = WORKFLOWS / "factory-pr-evidence.yml"
GATES_WORKFLOW = WORKFLOWS / "factory-gates.yml"
EVIDENCE_NAME = "Factory PR evidence"
TRUSTED_JOB = "factory-gates"
TRUSTED_PERMISSIONS = {
    "contents": "read",
    "pull-requests": "read",
    "actions": "read",
    "statuses": "write",
}
PR_NUMBER_EXPR = "github.event.workflow_run.pull_requests[0].number"
HEAD_SHA_EXPR = "github.event.workflow_run.head_sha"
RUN_ID_EXPR = "github.event.workflow_run.id"
ENV_EXPRESSIONS = {
    RUN_ID_EXPR,
    HEAD_SHA_EXPR,
    PR_NUMBER_EXPR,
    "secrets.GITHUB_TOKEN",
    "github.token",
    "runner.temp",
}
SAME_REPOSITORY = (
    "github.event.workflow_run.repository.full_name == github.repository",
    "github.event.workflow_run.head_repository.full_name == github.repository",
)
RUNNER_TEMP = "${{ runner.temp }}"
# The `secrets` context, not a path or file name that merely ends in "secrets".
SECRETS_REF = re.compile(r"(?<![\w./-])secrets\.\w+")

BUNDLE_FILE = "factory-evidence.json"
RED_FIRST = "red-first-proof"
SELF_REPORTED = "self-reported:"
ORDER_ID = "wo-20261006-trusted"
HEAD_BRANCH = f"wo/{ORDER_ID}"
CLAMP = "apps/demo/app/clamp.py"
TESTS = "apps/demo/tests/test_clamp.py"
EXISTING_TESTS = "apps/demo/tests/test_existing.py"
CAPS_HIGH = f"{TESTS}::test_clamp_caps_high"
LIFTS_LOW = f"{TESTS}::test_clamp_lifts_low"
EXISTING_NODE = f"{EXISTING_TESTS}::test_existing"
CLAMP_BUGGY = "def clamp(x: int, lo: int, hi: int) -> int:\n    return x\n"
CLAMP_FIXED = "def clamp(x: int, lo: int, hi: int) -> int:\n    return max(lo, min(x, hi))\n"
CLAMP_TESTS = (
    "from app.clamp import clamp\n\n\n"
    "def test_clamp_caps_high() -> None:\n    assert clamp(5, 0, 3) == 3\n\n\n"
    "def test_clamp_lifts_low() -> None:\n    assert clamp(-5, 0, 3) == 0\n"
)
EXISTING_TEST = "def test_existing() -> None:\n    assert True\n"


# =========================================================================================
# Workflow oracles
# =========================================================================================

SEPARATORS = {"&&", "||", ";", "|", "&", "\n", "(", ")"}
REDIRECTS = {">", ">>"}
SUMMARY_FILES = {"$GITHUB_STEP_SUMMARY", "${GITHUB_STEP_SUMMARY}"}
UV_OPTIONS_WITH_VALUE = {"--project", "--directory", "--python", "--with", "--group", "--extra"}
FACTORY_PROJECT = "scripts/factory"
UV_RUN = ("uv", "run", "--locked", "--project", FACTORY_PROJECT)

# The trusted job's allowlist: workflow, job and step keys; env names; actions (each
# pinned to a full commit sha) with their `with:` keys; `run` commands as parsed argv.
TRUSTED_WORKFLOW_KEYS = {"name", "on", True, "permissions", "jobs"}
TRUSTED_JOB_KEYS = {"name", "if", "runs-on", "permissions", "env", "steps"}
TRUSTED_STEP_KEYS = {"name", "if", "uses", "with", "run", "env"}
TRUSTED_ENV_NAMES = {"GITHUB_TOKEN", "PR_NUMBER", "HEAD_SHA", "EVIDENCE_DIR"}
TRUSTED_ACTIONS = {
    "actions/checkout": {"persist-credentials", "fetch-depth"},
    "astral-sh/setup-uv": {"enable-cache"},
    "actions/download-artifact": {"name", "run-id", "path", "github-token"},
}
TRUSTED_COMMANDS = {
    ("uv", "sync", "--locked", "--project", FACTORY_PROJECT),
    (
        *UV_RUN,
        "factory",
        "gate",
        "run",
        "--pr",
        "$PR_NUMBER",
        "--expect-head",
        "$HEAD_SHA",
        "--evidence",
        "$EVIDENCE_DIR",
    ),
    (*UV_RUN, "factory", "status", ">>", "$GITHUB_STEP_SUMMARY"),
}
TRUSTED_STEPS = sorted(
    [("uses", (action,)) for action in TRUSTED_ACTIONS]
    + [("run", command) for command in TRUSTED_COMMANDS]
)
PINNED_SHA = re.compile(r"[0-9a-f]{40}")


def load_workflow(path: Path) -> dict[str, Any]:
    assert path.is_file(), f"{path.relative_to(REPO_ROOT)} is missing"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), data
    return data


def triggers(workflow: dict[str, Any]) -> dict[str, Any]:
    """`on:` as a mapping (PyYAML reads the bare key `on` as `True`)."""
    on = workflow.get("on", workflow.get(True))
    if isinstance(on, str):
        return {on: None}
    if isinstance(on, list):
        return dict.fromkeys(on)
    return dict(on or {})


def jobs(workflow: dict[str, Any]) -> dict[str, dict[str, Any]]:
    found = workflow.get("jobs") or {}
    assert isinstance(found, dict), found
    return found


def steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return list(job.get("steps") or [])


def uses(step: dict[str, Any]) -> str:
    return str(step.get("uses") or "").split("@", 1)[0]


def step_with(step: dict[str, Any]) -> dict[str, Any]:
    return dict(step.get("with") or {})


def expression(value: object) -> str | None:
    """The body of a whole `${{ ... }}` value, else None."""
    match = re.fullmatch(r"\s*\$\{\{\s*(.*?)\s*\}\}\s*", str(value), flags=re.S)
    return match.group(1) if match else None


def expressions_in(value: object) -> list[str]:
    return [body.strip() for body in re.findall(r"\$\{\{(.*?)\}\}", str(value), flags=re.S)]


def is_false(value: object) -> bool:
    return value is False or str(value).strip().lower() == "false"


def shell_commands(run: str) -> list[tuple[list[str], list[str]]]:
    """Simple commands in a `run` block, each as (tokens, separator that follows it)."""
    text = run.replace("\\\n", " ")
    commands: list[tuple[list[str], list[str]]] = []
    for line in text.splitlines():
        lexer = shlex.shlex(line, posix=True, punctuation_chars=";&|()<>")
        lexer.whitespace_split = True
        lexer.commenters = "#"
        current: list[str] = []
        for token in lexer:
            if token in SEPARATORS:
                if current:
                    commands.append((current, [token]))
                current = []
            else:
                current.append(token)
        if current:
            commands.append((current, ["\n"]))
    return commands


def raw_argv(tokens: list[str]) -> list[str]:
    """Drop leading env assignments and redirections."""
    argv: list[str] = []
    skip = False
    for token in tokens:
        if skip:
            skip = False
            continue
        if token in REDIRECTS or token == "<":
            skip = True
            continue
        argv.append(token)
    while argv and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", argv[0]):
        argv = argv[1:]
    return argv


def uv_run_options(argv: list[str]) -> tuple[dict[str, str | None], list[str]]:
    """For `uv run [options] program ...`: (options, program argv)."""
    rest = argv[2:]
    options: dict[str, str | None] = {}
    while rest and rest[0].startswith("-"):
        option = rest.pop(0)
        if "=" in option:
            key, value = option.split("=", 1)
            options[key] = value
        elif option in UV_OPTIONS_WITH_VALUE:
            options[option] = rest.pop(0) if rest else None
        else:
            options[option] = None
    return options, rest


def program_argv(tokens: list[str]) -> list[str]:
    """Drop env assignments, a `uv run [options]` prefix and redirections."""
    argv = raw_argv(tokens)
    if argv[:2] == ["uv", "run"]:
        return uv_run_options(argv)[1]
    return argv


def env_name(token: str) -> str | None:
    match = re.fullmatch(r"\$(?:\{(\w+)\}|(\w+))", token)
    return (match.group(1) or match.group(2)) if match else None


def resolved(token: str, env: dict[str, Any]) -> str:
    """A `$VAR` / `${VAR}` argument resolved through `env:`, else the token itself."""
    name = env_name(token)
    if name is None:
        return token
    return str(env.get(name, token))


def canonical_path(text: str) -> str:
    text = re.sub(r"\$\{\{\s*runner\.temp\s*\}\}", RUNNER_TEMP, text.strip())
    text = re.sub(r"^\$\{?RUNNER_TEMP\}?", RUNNER_TEMP, text)
    return text.rstrip("/")


def options_of(argv: list[str], allowed: set[str]) -> dict[str, str] | None:
    """`--key value` / `--key=value` pairs, each allowed key exactly once; else None."""
    parsed: dict[str, str] = {}
    index = 0
    while index < len(argv):
        key = argv[index]
        if key.startswith("--") and "=" in key:
            key, value = key.split("=", 1)
            index += 1
        elif index + 1 < len(argv):
            value = argv[index + 1]
            index += 2
        else:
            return None
        if key not in allowed or key in parsed:
            return None
        parsed[key] = value
    return parsed if set(parsed) == allowed else None


def gate_invocation(run: str, env: dict[str, Any]) -> dict[str, str] | None:
    """The block is exactly one `factory gate run --pr --expect-head --evidence` command
    (its exit status is the step's), each value resolved through `env:`; else None."""
    commands = shell_commands(run)
    if len(commands) != 1:
        return None
    argv = program_argv(commands[0][0])
    if argv[:3] != ["factory", "gate", "run"]:
        return None
    parsed = options_of(argv[3:], {"--pr", "--expect-head", "--evidence"})
    if parsed is None:
        return None
    return {key: resolved(value, env) for key, value in parsed.items()}


def gate_step_is_bound(run: str, env: dict[str, Any], evidence_path: str) -> bool:
    found = gate_invocation(run, env)
    return (
        found is not None
        and expression(found["--pr"]) == PR_NUMBER_EXPR
        and expression(found["--expect-head"]) == HEAD_SHA_EXPR
        and canonical_path(found["--evidence"]) == canonical_path(evidence_path)
    )


def mentions(run: str, *words: str) -> bool:
    return any(
        program_argv(tokens)[: len(words)] == list(words)
        for tokens, _ in shell_commands(run)
        if tokens
    )


Signature = tuple[str, tuple[str, ...]]


def step_signature(step: dict[str, Any]) -> Signature | None:
    """`("uses", (action,))` or `("run", argv)` for one action or one command, else None."""
    if "uses" in step and "run" not in step:
        return ("uses", (uses(step),))
    if "run" in step and "uses" not in step:
        commands = shell_commands(str(step["run"]))
        if len(commands) == 1:
            return ("run", tuple(commands[0][0]))
    return None


def unlisted_env(scope: dict[str, Any]) -> list[str]:
    return sorted(set(scope.get("env") or {}) - TRUSTED_ENV_NAMES)


def step_problems(job_steps: list[dict[str, Any]]) -> list[str]:
    """Why the steps differ from the trusted allowlist (empty when they equal it)."""
    problems: list[str] = []
    signatures: list[Signature] = []
    for step in job_steps:
        label = f"step {step.get('name')!r}"
        if set(step) - TRUSTED_STEP_KEYS:
            problems.append(f"{label}: unlisted keys {sorted(set(step) - TRUSTED_STEP_KEYS)}")
        if unlisted_env(step):
            problems.append(f"{label}: unlisted env {unlisted_env(step)}")
        signature = step_signature(step)
        if signature is None:
            problems.append(f"{label}: not exactly one action or one command")
            continue
        kind, value = signature
        if kind == "uses":
            action, pin = value[0], str(step["uses"]).partition("@")[2]
            if action not in TRUSTED_ACTIONS:
                problems.append(f"{label}: unlisted action {step['uses']!r}")
            elif not PINNED_SHA.fullmatch(pin):
                problems.append(f"{label}: {action} is not pinned to a commit sha ({pin!r})")
            elif set(step_with(step)) - TRUSTED_ACTIONS[action]:
                extra = sorted(set(step_with(step)) - TRUSTED_ACTIONS[action])
                problems.append(f"{label}: unlisted `with:` keys {extra}")
        elif value not in TRUSTED_COMMANDS:
            problems.append(f"{label}: unlisted command {list(value)}")
        signatures.append(signature)
    if sorted(signatures) != TRUSTED_STEPS:
        problems.append(f"steps {sorted(signatures)} are not exactly {TRUSTED_STEPS}")
    return problems


def publishes_status_to_summary(run: str) -> bool:
    """`factory status` stdout goes to the summary: redirected, or piped into `tee -a`."""
    commands = shell_commands(run)
    for index, (tokens, after) in enumerate(commands):
        if program_argv(tokens)[:2] != ["factory", "status"]:
            continue
        if any(
            token in REDIRECTS and nxt in SUMMARY_FILES
            for token, nxt in zip(tokens, tokens[1:], strict=False)
        ):
            return True
        if after == ["|"] and index + 1 < len(commands):
            tee = commands[index + 1][0]
            if tee[:1] == ["tee"] and {"-a", "--append"} & set(tee) and SUMMARY_FILES & set(tee):
                return True
    return False


def condition_never_skips(condition: object) -> bool:
    if condition is None:
        return True
    text = expression(condition) or str(condition).strip()
    return text in {"always()", "!cancelled()"}


def grants_status_write(permissions: object) -> bool:
    if permissions == "write-all":
        return True
    return isinstance(permissions, dict) and permissions.get("statuses") == "write"


def effective_permissions(workflow: dict[str, Any], job: dict[str, Any]) -> object:
    return job["permissions"] if "permissions" in job else workflow.get("permissions")


def status_writers(workflow: dict[str, Any]) -> list[str]:
    return [
        name
        for name, job in jobs(workflow).items()
        if grants_status_write(effective_permissions(workflow, job))
        or effective_permissions(workflow, job) is None
    ]


def pull_request_target_problems(workflow: dict[str, Any]) -> list[str]:
    """`pull_request_target` with a head checkout or any executed step."""
    if "pull_request_target" not in triggers(workflow):
        return []
    problems = []
    for name, job in jobs(workflow).items():
        for step in steps(job):
            if uses(step) == "actions/checkout" and "ref" in step_with(step):
                problems.append(f"{name}: checkout ref {step_with(step)['ref']!r}")
            if "run" in step:
                problems.append(f"{name}: run step {step.get('name') or step['run']!r}")
    return problems


def pull_request_problems(workflow: dict[str, Any], text: str) -> list[str]:
    """A `pull_request` workflow: no status write (explicit or by default), no secrets."""
    if not {"pull_request", "pull_request_target"} & set(triggers(workflow)):
        return []
    problems = [f"{name}: can write statuses" for name in status_writers(workflow)]
    problems += [f"references {ref}" for ref in sorted(set(SECRETS_REF.findall(text)))]
    return problems


# --- oracle self-tests ---------------------------------------------------------------------

GOOD_ENV = {
    "PR_NUMBER": f"${{{{ {PR_NUMBER_EXPR} }}}}",
    "HEAD_SHA": f"${{{{ {HEAD_SHA_EXPR} }}}}",
    "EVIDENCE_DIR": "${{ runner.temp }}/factory-evidence",
}
GOOD_EVIDENCE_PATH = "${{ runner.temp }}/factory-evidence"
GATE_REAL = [
    'uv run --project scripts/factory factory gate run --pr "$PR_NUMBER" '
    '--expect-head "$HEAD_SHA" --evidence "$EVIDENCE_DIR"',
    'uv run --locked --project scripts/factory factory gate run --evidence "${EVIDENCE_DIR}" '
    '--pr "${PR_NUMBER}" --expect-head "${HEAD_SHA}"',
]
GATE_NO_OPS = [
    "echo factory gate run --pr $PR_NUMBER --expect-head $HEAD_SHA --evidence $EVIDENCE_DIR",
    "# factory gate run --pr $PR_NUMBER --expect-head $HEAD_SHA --evidence $EVIDENCE_DIR",
    f"{GATE_REAL[0]} || true",
    f"{GATE_REAL[0]}; exit 0",
    f"{GATE_REAL[0]} | tee log",
    f"set +e\n{GATE_REAL[0]}",
    'uv run --project scripts/factory factory gate run --pr "$PR_NUMBER" '
    '--evidence "$EVIDENCE_DIR"',
    f"{GATE_REAL[0]} --gate bus.schema",
    'uv run --project scripts/factory factory gate run --pr 1 --expect-head "$HEAD_SHA" '
    '--evidence "$EVIDENCE_DIR"',
    'uv run --project scripts/factory factory gate run --pr "$PR_NUMBER" --expect-head "$HEAD_SHA" '
    "--evidence ./evidence",
]
SUMMARY_NO_OPS = [
    "echo 'factory status' >> \"$GITHUB_STEP_SUMMARY\"",
    "uv run --project scripts/factory factory status",
    "uv run --project scripts/factory factory status | tee board.md",
]
SUMMARY_REAL = [
    'uv run --project scripts/factory factory status >> "$GITHUB_STEP_SUMMARY"',
    "uv run --project scripts/factory factory status | tee -a $GITHUB_STEP_SUMMARY",
]
PR_TARGET_BANNED = [
    {
        "on": {"pull_request_target": None},
        "jobs": {
            "j": {
                "steps": [
                    {
                        "uses": "actions/checkout@v4",
                        "with": {"ref": "${{ github.event.pull_request.head.sha }}"},
                    }
                ]
            }
        },
    },
    {"on": ["pull_request_target"], "jobs": {"j": {"steps": [{"run": "make test"}]}}},
]
PR_TARGET_ALLOWED = [
    {
        "on": {"pull_request_target": None},
        "jobs": {"j": {"steps": [{"uses": "actions/labeler@v5"}]}},
    },
    {"on": {"pull_request": None}, "jobs": {"j": {"steps": [{"run": "make test"}]}}},
]
PR_BANNED = [
    {"on": {"pull_request": None}, "jobs": {"j": {"permissions": {"statuses": "write"}}}},
    {"on": {"pull_request": None}, "permissions": "write-all", "jobs": {"j": {}}},
    {"on": {"pull_request": None}, "jobs": {"j": {}}},
]
PR_ALLOWED = [
    {"on": {"pull_request": None}, "permissions": {"contents": "read"}, "jobs": {"j": {}}},
    {"on": {"push": None}, "jobs": {"j": {"permissions": {"statuses": "write"}}}},
]


def check_gate_oracle() -> None:
    for run in GATE_REAL:
        assert gate_step_is_bound(run, GOOD_ENV, GOOD_EVIDENCE_PATH), f"oracle rejects {run!r}"
    for run in GATE_NO_OPS:
        assert not gate_step_is_bound(run, GOOD_ENV, GOOD_EVIDENCE_PATH), f"accepts {run!r}"
    assert not condition_never_skips("failure()")
    assert condition_never_skips("${{ !cancelled() }}")


def check_summary_oracle() -> None:
    for run in SUMMARY_NO_OPS:
        assert not publishes_status_to_summary(run), f"oracle accepts a no-op: {run!r}"
    for run in SUMMARY_REAL:
        assert publishes_status_to_summary(run), f"oracle rejects a real summary: {run!r}"


def check_pull_request_oracles() -> None:
    for workflow in PR_TARGET_BANNED:
        assert pull_request_target_problems(workflow), workflow
    for workflow in PR_TARGET_ALLOWED:
        assert not pull_request_target_problems(workflow), workflow
    for workflow in PR_BANNED:
        assert pull_request_problems(workflow, ""), workflow
    for workflow in PR_ALLOWED:
        assert not pull_request_problems(workflow, ""), workflow
    assert pull_request_problems(PR_ALLOWED[0], "token: ${{ secrets.DEPLOY_TOKEN }}")
    assert pull_request_problems(PR_ALLOWED[0], "token: ${{secrets.DEPLOY_TOKEN}}")
    for path in ("scripts/test_sync_runtime_secrets.py", "app/secrets.py", "x-secrets.yaml"):
        assert not pull_request_problems(PR_ALLOWED[0], f"run: pytest {path}"), path


# =========================================================================================
# Untrusted workflow: factory-pr-evidence.yml
# =========================================================================================


def evidence_workflow() -> dict[str, Any]:
    return load_workflow(EVIDENCE_WORKFLOW)


def test_evidence_workflow_is_read_only_on_pull_request() -> None:
    workflow = evidence_workflow()
    assert workflow.get("name") == EVIDENCE_NAME, workflow.get("name")
    on = triggers(workflow)
    assert "pull_request" in on, on
    assert not {"pull_request_target", "workflow_run"} & set(on), on
    assert workflow.get("permissions") == {"contents": "read"}, workflow.get("permissions")
    for name, job in jobs(workflow).items():
        assert job.get("permissions", {"contents": "read"}) == {"contents": "read"}, name
    text = EVIDENCE_WORKFLOW.read_text(encoding="utf-8")
    assert not SECRETS_REF.findall(text), "the evidence workflow references secrets"
    for name, job in jobs(workflow).items():
        for step in steps(job):
            run = str(step.get("run") or "")
            assert not mentions(run, "factory", "gate", "run"), f"{name} runs the gates: {run}"


def test_evidence_workflow_has_the_tests_job_and_the_red_first_producer() -> None:
    workflow_jobs = jobs(evidence_workflow())
    assert workflow_jobs.get("factory-tests", {}).get("name") == "Factory tests", workflow_jobs
    producer = workflow_jobs.get("red-first-evidence")
    assert producer is not None, sorted(workflow_jobs)
    env = {**(evidence_workflow().get("env") or {}), **(producer.get("env") or {})}
    runs = [(step, {**env, **(step.get("env") or {})}) for step in steps(producer)]
    calls = [
        (options_of(program_argv(tokens)[3:], {"--base", "--head", "--out"}), step_env)
        for step, step_env in runs
        for tokens, _ in shell_commands(str(step.get("run") or ""))
        if program_argv(tokens)[:3] == ["factory", "gate", "evidence"]
    ]
    assert len(calls) == 1, f"expected one `factory gate evidence` call: {calls}"
    ((parsed, step_env),) = calls
    assert parsed is not None, "`factory gate evidence` needs exactly --base, --head and --out"
    values = {key: resolved(value, step_env) for key, value in parsed.items()}
    assert expression(values["--base"]) == "github.event.pull_request.base.sha", values
    assert expression(values["--head"]) == "github.event.pull_request.head.sha", values
    uploads = [step for step in steps(producer) if uses(step) == "actions/upload-artifact"]
    assert len(uploads) == 1, uploads
    upload = step_with(uploads[0])
    assert upload.get("name") == "factory-evidence", upload
    assert canonical_path(str(upload.get("path"))) == canonical_path(values["--out"]), upload


def test_evidence_workflow_runs_the_full_factory_suite() -> None:
    """PR-C5 (T100): no marker, keyword or deselect selector once A and B are in C."""
    job = jobs(evidence_workflow()).get("factory-tests", {})
    runs = [str(step.get("run") or "") for step in steps(job)]
    syncs = [run for run in runs if mentions(run, "uv", "sync")]
    assert any("--locked" in run for run in syncs), runs
    pytest_calls = [
        program_argv(tokens)
        for run in runs
        for tokens, _ in shell_commands(run)
        if program_argv(tokens)[:1] == ["pytest"]
    ]
    assert len(pytest_calls) == 1, runs
    selectors = {"-m", "-k", "--deselect"}
    assert not [arg for arg in pytest_calls[0] if arg.split("=")[0] in selectors], pytest_calls


# =========================================================================================
# Trusted workflow: factory-gates.yml
# =========================================================================================


def gates_workflow() -> dict[str, Any]:
    return load_workflow(GATES_WORKFLOW)


def trusted_job() -> dict[str, Any]:
    """The `factory-gates` job; trusted only because `workflow_run` checks out `main`."""
    workflow = gates_workflow()
    assert set(triggers(workflow)) == {"workflow_run"}, (
        f"{GATES_WORKFLOW.name} must run only on workflow_run: {sorted(triggers(workflow))}"
    )
    job = jobs(workflow).get(TRUSTED_JOB)
    assert isinstance(job, dict), f"{TRUSTED_JOB} job is missing"
    return job


def trusted_steps() -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Each trusted step with its effective env (workflow < job < step)."""
    workflow, job = gates_workflow(), trusted_job()
    env = {**(workflow.get("env") or {}), **(job.get("env") or {})}
    return [(step, {**env, **(step.get("env") or {})}) for step in steps(job)]


def download_steps() -> list[dict[str, Any]]:
    return [step for step, _ in trusted_steps() if uses(step) == "actions/download-artifact"]


def test_gates_workflow_runs_only_on_completed_evidence_runs() -> None:
    """`workflow_run` takes the workflow file from the default branch, so a PR that edits
    either workflow or any gate is judged by `main`'s current gates (D5 (3))."""
    on = triggers(gates_workflow())
    assert set(on) == {"workflow_run"}, on
    workflow_run = on["workflow_run"] or {}
    assert workflow_run.get("workflows") == [EVIDENCE_NAME], workflow_run
    assert workflow_run.get("types") == ["completed"], workflow_run


def test_trusted_job_permissions_are_exactly_the_contract_set() -> None:
    assert trusted_job().get("permissions") == TRUSTED_PERMISSIONS, trusted_job().get("permissions")
    top = gates_workflow().get("permissions")
    assert top is None or (isinstance(top, dict) and "write" not in top.values()), top


def test_trusted_job_skips_runs_from_another_repository() -> None:
    condition = re.sub(r"\s+", " ", str(trusted_job().get("if") or ""))
    body = expression(condition) or condition
    for comparison in SAME_REPOSITORY:
        assert comparison in body, f"job `if:` lacks {comparison!r}: {condition!r}"
    assert "||" not in body, condition


def test_trusted_job_checks_out_main_only_without_credentials() -> None:
    """No `ref`/`repository` (the `with:` allowlist), so `workflow_run` checks out `main`."""
    checkouts = [step for step, _ in trusted_steps() if uses(step) == "actions/checkout"]
    assert len(checkouts) == 1, checkouts
    assert is_false(step_with(checkouts[0]).get("persist-credentials")), checkouts


def test_trusted_job_is_exactly_the_allowlist() -> None:
    """Supersedes the denylist oracle `head_code_reason` (verdict-07 T-C4-1)."""
    workflow, job = gates_workflow(), trusted_job()
    assert set(workflow) <= TRUSTED_WORKFLOW_KEYS, sorted(map(str, workflow))
    assert set(jobs(workflow)) == {TRUSTED_JOB}, sorted(jobs(workflow))
    assert set(job) <= TRUSTED_JOB_KEYS, sorted(job)
    assert not unlisted_env(job), unlisted_env(job)
    assert step_problems(steps(job)) == []


BYPASS_FORMS = [
    ("env wrapper", "env bash -c 'git checkout \"$HEAD_SHA\" && python steal.py'"),
    ("command wrapper", "command bash -c 'git checkout \"$HEAD_SHA\" && python steal.py'"),
    ("git global option", 'git -C . checkout "$HEAD_SHA"'),
    ("unlisted command", 'echo "$HEAD_SHA"'),
]


@pytest.mark.parametrize(("label", "run"), BYPASS_FORMS, ids=[f[0] for f in BYPASS_FORMS])
def test_trusted_allowlist_rejects_a_step_it_does_not_list(label: str, run: str) -> None:
    """Regression for T-C4-1's class: the forms the denylist let through, plus any other."""
    injected = {"name": label, "run": run}
    problems = step_problems([*steps(trusted_job()), injected])
    assert any(problem.startswith(f"step {label!r}: unlisted command") for problem in problems), (
        problems
    )


def test_trusted_runs_take_expressions_only_through_env() -> None:
    workflow, job = gates_workflow(), trusted_job()
    for scope in (workflow.get("env") or {}, job.get("env") or {}):
        for value in scope.values():
            assert set(expressions_in(value)) <= ENV_EXPRESSIONS, value
    for step, _ in trusted_steps():
        for value in (step.get("env") or {}).values():
            assert set(expressions_in(value)) <= ENV_EXPRESSIONS, value


def test_trusted_job_downloads_only_the_triggering_runs_evidence() -> None:
    """P12: exact run id, this repository, exact name, a fresh directory outside the checkout."""
    found = download_steps()
    assert len(found) == 1, f"expected one download-artifact step: {found}"
    options = step_with(found[0])
    assert options.get("name") == "factory-evidence", options
    assert expression(options.get("run-id")) == RUN_ID_EXPR, options
    assert canonical_path(str(options.get("path") or "")).startswith(f"{RUNNER_TEMP}/"), options


def test_trusted_job_restores_no_cache() -> None:
    """P12: no cache a PR-triggered workflow can write; GitHub-hosted runner."""
    runs_on = trusted_job().get("runs-on")
    assert isinstance(runs_on, str) and runs_on.startswith("ubuntu-"), runs_on
    for step, _ in trusted_steps():
        if uses(step) == "astral-sh/setup-uv":
            assert is_false(step_with(step).get("enable-cache")), step


def test_trusted_gate_step_runs_every_gate_bound_to_the_event() -> None:
    """Supersedes `test_workflow_gate_run_on_the_pr_is_not_allowed_to_fail` (T059)."""
    check_gate_oracle()
    (download,) = download_steps()
    evidence_path = str(step_with(download).get("path"))
    gate_steps = [
        (index, step, env)
        for index, (step, env) in enumerate(trusted_steps())
        if mentions(str(step.get("run") or ""), "factory", "gate", "run")
    ]
    assert len(gate_steps) == 1, f"expected one `factory gate run` step: {gate_steps}"
    ((index, step, env),) = gate_steps
    assert gate_step_is_bound(str(step["run"]), env, evidence_path), (
        "the gate step must be exactly `factory gate run --pr <event PR> --expect-head "
        f"<event head sha> --evidence <download path>`: {step}"
    )
    assert condition_never_skips(step.get("if")), step.get("if")
    download_index = next(i for i, (s, _) in enumerate(trusted_steps()) if s == download)
    assert download_index < index, "the evidence is downloaded after the gates ran"


def test_trusted_job_publishes_the_board_in_the_job_summary() -> None:
    """Supersedes `test_workflow_publishes_the_board_in_the_job_summary` (T059)."""
    check_summary_oracle()
    all_steps = [step for step, _ in trusted_steps()]
    summary = [
        i for i, s in enumerate(all_steps) if publishes_status_to_summary(str(s.get("run") or ""))
    ]
    assert len(summary) == 1, "expected one step writing `factory status` to the summary"
    gate = [
        i
        for i, s in enumerate(all_steps)
        if mentions(str(s.get("run") or ""), "factory", "gate", "run")
    ]
    assert gate, all_steps
    step = all_steps[summary[0]]
    condition = str(step.get("if", ""))
    runs_after_failure = "always()" in condition or "!cancelled()" in condition
    assert summary[0] < gate[0] or runs_after_failure, step


# =========================================================================================
# Repository-wide bans
# =========================================================================================


def every_workflow() -> Iterator[tuple[str, dict[str, Any], str]]:
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        text = path.read_text(encoding="utf-8")
        yield path.name, yaml.safe_load(text), text


def test_pull_request_triggers_hold_no_status_write_secret_or_head_execution() -> None:
    """Banned: `pull_request_target` with a head checkout or execution; a `pull_request`
    job that can write statuses (explicitly or by default token) or reads secrets."""
    check_pull_request_oracles()
    problems = {
        name: pull_request_target_problems(wf) + pull_request_problems(wf, text)
        for name, wf, text in every_workflow()
    }
    assert not {name: found for name, found in problems.items() if found}, problems


def test_only_the_trusted_job_holds_statuses_write() -> None:
    """Supersedes `test_workflow_can_post_commit_statuses` (T059)."""
    trusted_job()
    writers = {
        (name, job)
        for name, workflow, _ in every_workflow()
        for job, spec in jobs(workflow).items()
        if grants_status_write(effective_permissions(workflow, spec))
    }
    assert writers == {(GATES_WORKFLOW.name, TRUSTED_JOB)}, writers


# =========================================================================================
# `factory gate run` in CI mode (fixture repos + FakeGitHub)
# =========================================================================================


def head_as_data(repo: RepoBuilder, pair: BaseHeadPair) -> PullRequest:
    """Open the PR, then drop every head ref: the trusted job fetches the head by SHA."""
    pr = repo.make_pr(pair.head_branch)
    repo.git("branch", "-D", pair.head_branch)
    repo.git("update-ref", "-d", f"refs/remotes/origin/{pair.head_branch}")
    return pr


def fact(
    node_id: str, base: str = "failed", head: str = "passed", base_error: str | None = None
) -> dict[str, Any]:
    return {
        "node_id": node_id,
        "base_outcome": base,
        "head_outcome": head,
        "base_error": base_error,
    }


def bundle(
    pair: BaseHeadPair,
    tests: list[dict[str, Any]],
    *,
    status: str = "ran",
    error: str | None = None,
    head_sha: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "factory-evidence",
        "base_sha": pair.base_sha,
        "head_sha": head_sha or pair.head_sha,
        "red_first": {"status": status, "error": error, "tests": tests},
    }


def evidence_dir(tmp_path: Path, files: dict[str, bytes | dict[str, Any]]) -> Path:
    directory = tmp_path / "evidence"
    directory.mkdir()
    for name, content in files.items():
        data = content if isinstance(content, bytes) else json.dumps(content).encode()
        (directory / name).write_bytes(data)
    return directory


def clamp_pair(repo: RepoBuilder, *, base_has_clamp: bool = True) -> BaseHeadPair:
    base = {EXISTING_TESTS: EXISTING_TEST, "apps/demo/app/__init__.py": ""}
    if base_has_clamp:
        base[CLAMP] = CLAMP_BUGGY
    head: dict[str, str | None] = {
        CLAMP: CLAMP_FIXED,
        TESTS: CLAMP_TESTS,
        f"bus/orders/{ORDER_ID}/order.yaml": yaml_text(order(ORDER_ID)),
    }
    return repo.base_head_pair(base, head, head_branch=HEAD_BRANCH)


def ci_run(
    factory_cli: FactoryCli,
    repo: RepoBuilder,
    pr: PullRequest,
    *gates: str,
    expect_head: str | None = None,
    evidence: Path | None = None,
) -> CliResult:
    args = ["gate", "run"]
    for gate in gates:
        args += ["--gate", gate]
    args += ["--pr", str(pr.number), "--expect-head", expect_head or pr.head_sha]
    if evidence is not None:
        args += ["--evidence", str(evidence)]
    args.append("--json")
    return factory_cli(*args, repo=repo.path)


def report(result: CliResult) -> dict[str, Any]:
    try:
        envelope = json.loads(result.stdout)
    except ValueError as exc:
        raise AssertionError(
            f"exit {result.exit_code}; --json stdout is not one JSON document: "
            f"{result.stdout!r}\nstderr: {result.stderr}"
        ) from exc
    assert isinstance(envelope, dict), envelope
    body = (
        envelope.get("data") if envelope.get("ok") else (envelope.get("error") or {}).get("details")
    )
    assert isinstance(body, dict), envelope
    return body


def entry(body: dict[str, Any], gate_id: str) -> dict[str, Any]:
    matches = [g for g in body.get("gates", []) if g.get("id") == gate_id]
    assert len(matches) == 1, body
    return matches[0]


def statuses(github: FakeGitHub) -> dict[tuple[str, str], Any]:
    return {(status.sha, status.context): status for status in github.statuses}


def assert_red_first(
    result: CliResult, github: FakeGitHub, head_sha: str, outcome: str, *needles: str
) -> None:
    expected_exit = exit_codes.OK if outcome == "pass" else exit_codes.GATE_FAILURE
    assert result.exit_code == expected_exit, (
        f"expected exit {expected_exit}, got {result.exit_code}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    gate = entry(report(result), RED_FIRST)
    assert gate.get("outcome") == outcome, gate
    text = "\n".join(gate.get("messages", []))
    for needle in needles:
        assert needle.lower() in text.lower(), f"red-first does not name {needle!r}: {text}"
    posted = statuses(github).get((head_sha, f"factory/{RED_FIRST}"))
    assert posted is not None, sorted(statuses(github))
    assert posted.value == ("success" if outcome == "pass" else "failure"), posted.value
    assert posted.description.startswith(SELF_REPORTED), posted.description


def test_valid_red_to_green_bundle_passes_as_self_reported(
    repo: RepoBuilder, factory_cli: FactoryCli, fake_github: FakeGitHub, tmp_path: Path
) -> None:
    pair = clamp_pair(repo)
    pr = head_as_data(repo, pair)
    evidence = evidence_dir(
        tmp_path, {BUNDLE_FILE: bundle(pair, [fact(CAPS_HIGH), fact(LIFTS_LOW)])}
    )
    result = ci_run(factory_cli, repo, pr, RED_FIRST, "bus.schema", evidence=evidence)
    assert_red_first(result, fake_github, pair.head_sha, "pass", "self-reported")
    assert {sha for sha, _ in statuses(fake_github)} == {pair.head_sha}
    assert {context for _, context in statuses(fake_github)} == {
        f"factory/{RED_FIRST}",
        "factory/bus.schema",
    }


def test_import_error_on_base_is_red_only_for_a_module_the_pr_adds(
    repo: RepoBuilder, factory_cli: FactoryCli, fake_github: FakeGitHub, tmp_path: Path
) -> None:
    pair = clamp_pair(repo, base_has_clamp=False)
    pr = head_as_data(repo, pair)
    added = "ModuleNotFoundError: No module named 'app.clamp'"
    good = bundle(
        pair,
        [
            fact(CAPS_HIGH, "not_collected", base_error=added),
            fact(LIFTS_LOW, "error", "passed", added),
        ],
    )
    result = ci_run(
        factory_cli, repo, pr, RED_FIRST, evidence=evidence_dir(tmp_path, {BUNDLE_FILE: good})
    )
    assert_red_first(result, fake_github, pair.head_sha, "pass")
    fake_github.statuses.clear()
    gone = "ModuleNotFoundError: No module named 'vendor_sdk_that_is_gone'"
    broken = bundle(
        pair,
        [fact(CAPS_HIGH, "not_collected", base_error=gone), fact(LIFTS_LOW)],
    )
    other = tmp_path / "second"
    other.mkdir()
    result = ci_run(
        factory_cli, repo, pr, RED_FIRST, evidence=evidence_dir(other, {BUNDLE_FILE: broken})
    )
    assert_red_first(result, fake_github, pair.head_sha, "fail", CAPS_HIGH)


@pytest.mark.parametrize(
    ("label", "facts", "needle"),
    [
        ("passes on base", [fact(CAPS_HIGH, "passed"), fact(LIFTS_LOW)], CAPS_HIGH),
        ("skipped on base", [fact(CAPS_HIGH, "skipped"), fact(LIFTS_LOW)], CAPS_HIGH),
        ("fails on head", [fact(CAPS_HIGH), fact(LIFTS_LOW, head="failed")], LIFTS_LOW),
        ("errors on head", [fact(CAPS_HIGH), fact(LIFTS_LOW, head="error")], LIFTS_LOW),
    ],
)
def test_judge_applies_the_red_first_rule_to_the_raw_facts(
    repo: RepoBuilder,
    factory_cli: FactoryCli,
    fake_github: FakeGitHub,
    tmp_path: Path,
    label: str,
    facts: list[dict[str, Any]],
    needle: str,
) -> None:
    pair = clamp_pair(repo)
    pr = head_as_data(repo, pair)
    evidence = evidence_dir(tmp_path, {BUNDLE_FILE: bundle(pair, facts)})
    result = ci_run(factory_cli, repo, pr, RED_FIRST, evidence=evidence)
    assert_red_first(result, fake_github, pair.head_sha, "fail", needle)


def good_facts() -> list[dict[str, Any]]:
    return [fact(CAPS_HIGH), fact(LIFTS_LOW)]


def with_red_first(pair: BaseHeadPair, **red_first: Any) -> dict[str, Any]:
    data = bundle(pair, good_facts())
    data["red_first"].update(red_first)
    return data


def with_top(pair: BaseHeadPair, **fields: Any) -> dict[str, Any]:
    data = bundle(pair, good_facts())
    data.update(fields)
    return data


def with_fact(pair: BaseHeadPair, **fields: Any) -> dict[str, Any]:
    data = bundle(pair, good_facts())
    data["red_first"]["tests"][0].update(fields)
    return data


BundleCase = Callable[[BaseHeadPair, int], dict[str, bytes | dict[str, Any]] | None]
FAIL_CLOSED: list[tuple[str, BundleCase, str]] = [
    ("no --evidence", lambda pair, limit: None, "missing"),
    ("empty directory", lambda pair, limit: {}, "missing"),
    (
        "wrong file name",
        lambda pair, limit: {"bundle.json": bundle(pair, good_facts())},
        "bundle.json",
    ),
    (
        "second file",
        lambda pair, limit: {BUNDLE_FILE: bundle(pair, good_facts()), "extra.json": b"{}"},
        "extra.json",
    ),
    ("not JSON", lambda pair, limit: {BUNDLE_FILE: b"{not json"}, "unreadable"),
    ("not UTF-8", lambda pair, limit: {BUNDLE_FILE: b"\xff\xfe\x00{}"}, "unreadable"),
    (
        "over the size limit",
        lambda pair, limit: {
            BUNDLE_FILE: json.dumps(bundle(pair, good_facts())).encode() + b" " * (limit + 1)
        },
        "size limit",
    ),
    ("wrong kind", lambda pair, limit: {BUNDLE_FILE: with_top(pair, kind="evidence")}, "schema"),
    (
        "unknown schema version",
        lambda pair, limit: {BUNDLE_FILE: with_top(pair, schema_version=2)},
        "schema",
    ),
    (
        "a verdict field",
        lambda pair, limit: {BUNDLE_FILE: with_top(pair, verdict="red")},
        "schema",
    ),
    ("a PR number", lambda pair, limit: {BUNDLE_FILE: with_top(pair, pr=99)}, "schema"),
    (
        "an order id",
        lambda pair, limit: {BUNDLE_FILE: with_top(pair, order_id="wo-20261006-other")},
        "schema",
    ),
    (
        "a classification as outcome",
        lambda pair, limit: {BUNDLE_FILE: with_fact(pair, base_outcome="red")},
        "schema",
    ),
    (
        "a judgment per test",
        lambda pair, limit: {BUNDLE_FILE: with_fact(pair, red=True)},
        "schema",
    ),
    (
        "a short sha",
        lambda pair, limit: {BUNDLE_FILE: with_top(pair, base_sha=pair.base_sha[:12])},
        "schema",
    ),
    (
        "another head",
        lambda pair, limit: {BUNDLE_FILE: with_top(pair, head_sha=pair.base_sha)},
        "head_sha",
    ),
    (
        "a crashed producer",
        lambda pair, limit: {
            BUNDLE_FILE: with_red_first(pair, status="crashed", error="pytest exploded", tests=[])
        },
        "crashed",
    ),
    (
        "a test that is not new or changed",
        lambda pair, limit: {
            BUNDLE_FILE: bundle(pair, [*good_facts(), fact(EXISTING_NODE)]),
        },
        EXISTING_NODE,
    ),
    (
        "an omitted test",
        lambda pair, limit: {BUNDLE_FILE: bundle(pair, [fact(CAPS_HIGH)])},
        LIFTS_LOW,
    ),
]


def evidence_limit(repo: RepoBuilder) -> int:
    limit = getattr(repo.settings, "evidence_max_bytes", None)
    assert isinstance(limit, int) and limit > 0, (
        "typed config `evidence_max_bytes` (factory.toml, Settings) is missing"
    )
    return limit


@pytest.mark.parametrize(("label", "make", "needle"), FAIL_CLOSED, ids=[c[0] for c in FAIL_CLOSED])
def test_red_first_fails_closed_on_bad_evidence_and_other_gates_still_run(
    repo: RepoBuilder,
    factory_cli: FactoryCli,
    fake_github: FakeGitHub,
    tmp_path: Path,
    label: str,
    make: BundleCase,
    needle: str,
) -> None:
    pair = clamp_pair(repo)
    pr = head_as_data(repo, pair)
    files = make(pair, evidence_limit(repo))
    evidence = None if files is None else evidence_dir(tmp_path, files)
    result = ci_run(factory_cli, repo, pr, RED_FIRST, "bus.schema", evidence=evidence)
    assert_red_first(result, fake_github, pair.head_sha, "fail", needle)
    assert entry(report(result), "bus.schema").get("outcome") == "pass", report(result)


def test_moved_head_posts_nothing_and_exits_0(
    repo: RepoBuilder, factory_cli: FactoryCli, fake_github: FakeGitHub, tmp_path: Path
) -> None:
    pair = clamp_pair(repo)
    repo.checkout(pair.head_branch)
    repo.write("README.md", "# moved on\n")
    newer = repo.commit("newer head")
    repo.push()
    repo.checkout("main")
    pr = head_as_data(repo, BaseHeadPair(pair.base_sha, newer, pair.head_branch))
    evidence = evidence_dir(tmp_path, {BUNDLE_FILE: bundle(pair, good_facts())})
    result = ci_run(factory_cli, repo, pr, expect_head=pair.head_sha, evidence=evidence)
    assert result.exit_code == exit_codes.OK, (result.exit_code, result.stdout, result.stderr)
    assert fake_github.statuses == [], statuses(fake_github)


def installed_ci_gates() -> set[str]:
    return {gate.id for gate in load_registry().gates if gate.hook_twin_of is None}


def rewired_head_registry() -> str:
    """The head's registry drops `bus.immutable`, rewires `bus.schema`, adds a gate."""
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    rows = [row for row in data["gates"] if row["id"] != "bus.immutable"]
    for row in rows:
        if row["id"] == "bus.schema":
            row["entrypoint"] = "factory.api:run_gate"
    rows.append({**rows[0], "id": "head-only-gate", "entrypoint": "factory.api:run_gate"})
    data["gates"] = rows
    return yaml.safe_dump(data, sort_keys=False)


ALWAYS_PASS = (
    "from factory.api import GateContext, GateResult\n\n\n"
    "def run(ctx: GateContext) -> GateResult:\n"
    "    return GateResult(gate_id='bus.immutable', passed=True)\n"
)


def test_ci_mode_runs_main_registry_whatever_the_head_registry_says(
    repo: RepoBuilder, factory_cli: FactoryCli, fake_github: FakeGitHub, tmp_path: Path
) -> None:
    merged = "bus/orders/wo-20261006-merged-earlier/order.yaml"
    pair = repo.base_head_pair(
        {merged: yaml_text(order("wo-20261006-merged-earlier"))},
        {
            f"bus/orders/{ORDER_ID}/order.yaml": yaml_text(order(ORDER_ID)),
            merged: yaml_text(order("wo-20261006-merged-earlier", goal="Rewritten after merge.")),
            "scripts/factory/gates.yaml": rewired_head_registry(),
            "scripts/factory/src/factory/gates/pr/bus_immutable.py": ALWAYS_PASS,
        },
        head_branch=HEAD_BRANCH,
    )
    pr = head_as_data(repo, pair)
    evidence = evidence_dir(tmp_path, {BUNDLE_FILE: bundle(pair, [])})
    result = ci_run(factory_cli, repo, pr, evidence=evidence)
    assert result.exit_code == exit_codes.GATE_FAILURE, (result.exit_code, result.stderr)
    body = report(result)
    assert {g.get("id") for g in body.get("gates", [])} == installed_ci_gates(), body
    immutable = entry(body, "bus.immutable")
    assert immutable.get("outcome") == "fail", immutable
    assert any(merged in line for line in immutable.get("messages", [])), immutable
    assert {context for _, context in statuses(fake_github)} == {
        f"factory/{gate}" for gate in installed_ci_gates()
    }


def test_ci_mode_still_validates_the_head_registry_as_data(
    repo: RepoBuilder, factory_cli: FactoryCli, tmp_path: Path
) -> None:
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    data["gates"][0]["category"] = "not-a-category"
    pair = repo.base_head_pair(
        {},
        {
            f"bus/orders/{ORDER_ID}/order.yaml": yaml_text(order(ORDER_ID)),
            "scripts/factory/gates.yaml": yaml.safe_dump(data, sort_keys=False),
        },
        head_branch=HEAD_BRANCH,
    )
    pr = head_as_data(repo, pair)
    evidence = evidence_dir(tmp_path, {BUNDLE_FILE: bundle(pair, [])})
    result = ci_run(factory_cli, repo, pr, "gate.fail-mode-category", evidence=evidence)
    assert result.exit_code == exit_codes.GATE_FAILURE, (result.exit_code, result.stderr)
    gate = entry(report(result), "gate.fail-mode-category")
    assert gate.get("outcome") == "fail", gate
    assert any("not-a-category" in line for line in gate.get("messages", [])), gate


def marker_source(marker: Path) -> str:
    return f"from pathlib import Path\n\nPath({str(marker)!r}).write_text('ran')\n"


def test_ci_mode_never_executes_head_code(
    repo: RepoBuilder, factory_cli: FactoryCli, tmp_path: Path
) -> None:
    marker = tmp_path / "head-code-ran"
    planted = marker_source(marker)
    node = "apps/demo/tests/test_marker.py::test_marker"
    pair = repo.base_head_pair(
        {
            "scripts/validate_secrets_schema.py": 'print("ok")\n',
            "scripts/validate_deploy_env.py": 'print("ok")\n',
        },
        {
            f"bus/orders/{ORDER_ID}/order.yaml": yaml_text(order(ORDER_ID)),
            "conftest.py": planted,
            "apps/demo/conftest.py": planted,
            "apps/demo/tests/test_marker.py": planted
            + "\n\ndef test_marker() -> None:\n    pass\n",
            "scripts/validate_secrets_schema.py": planted,
            "scripts/validate_deploy_env.py": planted,
            "scripts/factory/src/factory/gates/pr/bus_immutable.py": planted,
        },
        head_branch=HEAD_BRANCH,
    )
    pr = head_as_data(repo, pair)
    evidence = evidence_dir(tmp_path, {BUNDLE_FILE: bundle(pair, [fact(node)])})
    result = ci_run(factory_cli, repo, pr, evidence=evidence)
    assert result.exit_code in (exit_codes.OK, exit_codes.GATE_FAILURE), result
    assert not marker.exists(), "a CI-mode gate run executed code from the PR head"
    assert repo.current_branch() == "main"
    assert repo.git("status", "--porcelain") == ""
    assert len(repo.git("worktree", "list", "--porcelain").split("\n\n")) == 1


# =========================================================================================
# Existing validators: main's script judges the exported head tree
# =========================================================================================

VALIDATED = "deploy/validator-input.txt"
MAIN_VALIDATOR = (
    "import sys\n"
    "from pathlib import Path\n\n"
    "args = sys.argv[1:]\n"
    'root = Path(args[args.index("--repo-root") + 1]) if "--repo-root" in args else Path.cwd()\n'
    f'target = root / "{VALIDATED}"\n'
    'text = target.read_text() if target.is_file() else ""\n'
    'if "INVALID" in text:\n'
    '    print("main validator: input invalid")\n'
    "    sys.exit(1)\n"
    'print("main validator: ok")\n'
)
VALIDATORS = [
    ("validate-secrets-schema", "scripts/validate_secrets_schema.py"),
    ("validate-deploy-env", "scripts/validate_deploy_env.py"),
]


@pytest.mark.parametrize(("gate_id", "script"), VALIDATORS)
def test_validators_run_mains_script_against_the_head_tree(
    repo: RepoBuilder, gate_id: str, script: str
) -> None:
    hollow = repo.base_head_pair(
        {script: MAIN_VALIDATOR},
        {script: "import sys\nsys.exit(0)\n", VALIDATED: "INVALID\n"},
        head_branch="head/hollow-validator",
    )
    assert_blocks(gate_id, raw_context(repo, hollow), "main validator: input invalid")
    strict = repo.base_head_pair(
        {},
        {script: "import sys\nsys.exit(1)\n", VALIDATED: "fine\n"},
        head_branch="head/failing-copy",
    )
    assert_passes(gate_id, raw_context(repo, strict))
    fixed = repo.base_head_pair(
        {VALIDATED: "INVALID\n"}, {VALIDATED: "fine\n"}, head_branch="head/fix"
    )
    assert_passes(gate_id, raw_context(repo, fixed))


# =========================================================================================
# `factory gate evidence` (the untrusted producer)
# =========================================================================================

RED_FIRST_MODULE = "factory.gates.drift.red_first"


def stub_collect_facts(monkeypatch: pytest.MonkeyPatch, function: Callable[..., Any]) -> None:
    """Slice B's seam `red_first.collect_facts(ctx)`, stubbed when B is not merged yet."""
    try:
        module = importlib.import_module(RED_FIRST_MODULE)
    except ImportError:
        parent_name = RED_FIRST_MODULE.rsplit(".", 1)[0]
        try:
            parent = importlib.import_module(parent_name)
        except ImportError:
            parent = types.ModuleType(parent_name)
            monkeypatch.setitem(sys.modules, parent_name, parent)
        module = types.ModuleType(RED_FIRST_MODULE)
        monkeypatch.setitem(sys.modules, RED_FIRST_MODULE, module)
        monkeypatch.setattr(parent, "red_first", module, raising=False)
        module.collect_facts = function  # type: ignore[attr-defined]
    else:
        monkeypatch.setattr(module, "collect_facts", function, raising=False)


def no_github(*args: Any) -> Any:
    raise AssertionError("`factory gate evidence` built a GitHub adapter (it needs no token)")


def run_evidence(
    factory_cli: FactoryCli, repo: RepoBuilder, pair: BaseHeadPair, out: Path | None
) -> CliResult:
    args = ["gate", "evidence", "--base", pair.base_sha, "--head", pair.head_sha]
    if out is not None:
        args += ["--out", str(out)]
    return factory_cli(*args, repo=repo.path)


def read_bundle(out: Path) -> dict[str, Any]:
    assert out.is_dir(), f"{out} was not created"
    names = sorted(path.name for path in out.iterdir())
    assert names == [BUNDLE_FILE], names
    data = json.loads((out / BUNDLE_FILE).read_text(encoding="utf-8"))
    assert isinstance(data, dict), data
    return data


def test_gate_evidence_serializes_raw_facts_sorted_and_posts_nothing(
    repo: RepoBuilder,
    factory_cli: FactoryCli,
    fake_github: FakeGitHub,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pair = clamp_pair(repo)
    seen: list[tuple[Path, str, str]] = []

    def collect_facts(ctx: Any) -> list[types.SimpleNamespace]:
        seen.append((Path(ctx.repo_path), ctx.base_sha, ctx.head_sha))
        return [
            types.SimpleNamespace(**fact(LIFTS_LOW, "failed", "failed")),
            types.SimpleNamespace(
                **fact(CAPS_HIGH, "not_collected", base_error="E   No module named 'x'")
            ),
        ]

    stub_collect_facts(monkeypatch, collect_facts)
    monkeypatch.setattr(DEPS, "github", no_github)
    out = tmp_path / "out"
    result = run_evidence(factory_cli, repo, pair, out)
    assert result.exit_code == exit_codes.OK, (result.exit_code, result.stdout, result.stderr)
    assert seen == [(repo.path, pair.base_sha, pair.head_sha)], seen
    assert read_bundle(out) == bundle(
        pair,
        [
            fact(CAPS_HIGH, "not_collected", base_error="E   No module named 'x'"),
            fact(LIFTS_LOW, "failed", "failed"),
        ],
    )
    assert fake_github.statuses == []


@pytest.mark.parametrize(
    ("label", "behaviour", "needle"),
    [
        ("raises", "raise", "pytest exploded"),
        ("unknown outcome", "xpassed", "xpassed"),
    ],
)
def test_gate_evidence_records_a_crash_and_still_exits_0(
    repo: RepoBuilder,
    factory_cli: FactoryCli,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    label: str,
    behaviour: str,
    needle: str,
) -> None:
    pair = clamp_pair(repo)

    def collect_facts(ctx: Any) -> list[types.SimpleNamespace]:
        if behaviour == "raise":
            raise RuntimeError("pytest exploded")
        return [types.SimpleNamespace(**fact(CAPS_HIGH, behaviour))]

    stub_collect_facts(monkeypatch, collect_facts)
    out = tmp_path / "out"
    result = run_evidence(factory_cli, repo, pair, out)
    assert result.exit_code == exit_codes.OK, (result.exit_code, result.stdout, result.stderr)
    data = read_bundle(out)
    assert (data.get("base_sha"), data.get("head_sha")) == (pair.base_sha, pair.head_sha), data
    red_first = data.get("red_first", {})
    assert red_first.get("status") == "crashed", red_first
    assert red_first.get("tests") == [], red_first
    assert needle in str(red_first.get("error")), red_first


def test_gate_evidence_without_out_is_a_usage_error(
    repo: RepoBuilder, factory_cli: FactoryCli, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub_collect_facts(monkeypatch, lambda ctx: [])
    result = run_evidence(factory_cli, repo, clamp_pair(repo), None)
    assert result.exit_code == exit_codes.USAGE, (result.exit_code, result.stdout, result.stderr)
    assert "--out" in result.stdout + result.stderr, (result.stdout, result.stderr)
