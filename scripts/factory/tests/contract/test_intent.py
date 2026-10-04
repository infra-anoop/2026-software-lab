"""T061 — `factory check intent [--coverage]` and gate `factory-check-intent` (FR-023).

Presence (SC-005a, catalog `trace.presence`): over every `specs/*/intent.yaml`
(`north_star` and `intents`), an intent is mapped when its own `checks` list is
non-empty, a `scripts/factory/gates.yaml` row lists it in `intents`, or an
`acceptance.md` row lists it in `intents`. Any unmapped intent fails (exit 1).

Effective coverage (SC-005b, catalog `trace.effective_coverage`): the share of intents
backed by an implemented check (registered in the repo's `gates.yaml` with an
importable entrypoint) whose latest `factory/<gate-id>` commit status on HEAD is
`success`, or by an explicit governor-judged mapping (`kind: human`). Self-reported
`status: exists` in `intent.yaml` is not evidence.

`--json` data (command-specific, contracts/cli.md § JSON envelope): `intents` (every
intent id read), `unmapped` (ids without a mapping); with `--coverage`, `coverage`
with `share`, `covered`, `uncovered`. On a presence failure the error `details`
carry `unmapped`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from factory.cli import exit_codes
from tests.fixtures.cli_runner import CliResult, FactoryCli
from tests.fixtures.repo_builder import RepoBuilder
from tests.unit.gates.drift.helpers import assert_blocks, assert_passes

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[4]
GATE = "factory-check-intent"
REGISTRY = "scripts/factory/gates.yaml"
IMPORTABLE = "factory.api:run_gate"
NOT_IMPORTABLE = "factory.gates.drift.no_such_gate:run"


def ci(ref: str, status: str = "exists") -> dict[str, str]:
    return {"kind": "ci", "ref": ref, "status": status}


def intent(intent_id: str, *checks: dict[str, str], has_checks: bool = True) -> dict[str, Any]:
    data: dict[str, Any] = {"id": intent_id, "kind": "goal", "statement": f"{intent_id} holds."}
    if has_checks:
        data["checks"] = list(checks)
    return data


def intent_file(
    feature: str, *intents: dict[str, Any], north_star: dict[str, Any] | None = None
) -> str:
    data: dict[str, Any] = {"schema_version": 1, "feature": feature}
    if north_star is not None:
        data["north_star"] = north_star
    data["intents"] = list(intents)
    return yaml.safe_dump(data, sort_keys=False)


def gate_row(gate_id: str, intents: list[str], entrypoint: str = IMPORTABLE) -> dict[str, Any]:
    return {
        "id": gate_id,
        "class": "drift",
        "category": "drift",
        "intents": intents,
        "ci_job": "factory-gates",
        "priority": "P1",
        "scope": "repo",
        "entrypoint": entrypoint,
    }


def registry(*rows: dict[str, Any]) -> str:
    return yaml.safe_dump({"schema_version": 1, "gates": list(rows)}, sort_keys=False)


def commit_files(repo: RepoBuilder, files: dict[str, str]) -> str:
    for relative, text in files.items():
        repo.write(relative, text)
    return repo.commit("intent fixture")


def check_intent(factory_cli: FactoryCli, repo: Path, *args: str) -> CliResult:
    return factory_cli("check", "intent", *args, repo=repo)


def envelope(result: CliResult) -> dict[str, Any]:
    try:
        data = json.loads(result.stdout)
    except ValueError as exc:
        raise AssertionError(f"not one JSON document: {result.stdout!r} / {result.stderr}") from exc
    assert isinstance(data, dict), data
    return data


def ok_data(result: CliResult) -> dict[str, Any]:
    assert result.exit_code == exit_codes.OK, result
    body = envelope(result)
    assert body.get("ok") is True and isinstance(body.get("data"), dict), body
    data: dict[str, Any] = body["data"]
    return data


def failed_error(result: CliResult) -> dict[str, Any]:
    assert result.exit_code == exit_codes.GATE_FAILURE, result
    body = envelope(result)
    assert body.get("ok") is False and isinstance(body.get("error"), dict), body
    error: dict[str, Any] = body["error"]
    assert error.get("code") == exit_codes.GATE_FAILURE, body
    return error


# --- presence (CLI) -------------------------------------------------------------------------


def test_presence_passes_and_lists_every_intent(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    commit_files(
        repo,
        {
            "specs/demo-feature/intent.yaml": intent_file(
                "demo-feature",
                intent("I-D1", ci("bus.schema")),
                intent("I-D2", ci("x.y", "planned")),
            )
        },
    )
    data = ok_data(check_intent(factory_cli, repo.path, "--json"))
    assert sorted(data["intents"]) == ["I-D1", "I-D2"], data
    assert data["unmapped"] == [], data


def test_presence_fails_naming_the_intent_whose_mappings_are_all_removed(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    commit_files(
        repo,
        {
            "specs/demo-feature/intent.yaml": intent_file(
                "demo-feature", intent("I-D1", ci("bus.schema")), intent("I-D2")
            )
        },
    )
    error = failed_error(check_intent(factory_cli, repo.path, "--json"))
    assert "I-D2" in error["message"], error
    assert error["details"]["unmapped"] == ["I-D2"], error


def test_presence_failure_is_reported_in_plain_output(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    commit_files(
        repo, {"specs/demo-feature/intent.yaml": intent_file("demo-feature", intent("I-D2"))}
    )
    result = check_intent(factory_cli, repo.path)
    assert result.exit_code == exit_codes.GATE_FAILURE, result
    assert "I-D2" in result.stdout + result.stderr, result


def test_intent_without_a_checks_key_is_unmapped(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    commit_files(
        repo,
        {
            "specs/demo-feature/intent.yaml": intent_file(
                "demo-feature", intent("I-D1", ci("bus.schema")), intent("I-D3", has_checks=False)
            )
        },
    )
    error = failed_error(check_intent(factory_cli, repo.path, "--json"))
    assert error["details"]["unmapped"] == ["I-D3"], error


@pytest.mark.parametrize("source", ["registry", "catalog"])
def test_a_registry_or_catalog_mapping_alone_keeps_presence(
    repo: RepoBuilder, factory_cli: FactoryCli, source: str
) -> None:
    files = {
        "specs/demo-feature/intent.yaml": intent_file(
            "demo-feature", intent("I-D1", ci("bus.schema")), intent("I-D2")
        )
    }
    if source == "registry":
        files[REGISTRY] = registry(gate_row("demo-gate", ["I-D2"]))
    else:
        files["specs/demo-feature/acceptance.md"] = (
            "| id | class | intents | severity | when | shall | how | evidence |\n"
            "|----|-------|---------|----------|------|-------|-----|----------|\n"
            "| demo.two | SC-001 | I-D9, I-D2 | must | always | holds | auto | planned |\n"
        )
    commit_files(repo, files)
    data = ok_data(check_intent(factory_cli, repo.path, "--json"))
    assert data["unmapped"] == [], data
    assert "I-D2" in data["intents"], data


def test_presence_spans_every_feature(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    commit_files(
        repo,
        {
            "specs/alpha/intent.yaml": intent_file("alpha", intent("I-A1", ci("bus.schema"))),
            "specs/beta/intent.yaml": intent_file(
                "beta", intent("I-B1", ci("bus.schema")), intent("I-B2")
            ),
        },
    )
    error = failed_error(check_intent(factory_cli, repo.path, "--json"))
    assert error["details"]["unmapped"] == ["I-B2"], error


def test_north_star_counts_as_an_intent(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    star = {"id": "I-N9", "statement": "The north star.", "checks": []}
    commit_files(
        repo,
        {
            "specs/demo-feature/intent.yaml": intent_file(
                "demo-feature", intent("I-D1", ci("bus.schema")), north_star=star
            )
        },
    )
    error = failed_error(check_intent(factory_cli, repo.path, "--json"))
    assert error["details"]["unmapped"] == ["I-N9"], error


def test_flow_and_block_style_checks_are_both_read(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    """Both YAML styles occur in this repo's intent files (001 block, 002 flow)."""
    text = (
        "schema_version: 1\nfeature: demo-feature\nintents:\n"
        "  - id: I-D1\n    kind: goal\n    statement: Flow style.\n"
        "    checks: [{ kind: ci, ref: bus.schema, status: exists }]\n"
        "  - id: I-D2\n    kind: goal\n    statement: Block style.\n"
        "    checks:\n      - { kind: lint, ref: test-seam-ban, status: planned }\n"
        "  - id: I-D3\n    kind: goal\n    statement: Empty flow list.\n    checks: []\n"
    )
    commit_files(repo, {"specs/demo-feature/intent.yaml": text})
    error = failed_error(check_intent(factory_cli, repo.path, "--json"))
    assert error["details"]["unmapped"] == ["I-D3"], error


