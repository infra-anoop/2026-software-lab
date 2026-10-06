"""Bookkeeping-commit counter (catalog `history.no_bookkeeping`; consumed by the scorecard).

A bookkeeping commit is a non-merge commit whose every change is inside `bus/`, that
edits or deletes an existing file (an event append is not bookkeeping), and whose changed
lines only set status-like keys or SHA-like values. The counter reads diffs, not schema.
"""

from __future__ import annotations

import re
from pathlib import Path

from factory.bus.models import FORBIDDEN_KEYS
from factory.orders import git

DEFAULT_BUS_DIR = "bus"
_KEY_LINE = re.compile(r"^\s*-?\s*(?P<key>[A-Za-z_][\w-]*)\s*:\s*(?P<value>.*)$")
_SHA_VALUE = re.compile(r"^['\"]?[0-9a-f]{7,40}['\"]?$")


def _is_bookkeeping_line(line: str) -> bool:
    if not line.strip():
        return True
    match = _KEY_LINE.match(line)
    if match is None:
        return bool(_SHA_VALUE.match(line.strip().lstrip("- ").strip()))
    key = match["key"].lower()
    value = match["value"].strip()
    return key in FORBIDDEN_KEYS or "sha" in key or bool(_SHA_VALUE.match(value))


def is_bookkeeping_commit(repo: Path, sha: str, bus_dir: str = DEFAULT_BUS_DIR) -> bool:
    status = git.git_text(repo, "diff-tree", "--no-commit-id", "-r", "--name-status", sha)
    changes = [line.split("\t", 1) for line in status.splitlines() if line]
    if not changes:
        return False
    if any(not path.startswith(f"{bus_dir}/") for _, path in changes):
        return False
    if all(kind == "A" for kind, _ in changes):
        return False
    patch = git.git_text(repo, "diff-tree", "--no-commit-id", "-r", "-p", "-U0", sha)
    changed = [
        line[1:]
        for line in patch.splitlines()
        if line[:1] in {"+", "-"} and not line.startswith(("+++", "---"))
    ]
    return all(_is_bookkeeping_line(line) for line in changed)


def count_bookkeeping_commits(repo: Path, *, since: str, bus_dir: str = DEFAULT_BUS_DIR) -> int:
    """Bookkeeping commits reachable from any branch (local or remote) but not from `since`."""
    out = git.git_text(repo, "rev-list", "--no-merges", "--branches", "--remotes", "--not", since)
    return sum(1 for sha in out.splitlines() if sha and is_bookkeeping_commit(repo, sha, bus_dir))
