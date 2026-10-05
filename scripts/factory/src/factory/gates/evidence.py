"""Red-first evidence (contracts/gates.md § Evidence bundle; spec D5, D7 Wave 1).

The untrusted producer (`factory gate evidence`, PR-triggered workflow) serializes the raw
per-test facts from Slice B's `red_first.collect_facts(ctx)` into `factory-evidence.json`;
it classifies nothing. The trusted job reads that file as data and judges it here: the new
and changed test functions come from git (AST, head vs merge base), and the red-first rule
is applied to the raw facts. Any doubt about the bundle fails closed. The facts come from
the PR's own run, so every result is `self-reported:`; the T* re-run is the proof of record.
"""

from __future__ import annotations

import ast
import importlib
import json
import re
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import Any, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from factory.api import GateContext, GateResult
from factory.gates.repo._git import GitError, changed, failed, git, read_blobs

GATE_ID = "red-first-proof"
BUNDLE_FILE = "factory-evidence.json"
SELF_REPORTED = "self-reported:"
RED_FIRST_MODULE = "factory.gates.drift.red_first"
SHA_PATTERN = r"^[0-9a-f]{40}$"
MISSING_MODULE_RE = re.compile(r"No module named '([\w.]+)'")
MISSING_NAME_RE = re.compile(r"cannot import name '(\w+)' from '([\w.]+)'")

Outcome = Literal["passed", "failed", "error", "skipped", "not_collected"]
OUTCOMES: tuple[str, ...] = get_args(Outcome)


class TestFact(BaseModel):
    """One new or changed test function: raw outcomes on base and head, never a verdict."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    node_id: str = Field(min_length=1)
    base_outcome: Outcome
    head_outcome: Outcome
    base_error: str | None


class RedFirstFacts(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    status: Literal["ran", "crashed"]
    error: str | None
    tests: list[TestFact]


class EvidenceBundle(BaseModel):
    """`factory-evidence.json`: extra keys are rejected at every level."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal[1]
    kind: Literal["factory-evidence"]
    base_sha: str = Field(pattern=SHA_PATTERN)
    head_sha: str = Field(pattern=SHA_PATTERN)
    red_first: RedFirstFacts


# --- producer ----------------------------------------------------------------------------


def _fact(raw: Any) -> TestFact:
    node_id = getattr(raw, "node_id", None)
    for field in ("base_outcome", "head_outcome"):
        value = getattr(raw, field, None)
        if value not in OUTCOMES:
            raise ValueError(f"{node_id}: unknown {field} {value!r}")
    base_error = getattr(raw, "base_error", None)
    return TestFact(
        node_id=str(node_id),
        base_outcome=raw.base_outcome,
        head_outcome=raw.head_outcome,
        base_error=None if base_error is None else str(base_error),
    )


def produce(ctx: GateContext) -> EvidenceBundle:
    """Serialize Slice B's raw facts; a crash or an unknown outcome is `status: crashed`."""
    try:
        collect = importlib.import_module(RED_FIRST_MODULE).collect_facts
        tests = sorted((_fact(raw) for raw in collect(ctx)), key=lambda t: t.node_id)
        red_first = RedFirstFacts(status="ran", error=None, tests=tests)
    except Exception as exc:
        red_first = RedFirstFacts(status="crashed", error=f"{type(exc).__name__}: {exc}", tests=[])
    return EvidenceBundle(
        schema_version=1,
        kind="factory-evidence",
        base_sha=ctx.base_sha,
        head_sha=ctx.head_sha,
        red_first=red_first,
    )


