"""Gate `catalog-test-linkage` (T048; FR-018; I-B7; contracts/gates.md § Catalog-linkage).

Rows of any `acceptance.md` that the change adds or edits, plus the rows named in the
effective order's `checks`, are judged at head: a `how: auto` row needs `evidence`, and
an order-check row needs existing evidence (not `planned`). Evidence is a pytest node
id `<path>::<test>` or an eval case `eval:<path>#<case-id>` (governor 2026-10-04).

Eval files are read as the git blob at head. A tracked symlink, an unsupported type,
malformed YAML/JSON/JSONL, a wrong shape, or any entry that is not a mapping with `id`
fails closed (T-B2-2).
"""

from __future__ import annotations

import ast
import json
import posixpath
from typing import Any

import yaml

from factory.api import GateContext, GateResult
from factory.gates.drift._common import OrderMissing, effective_order, failed, verdict
from factory.gates.drift._git import REGULAR_FILE_MODES, SYMLINK_MODE, Change, blob_text, tree_entry
from factory.gates.drift._specs import TableRow, tables

GATE = "catalog-test-linkage"
CATALOG_NAME = "acceptance.md"
PLANNED = "planned"
EVAL_PREFIX = "eval:"
YAML_SUFFIXES = (".yaml", ".yml")


class EvidenceError(Exception):
    """Evidence does not resolve at head; the message says why."""


def normalize(evidence: str) -> str:
    return evidence.strip().strip("`").strip()


def safe_path(path: str) -> str:
    if not path or path.startswith("/") or "\\" in path:
        raise EvidenceError(f"{path!r} is not a repo-relative path")
    if any(part in {"..", "."} for part in path.split("/")) or posixpath.normpath(path) != path:
        raise EvidenceError(f"{path!r} must not contain '.' or '..' segments")
    return path


def regular_blob(change: Change, path: str) -> str:
    entry = tree_entry(change.repo, change.head, path)
    if entry is None:
        raise EvidenceError(f"{path} does not exist at head")
    mode, sha = entry
    if mode == SYMLINK_MODE:
        raise EvidenceError(f"{path} is a symlink at head; evidence must be a regular file")
    if mode not in REGULAR_FILE_MODES:
        raise EvidenceError(f"{path} is not a regular file at head (mode {mode})")
    return blob_text(change.repo, sha)


def defined_tests(source: str) -> set[str]:
    """`test` and `Class::test` names defined in a test module."""
    names: set[str] = set()
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                    names.add(f"{node.name}::{item.name}")
    return names


def check_node_id(change: Change, evidence: str) -> None:
    path, _, name = evidence.partition("::")
    name = name.split("[", 1)[0]
    if not name:
        raise EvidenceError(f"{evidence!r} is not `<path>::<test>`")
    source = regular_blob(change, safe_path(path))
    try:
        defined = defined_tests(source)
    except SyntaxError as exc:
        raise EvidenceError(f"{path} does not parse at head ({exc.msg})") from exc
    if name not in defined:
        raise EvidenceError(f"{path} defines no test {name!r} at head")


def eval_cases(path: str, text: str) -> list[dict[str, Any]]:
    """Every case of an eval file, or `EvidenceError` when any part is malformed."""
    try:
        if path.endswith(".jsonl"):
            items: Any = [json.loads(line) for line in text.splitlines() if line.strip()]
        elif path.endswith(".json"):
            items = json.loads(text)
        elif path.endswith(YAML_SUFFIXES):
            items = yaml.safe_load(text)
        else:
            raise EvidenceError(f"{path}: eval files are YAML, JSON or JSONL")
    except (ValueError, yaml.YAMLError) as exc:
        raise EvidenceError(f"{path} is malformed ({type(exc).__name__})") from exc
    if not path.endswith(".jsonl") and isinstance(items, dict):
        if "cases" not in items:
            raise EvidenceError(f"{path}: a mapping must hold a `cases:` list")
        items = items["cases"]
    if not isinstance(items, list):
        raise EvidenceError(f"{path}: cases must be a list")
    for index, item in enumerate(items):
        if not isinstance(item, dict) or "id" not in item:
            raise EvidenceError(f"{path}: case {index} is not a mapping with `id`")
    return items


def check_eval(change: Change, evidence: str) -> None:
    reference = evidence[len(EVAL_PREFIX) :]
    path, hash_sign, case_id = reference.partition("#")
    if not hash_sign or not case_id:
        raise EvidenceError(f"{evidence!r} is not `eval:<path>#<case-id>`")
    path = safe_path(path)
    cases = eval_cases(path, regular_blob(change, path))
    if not any(isinstance(c["id"], str) and c["id"] == case_id for c in cases):
        raise EvidenceError(f"{path} has no case with id {case_id!r} at head")


def check_evidence(change: Change, evidence: str) -> None:
    if evidence.startswith(EVAL_PREFIX):
        check_eval(change, evidence)
    elif "::" in evidence:
        check_node_id(change, evidence)
    else:
        raise EvidenceError(f"{evidence!r} is neither a pytest node id nor an eval reference")


def catalog_rows(text: str) -> list[TableRow]:
    return [
        row
        for table in tables(text)
        for row in table
        if "id" in row.cells and "how" in row.cells and row.cells["id"].strip()
    ]


def run(ctx: GateContext) -> GateResult:
    try:
        order = effective_order(ctx)
    except OrderMissing as exc:
        return failed(GATE, [str(exc)])
    checks = set(order.checks) if order else set()
    change = Change.of(ctx)
    catalogs = [p for p in change.head_paths() if posixpath.basename(p) == CATALOG_NAME]
    problems: list[str] = []
    found: set[str] = set()
    for path in catalogs:
        text = change.head_text(path) or ""
        added = {line for _n, line in change.added_lines.get(path, [])}
        for row in catalog_rows(text):
            row_id = row.cells["id"].strip().strip("`")
            in_checks = row_id in checks
            if in_checks:
                found.add(row_id)
            if row.line not in added and not in_checks:
                continue
            how = row.cells["how"].strip().lower()
            if "evidence" not in row.cells:
                if how == "auto":
                    problems.append(f"{path}: auto row {row_id} has no evidence column")
                continue
            evidence = normalize(row.cells["evidence"])
            if how == "auto" and not evidence:
                problems.append(f"{path}: auto row {row_id} has no evidence")
                continue
            if not in_checks:
                continue
            if not evidence or evidence == PLANNED:
                problems.append(
                    f"{path}: row {row_id} is in the order's checks but its evidence is"
                    f" {evidence or 'empty'!r}; name the test or eval case"
                )
                continue
            try:
                check_evidence(change, evidence)
            except EvidenceError as exc:
                problems.append(f"{path}: row {row_id} evidence does not resolve: {exc}")
    for missing in sorted(checks - found):
        problems.append(f"order check {missing} has no row in any {CATALOG_NAME} at head")
    return verdict(GATE, problems, "judged catalog rows are linked")
