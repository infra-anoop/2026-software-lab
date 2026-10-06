"""Gate `red-first-proof` (T042; FR-012; I-B7, I-P2; research.md § Red-first proof).

New and changed tests (by test function, head vs base) must fail on base code with the
head test files overlaid, with a real failure inside the test body. A collection or
import error is red only when every missing name is a module or symbol the PR adds;
any other base error is "base broken". The same tests must pass on head. A PR with no
new or changed tests passes.

The base and head trees are materialized from `git archive` into a temporary
directory outside the repository; tests run there in a subprocess with a small result
plugin, under the project's own interpreter (`uv run` when the project root has a
`pyproject.toml`, else this interpreter). Each test file runs on its own, per side, so
one file's collection error cannot hide another file's tests (T106). The child gets
only `factory.config.child_environment()`: an explicit allowlist, never the caller's
environment (PR-B4).

`collect_facts(ctx)` returns the raw per-test facts the verdict is judged from (node
id, pytest outcome per side, raw error text) without classifying them; the evidence
bundle built from them is Slice C's (T097).
"""

from __future__ import annotations

import ast
import io
import json
import re
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from factory.api import GateContext, GateResult
from factory.config.settings import child_environment
from factory.gates.drift._common import passed, verdict
from factory.gates.drift._git import Change, FileChange, GitError, list_paths

GATE = "red-first-proof"
TEST_DIRS = frozenset({"tests", "test"})
TIMEOUT_SECONDS = 900
PYTEST_ABORTED = frozenset({2, 3, 4})  # interrupted, internal error, usage error
MISSING_MODULE_RE = re.compile(r"No module named '([\w.]+)'")
MISSING_NAME_RE = re.compile(r"cannot import name '(\w+)' from '([\w.]+)'")
# Runs in the child interpreter: `python -c BOOTSTRAP <results.json> <pytest args...>`.
BOOTSTRAP = """\
import json, sys
sys.dont_write_bytecode = True
import pytest

results = {"tests": {}, "collect_errors": []}


class Recorder:
    def pytest_runtest_logreport(self, report):
        entry = results["tests"].setdefault(report.nodeid, {})
        if report.when == "call":
            entry["call"] = report.outcome
        elif report.when == "setup" and report.failed:
            entry["setup"] = "failed"
        elif report.when == "setup" and report.skipped:
            entry["call"] = "skipped"

    def pytest_collectreport(self, report):
        if report.failed:
            results["collect_errors"].append(
                {"nodeid": report.nodeid, "text": str(report.longrepr)}
            )


code = pytest.main(sys.argv[2:], plugins=[Recorder()])
with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump(results, handle)
sys.exit(int(code))
"""


def is_test_file(path: str) -> bool:
    name = PurePosixPath(path).name
    return name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py"))


def is_test_support(path: str) -> bool:
    pure = PurePosixPath(path)
    return (
        is_test_file(path)
        or pure.name == "conftest.py"
        or any(part in TEST_DIRS for part in pure.parts[:-1])
    )


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


def project_root(path: str, head_paths: set[str]) -> str:
    """Closest ancestor with `pyproject.toml`, else the top-most with `conftest.py`."""
    parents = [str(p) for p in PurePosixPath(path).parents if str(p) != "."]
    for parent in parents:
        if f"{parent}/pyproject.toml" in head_paths:
            return parent
    with_conftest = [parent for parent in parents if f"{parent}/conftest.py" in head_paths]
    if with_conftest:
        return with_conftest[-1]
    return str(PurePosixPath(path).parent)


@dataclass
class Outcome:
    calls: list[str] = field(default_factory=list)
    setup_failed: bool = False


@dataclass
class Run:
    outcomes: dict[str, Outcome]
    collect_errors: list[dict[str, str]]
    crashed: str | None = None

    def outcome(self, node_id: str) -> Outcome:
        merged = Outcome()
        for reported, outcome in self.outcomes.items():
            if reported == node_id or reported.startswith(node_id + "["):
                merged.calls += outcome.calls
                merged.setup_failed |= outcome.setup_failed
        return merged

    def collect_error(self, file_id: str) -> str | None:
        texts = [e["text"] for e in self.collect_errors if e["nodeid"] in {file_id, ""}]
        return "\n".join(texts) if texts else None


def materialize(repo: Path, sha: str, root: str, dest: Path) -> Path:
    """Extract the whole tree at `sha` (tests may read repo files outside their project)."""
    args = ["git", "-C", str(repo), "archive", "--format=tar", sha]
    result = subprocess.run(args, check=False, capture_output=True)
    if result.returncode != 0:
        raise GitError(result.stderr.decode(errors="replace").strip())
    with tarfile.open(fileobj=io.BytesIO(result.stdout)) as archive:
        archive.extractall(dest, filter="data")
    target = dest / root if root else dest
    target.mkdir(parents=True, exist_ok=True)
    return target


