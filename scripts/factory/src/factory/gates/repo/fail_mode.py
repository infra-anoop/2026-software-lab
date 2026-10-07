"""`gate.fail-mode-category` (I-P9): every registry row at head is valid, and
`class: governor-only` holds exactly for the governor categories.

The head registry (`scripts/factory/gates.yaml`) is the source of truth: when it is
missing or unreadable the gate blocks and names the path; there is no fallback to the
installed registry.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import yaml
from pydantic import ValidationError

from factory.api import GateContext, GateResult
from factory.gates.registry import Gate
from factory.gates.repo._git import outcome, show

GATE_ID = "gate.fail-mode-category"
REGISTRY_FILE = "scripts/factory/gates.yaml"


def _error_text(exc: ValidationError) -> str:
    parts = []
    for error in exc.errors():
        where = ".".join(str(part) for part in error["loc"])
        message = str(error["msg"])
        if where and error["type"] != "missing":
            message += f" (got {error['input']!r})"
        parts.append(f"{where}: {message}" if where else message)
    return "; ".join(parts)


def parse_registry(text: str | None, path: str = REGISTRY_FILE) -> tuple[list[Gate], list[str]]:
    """Valid rows plus one problem per invalid row or file-level defect (each names a gate
    id or the path)."""
    if text is None:
        return [], [f"{path}: not found"]
    try:
        raw: Any = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return [], [f"{path}: unreadable YAML ({str(exc).splitlines()[0]})"]
    if not isinstance(raw, dict) or not isinstance(raw.get("gates"), list):
        return [], [f"{path}: expected a mapping with a `gates` list"]
    problems = []
    if raw.get("schema_version") != 1:
        problems.append(f"{path}: schema_version must be 1")
    unknown_keys = sorted(set(raw) - {"schema_version", "gates"})
    if unknown_keys:
        problems.append(f"{path}: unknown keys {unknown_keys}")
    gates: list[Gate] = []
    for index, row in enumerate(raw["gates"]):
        gate_id = row.get("id") if isinstance(row, dict) else None
        label = gate_id if isinstance(gate_id, str) and gate_id else f"{path}: row {index}"
        try:
            gates.append(Gate.model_validate(row))
        except ValidationError as exc:
            problems.append(f"{label}: {_error_text(exc)}")
    counts = Counter(gate.id for gate in gates)
    problems += [f"{gate_id}: duplicate gate id" for gate_id, n in counts.items() if n > 1]
    return gates, problems


def head_registry(ctx: GateContext) -> tuple[list[Gate], list[str]]:
    return parse_registry(show(ctx.repo_path, ctx.head_sha, REGISTRY_FILE))


def run(ctx: GateContext) -> GateResult:
    gates, problems = head_registry(ctx)
    return outcome(GATE_ID, problems, f"{len(gates)} registry rows valid")