def test_presence_holds_on_this_repository(factory_cli: FactoryCli) -> None:
    data = ok_data(check_intent(factory_cli, REPO_ROOT, "--json"))
    assert data["unmapped"] == [], data
    assert {"I-N1", "I-B7", "I-P10", "SW-N1", "SW-Q1"} <= set(data["intents"]), data


# --- gate factory-check-intent (head commit is the input) -----------------------------------


MAPPED = intent_file("demo-feature", intent("I-D1", ci("bus.schema")), intent("I-D2", ci("x")))
UNMAPPED = intent_file("demo-feature", intent("I-D1", ci("bus.schema")), intent("I-D2"))


def test_gate_passes_when_head_maps_every_intent(repo: RepoBuilder) -> None:
    """The base (and the checked-out working tree) is unmapped; the head is judged."""
    pair = repo.base_head_pair(
        {"specs/demo-feature/intent.yaml": UNMAPPED}, {"specs/demo-feature/intent.yaml": MAPPED}
    )
    assert_passes(GATE, repo.gate_context(pair, pr_number=1))


def test_gate_blocks_when_head_drops_all_mappings_of_an_intent(repo: RepoBuilder) -> None:
    pair = repo.base_head_pair(
        {"specs/demo-feature/intent.yaml": MAPPED}, {"specs/demo-feature/intent.yaml": UNMAPPED}
    )
    assert_blocks(GATE, repo.gate_context(pair, pr_number=1), "I-D2")


