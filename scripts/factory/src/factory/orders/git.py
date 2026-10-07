"""Git plumbing for order commands and lifecycle reads (subprocess; no business logic).

Ref-only: event commits are built with `hash-object` / `mktree` / `commit-tree` on a base
commit and pushed. Nothing here merges, checks out, resets or writes HEAD, the index or a
working tree. Pushes are plain (never forced); their outcome is read from `--porcelain`
stdout, where a lost race shows up as `!` (rejected) or, for a first-writer push whose
commit origin already holds, `=` (up to date). Local branches move only after a push
landed, by compare-and-swap, and never while checked out in any worktree.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from factory.config.settings import git_environment

REMOTE = "origin"
MAIN = "main"
ORDER_BRANCH_PREFIX = "wo/"
APP_USERNAME = "x-access-token"
_PASSWORD_VARIABLE = "FACTORY_GIT_APP_TOKEN"
# The helper reads the token from its environment: command lines reach GIT_TRACE and ps.
_APP_HELPER = (
    f"!f() {{ test \"$1\" = get && printf 'username={APP_USERNAME}\\npassword=%s\\n'"
    f' "${_PASSWORD_VARIABLE}"; }}; f'
)

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


class PushUpToDate(PushRejected):
    """A first-writer push found origin already at our commit: someone else wrote it."""


def _transport(password: str | None) -> tuple[list[str], dict[str, str] | None]:
    """(config args, child env) so a network command authenticates as the App with
    `password`, ahead of (and instead of) any ambient helper; nothing for None."""
    if password is None:
        return [], None
    config = ["-c", "credential.helper=", "-c", f"credential.helper={_APP_HELPER}"]
    return config, git_environment({_PASSWORD_VARIABLE: password, "GIT_TERMINAL_PROMPT": "0"})


def _git(
    repo: Path, args: tuple[str, ...], *, stdin: bytes | None = None, password: str | None = None
) -> subprocess.CompletedProcess[bytes]:
    config, env = _transport(password)
    return subprocess.run(
        ["git", *config, "-C", str(repo), *args],
        input=stdin,
        env=env,
        check=False,
        capture_output=True,
    )


def run_git(repo: Path, *args: str, stdin: bytes | None = None) -> bytes:
    result = _git(repo, args, stdin=stdin)
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


def fetch(repo: Path, *, password: str | None = None) -> None:
    """Refresh remote-tracking refs (raises `GitError` when the remote is unreachable).

    With `password`, authenticates as the App (`x-access-token`); else ambient credentials.
    """
    args = ("fetch", "--quiet", "--prune", REMOTE)
    result = _git(repo, args, password=password)
    if result.returncode != 0:
        raise GitError(args, result.stderr.decode(errors="replace"))


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


def added_commits(
    repo: Path, ref: str, path: str, *, first_parent: bool = False
) -> list[tuple[str, datetime]]:
    """(sha, committer date) of commits on `ref` that added `path` (newest first)."""
    args = ["log", "--diff-filter=A", "--format=%H %cI"]
    if first_parent:
        args.append("--first-parent")
    out = git_text(repo, *args, ref, "--", path)
    commits = []
    for line in out.splitlines():
        if line:
            sha, stamp = line.split(" ", 1)
            commits.append((sha, datetime.fromisoformat(stamp).astimezone(UTC)))
    return commits


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


def _porcelain_flag(stdout: str, target: str) -> str | None:
    """The `--porcelain` status flag git printed for `target` (`!`, `=`, ` `, `*`, ...)."""
    for line in stdout.splitlines():
        fields = line.split("\t")
        if len(fields) >= 2 and fields[1].split(":")[-1] == target and fields[0]:
            return fields[0][0]
    return None


def push(
    repo: Path,
    sha: str,
    branch: str,
    *,
    first_writer: bool = True,
    password: str | None = None,
) -> None:
    """Fast-forward `origin/<branch>` to `sha` (create it when absent); never forces.

    With `password`, authenticates as the App (`x-access-token`); else ambient credentials.
    Raises `PushRejected` when origin refused the update and, when `first_writer`,
    `PushUpToDate` when origin already held `sha` (our push wrote nothing).
    """
    target = f"refs/heads/{branch}"
    args = ("push", "--porcelain", REMOTE, f"{sha}:{target}")
    result = _git(repo, args, password=password)
    stdout = result.stdout.decode(errors="replace")
    stderr = result.stderr.decode(errors="replace")
    flag = _porcelain_flag(stdout, target)
    if flag == "!":
        raise PushRejected(args, stdout + stderr)
    if result.returncode != 0:
        if any(marker in stderr.lower() for marker in _REJECTED_MARKERS):
            raise PushRejected(args, stderr)
        raise GitError(args, stderr)
    run_git(repo, "update-ref", remote_ref(branch), sha)
    if flag == "=" and first_writer:
        raise PushUpToDate(args, f"origin {target} was already at {sha[:7]}")


def checked_out_branches(repo: Path) -> set[str]:
    """Branches checked out in the main worktree or any linked worktree."""
    out = git_text(repo, "worktree", "list", "--porcelain")
    prefix = "branch refs/heads/"
    return {line.removeprefix(prefix) for line in out.splitlines() if line.startswith(prefix)}


def advance_local_branch(repo: Path, branch: str, sha: str) -> str | None:
    """After a landed push: compare-and-swap local `branch` forward to `sha`.

    Returns None when local `branch` is at `sha` (or was created there), else a note for
    the caller saying why it was left where it was. A branch checked out in any worktree
    is never moved, nor is one that has commits `sha` lacks.
    """
    local = f"refs/heads/{branch}"
    old = rev_parse(repo, local)
    if old == sha:
        return None
    if old is not None and not is_ancestor(repo, old, sha):
        return (
            f"local {branch} has diverged from origin/{branch} (left at {old[:7]}; origin is at"
            f" {sha[:7]}), so `git pull --ff-only` cannot pick the event up yet: rebase or merge"
            f" origin/{branch} first"
        )
    if branch in checked_out_branches(repo):
        return (
            f"{branch} is checked out, so it was left at {(old or '')[:7]}; origin/{branch} is"
            f" at {sha[:7]}. Pick the event up with `git pull --ff-only`"
        )
    try:
        run_git(repo, "update-ref", local, sha, old or "")
    except GitError:
        return f"local {branch} moved while the event was pushed, so it was left alone"
    return None
