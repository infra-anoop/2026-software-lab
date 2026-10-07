"""T013 — exit codes of every `factory` command (contracts/cli.md).

One case per refusal row (exit 2), one exit-0 case per command without refusals,
one external-failure case (exit 4). Red until the owning slice lands (CP1), except
`check schema` and usage errors, which P0 implements.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from factory.api import OrderState
from factory.cli import exit_codes
from factory.lifecycle.derive import derive_snapshot
from tests.fixtures.cli_runner import CliResult, FactoryCli
from tests.fixtures.repo_builder import RepoBuilder, message, order, yaml_text

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURES = REPO_ROOT / "scripts/factory/tests/fixtures"
DAY = "20261006"
OPEN_DECISION = "pick-host"

# Commands whose owning task has not landed. `Factory tests` is a required check, so these
# contracts stay recorded as strict expected failures: the task that builds the command
# turns them into unexpected passes, which fail the suite until it deletes its entry here.
UNBUILT = {"retro": "T069", "correction new": "T081", "sprint close": "T081"}


def unbuilt(command: str) -> pytest.MarkDecorator:
    task = UNBUILT[command]
    return pytest.mark.xfail(
        reason=f"`factory {command}` is unbuilt until {task}; {task} deletes this entry",
        raises=AssertionError,
        strict=True,
    )


def oid(slug: str) -> str:
    return f"wo-{DAY}-{slug}"


def assert_exit(result: CliResult, expected: int) -> None:
    assert result.exit_code == expected, (
        f"expected exit {expected}, got {result.exit_code}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def issue(repo: RepoBuilder, order_id: str, **fields: object) -> None:
    fields.setdefault("owned_paths", [f"apps/demo/{order_id}/**"])
    repo.issue_order(order(order_id, **fields))


def claim_event(repo: RepoBuilder, order_id: str) -> None:
    repo.add_event(order_id, message("claim", order_id=order_id))


def open_human_decision(repo: RepoBuilder) -> None:
    repo.checkout("main")
    repo.write_message(message("decision_request", decision_id=OPEN_DECISION, blocking=True))
    repo.commit("decision request: pick host")
    repo.push("main")


def handoff_commit(
    repo: RepoBuilder, order_id: str, files: dict[str, str], *, valid: bool = True
) -> None:
    handoff = message("handoff", order_id=order_id)
    if not valid:
        del handoff["deviations"]
    repo.add_event(order_id, handoff, validate=valid, extra_files=files)
    repo.add_event(order_id, message("run_complete", order_id=order_id))


def claimed_with_handoff(repo: RepoBuilder, order_id: str) -> None:
    issue(repo, order_id, owned_paths=["apps/demo/app/calc.py"], checks=[])
    claim_event(repo, order_id)
    handoff_commit(repo, order_id, {"apps/demo/app/calc.py": "def add(a, b):\n    return a + b\n"})


def verdict_file(repo: RepoBuilder, order_id: str, **overrides: object) -> Path:
    head = repo.head_sha(f"wo/{order_id}")
    fields: dict[str, object] = {
        "inputs": [{"path": f"bus/orders/{order_id}/order.yaml", "sha": head}],
        **overrides,
    }
    data = message("verdict", order_id=order_id, **fields)
    path = repo.root / "verdict.yaml"
    path.write_text(yaml_text(data), encoding="utf-8")
    return path


# --- P0: check schema (green at CP0) ------------------------------------------------------


def test_check_schema_ok_on_sample_messages(factory_cli: FactoryCli) -> None:
    result = factory_cli("check", "schema", "--path", str(FIXTURES / "messages"), repo=REPO_ROOT)
    assert_exit(result, exit_codes.OK)


def test_check_schema_fails_on_invalid_sample(factory_cli: FactoryCli) -> None:
    result = factory_cli(
        "check", "schema", "--path", str(FIXTURES / "invalid_messages"), repo=REPO_ROOT
    )
    assert_exit(result, exit_codes.GATE_FAILURE)
    assert "status" in result.stdout


def test_check_schema_ok_on_fixture_bus(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    repo.write_message(order(oid("ok")))
    repo.write_message(message("decision_request"))
    assert_exit(factory_cli("check", "schema", repo=repo.path), exit_codes.OK)


def test_check_schema_fails_on_handwritten_status(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    repo.write_message(order(oid("bad"), progress="50%"), validate=False)
    assert_exit(factory_cli("check", "schema", repo=repo.path), exit_codes.GATE_FAILURE)


def test_check_schema_fails_on_misplaced_message(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    repo.write(f"bus/orders/{oid('elsewhere')}/order.yaml", yaml_text(order(oid("real"))))
    assert_exit(factory_cli("check", "schema", repo=repo.path), exit_codes.GATE_FAILURE)


def test_check_schema_json_output(factory_cli: FactoryCli) -> None:
    result = factory_cli(
        "check", "schema", "--json", "--path", str(FIXTURES / "messages"), repo=REPO_ROOT
    )
    assert_exit(result, exit_codes.OK)
    assert '"ok": true' in result.stdout


# --- usage / config errors (green at CP0) -------------------------------------------------


def test_unknown_command_is_usage_error(factory_cli: FactoryCli) -> None:
    assert_exit(factory_cli("frobnicate"), exit_codes.USAGE)


def test_missing_required_option_is_usage_error(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    assert_exit(factory_cli("release", oid("x"), repo=repo.path), exit_codes.USAGE)


def test_missing_config_is_usage_error(tmp_path: Path, factory_cli: FactoryCli) -> None:
    assert_exit(factory_cli("check", "schema", repo=tmp_path), exit_codes.USAGE)


# --- board (slice A) ----------------------------------------------------------------------


def test_status_exit_0(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    issue(repo, oid("board"))
    assert_exit(factory_cli("status", repo=repo.path), exit_codes.OK)


def test_status_json_exit_0(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    assert_exit(factory_cli("status", "--json", repo=repo.path), exit_codes.OK)


def test_status_judges_a_catalog_row_check_by_the_head_catalog(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    """T105 / amendment-02: the board derives with the repo, so a `checks` id that is a row
    of the PR head's `acceptance.md` is satisfied by green `factory/catalog-test-linkage`."""
    order_id = oid("catalog-row")
    repo.add_demo_feature()
    issue(repo, order_id, checks=["demo.adds"])
    claim_event(repo, order_id)
    repo.add_event(order_id, message("handoff", order_id=order_id))
    pr = repo.make_pr(f"wo/{order_id}")
    repo.github.set_commit_status(pr.head_sha, "factory/catalog-test-linkage", "success", "ok")
    inputs = [{"path": f"bus/orders/{order_id}/order.yaml", "sha": pr.head_sha}]
    verdict = message("verdict", order_id=order_id, decision="accept", inputs=inputs)
    repo.add_event(order_id, verdict)
    expected = next(
        o.state
        for o in derive_snapshot(repo.path, repo.github, settings=repo.settings).orders
        if o.order_id == order_id
    )
    assert expected != OrderState.IN_REVIEW, f"derive with the repo gives {expected}"

    result = factory_cli("status", "--json", repo=repo.path)
    assert_exit(result, exit_codes.OK)
    board = json.loads(result.stdout)["data"]
    states = {
        card.get("order_id") or card.get("id"): card.get("state")
        for section in ("in_flight", "blocked", "waiting_on_governor", "ready")
        for card in board[section]
    }
    assert states.get(order_id) == expected.value, (
        f"board shows {order_id} as {states.get(order_id)!r}; derive with the repo gives"
        f" {expected.value!r}"
    )


