"""Gate `deferral-words-need-od` (T045; FR-015; I-B6).

Rule verbatim from contracts/gates.md § Deferral-words rule: in `specs/**` and
`notes/sprints/**`, the words *later, optional, deferred, TBD, future, stretch* need,
on the same line or table row, one of: an Open Decision id that exists (`D\\d+`), a
pointer `→ <artifact>` to an existing file or phase (`→ plan`, `→ sprint 03` with a
waived OD), or `[governor-judged]`. Words inside backtick code spans are exempt.
Only added lines are judged. A pointer's file must be a regular file blob at head
(`100644`/`100755`); a directory, symlink or gitlink does not count (amendment-05).

A sprint pointer is served by the OD ids on its line, which must include a waived
decision; those ids do not also satisfy the OD-id clause (T-B3).
"""

from __future__ import annotations

import posixpath
import re
from functools import cached_property

from factory.api import GateContext, GateResult
from factory.gates.drift._common import verdict
from factory.gates.drift._git import REGULAR_FILE_MODES, Change, tree_entry
from factory.gates.drift._specs import OpenDecision, open_decisions

GATE = "deferral-words-need-od"
WORDS = ("later", "optional", "deferred", "TBD", "future", "stretch")
WORD_RE = re.compile(r"(?<!\w)(" + "|".join(WORDS) + r")(?!\w)", re.IGNORECASE)
CODE_SPAN_RE = re.compile(r"`[^`]*`")
OD_REF_RE = re.compile(r"(?<!\w)(D\d+)(?!\w)")
POINTER_RE = re.compile(r"→\s*(\[[^\]]*\]\(([^)\s]+)\)|\S+)")
SPRINT_POINTER_RE = re.compile(r"→\s*sprint\s+\d+(?!\w)", re.IGNORECASE)
PHASES = frozenset({"plan"})
GOVERNOR_TAG = "[governor-judged]"
SPRINT_NOTES = "notes/sprints/"


class Scope:
    def __init__(self, ctx: GateContext, change: Change) -> None:
        self.ctx = ctx
        self.change = change
        self.spec_roots = [root.rstrip("/") + "/" for root in ctx.config.spec_roots]

    def judged(self, path: str) -> bool:
        return path.startswith(SPRINT_NOTES) or any(path.startswith(r) for r in self.spec_roots)

    @cached_property
    def all_decisions(self) -> dict[str, OpenDecision]:
        merged: dict[str, OpenDecision] = {}
        for root in self.spec_roots:
            for path in self.change.head_paths(root.rstrip("/")):
                parts = path[len(root) :].split("/")
                if len(parts) == 2 and parts[1] == "spec.md":
                    for key, value in open_decisions(self.change.head_text(path) or "").items():
                        merged.setdefault(key, value)
        return merged

    def decisions_for(self, path: str) -> dict[str, OpenDecision]:
        """The file's own feature spec under a spec root; every spec elsewhere."""
        for root in self.spec_roots:
            if path.startswith(root):
                rest = path[len(root) :].split("/")
                if len(rest) > 1:
                    spec = self.change.head_text(f"{root}{rest[0]}/spec.md")
                    return open_decisions(spec or "")
        return self.all_decisions

    def regular_file_at_head(self, target: str, source: str) -> bool:
        """A regular file blob (100644/100755) at head; directories, symlinks and gitlinks
        do not count (PR-B1)."""
        for candidate in (target, posixpath.join(posixpath.dirname(source), target)):
            normal = posixpath.normpath(candidate)
            if normal.startswith("../") or normal.startswith("/"):
                continue
            entry = tree_entry(self.change.repo, self.change.head, normal)
            if entry is not None and entry[0] in REGULAR_FILE_MODES:
                return True
        return False


def pointer_ok(line: str, path: str, scope: Scope) -> bool:
    for match in POINTER_RE.finditer(line):
        target = match.group(2) or match.group(1)
        target = target.strip("`").rstrip(".,;:!?)")
        if target.lower() in PHASES:
            return True
        if target and scope.regular_file_at_head(target, path):
            return True
    return False


def satisfied(line: str, path: str, scope: Scope) -> bool:
    if GOVERNOR_TAG in line or pointer_ok(line, path, scope):
        return True
    decisions = scope.decisions_for(path)
    cited = [decisions[d] for d in OD_REF_RE.findall(line) if d in decisions]
    if SPRINT_POINTER_RE.search(line):
        return any(decision.is_waived for decision in cited)
    return bool(cited)


def run(ctx: GateContext) -> GateResult:
    change = Change.of(ctx)
    scope = Scope(ctx, change)
    problems: list[str] = []
    for path, lines in sorted(change.added_lines.items()):
        if not scope.judged(path):
            continue
        for number, line in lines:
            words = WORD_RE.findall(CODE_SPAN_RE.sub("", line))
            if words and not satisfied(line, path, scope):
                problems.append(
                    f"{path}:{number}: {', '.join(dict.fromkeys(w for w in words))} needs an"
                    " Open Decision id, a → pointer to a file or phase, or [governor-judged]"
                    f" on the same line: {line.strip()!r}"
                )
    return verdict(GATE, problems, "every added deferral word carries a reference")