def run_pytest(project: Path, node_ids: list[str], out: Path) -> Run:
    if (project / "pyproject.toml").is_file():
        command = ["uv", "run", "--directory", str(project), "--locked", "python"]
    else:
        command = [sys.executable]
    command += [
        "-c",
        BOOTSTRAP,
        str(out),
        "-q",
        "-p",
        "no:cacheprovider",
        "-o",
        "addopts=",
        "--continue-on-collection-errors",
        "--rootdir",
        str(project),
        *node_ids,
    ]
    try:
        result = subprocess.run(
            command,
            cwd=project,
            env=child_environment(),
            check=False,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Run({}, [], crashed=str(exc))
    if not out.is_file():
        tail = (result.stdout + result.stderr).strip().splitlines()[-5:]
        return Run({}, [], crashed=" / ".join(tail) or f"pytest exited {result.returncode}")
    data = json.loads(out.read_text(encoding="utf-8"))
    if result.returncode in PYTEST_ABORTED and not data["tests"] and not data["collect_errors"]:
        tail = (result.stdout + result.stderr).strip().splitlines()[-5:]
        return Run({}, [], crashed=" / ".join(tail) or f"pytest exited {result.returncode}")
    outcomes: dict[str, Outcome] = {}
    for node_id, entry in data["tests"].items():
        outcome = outcomes.setdefault(node_id, Outcome())
        if "call" in entry:
            outcome.calls.append(entry["call"])
        outcome.setup_failed |= entry.get("setup") == "failed"
    return Run(outcomes, data["collect_errors"])


class Judge:
    def __init__(self, change: Change) -> None:
        self.change = change
        self.files = {c.path: c for c in change.files}

    def module_of(self, path: str) -> str:
        pure = PurePosixPath(path)
        parts = list(pure.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts.pop()
        return ".".join(parts)

    def adds_module(self, module: str) -> bool:
        return any(
            c.status == "A"
            and c.path.endswith(".py")
            and _dotted_suffix(self.module_of(c.path), module)
            for c in self.change.files
        )

    def adds_symbol(self, symbol: str, module: str) -> bool:
        for c in self.change.files:
            if c.status == "D" or not c.path.endswith(".py"):
                continue
            if not _dotted_suffix(self.module_of(c.path), module):
                continue
            head = top_level_names(self.change.head_text(c.path))
            base = top_level_names(self.change.base_text(c.path))
            if symbol in head and symbol not in base:
                return True
        return False

    def adds_name(self, name: str, module: str) -> bool:
        """`from module import name`: a symbol the PR adds to `module`, or a submodule
        `module.name` the PR adds (W7)."""
        return self.adds_symbol(name, module) or self.adds_module(f"{module}.{name}")

    def error_is_red(self, text: str) -> bool:
        modules = MISSING_MODULE_RE.findall(text)
        symbols = MISSING_NAME_RE.findall(text)
        if not modules and not symbols:
            return False
        return all(self.adds_module(m) for m in modules) and all(
            self.adds_name(s, m) for s, m in symbols
        )


def _dotted_suffix(module: str, wanted: str) -> bool:
    return module == wanted or module.endswith("." + wanted)


def judged_tests(
    change: Change, test_files: list[FileChange]
) -> tuple[dict[str, list[str]], list[str]]:
    """Path -> new or changed test names; plus problems for unparseable files."""
    judged: dict[str, list[str]] = {}
    problems: list[str] = []
    for test_file in test_files:
        head = change.head_text(test_file.path) or ""
        try:
            head_tests = tests_in(head)
        except SyntaxError as exc:
            problems.append(f"{test_file.path} does not parse at head ({exc.msg})")
            continue
        try:
            base_tests = tests_in(change.base_text(test_file.path) or "")
        except SyntaxError:
            base_tests = {}
        names = [n for n, src in head_tests.items() if base_tests.get(n) != src]
        if names:
            judged[test_file.path] = names
    return judged, problems


def run(ctx: GateContext) -> GateResult:
    change = Change.of(ctx)
    judged, problems = judged_tests(change, test_files_of(change))
    if not judged and not problems:
        return passed(GATE, "no new or changed tests")
    judge = Judge(change)
    for node in collect_nodes(change, judged):
        base_problem = base_verdict(node.base, node.file_id, node.node_id, judge)
        if base_problem:
            problems.append(f"{node.label}: {base_problem}")
        head_problem = head_verdict(node.head, node.file_id, node.node_id)
        if head_problem:
            problems.append(f"{node.label}: {head_problem}")
    return verdict(
        GATE, problems, f"{sum(map(len, judged.values()))} new/changed test(s) red first"
    )


@dataclass(frozen=True)
class NodeFacts:
    """Raw facts for one new or changed test; nothing here is a judgment."""

    node_id: str
    base_outcome: str | None
    head_outcome: str | None
    base_error: str | None
    head_error: str | None


def collect_facts(ctx: GateContext) -> list[NodeFacts]:
    """Per-test facts for the change's new or changed tests (the Slice C evidence seam).

    Outcomes are pytest's (`passed`, `failed`, `skipped`), `error` when the test's file
    or setup errors, or None when the test was not reported. Unparseable test files
    contribute no facts.
    """
    change = Change.of(ctx)
    judged, _problems = judged_tests(change, test_files_of(change))
    return [
        NodeFacts(
            node_id=node.label,
            base_outcome=raw_outcome(node.base, node.file_id, node.node_id),
            head_outcome=raw_outcome(node.head, node.file_id, node.node_id),
            base_error=raw_error(node.base, node.file_id),
            head_error=raw_error(node.head, node.file_id),
        )
        for node in collect_nodes(change, judged)
    ]


def test_files_of(change: Change) -> list[FileChange]:
    return [c for c in change.files if c.status != "D" and is_test_file(c.path)]


@dataclass(frozen=True)
class Node:
    label: str
    file_id: str
    node_id: str
    base: Run
    head: Run


def collect_nodes(change: Change, judged: dict[str, list[str]]) -> list[Node]:
    if not judged:
        return []
    head_paths = set(list_paths(change.repo, change.head))
    by_root: dict[str, dict[str, list[str]]] = {}
    for path, names in judged.items():
        by_root.setdefault(project_root(path, head_paths), {})[path] = names
    support = [c for c in change.files if is_test_support(c.path)]
    nodes: list[Node] = []
    with tempfile.TemporaryDirectory(prefix="factory-red-first-") as tmp:
        work = Path(tmp)
        for index, (root, files) in enumerate(sorted(by_root.items())):
            nodes += root_nodes(change, root, files, support, work / str(index))
    return nodes


def root_nodes(
    change: Change,
    root: str,
    files: dict[str, list[str]],
    support: list[FileChange],
    work: Path,
) -> list[Node]:
    base_dir = materialize(change.repo, change.merge_base, root, work / "base")
    head_dir = materialize(change.repo, change.head, root, work / "head")
    prefix = f"{root}/" if root else ""
    for item in support:
        if not item.path.startswith(prefix):
            continue
        target = base_dir / item.path[len(prefix) :]
        if item.status == "D":
            target.unlink(missing_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(change.head_text(item.path) or "", encoding="utf-8")
    nodes: list[Node] = []
    for index, (path, names) in enumerate(sorted(files.items())):
        file_id = path[len(prefix) :]
        node_ids = [f"{file_id}::{name}" for name in names]
        base_run = run_pytest(base_dir, node_ids, work / f"base-{index}.json")
        head_run = run_pytest(head_dir, node_ids, work / f"head-{index}.json")
        nodes += [
            Node(f"{prefix}{node_id}", file_id, node_id, base_run, head_run) for node_id in node_ids
        ]
    return nodes


def raw_error(run: Run, file_id: str) -> str | None:
    return run.crashed or run.collect_error(file_id)


def raw_outcome(run: Run, file_id: str, node_id: str) -> str | None:
    if run.crashed or run.collect_error(file_id) is not None:
        return "error"
    outcome = run.outcome(node_id)
    if outcome.setup_failed:
        return "error"
    for state in ("failed", "skipped", "passed"):
        if state in outcome.calls:
            return state
    return None


def base_verdict(run: Run, file_id: str, node_id: str, judge: Judge) -> str | None:
    if run.crashed:
        return f"base broken (the test run did not complete: {run.crashed})"
    error = run.collect_error(file_id)
    if error is not None:
        if judge.error_is_red(error):
            return None
        last = error.strip().splitlines()[-1] if error.strip() else "collection error"
        return f"base broken, not red: {last}"
    outcome = run.outcome(node_id)
    if outcome.setup_failed:
        return "base broken, not red: errors before the test body runs"
    if not outcome.calls:
        return "base broken, not red: not collected on base"
    if "passed" in outcome.calls:
        return "passes on base code; a new or changed test must fail first (red first)"
    if "skipped" in outcome.calls:
        return "is skipped on base; a skip is not a test failure (red first)"
    return None


def head_verdict(run: Run, file_id: str, node_id: str) -> str | None:
    if run.crashed:
        return f"the head test run did not complete: {run.crashed}"
    if run.collect_error(file_id) is not None:
        return "does not collect on head"
    outcome = run.outcome(node_id)
    if outcome.setup_failed or not outcome.calls or any(c != "passed" for c in outcome.calls):
        return "does not pass on head"
    return None