def write_bundle(bundle: EvidenceBundle, out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    target = out / BUNDLE_FILE
    target.write_text(bundle.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return target


# --- trusted judge -----------------------------------------------------------------------


def _fail(*problems: str) -> GateResult:
    return failed(GATE_ID, list(problems))


def load_bundle(evidence: Path | None, max_bytes: int) -> EvidenceBundle | GateResult:
    """The one bundle in `evidence`, or a failing result naming why it cannot be trusted."""
    if evidence is None:
        return _fail("evidence missing: no --evidence directory (CI mode requires one)")
    if not evidence.is_dir():
        return _fail(f"evidence missing: {evidence} is not a directory")
    names = sorted(path.name for path in evidence.iterdir())
    problems = [
        f"unexpected file {name!r} in the evidence" for name in names if name != BUNDLE_FILE
    ]
    if BUNDLE_FILE not in names:
        problems.append(f"evidence missing: no {BUNDLE_FILE}")
    if problems:
        return _fail(*problems)
    path = evidence / BUNDLE_FILE
    if path.is_symlink() or not path.is_file():
        return _fail(f"{BUNDLE_FILE} is not a regular file")
    size = path.stat().st_size
    if size > max_bytes:
        return _fail(f"{BUNDLE_FILE} is {size} bytes, over the size limit of {max_bytes}")
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        return _fail(f"{BUNDLE_FILE} is unreadable ({type(exc).__name__})")
    try:
        return EvidenceBundle.model_validate(data)
    except ValidationError as exc:
        where = "; ".join(
            f"{'.'.join(map(str, error['loc'])) or '<root>'}: {error['msg']}"
            for error in exc.errors()[:5]
        )
        return _fail(f"{BUNDLE_FILE} fails its schema ({where})")


def is_test_file(path: str) -> bool:
    name = PurePosixPath(path).name
    return name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py"))


def tests_in(source: str) -> dict[str, str]:
    """Test name (`test` or `Class::test`) -> its source text."""
    found: dict[str, str] = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith(
            "test"
        ):
            found[node.name] = ast.get_source_segment(source, node) or ""
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            for item in node.body:
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef) and (
                    item.name.startswith("test")
                ):
                    found[f"{node.name}::{item.name}"] = ast.get_source_segment(source, item) or ""
    return found


def top_level_names(source: str | None) -> set[str]:
    if not source:
        return set()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names.update(t.id for t in targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.Import | ast.ImportFrom):
            names.update((a.asname or a.name).split(".")[0] for a in node.names)
    return names


def _module_of(path: str) -> str:
    parts = list(PurePosixPath(path).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _dotted_suffix(module: str, wanted: str) -> bool:
    return module == wanted or module.endswith("." + wanted)


class Change:
    """The PR's changed files (head vs merge base), read from git as data."""

    def __init__(self, ctx: GateContext) -> None:
        self.repo = ctx.repo_path
        self.head = ctx.head_sha
        self.merge_base = git(self.repo, "merge-base", ctx.base_sha, ctx.head_sha).strip()
        self.files = changed(self.repo, ctx.base_sha, ctx.head_sha)
        python = [path for _, path in self.files if path.endswith(".py")]
        self._head = read_blobs(self.repo, self.head, python)
        self._base = read_blobs(self.repo, self.merge_base, python)

    def head_text(self, path: str) -> str | None:
        return self._head.get(path)

    def base_text(self, path: str) -> str | None:
        return self._base.get(path)

    def adds_module(self, module: str) -> bool:
        return any(
            status == "A" and path.endswith(".py") and _dotted_suffix(_module_of(path), module)
            for status, path in self.files
        )

    def adds_symbol(self, symbol: str, module: str) -> bool:
        for status, path in self.files:
            if status == "D" or not path.endswith(".py"):
                continue
            if not _dotted_suffix(_module_of(path), module):
                continue
            if symbol in top_level_names(self.head_text(path)) and symbol not in top_level_names(
                self.base_text(path)
            ):
                return True
        return False

    def error_is_red(self, text: str | None) -> bool:
        """A base import error is red only when every missing name is one the PR adds."""
        modules = MISSING_MODULE_RE.findall(text or "")
        symbols = MISSING_NAME_RE.findall(text or "")
        if not modules and not symbols:
            return False
        return all(self.adds_module(m) for m in modules) and all(
            self.adds_symbol(s, m) for s, m in symbols
        )

    def judged_tests(self) -> tuple[list[str], list[str]]:
        """Node ids of new or changed test functions; plus problems for unparseable files."""
        nodes: list[str] = []
        problems: list[str] = []
        for status, path in self.files:
            if status == "D" or not is_test_file(path):
                continue
            try:
                head_tests = tests_in(self.head_text(path) or "")
            except SyntaxError as exc:
                problems.append(f"{path} does not parse at head ({exc.msg})")
                continue
            try:
                base_tests = tests_in(self.base_text(path) or "")
            except SyntaxError:
                base_tests = {}
            nodes += [f"{path}::{n}" for n, src in head_tests.items() if base_tests.get(n) != src]
        return nodes, problems


def _last_line(text: str | None) -> str:
    lines = [line for line in (text or "").strip().splitlines() if line.strip()]
    return lines[-1].strip() if lines else "no error text"


def base_problem(fact: TestFact, change: Change) -> str | None:
    if fact.base_outcome == "failed":
        return None
    if fact.base_outcome in ("error", "not_collected"):
        if change.error_is_red(fact.base_error):
            return None
        return f"base broken, not red ({fact.base_outcome}): {_last_line(fact.base_error)}"
    if fact.base_outcome == "passed":
        return "passes on base code; a new or changed test must fail first (red first)"
    return "is skipped on base; a skip is not a test failure (red first)"


def _duplicates(node_ids: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    twice: list[str] = []
    for node_id in node_ids:
        if node_id in seen and node_id not in twice:
            twice.append(node_id)
        seen.add(node_id)
    return twice


def judge(ctx: GateContext, evidence: Path | None) -> GateResult:
    """`red-first-proof` from the bundle in `evidence`, judged by `main`'s code."""
    loaded = load_bundle(evidence, ctx.config.evidence_max_bytes)
    if isinstance(loaded, GateResult):
        return loaded
    bundle = loaded
    if bundle.head_sha != ctx.head_sha:
        return _fail(f"bundle head_sha {bundle.head_sha} is not the PR head {ctx.head_sha}")
    if bundle.red_first.status == "crashed":
        return _fail(f"the evidence producer crashed: {bundle.red_first.error or 'no error text'}")
    try:
        change = Change(ctx)
    except GitError as exc:
        return _fail(f"cannot read the change from git ({exc})")
    expected, problems = change.judged_tests()
    facts = {fact.node_id: fact for fact in bundle.red_first.tests}
    problems += [
        f"{node}: listed twice" for node in _duplicates(f.node_id for f in bundle.red_first.tests)
    ]
    problems += [
        f"{node}: not a new or changed test function" for node in facts if node not in expected
    ]
    for node in expected:
        fact = facts.get(node)
        if fact is None:
            problems.append(f"{node}: omitted from the evidence")
            continue
        base = base_problem(fact, change)
        if base:
            problems.append(f"{node}: {base}")
        if fact.head_outcome != "passed":
            problems.append(f"{node}: does not pass on head ({fact.head_outcome})")
    if problems:
        return _fail(*problems)
    note = (
        f"{SELF_REPORTED} {len(expected)} new or changed test(s) red on base, green on head "
        "(facts from the PR's own run; the T* re-run is the proof of record)"
    )
    return GateResult(gate_id=GATE_ID, passed=True, messages=[f"{GATE_ID}: {note}"])
