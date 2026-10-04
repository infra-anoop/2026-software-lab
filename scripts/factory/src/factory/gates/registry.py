"""Gate registry model + loader (`scripts/factory/gates.yaml`; data-model § Gate).

Rule: `class: governor-only` <=> `category` in {spend, secrets, irreversible,
governor_decision}. Frozen at CP0; slices append their own rows to gates.yaml.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from factory import PROJECT_DIR

REGISTRY_PATH = PROJECT_DIR / "gates.yaml"
GOVERNOR_ONLY_CATEGORIES = frozenset({"spend", "secrets", "irreversible", "governor_decision"})

GateClassName = Literal["drift", "governor-only"]
GateCategory = Literal["drift", "spend", "secrets", "irreversible", "governor_decision"]
GatePriority = Literal["P1", "P2", "P3"]
GateScope = Literal["changed_lines", "repo", "pr"]


class RegistryError(Exception):
    """gates.yaml is missing, invalid, or names an unknown gate."""


class Gate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    id: str = Field(min_length=1)
    gate_class: GateClassName = Field(alias="class")
    category: GateCategory
    intents: list[str] = Field(min_length=1)
    ci_job: str = Field(min_length=1)
    hook_twin_of: str | None = None
    priority: GatePriority
    scope: GateScope
    entrypoint: str = Field(pattern=r"^[A-Za-z_][\w.]*:[A-Za-z_]\w*$")

    @model_validator(mode="after")
    def _class_matches_category(self) -> Self:
        governor_only = self.gate_class == "governor-only"
        if governor_only != (self.category in GOVERNOR_ONLY_CATEGORIES):
            raise ValueError(
                f"gate {self.id!r}: class governor-only is required exactly when category is one"
                f" of {sorted(GOVERNOR_ONLY_CATEGORIES)} (got class={self.gate_class},"
                f" category={self.category})"
            )
        return self

    @property
    def module(self) -> str:
        return self.entrypoint.split(":", 1)[0]

    @property
    def function(self) -> str:
        return self.entrypoint.split(":", 1)[1]


class Registry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    gates: list[Gate]

    @model_validator(mode="after")
    def _unique_ids(self) -> Self:
        counts = Counter(gate.id for gate in self.gates)
        duplicates = sorted(gate_id for gate_id, n in counts.items() if n > 1)
        if duplicates:
            raise ValueError(f"duplicate gate ids: {duplicates}")
        return self

    def ids(self) -> list[str]:
        return [gate.id for gate in self.gates]

    def get(self, gate_id: str) -> Gate:
        for gate in self.gates:
            if gate.id == gate_id:
                return gate
        raise RegistryError(f"gate {gate_id!r} is not registered in gates.yaml")


def load_registry(path: Path = REGISTRY_PATH) -> Registry:
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistryError(f"{path}: not found") from exc
    except yaml.YAMLError as exc:
        raise RegistryError(f"{path}: invalid YAML: {exc}") from exc
    try:
        return Registry.model_validate(raw)
    except ValidationError as exc:
        raise RegistryError(f"{path}: {exc}") from exc
