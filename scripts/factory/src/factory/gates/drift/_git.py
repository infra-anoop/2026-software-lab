"""Read-only git access for drift gates: changed paths, added lines, and head blobs."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from factory.api import GateContext

HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
REGULAR_FILE_MODES = frozenset({"100644", "100755"})
SYMLINK_MODE = "120000"


class GitError(Exception):
    """A git command failed (bad sha, unreadable object)."""


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "-c", "core.quotePath=false", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


@dataclass(frozen=True)
class FileChange:
    """One path in the change, renames off: status is `A`, `M`, `D` or `T`."""

    status: str
    path: str


@dataclass
class Change:
    """The PR's change: `base...head` (merge base to head), `git diff --no-renames`."""

    repo: Path
    base: str
    head: str
    _blobs: dict[str, str | None] = field(default_factory=dict)

    @classmethod
    def of(cls, ctx: GateContext) -> Change:
        return cls(ctx.repo_path, ctx.base_sha, ctx.head_sha)

    @cached_property
    def merge_base(self) -> str:
        try:
            return git(self.repo, "merge-base", self.base, self.head).strip()
        except GitError:
            return self.base

    @cached_property
    def files(self) -> list[FileChange]:
        out = git(
            self.repo, "diff", "--no-renames", "--name-status", "-z", self.merge_base, self.head
        )
        parts = [part for part in out.split("\0") if part]
        return [FileChange(parts[i][0], parts[i + 1]) for i in range(0, len(parts) - 1, 2)]

    @cached_property
    def added_lines(self) -> dict[str, list[tuple[int, str]]]:
        """Added lines per head path, as `(head line number, text)`."""
        out = git(
            self.repo,
            "diff",
            "--no-renames",
            "--no-color",
            "--no-ext-diff",
            "-U0",
            self.merge_base,
            self.head,
        )
        added: dict[str, list[tuple[int, str]]] = {}
        path: str | None = None
        in_header = False
        number = 0
        for line in out.split("\n"):
            if line.startswith("diff --git "):
                in_header, path = True, None
                continue
            if in_header:
                if line.startswith("+++ "):
                    target = line[4:]
                    path = target[2:] if target.startswith("b/") else None
                hunk = HUNK_RE.match(line)
                if hunk:
                    in_header, number = False, int(hunk.group(1))
                continue
            hunk = HUNK_RE.match(line)
            if hunk:
                number = int(hunk.group(1))
            elif path is not None and line.startswith("+"):
                added.setdefault(path, []).append((number, line[1:]))
                number += 1
        return added

    def changed_paths(self) -> list[str]:
        return [change.path for change in self.files]

    def head_text(self, path: str) -> str | None:
        return self.text_at(self.head, path)

    def base_text(self, path: str) -> str | None:
        return self.text_at(self.merge_base, path)

    def text_at(self, ref: str, path: str) -> str | None:
        """The regular-file blob at `ref:path` as text, or None when absent."""
        key = f"{ref}:{path}"
        if key not in self._blobs:
            entry = tree_entry(self.repo, ref, path)
            if entry is None or entry[0] not in REGULAR_FILE_MODES:
                self._blobs[key] = None
            else:
                self._blobs[key] = blob_text(self.repo, entry[1])
        return self._blobs[key]

    def head_paths(self, prefix: str = "") -> list[str]:
        return list_paths(self.repo, self.head, prefix)


def tree_entry(repo: Path, ref: str, path: str) -> tuple[str, str] | None:
    """`(mode, object sha)` of `path` in `ref`'s tree, or None when absent."""
    out = git(repo, "ls-tree", "-z", ref, "--", path)
    for record in out.split("\0"):
        if not record:
            continue
        meta, name = record.split("\t", 1)
        mode, _kind, sha = meta.split(" ")
        if name == path:
            return mode, sha
    return None


def blob_text(repo: Path, sha: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "blob", sha], check=False, capture_output=True
    )
    if result.returncode != 0:
        raise GitError(f"git cat-file blob {sha}: {result.stderr.decode(errors='replace')}")
    return result.stdout.decode("utf-8", errors="replace")


def list_paths(repo: Path, ref: str, prefix: str = "") -> list[str]:
    args = ["ls-tree", "-r", "--name-only", "-z", ref]
    if prefix:
        args += ["--", prefix]
    return [path for path in git(repo, *args).split("\0") if path]
