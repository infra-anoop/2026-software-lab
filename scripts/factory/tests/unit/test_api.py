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
