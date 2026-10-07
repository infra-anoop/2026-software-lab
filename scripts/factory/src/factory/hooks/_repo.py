"""Fast, offline repository reads for hooks: git root, checked-out branch, config.

The branch comes from the `HEAD` file (worktree-aware), not from a git subprocess.
"""

from __future__ import annotations

import os.path
import re
import tomllib
from pathlib import Path

ORDER_BRANCH = re.compile(r"^wo/(?P<order_id>wo-\d{8}-[a-z0-9]+(?:-[a-z0-9]+)*)$")
MAIN_REFS = ("refs/heads/main", "refs/remotes/origin/main")
DEFAULT_CAP = 3


def git_root(start: Path) -> Path | None:
    """Nearest directory from `start` upward that holds a `.git` entry."""
    here = Path(os.path.normpath(os.path.abspath(start)))
    for directory in (here, *here.parents):
        if (directory / ".git").exists():
            return directory
    return None


def git_dir(root: Path) -> Path | None:
    dot_git = root / ".git"
    if dot_git.is_dir():
        return dot_git
    try:
        text = dot_git.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("gitdir:"):
        return None
    target = Path(text.removeprefix("gitdir:").strip())
    return target if target.is_absolute() else root / target


def branch_in(directory: Path, *, explicit_git_dir: Path | None = None) -> str | None:
    """Branch checked out in the repository containing `directory` (None when detached
    or not a repository)."""
    if explicit_git_dir is not None:
        head_dir: Path | None = explicit_git_dir
    else:
        root = git_root(directory)
        head_dir = git_dir(root) if root else None
    if head_dir is None:
        return None
    try:
        head = (head_dir / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return head.removeprefix("ref: refs/heads/") if head.startswith("ref: refs/heads/") else None


def order_of_branch(branch: str | None) -> str | None:
    match = ORDER_BRANCH.match(branch or "")
    return match["order_id"] if match else None


def git(root: Path, *args: str, stdin: str | None = None) -> str:
    """Output of a local git command ('' on failure); never fetches."""
    import subprocess  # only hooks that read refs pay for it

    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
        input=stdin,
    )
    return result.stdout if result.returncode == 0 else ""


def present(root: Path, specs: list[str]) -> list[bool]:
    """Whether each `<rev>:<path>` spec names an object, in one `cat-file` call."""
    if not specs:
        return []
    out = git(root, "cat-file", "--batch-check", stdin="".join(f"{s}\n" for s in specs))
    lines = out.splitlines()
    if len(lines) != len(specs):
        return [False] * len(specs)
    return [not line.endswith(" missing") for line in lines]


def config(root: Path) -> dict[str, object]:
    try:
        with (root / "factory.toml").open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def bus_dir(settings: dict[str, object]) -> str:
    value = settings.get("bus_dir")
    return value if isinstance(value, str) and value else "bus"


def concurrency_cap(settings: dict[str, object]) -> int:
    value = settings.get("concurrency_cap")
    return value if isinstance(value, int) and value > 0 else DEFAULT_CAP