# --- effective coverage (CLI --coverage) ----------------------------------------------------


def post_status(factory_cli: FactoryCli, sha: str, gate_id: str, value: str) -> None:
    factory_cli.github.set_commit_status(sha, f"factory/{gate_id}", value, f"{gate_id}: {value}")


def coverage_data(factory_cli: FactoryCli, repo: Path) -> dict[str, Any]:
    data = ok_data(check_intent(factory_cli, repo, "--coverage", "--json"))
    coverage = data.get("coverage")
    assert isinstance(coverage, dict), data
    return coverage


def test_coverage_counts_only_implemented_passing_or_governor_judged(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    head = commit_files(
        repo,
        {
            "specs/demo-feature/intent.yaml": intent_file(
                "demo-feature",
                intent("I-D1", ci("g-live")),
                intent("I-D2", ci("g-failing")),
                intent("I-D3", ci("g-unimportable")),
                intent("I-D4", ci("ghost-gate", "exists")),
                intent("I-D5", {"kind": "human", "ref": "sprint-postmortem", "status": "exists"}),
                intent("I-D6"),
                intent("I-D7", ci("g-never-ran")),
                intent("I-D8", {"kind": "metric", "ref": "scorecard.drift", "status": "planned"}),
            ),
            REGISTRY: registry(
                gate_row("g-live", ["I-D1", "I-D6"]),
                gate_row("g-failing", ["I-D2"]),
                gate_row("g-unimportable", ["I-D3"], entrypoint=NOT_IMPORTABLE),
                gate_row("g-never-ran", ["I-D7"]),
            ),
        },
    )
    post_status(factory_cli, head, "g-live", "success")
    post_status(factory_cli, head, "g-failing", "failure")
    post_status(factory_cli, head, "g-unimportable", "success")
    post_status(factory_cli, head, "ghost-gate", "success")
    coverage = coverage_data(factory_cli, repo.path)
    assert set(coverage["covered"]) == {"I-D1", "I-D5", "I-D6"}, coverage
    assert set(coverage["uncovered"]) == {"I-D2", "I-D3", "I-D4", "I-D7", "I-D8"}, coverage
    assert coverage["share"] == pytest.approx(3 / 8), coverage


def test_coverage_drops_when_a_passing_check_starts_failing(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    head = commit_files(
        repo,
        {
            "specs/demo-feature/intent.yaml": intent_file(
                "demo-feature", intent("I-D1", ci("g-live")), intent("I-D2", ci("g-other"))
            ),
            REGISTRY: registry(gate_row("g-live", ["I-D1"]), gate_row("g-other", ["I-D2"])),
        },
    )
    post_status(factory_cli, head, "g-live", "success")
    post_status(factory_cli, head, "g-other", "success")
    assert coverage_data(factory_cli, repo.path)["share"] == pytest.approx(1.0)
    post_status(factory_cli, head, "g-live", "failure")
    after = coverage_data(factory_cli, repo.path)
    assert after["share"] == pytest.approx(0.5), after
    assert set(after["uncovered"]) == {"I-D1"}, after
