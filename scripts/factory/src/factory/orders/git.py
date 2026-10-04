"""Git plumbing for order commands and lifecycle reads (subprocess; no business logic).

Event commits are built with `hash-object` / `mktree` / `commit-tree` on a base commit,
so writing an event never touches the caller's index or working tree. Pushes are plain
(never forced): a non-fast-forward rejection is how a lost claim race shows up.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

REMOTE = "origin"
MAIN = "main"
ORDER_BRANCH_PREFIX = "wo/"

_REJECTED_MARKERS = (
    "[rejected]",
    "non-fast-forward",
    "fetch first",
    "cannot lock ref",
    "failed to update ref",
    "already exists",
    "stale info",
)


class GitError(Exception):
    """A git command failed (unreachable remote, unknown ref, ...)."""

    def __init__(self, args: tuple[str, ...], stderr: str) -> None:
        super().__init__(f"git {' '.join(args)}: {stderr.strip() or 'failed'}")
        self.stderr = stderr


class PushRejected(GitError):
    """The remote refused a push (someone else moved the branch first)."""


def run_git(repo: Path, *args: str, stdin: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], input=stdin, check=False, capture_output=True
    )
    if result.returncode != 0:
        raise GitError(args, result.stderr.decode(errors="replace"))
    return result.stdout


def git_text(repo: Path, *args: str) -> str:
    return run_git(repo, *args).decode("utf-8", errors="replace").strip()


def rev_parse(repo: Path, ref: str) -> str | None:
    try:
        return git_text(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    except GitError:
        return None


def object_exists(repo: Path, spec: str) -> bool:
    try:
        run_git(repo, "cat-file", "-e", spec)
    except GitError:
        return False
    return True


def fetch(repo: Path) -> None:
    """Refresh remote-tracking refs (raises `GitError` when the remote is unreachable)."""
    run_git(repo, "fetch", "--quiet", "--prune", REMOTE)


def remote_ref(branch: str) -> str:
    return f"refs/remotes/{REMOTE}/{branch}"


def main_ref(repo: Path) -> str | None:
    """`origin/main` when known, else local `main`."""
    for ref in (remote_ref(MAIN), f"refs/heads/{MAIN}"):
        if rev_parse(repo, ref):
            return ref
    return None


def order_branch(order_id: str) -> str:
    return f"{ORDER_BRANCH_PREFIX}{order_id}"


def remote_order_refs(repo: Path) -> dict[str, str]:
    """Order id -> remote-tracking ref for every `origin/wo/*` branch."""
    prefix = remote_ref(ORDER_BRANCH_PREFIX)
    out = git_text(repo, "for-each-ref", "--format=%(refname)", prefix)
    return {line.removeprefix(prefix): line for line in out.splitlines() if line}


def current_branch(repo: Path) -> str | None:
    try:
        return git_text(repo, "symbolic-ref", "--quiet", "--short", "HEAD")
    except GitError:
        return None


def commit_time(repo: Path, ref: str) -> datetime:
    stamp = git_text(repo, "log", "-1", "--format=%cI", ref)
    return datetime.fromisoformat(stamp).astimezone(UTC)


def is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", ancestor, descendant],
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def merge_base(repo: Path, a: str, b: str) -> str:
    return git_text(repo, "merge-base", a, b)


def changed_paths(repo: Path, base: str, head: str) -> list[str]:
    out = git_text(repo, "diff", "--name-only", "--no-renames", f"{base}...{head}")
    return [line for line in out.splitlines() if line]


def added_dates(repo: Path, ref: str, path: str, *, first_parent: bool = False) -> list[datetime]:
    """Committer dates of commits on `ref` that added `path` (newest first)."""
    args = ["log", "--diff-filter=A", "--format=%cI"]
    if first_parent:
        args.append("--first-parent")
    out = git_text(repo, *args, ref, "--", path)
    return [datetime.fromisoformat(line).astimezone(UTC) for line in out.splitlines() if line]


def _ls_tree(repo: Path, tree: str) -> list[tuple[str, str, str, str]]:
    raw = run_git(repo, "ls-tree", "-z", tree).decode()
    entries = []
    for record in raw.split("\0"):
        if not record:
            continue
        meta, name = record.split("\t", 1)
        mode, kind, sha = meta.split(" ")
        entries.append((mode, kind, sha, name))
    return entries


def _tree_with(repo: Path, tree: str | None, parts: tuple[str, ...], blob: str) -> str:
    entries = {e[3]: e for e in _ls_tree(repo, tree)} if tree else {}
    name = parts[0]
    if len(parts) == 1:
        entries[name] = ("100644", "blob", blob, name)
    else:
        existing = entries.get(name)
        subtree = existing[2] if existing and existing[1] == "tree" else None
        entries[name] = ("040000", "tree", _tree_with(repo, subtree, parts[1:], blob), name)
    payload = "".join(f"{mode} {kind} {sha}\t{n}\0" for mode, kind, sha, n in entries.values())
    return run_git(repo, "mktree", "-z", stdin=payload.encode()).decode().strip()


def commit_files(repo: Path, base: str, files: dict[str, bytes], message: str) -> str:
    """A new commit on top of `base` that adds or replaces `files`; refs are untouched."""
    tree = git_text(repo, "rev-parse", f"{base}^{{tree}}")
    for path, content in sorted(files.items()):
        blob = run_git(repo, "hash-object", "-w", "--stdin", stdin=content).decode().strip()
        tree = _tree_with(repo, tree, PurePosixPath(path).parts, blob)
    return git_text(repo, "commit-tree", tree, "-p", base, "-m", message)


def push(repo: Path, sha: str, branch: str) -> None:
    """Fast-forward `origin/<branch>` to `sha` (create it when absent); never forces."""
    try:
        run_git(repo, "push", "--quiet", "--porcelain", REMOTE, f"{sha}:refs/heads/{branch}")
    except GitError as exc:
        text = exc.stderr.lower()
        if any(marker in text for marker in _REJECTED_MARKERS):
            raise PushRejected(("push", REMOTE, branch), exc.stderr) from exc
        raise
    run_git(repo, "update-ref", remote_ref(branch), sha)


def advance_local_branch(repo: Path, branch: str, sha: str) -> bool:
    """Move local `branch` to `sha` when that is a fast-forward; False if left alone."""
    local = f"refs/heads/{branch}"
    old = rev_parse(repo, local)
    if old == sha:
        return True
    if old and not is_ancestor(repo, old, sha):
        return False
    if current_branch(repo) == branch:
        run_git(repo, "merge", "--ff-only", "--quiet", sha)
    else:
        run_git(repo, "update-ref", local, sha, *([old] if old else []))
    return True
