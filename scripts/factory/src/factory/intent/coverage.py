"""Intent presence and effective coverage (T063; FR-023; SC-005; catalog `trace.*`).

Presence: every intent in every `<spec root>/*/intent.yaml` (`north_star` and
`intents`) is mapped by its own non-empty `checks`, a `gates.yaml` row listing it in
`intents`, or an `acceptance.md` row listing it in `intents`.

Effective coverage: the share of intents backed by an implemented check (a gate in
the repo's `gates.yaml` whose entrypoint imports) whose latest `factory/<gate-id>`
commit status on HEAD is `success`, or by a governor-judged mapping: `kind: human`
with `status: exists` (governor 2026-10-04). A gate backs an intent it lists, or one
whose own non-human check names the gate. Below 90% fails only in sprint-close mode
(`--require-target`, governor 2026-10-04).
"""

from __future__ import annotations

import importlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

import yaml
from pydantic import ValidationError

from factory.api import GateContext, GateResult
from factory.gates.drift._git import Change, list_paths
from factory.gates.drift._specs import tables
from factory.gates.registry import Gate, Registry, RegistryError

GATE = "factory-check-intent"
REGISTRY_PATH = "scripts/factory/gates.yaml"
INTENT_FILE = "intent.yaml"
CATALOG_FILE = "acceptance.md"
TARGET = Fraction(9, 10)


class IntentError(Exception):
    """An intent file cannot be read as intents."""


class Tree(Protocol):
    """Read-only view of the repository: the working tree or one git commit."""

    def paths(self, prefix: str) -> list[str]: ...

    def read(self, path: str) -> str | None: ...


class WorkTree:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def paths(self, prefix: str) -> list[str]:
        base = self.root / prefix
        if not base.is_dir():
            return []
        return sorted(p.relative_to(self.root).as_posix() for p in base.rglob("*") if p.is_file())

    def read(self, path: str) -> str | None:
        target = self.root / path
        return target.read_text(encoding="utf-8") if target.is_file() else None


class GitTree:
    def __init__(self, repo: Path, ref: str) -> None:
        self._change = Change(Path(repo), ref, ref)
        self.ref = ref

    def paths(self, prefix: str) -> list[str]:
        return list_paths(self._change.repo, self.ref, prefix)

    def read(self, path: str) -> str | None:
        return self._change.text_at(self.ref, path)


@dataclass(frozen=True)
class Check:
    kind: str
    ref: str
    status: str

    @property
    def governor_judged(self) -> bool:
        return self.kind == "human" and self.status == "exists"


@dataclass
class Intent:
    id: str
    checks: list[Check] = field(default_factory=list)


def _checks(entry: Mapping[str, Any], where: str) -> list[Check]:
    raw = entry.get("checks") or []
    if not isinstance(raw, list):
        raise IntentError(f"{where}: intent {entry.get('id')!r} checks must be a list")
    return [
        Check(str(c.get("kind", "")), str(c.get("ref", "")), str(c.get("status", "")))
        for c in raw
        if isinstance(c, Mapping)
    ]


def intent_files(tree: Tree, spec_roots: Iterable[str]) -> list[str]:
    found: list[str] = []
    for root in spec_roots:
        prefix = root.rstrip("/")
        for path in tree.paths(prefix):
            parts = PurePosixPath(path).parts
            if len(parts) == len(PurePosixPath(prefix).parts) + 2 and parts[-1] == INTENT_FILE:
                found.append(path)
    return sorted(found)


def load_intents(tree: Tree, spec_roots: Iterable[str]) -> dict[str, Intent]:
    intents: dict[str, Intent] = {}
    for path in intent_files(tree, spec_roots):
        try:
            data = yaml.safe_load(tree.read(path) or "") or {}
        except yaml.YAMLError as exc:
            raise IntentError(f"{path}: invalid YAML ({exc})") from exc
        if not isinstance(data, Mapping):
            raise IntentError(f"{path}: an intent file is a mapping")
        entries = [data["north_star"]] if isinstance(data.get("north_star"), Mapping) else []
        raw = data.get("intents") or []
        entries += [e for e in raw if isinstance(e, Mapping)] if isinstance(raw, list) else []
        for entry in entries:
            if not entry.get("id"):
                raise IntentError(f"{path}: an intent has no id")
            intent = intents.setdefault(str(entry["id"]), Intent(str(entry["id"])))
            intent.checks += _checks(entry, path)
    return intents


