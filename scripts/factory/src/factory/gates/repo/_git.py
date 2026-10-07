"""Read-only git access and result helpers shared by slice C gates and the runner.

Gates judge commits, never the working tree: every read names a sha. Diffs run with
`--no-renames`, so a rename is a delete plus an add.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from factory.api import GateResult


class GitError(RuntimeError):
    """A git command failed (unknown sha, not a repository, ...)."""


def git(repo: Path, *args: str, stdin: str | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        input=stdin,
    )
    if result.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def show(repo: Path, sha: str, path: str) -> str | None:
    """Text of `path` at `sha`, or None when the path does not exist there."""
    return read_blobs(repo, sha, [path])[path]


def read_blobs(repo: Path, sha: str, paths: list[str]) -> dict[str, str | None]:
    """Texts of `paths` at `sha` in one `git cat-file --batch` call (None when missing)."""
    return dict(zip(paths, read_specs(repo, [f"{sha}:{path}" for path in paths]), strict=True))


def read_specs(repo: Path, specs: list[str]) -> list[str | None]:
    """Texts of `<rev>:<path>` specs in one `git cat-file --batch` call (None when missing)."""
    if not specs:
        return []
    request = "".join(f"{spec}\n" for spec in specs)
    result = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "--batch"],
        check=False,
        capture_output=True,
        input=request.encode(),
    )
    if result.returncode != 0:
        raise GitError(f"git cat-file --batch: {result.stderr.decode(errors='replace').strip()}")
    out = result.stdout
    texts: list[str | None] = []
    offset = 0
    for _ in specs:
        end = out.index(b"\n", offset)
        header = out[offset:end].decode(errors="replace").split()
        offset = end + 1
        text = None
        if len(header) == 3 and header[2].isdigit():
            size = int(header[2])
            if header[1] == "blob":
                text = out[offset : offset + size].decode("utf-8", errors="replace")
            offset += size + 1
        texts.append(text)
    return texts


def exists(repo: Path, sha: str, path: str) -> bool:
    return object_type(repo, f"{sha}:{path}") is not None


def object_type(repo: Path, spec: str) -> str | None:
    """`blob`, `tree`, `commit`, ... for an object spec, or None when it does not resolve."""
    result = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-t", spec],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def changed(repo: Path, base: str, head: str, *paths: str) -> list[tuple[str, str]]:
    """`(status, path)` for every path changed on head since its merge base with `base`."""
    out = git(repo, "diff", "--no-renames", "--name-status", "-z", f"{base}...{head}", "--", *paths)
    fields = [field for field in out.split("\0") if field]
    return [(fields[i][0], fields[i + 1]) for i in range(0, len(fields) - 1, 2)]


def ls_tree(repo: Path, sha: str, *paths: str) -> list[str]:
    out = git(repo, "ls-tree", "-r", "--name-only", "-z", sha, "--", *paths)
    return [path for path in out.split("\0") if path]


def rev_parse(repo: Path, ref: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def passed(gate_id: str, note: str | None = None) -> GateResult:
    return GateResult(gate_id=gate_id, passed=True, messages=[f"{gate_id}: {note}"] if note else [])


def failed(gate_id: str, problems: list[str]) -> GateResult:
    return GateResult(
        gate_id=gate_id, passed=False, messages=[f"{gate_id}: {problem}" for problem in problems]
    )


def outcome(gate_id: str, problems: list[str], ok_note: str) -> GateResult:
    return failed(gate_id, problems) if problems else passed(gate_id, ok_note)
