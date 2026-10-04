"""T009 — gate registry model, loader, and the P1 rows of gates.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from factory.gates.registry import Gate, Registry, RegistryError, load_registry

# Every P1 gate id in specs/001-factory-v2/contracts/gates.md § P1 registry.
P1_GATES: dict[str, tuple[str, str, list[str], str]] = {
    "bus.schema": ("drift", "drift", ["I-M2"], "repo"),
    "bus.immutable": ("drift", "drift", ["I-M2"], "changed_lines"),
    "bus.no-handwritten-status": ("drift", "drift", ["I-M2"], "changed_lines"),
    "factory-check-intent": ("drift", "drift", ["I-N1", "I-P4"], "repo"),
    "red-first-proof": ("drift", "drift", ["I-B7", "I-P2"], "changed_lines"),
    "test-seam-ban": ("drift", "drift", ["I-A8"], "changed_lines"),
    "diff-within-owned-paths": ("drift", "drift", ["I-B8", "I-A8"], "changed_lines"),
    "deferral-words-need-od": ("drift", "drift", ["I-B6"], "changed_lines"),
    "order-fidelity-declared": ("drift", "drift", ["I-B5"], "changed_lines"),
    "lock.letter-tokens": ("drift", "drift", ["I-B5"], "changed_lines"),
    "decision-request-no-ids": ("drift", "drift", ["I-B3"], "changed_lines"),
    "catalog-test-linkage": ("drift", "drift", ["I-B7"], "changed_lines"),
    "pr-links-order": ("drift", "drift", ["I-P1"], "pr"),
    "order-blocked-on-open-human-od": ("governor-only", "governor_decision", ["I-X3"], "pr"),
    "spawn-concurrency-cap": ("drift", "drift", ["I-X4"], "pr"),
    "verdict.reviewer-family-differs": ("drift", "drift", ["I-P3"], "pr"),
    "verdict.inputs-isolated": ("drift", "drift", ["I-P3"], "pr"),
    "message.override": ("governor-only", "governor_decision", ["I-M1", "I-P9"], "pr"),
    "gate.fail-mode-category": ("drift", "drift", ["I-P9"], "repo"),
    "hook-has-ci-twin": ("drift", "drift", ["I-G5"], "repo"),
    "factory-status-test": ("drift", "drift", ["I-M4"], "repo"),
    "validate-secrets-schema": ("governor-only", "secrets", ["I-O2", "I-A3"], "repo"),
    "validate-deploy-env": ("drift", "drift", ["I-O1"], "repo"),
    "uv-sync-locked": ("drift", "drift", ["I-O3"], "repo"),
}


def gate_row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": "demo-gate",
        "class": "drift",
        "category": "drift",
        "intents": ["I-X1"],
        "ci_job": "factory-gates",
        "priority": "P1",
        "scope": "repo",
        "entrypoint": "factory.gates.demo:run",
    }
    row.update(overrides)
    return row


def test_registry_lists_every_p1_gate_with_contract_fields() -> None:
    registry = load_registry()
    for gate_id, (gate_class, category, intents, scope) in P1_GATES.items():
        gate = registry.get(gate_id)
        assert (gate.gate_class, gate.category, gate.intents, gate.scope, gate.priority) == (
            gate_class,
            category,
            intents,
            scope,
            "P1",
        ), gate_id
        assert ":" in gate.entrypoint


@pytest.mark.parametrize("category", ["spend", "secrets", "irreversible", "governor_decision"])
def test_governor_only_categories_require_governor_only_class(category: str) -> None:
    Gate.model_validate(gate_row(**{"class": "governor-only", "category": category}))
    with pytest.raises(ValidationError, match="governor-only"):
        Gate.model_validate(gate_row(category=category))


def test_governor_only_class_requires_governor_category() -> None:
    with pytest.raises(ValidationError, match="governor-only"):
        Gate.model_validate(gate_row(**{"class": "governor-only", "category": "drift"}))


@pytest.mark.parametrize("entrypoint", ["factory.gates.demo", "factory.gates.demo:", ":run"])
def test_entrypoint_is_module_colon_function(entrypoint: str) -> None:
    with pytest.raises(ValidationError):
        Gate.model_validate(gate_row(entrypoint=entrypoint))


def test_duplicate_gate_ids_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate"):
        Registry.model_validate({"schema_version": 1, "gates": [gate_row(), gate_row()]})


def test_unknown_gate_lookup_raises() -> None:
    with pytest.raises(RegistryError):
        load_registry().get("no-such-gate")


def test_load_registry_reports_invalid_file(tmp_path: Path) -> None:
    path = tmp_path / "gates.yaml"
    path.write_text(yaml.safe_dump({"schema_version": 1, "gates": [gate_row(scope="all")]}))
    with pytest.raises(RegistryError, match=str(path)):
        load_registry(path)