def test_decisions_exit_0(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    open_human_decision(repo)
    assert_exit(factory_cli("decisions", repo=repo.path), exit_codes.OK)


def test_scorecard_exit_0(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    assert_exit(factory_cli("scorecard", repo=repo.path), exit_codes.OK)


# --- order new / issue (slice A) ------------------------------------------------------------


def test_order_new_exit_0(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    repo.add_demo_feature()
    result = factory_cli(
        "order",
        "new",
        "--feature",
        "demo-feature",
        "--from-task",
        "T002",
        "--lock",
        "D1=letter",
        "--size-minutes",
        "45",
        repo=repo.path,
    )
    assert_exit(result, exit_codes.OK)


def test_order_new_refuses_size_over_horizon(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    repo.add_demo_feature()
    result = factory_cli(
        "order",
        "new",
        "--feature",
        "demo-feature",
        "--from-task",
        "T001",
        "--size-minutes",
        "90",
        repo=repo.path,
    )
    assert_exit(result, exit_codes.REFUSED)


def test_order_new_refuses_touched_named_lock_without_fidelity(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    repo.add_demo_feature()
    result = factory_cli(
        "order",
        "new",
        "--feature",
        "demo-feature",
        "--from-task",
        "T002",
        "--size-minutes",
        "45",
        repo=repo.path,
    )
    assert_exit(result, exit_codes.REFUSED)


def test_order_issue_exit_0(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    repo.write_message(order(oid("issue")))
    assert_exit(factory_cli("order", "issue", oid("issue"), repo=repo.path), exit_codes.OK)


def test_order_issue_refuses_open_human_decision(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    open_human_decision(repo)
    repo.write_message(order(oid("blocked"), depends_on_decisions=[OPEN_DECISION]))
    result = factory_cli("order", "issue", oid("blocked"), repo=repo.path)
    assert_exit(result, exit_codes.REFUSED)


def test_order_issue_refuses_invalid_schema(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    repo.write_message(order(oid("invalid"), size_minutes=90), validate=False)
    result = factory_cli("order", "issue", oid("invalid"), repo=repo.path)
    assert_exit(result, exit_codes.REFUSED)


# --- claim / release (slice A) --------------------------------------------------------------


def test_claim_exit_0(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    issue(repo, oid("claimable"))
    result = factory_cli(
        "claim", oid("claimable"), "--actor-model", "claude-opus-5.5", repo=repo.path
    )
    assert_exit(result, exit_codes.OK)


def test_claim_refuses_at_cap(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    for n in range(3):
        issue(repo, oid(f"active-{n}"))
        claim_event(repo, oid(f"active-{n}"))
    issue(repo, oid("fourth"))
    result = factory_cli("claim", oid("fourth"), "--actor-model", "claude-opus-5.5", repo=repo.path)
    assert_exit(result, exit_codes.REFUSED)


def test_claim_refuses_owned_path_overlap(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    issue(repo, oid("holder"), owned_paths=["apps/demo/**"])
    claim_event(repo, oid("holder"))
    issue(repo, oid("overlap"), owned_paths=["apps/demo/app/calc.py"])
    result = factory_cli(
        "claim", oid("overlap"), "--actor-model", "claude-opus-5.5", repo=repo.path
    )
    assert_exit(result, exit_codes.REFUSED)


def test_claim_refuses_blocked_on_governor(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    open_human_decision(repo)
    issue(repo, oid("waiting"), depends_on_decisions=[OPEN_DECISION])
    result = factory_cli(
        "claim", oid("waiting"), "--actor-model", "claude-opus-5.5", repo=repo.path
    )
    assert_exit(result, exit_codes.REFUSED)


def test_claim_refuses_already_claimed(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    issue(repo, oid("taken"))
    claim_event(repo, oid("taken"))
    result = factory_cli("claim", oid("taken"), "--actor-model", "claude-opus-5.5", repo=repo.path)
    assert_exit(result, exit_codes.REFUSED)


def test_claim_origin_unreachable_is_external_failure(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    issue(repo, oid("offline"))
    repo.git("fetch", "-q", "origin")
    repo.git("remote", "set-url", "origin", str(repo.root / "missing.git"))
    result = factory_cli(
        "claim", oid("offline"), "--actor-model", "claude-opus-5.5", repo=repo.path
    )
    assert_exit(result, exit_codes.EXTERNAL)


def test_release_exit_0(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    issue(repo, oid("released"))
    claim_event(repo, oid("released"))
    result = factory_cli("release", oid("released"), "--reason", "abandoned", repo=repo.path)
    assert_exit(result, exit_codes.OK)


# --- handoff / pr open / verdict / bus pr (slice A) -------------------------------------------


def test_handoff_exit_0(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    repo.add_demo_feature()
    claimed_with_handoff(repo, oid("handed"))
    repo.checkout(f"wo/{oid('handed')}")
    assert_exit(factory_cli("handoff", oid("handed"), repo=repo.path), exit_codes.OK)


def test_handoff_refuses_while_a_gate_fails(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    repo.add_demo_feature()
    order_id = oid("outside")
    issue(repo, order_id, owned_paths=["apps/demo/app/calc.py"], checks=[])
    claim_event(repo, order_id)
    handoff_commit(
        repo,
        order_id,
        {
            "apps/demo/app/calc.py": "def add(a, b):\n    return a + b\n",
            "deploy/railway/demo.toml": "[deploy]\n",
        },
    )
    repo.checkout(f"wo/{order_id}")
    assert_exit(factory_cli("handoff", order_id, repo=repo.path), exit_codes.REFUSED)


def test_pr_open_exit_0(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    repo.add_demo_feature()
    claimed_with_handoff(repo, oid("pr"))
    repo.checkout(f"wo/{oid('pr')}")
    assert_exit(factory_cli("pr", "open", oid("pr"), repo=repo.path), exit_codes.OK)


def test_pr_open_refuses_without_handoff(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    issue(repo, oid("nohandoff"))
    claim_event(repo, oid("nohandoff"))
    repo.checkout(f"wo/{oid('nohandoff')}")
    assert_exit(factory_cli("pr", "open", oid("nohandoff"), repo=repo.path), exit_codes.REFUSED)


def test_pr_open_refuses_invalid_handoff(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    repo.add_demo_feature()
    order_id = oid("badhandoff")
    issue(repo, order_id, owned_paths=["apps/demo/app/calc.py"], checks=[])
    claim_event(repo, order_id)
    handoff_commit(repo, order_id, {"apps/demo/app/calc.py": "X = 1\n"}, valid=False)
    repo.checkout(f"wo/{order_id}")
    assert_exit(factory_cli("pr", "open", order_id, repo=repo.path), exit_codes.REFUSED)


def test_verdict_exit_0(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    repo.add_demo_feature()
    claimed_with_handoff(repo, oid("judged"))
    path = verdict_file(repo, oid("judged"))
    repo.checkout(f"wo/{oid('judged')}")
    result = factory_cli("verdict", oid("judged"), "--file", str(path), repo=repo.path)
    assert_exit(result, exit_codes.OK)


def test_verdict_refuses_same_family_reviewer(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    repo.add_demo_feature()
    claimed_with_handoff(repo, oid("samefamily"))
    path = verdict_file(
        repo,
        oid("samefamily"),
        actor_model="claude-opus-5.5",
        reviewer_model="claude-opus-5.5",
        reviewer_family="anthropic",
    )
    repo.checkout(f"wo/{oid('samefamily')}")
    result = factory_cli("verdict", oid("samefamily"), "--file", str(path), repo=repo.path)
    assert_exit(result, exit_codes.REFUSED)


def test_verdict_refuses_input_that_is_not_a_git_path(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    repo.add_demo_feature()
    order_id = oid("transcript")
    claimed_with_handoff(repo, order_id)
    head = repo.head_sha(f"wo/{order_id}")
    path = verdict_file(
        repo, order_id, inputs=[{"path": "notes/chat-transcript-2026-10-06.md", "sha": head}]
    )
    repo.checkout(f"wo/{order_id}")
    result = factory_cli("verdict", order_id, "--file", str(path), repo=repo.path)
    assert_exit(result, exit_codes.REFUSED)


def test_bus_pr_exit_0(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    written = repo.write_message(message("decision_request", decision_id="web-view"))
    result = factory_cli("bus", "pr", "--message", written, repo=repo.path)
    assert_exit(result, exit_codes.OK)


def test_bus_pr_refuses_non_bus_paths(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    written = repo.write_message(message("decision_request", decision_id="web-view"))
    repo.write("apps/demo/app/calc.py", "X = 1\n")
    result = factory_cli(
        "bus", "pr", "--message", written, "--message", "apps/demo/app/calc.py", repo=repo.path
    )
    assert_exit(result, exit_codes.REFUSED)


# --- override / gate run / hooks / checks / retro (slice C, B) --------------------------------


def test_override_drift_gate_exit_0(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    issue(repo, oid("override"))
    claim_event(repo, oid("override"))
    repo.checkout(f"wo/{oid('override')}")
    result = factory_cli(
        "override",
        oid("override"),
        "--gate",
        "red-first-proof",
        "--reason",
        "Base suite broken by an unrelated module; new test verified red by hand.",
        "--actor-model",
        "claude-opus-5.5",
        "--pr",
        "1",
        repo=repo.path,
    )
    assert_exit(result, exit_codes.OK)


@pytest.mark.parametrize("reason", ["", "   "])
def test_override_refuses_empty_reason(
    repo: RepoBuilder, factory_cli: FactoryCli, reason: str
) -> None:
    issue(repo, oid("noreason"))
    claim_event(repo, oid("noreason"))
    repo.checkout(f"wo/{oid('noreason')}")
    result = factory_cli(
        "override",
        oid("noreason"),
        "--gate",
        "red-first-proof",
        "--reason",
        reason,
        "--actor-model",
        "claude-opus-5.5",
        "--pr",
        "1",
        repo=repo.path,
    )
    assert_exit(result, exit_codes.REFUSED)


def test_override_refuses_governor_only_gate_by_non_governor(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    issue(repo, oid("govonly"))
    claim_event(repo, oid("govonly"))
    repo.checkout(f"wo/{oid('govonly')}")
    result = factory_cli(
        "override",
        oid("govonly"),
        "--gate",
        "order-blocked-on-open-human-od",
        "--reason",
        "Ship it anyway.",
        "--actor",
        "orchestrator",
        "--actor-model",
        "claude-opus-5.5",
        "--pr",
        "1",
        repo=repo.path,
    )
    assert_exit(result, exit_codes.REFUSED)


def test_gate_run_exit_0_on_clean_change(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    pair = repo.base_head_pair({}, {"README.md": "# fixture repo, edited\n"})
    result = factory_cli(
        "gate",
        "run",
        "--gate",
        "bus.schema",
        "--base",
        pair.base_sha,
        "--head",
        pair.head_sha,
        repo=repo.path,
    )
    assert_exit(result, exit_codes.OK)


def test_hook_shell_guard_allows_plain_command(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    stdin = '{"command": "ls -la", "cwd": "' + str(repo.path) + '"}'
    result = factory_cli("hook", "shell-guard", repo=repo.path, stdin=stdin)
    assert_exit(result, exit_codes.OK)


def test_hook_shell_guard_denies_pip_install(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    stdin = '{"command": "pip install requests", "cwd": "' + str(repo.path) + '"}'
    result = factory_cli("hook", "shell-guard", repo=repo.path, stdin=stdin)
    assert_exit(result, exit_codes.REFUSED)


def test_check_intent_exit_0(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    repo.write(
        "specs/demo-feature/intent.yaml",
        "schema_version: 1\nfeature: demo-feature\nintents:\n"
        "  - id: I-D1\n    kind: goal\n    statement: Bus files validate.\n"
        "    checks:\n      - { kind: ci, ref: bus.schema, status: exists }\n",
    )
    repo.commit("intent")
    assert_exit(factory_cli("check", "intent", repo=repo.path), exit_codes.OK)


def test_check_hooks_exit_0(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    assert_exit(factory_cli("check", "hooks", repo=repo.path), exit_codes.OK)


def test_check_registry_exit_0(factory_cli: FactoryCli) -> None:
    assert_exit(factory_cli("check", "registry", repo=REPO_ROOT), exit_codes.OK)


def test_check_immutability_exit_0(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    pair = repo.base_head_pair(
        {}, {f"bus/orders/{oid('new')}/order.yaml": yaml_text(order(oid("new")))}
    )
    result = factory_cli(
        "check", "immutability", "--base", pair.base_sha, "--head", pair.head_sha, repo=repo.path
    )
    assert_exit(result, exit_codes.OK)


@unbuilt("retro")
def test_retro_exit_0(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    assert_exit(factory_cli("retro", "--since", "main", repo=repo.path), exit_codes.OK)


# --- mining loop (US7, Wave 2) ----------------------------------------------------------------


@unbuilt("correction new")
def test_correction_new_exit_0(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    result = factory_cli(
        "correction",
        "new",
        "--target",
        oid("any"),
        "--what",
        "Worker swapped the named host for another one.",
        "--tag",
        "drift",
        repo=repo.path,
    )
    assert_exit(result, exit_codes.OK)


@unbuilt("sprint close")
def test_sprint_close_refuses_without_postmortem(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    result = factory_cli("sprint", "close", "--sprint", "2026-10-sprint-02", repo=repo.path)
    assert_exit(result, exit_codes.REFUSED)


@unbuilt("sprint close")
def test_sprint_close_refuses_undispositioned_correction(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    repo.write_message(message("correction"))
    repo.write("bus/postmortems/2026-10-sprint-02.yaml", "sprint: 2026-10-sprint-02\n")
    repo.commit("correction + post-mortem without dispositions")
    repo.push("main")
    result = factory_cli("sprint", "close", "--sprint", "2026-10-sprint-02", repo=repo.path)
    assert_exit(result, exit_codes.REFUSED)


# --- --json envelope over every command (review T3) -------------------------------------------
#
# contracts/cli.md § JSON envelope: with `--json`, stdout is exactly one JSON object,
# `{"ok": true, "command", "data"}` on exit 0 or `{"ok": false, "command", "error"}`
# otherwise. `factory hook` is exempt (its stdout is the Cursor hook protocol).

Scenario = Callable[[RepoBuilder], tuple[list[str], Path]]


def _status(repo: RepoBuilder) -> tuple[list[str], Path]:
    issue(repo, oid("board"))
    return ["status"], repo.path


def _decisions(repo: RepoBuilder) -> tuple[list[str], Path]:
    open_human_decision(repo)
    return ["decisions"], repo.path


def _scorecard(repo: RepoBuilder) -> tuple[list[str], Path]:
    return ["scorecard"], repo.path


def _order_new(repo: RepoBuilder) -> tuple[list[str], Path]:
    repo.add_demo_feature()
    args = ["order", "new", "--feature", "demo-feature", "--from-task", "T002"]
    return [*args, "--lock", "D1=letter", "--size-minutes", "45"], repo.path


def _order_issue(repo: RepoBuilder) -> tuple[list[str], Path]:
    repo.write_message(order(oid("issue")))
    return ["order", "issue", oid("issue")], repo.path


def _claim(repo: RepoBuilder) -> tuple[list[str], Path]:
    issue(repo, oid("claimable"))
    return ["claim", oid("claimable"), "--actor-model", "claude-opus-5.5"], repo.path


def _claim_at_cap(repo: RepoBuilder) -> tuple[list[str], Path]:
    for n in range(3):
        issue(repo, oid(f"active-{n}"))
        claim_event(repo, oid(f"active-{n}"))
    issue(repo, oid("fourth"))
    return ["claim", oid("fourth"), "--actor-model", "claude-opus-5.5"], repo.path


def _release(repo: RepoBuilder) -> tuple[list[str], Path]:
    issue(repo, oid("released"))
    claim_event(repo, oid("released"))
    return ["release", oid("released"), "--reason", "abandoned"], repo.path


def _handoff(repo: RepoBuilder) -> tuple[list[str], Path]:
    repo.add_demo_feature()
    claimed_with_handoff(repo, oid("handed"))
    repo.checkout(f"wo/{oid('handed')}")
    return ["handoff", oid("handed")], repo.path


def _pr_open(repo: RepoBuilder) -> tuple[list[str], Path]:
    repo.add_demo_feature()
    claimed_with_handoff(repo, oid("pr"))
    repo.checkout(f"wo/{oid('pr')}")
    return ["pr", "open", oid("pr")], repo.path


def _verdict(repo: RepoBuilder) -> tuple[list[str], Path]:
    repo.add_demo_feature()
    claimed_with_handoff(repo, oid("judged"))
    path = verdict_file(repo, oid("judged"))
    repo.checkout(f"wo/{oid('judged')}")
    return ["verdict", oid("judged"), "--file", str(path)], repo.path


def _bus_pr(repo: RepoBuilder) -> tuple[list[str], Path]:
    written = repo.write_message(message("decision_request", decision_id="web-view"))
    return ["bus", "pr", "--message", written], repo.path


def _override_args(order_id: str, reason: str) -> list[str]:
    return [
        "override",
        order_id,
        "--gate",
        "red-first-proof",
        "--reason",
        reason,
        "--actor-model",
        "claude-opus-5.5",
        "--pr",
        "1",
    ]


def _override(repo: RepoBuilder) -> tuple[list[str], Path]:
    issue(repo, oid("override"))
    claim_event(repo, oid("override"))
    repo.checkout(f"wo/{oid('override')}")
    reason = "Base suite broken by an unrelated module; new test verified red by hand."
    return _override_args(oid("override"), reason), repo.path


def _override_empty_reason(repo: RepoBuilder) -> tuple[list[str], Path]:
    issue(repo, oid("noreason"))
    claim_event(repo, oid("noreason"))
    repo.checkout(f"wo/{oid('noreason')}")
    return _override_args(oid("noreason"), " "), repo.path


def _gate_run(repo: RepoBuilder) -> tuple[list[str], Path]:
    pair = repo.base_head_pair({}, {"README.md": "# fixture repo, edited\n"})
    args = ["gate", "run", "--gate", "bus.schema"]
    return [*args, "--base", pair.base_sha, "--head", pair.head_sha], repo.path


def _check_schema(repo: RepoBuilder) -> tuple[list[str], Path]:
    repo.write_message(order(oid("ok")))
    return ["check", "schema"], repo.path


def _check_schema_failing(repo: RepoBuilder) -> tuple[list[str], Path]:
    repo.write_message(order(oid("bad"), progress="50%"), validate=False)
    return ["check", "schema"], repo.path


def _check_intent(repo: RepoBuilder) -> tuple[list[str], Path]:
    repo.write(
        "specs/demo-feature/intent.yaml",
        "schema_version: 1\nfeature: demo-feature\nintents:\n"
        "  - id: I-D1\n    kind: goal\n    statement: Bus files validate.\n"
        "    checks:\n      - { kind: ci, ref: bus.schema, status: exists }\n",
    )
    repo.commit("intent")
    return ["check", "intent"], repo.path


def _check_hooks(repo: RepoBuilder) -> tuple[list[str], Path]:
    return ["check", "hooks"], repo.path


def _check_registry(repo: RepoBuilder) -> tuple[list[str], Path]:
    return ["check", "registry"], REPO_ROOT


def _check_immutability(repo: RepoBuilder) -> tuple[list[str], Path]:
    pair = repo.base_head_pair(
        {}, {f"bus/orders/{oid('new')}/order.yaml": yaml_text(order(oid("new")))}
    )
    args = ["check", "immutability", "--base", pair.base_sha, "--head", pair.head_sha]
    return args, repo.path


def _retro(repo: RepoBuilder) -> tuple[list[str], Path]:
    return ["retro", "--since", "main"], repo.path


def _correction_new(repo: RepoBuilder) -> tuple[list[str], Path]:
    what = "Worker swapped the named host for another one."
    args = ["correction", "new", "--target", oid("any"), "--what", what, "--tag", "drift"]
    return args, repo.path


def _sprint_close(repo: RepoBuilder) -> tuple[list[str], Path]:
    return ["sprint", "close", "--sprint", "2026-10-sprint-02"], repo.path


def _missing_config(repo: RepoBuilder) -> tuple[list[str], Path]:
    empty = repo.root / "no-config"
    empty.mkdir()
    return ["check", "schema"], empty


def _unknown_option(repo: RepoBuilder) -> tuple[list[str], Path]:
    return ["check", "schema", "--no-such-option"], repo.path


JSON_SCENARIOS: list[tuple[str, Scenario, int]] = [
    ("status", _status, exit_codes.OK),
    ("decisions", _decisions, exit_codes.OK),
    ("scorecard", _scorecard, exit_codes.OK),
    ("order new", _order_new, exit_codes.OK),
    ("order issue", _order_issue, exit_codes.OK),
    ("claim", _claim, exit_codes.OK),
    ("claim", _claim_at_cap, exit_codes.REFUSED),
    ("release", _release, exit_codes.OK),
    ("handoff", _handoff, exit_codes.OK),
    ("pr open", _pr_open, exit_codes.OK),
    ("verdict", _verdict, exit_codes.OK),
    ("bus pr", _bus_pr, exit_codes.OK),
    ("override", _override, exit_codes.OK),
    ("override", _override_empty_reason, exit_codes.REFUSED),
    ("gate run", _gate_run, exit_codes.OK),
    ("check schema", _check_schema, exit_codes.OK),
    ("check schema", _check_schema_failing, exit_codes.GATE_FAILURE),
    ("check schema", _missing_config, exit_codes.USAGE),
    ("check schema", _unknown_option, exit_codes.USAGE),
    ("check intent", _check_intent, exit_codes.OK),
    ("check hooks", _check_hooks, exit_codes.OK),
    ("check registry", _check_registry, exit_codes.OK),
    ("check immutability", _check_immutability, exit_codes.OK),
    ("retro", _retro, exit_codes.OK),
    ("correction new", _correction_new, exit_codes.OK),
    ("sprint close", _sprint_close, exit_codes.REFUSED),
]


def parse_envelope(result: CliResult) -> dict[str, Any]:
    try:
        envelope = json.loads(result.stdout)
    except ValueError as exc:
        raise AssertionError(
            f"--json stdout is not one JSON document: {result.stdout!r}\nstderr: {result.stderr}"
        ) from exc
    assert isinstance(envelope, dict), envelope
    return envelope


@pytest.mark.parametrize(
    ("command", "scenario", "expected"),
    JSON_SCENARIOS,
    ids=[f"{command}-{scenario.__name__.lstrip('_')}" for command, scenario, _ in JSON_SCENARIOS],
)
def test_json_envelope(
    request: pytest.FixtureRequest,
    repo: RepoBuilder,
    factory_cli: FactoryCli,
    command: str,
    scenario: Scenario,
    expected: int,
) -> None:
    if command in UNBUILT:
        request.applymarker(unbuilt(command))
    args, repo_path = scenario(repo)
    result = factory_cli(*args, "--json", repo=repo_path)
    assert_exit(result, expected)
    envelope = parse_envelope(result)
    assert envelope.get("command") == command, envelope
    if expected == exit_codes.OK:
        assert set(envelope) == {"ok", "command", "data"}, envelope
        assert envelope["ok"] is True
    else:
        assert set(envelope) == {"ok", "command", "error"}, envelope
        assert envelope["ok"] is False
        error = envelope["error"]
        assert isinstance(error, dict) and error.get("code") == expected, envelope
        assert isinstance(error.get("message"), str) and error["message"].strip(), envelope