def load_registry_from(tree: Tree) -> Registry:
    text = tree.read(REGISTRY_PATH)
    if text is None:
        return Registry(schema_version=1, gates=[])
    try:
        return Registry.model_validate(yaml.safe_load(text))
    except (yaml.YAMLError, ValidationError) as exc:
        raise RegistryError(f"{REGISTRY_PATH}: {exc}") from exc


def catalog_mappings(tree: Tree, spec_roots: Iterable[str]) -> set[str]:
    mapped: set[str] = set()
    for root in spec_roots:
        for path in tree.paths(root.rstrip("/")):
            if PurePosixPath(path).name != CATALOG_FILE:
                continue
            for table in tables(tree.read(path) or ""):
                for row in table:
                    cell = row.cells.get("intents", "")
                    mapped.update(i.strip().strip("`") for i in cell.split(",") if i.strip())
    return mapped


@dataclass(frozen=True)
class Presence:
    intents: list[str]
    unmapped: list[str]


@dataclass(frozen=True)
class Coverage:
    covered: list[str]
    uncovered: list[str]

    @property
    def share(self) -> float:
        total = len(self.covered) + len(self.uncovered)
        return len(self.covered) / total if total else 0.0

    @property
    def meets_target(self) -> bool:
        total = len(self.covered) + len(self.uncovered)
        return total > 0 and Fraction(len(self.covered), total) >= TARGET

    def as_data(self) -> dict[str, Any]:
        return {"share": self.share, "covered": self.covered, "uncovered": self.uncovered}

    def summary(self) -> str:
        total = len(self.covered) + len(self.uncovered)
        return f"{len(self.covered)}/{total} ({self.share:.1%})"


def presence(tree: Tree, spec_roots: Iterable[str]) -> Presence:
    roots = list(spec_roots)
    intents = load_intents(tree, roots)
    by_gates = {i for gate in load_registry_from(tree).gates for i in gate.intents}
    by_catalog = catalog_mappings(tree, roots)
    unmapped = [
        intent.id
        for intent in intents.values()
        if not intent.checks and intent.id not in by_gates and intent.id not in by_catalog
    ]
    return Presence(sorted(intents), sorted(unmapped))


def importable(gate: Gate) -> bool:
    try:
        return callable(getattr(importlib.import_module(gate.module), gate.function))
    except (ImportError, AttributeError):
        return False


def coverage(tree: Tree, spec_roots: Iterable[str], statuses: Mapping[str, str]) -> Coverage:
    """`statuses`: commit-status context -> state on HEAD (latest per context)."""
    intents = load_intents(tree, list(spec_roots))
    live = [
        gate
        for gate in load_registry_from(tree).gates
        if statuses.get(f"factory/{gate.id}") == "success" and importable(gate)
    ]
    covered: list[str] = []
    uncovered: list[str] = []
    for intent in sorted(intents.values(), key=lambda i: i.id):
        refs = {c.ref for c in intent.checks if c.kind != "human"}
        backed = any(c.governor_judged for c in intent.checks) or any(
            intent.id in gate.intents or gate.id in refs for gate in live
        )
        (covered if backed else uncovered).append(intent.id)
    return Coverage(covered, uncovered)


def presence_gate(ctx: GateContext) -> GateResult:
    """Gate `factory-check-intent`: presence over the head commit."""
    tree = GitTree(ctx.repo_path, ctx.head_sha)
    try:
        result = presence(tree, ctx.config.spec_roots)
    except (IntentError, RegistryError) as exc:
        return GateResult(gate_id=GATE, passed=False, messages=[f"{GATE}: {exc}"])
    if result.unmapped:
        return GateResult(
            gate_id=GATE,
            passed=False,
            messages=[
                f"{GATE}: intent {intent_id} has no check mapping (own checks, gates.yaml,"
                " or an acceptance.md row)"
                for intent_id in result.unmapped
            ],
            intent_ids=result.unmapped,
        )
    return GateResult(
        gate_id=GATE,
        passed=True,
        messages=[f"{GATE}: all {len(result.intents)} intents are mapped"],
    )


def group_by_intent(
    results: Iterable[GateResult], registry: Registry | None = None
) -> dict[str, list[GateResult]]:
    """Gate results per intent id: a result's own `intent_ids`, else its registry row's."""
    gates = {gate.id: gate for gate in registry.gates} if registry else {}
    grouped: dict[str, list[GateResult]] = {}
    for result in results:
        gate = gates.get(result.gate_id)
        ids = result.intent_ids or (gate.intents if gate else [])
        for intent_id in ids:
            grouped.setdefault(intent_id, []).append(result)
    return dict(sorted(grouped.items()))
