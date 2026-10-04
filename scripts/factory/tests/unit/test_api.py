"""T010 — frozen interfaces: `run_gate` dispatch and port conformance."""

from __future__ import annotations

import pytest

from factory import api
from factory.api import (
    GateContext,
    GateEntrypointError,
    GateResult,
    GitHubPort,
    OrderState,
    run_gate,
)
from factory.gates.registry import Registry
from tests.fixtures.fake_github import FakeGitHub
from tests.fixtures.repo_builder import RepoBuilder


def passing_gate(ctx: GateContext) -> GateResult:
    return GateResult(gate_id="demo-pass", passed=True, messages=[ctx.head_sha])


def _registry(*rows: tuple[str, str]) -> Registry:
    return Registry.model_validate(
        {
            "schema_version": 1,
            "gates": [
                {
                    "id": gate_id,
                    "class": "drift",
                    "category": "drift",
                    "intents": ["I-X1"],
                    "ci_job": "factory-gates",
                    "priority": "P1",
                    "scope": "repo",
                    "entrypoint": entrypoint,
                }
                for gate_id, entrypoint in rows
            ],
        }
    )


@pytest.fixture
def ctx(repo: RepoBuilder) -> GateContext:
    return repo.gate_context(repo.base_head_pair({}, {"x.txt": "x\n"}))


def test_run_gate_dispatches_to_registry_entrypoint(
    ctx: GateContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = _registry(("demo-pass", "tests.unit.test_api:passing_gate"))
    monkeypatch.setattr(api, "load_registry", lambda: registry)
    result = run_gate("demo-pass", ctx)
    assert result == GateResult(gate_id="demo-pass", passed=True, messages=[ctx.head_sha])


def test_run_gate_unregistered_raises(ctx: GateContext) -> None:
    with pytest.raises(GateEntrypointError, match="not registered"):
        run_gate("no-such-gate", ctx)


def test_run_gate_unimportable_entrypoint_raises(
    ctx: GateContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = _registry(("demo-missing", "factory.gates.nowhere:run"))
    monkeypatch.setattr(api, "load_registry", lambda: registry)
    with pytest.raises(GateEntrypointError, match="not importable"):
        run_gate("demo-missing", ctx)


def test_fake_github_implements_github_port() -> None:
    assert isinstance(FakeGitHub(), GitHubPort)


def test_github_port_reads_commit_statuses() -> None:
    assert callable(getattr(GitHubPort, "list_commit_statuses", None)), (
        "GitHubPort writes commit statuses but has no operation to read them back"
    )


def assert_commit_status_read_after_write(port: GitHubPort) -> None:
    """Port conformance: statuses written by the gate runner are what lifecycle reads."""
    sha = "a" * 40
    other = "b" * 40
    port.set_commit_status(sha, "factory/red-first-proof", "pending", "running")
    port.set_commit_status(
        sha, "factory/red-first-proof", "success", "red first", "https://ci.test/1"
    )
    port.set_commit_status(sha, "factory/test-seam-ban", "failure", "seam in app/llm.py")
    port.set_commit_status(other, "factory/test-seam-ban", "success", "clean")
    read = getattr(port, "list_commit_statuses", None)
    status_type = getattr(api, "CommitStatus", None)
    assert read is not None and status_type is not None, "no commit-status read on the port"
    statuses = read(sha)
    assert all(isinstance(s, status_type) for s in statuses)
    by_context = {s.context: s for s in statuses}
    assert len(statuses) == len(by_context), "expected the latest status per context only"
    assert set(by_context) == {"factory/red-first-proof", "factory/test-seam-ban"}
    latest = by_context["factory/red-first-proof"]
    assert (latest.state, latest.description, latest.target_url) == (
        "success",
        "red first",
        "https://ci.test/1",
    )
    assert by_context["factory/test-seam-ban"].state == "failure"
    assert read("c" * 40) == []


def test_fake_github_commit_status_read_after_write() -> None:
    assert_commit_status_read_after_write(FakeGitHub())


def test_order_states_match_data_model() -> None:
    assert {s.value for s in OrderState} == {
        "issued",
        "claimed",
        "in_review",
        "accepted",
        "rejected",
        "merged",
        "released",
        "stale",
        "blocked_on_governor",
    }
