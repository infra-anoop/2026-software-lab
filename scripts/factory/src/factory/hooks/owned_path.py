"""`owned-path-warn` (postToolUse on Write/Delete; CI twin `diff-within-owned-paths`).

Warn-only: on a `wo/<order-id>` branch, a written or deleted file outside the effective
order's `owned_paths` (order plus amendments in `amend-NN` order) and outside the
order's own bus directory gets an `additional_context` note. The file is judged in the
repository that contains it (nearest `.git`, so nested worktrees judge their own branch).
"""

from __future__ import annotations

import os.path
import re
from pathlib import Path

from factory.hooks._paths import matches
from factory.hooks._repo import branch_in, bus_dir, config, git_root, order_of_branch

MUTATING_TOOLS = frozenset({"Write", "Delete"})
AMENDMENT = re.compile(r"^amendment-(\d+)\.ya?ml$")


def _load(path: Path) -> dict[str, object]:
    import yaml  # only paid on a work branch

    try:
        data = yaml.load(
            path.read_text(encoding="utf-8"), Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader)
        )
    except (OSError, yaml.YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def effective_owned_paths(order_dir: Path) -> list[str] | None:
    """Owned paths of the order in `order_dir` with amendments applied; None if no order."""
    order = _load(order_dir / "order.yaml")
    owned = order.get("owned_paths")
    if not isinstance(owned, list):
        return None
    amendments = sorted(
        (int(match[1]), entry)
        for entry in (order_dir.iterdir() if order_dir.is_dir() else [])
        if (match := AMENDMENT.match(entry.name))
    )
    for _, entry in amendments:
        amendment = _load(entry)
        supersedes = amendment.get("supersedes")
        values = amendment.get("values")
        if (
            isinstance(supersedes, list)
            and "owned_paths" in supersedes
            and isinstance(values, dict)
        ):
            replacement = values.get("owned_paths")
            if isinstance(replacement, list):
                owned = replacement
    return [str(pattern) for pattern in owned]


def warning(file_path: Path) -> str:
    repo = git_root(file_path.parent)
    if repo is None:
        return ""
    order_id = order_of_branch(branch_in(repo))
    if order_id is None:
        return ""
    relative = Path(os.path.relpath(file_path, repo)).as_posix()
    if relative.startswith("../"):
        return ""
    bus = bus_dir(config(repo))
    if relative.startswith(f"{bus}/orders/{order_id}/"):
        return ""
    owned = effective_owned_paths(repo / bus / "orders" / order_id)
    if owned is None:
        return (
            f"owned-path-warn: {relative} was changed on wo/{order_id}, but the order file "
            f"{bus}/orders/{order_id}/order.yaml is missing, so ownership is unknown."
        )
    if matches(relative, owned):
        return ""
    return (
        f"owned-path-warn: {relative} is outside the owned paths of order {order_id} "
        f"({', '.join(owned)}). Revert it, or record an amendment if the order must grow; "
        "the CI gate diff-within-owned-paths will fail otherwise."
    )


def handle(payload: dict[str, object], root: Path) -> tuple[int, dict[str, str]]:
    if payload.get("tool_name") not in MUTATING_TOOLS:
        return 0, {}
    tool_input = payload.get("tool_input")
    raw = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    if not isinstance(raw, str) or not raw:
        return 0, {}
    cwd = payload.get("cwd")
    base = Path(cwd) if isinstance(cwd, str) and cwd else root
    file_path = Path(os.path.normpath(os.path.join(base, os.path.expanduser(raw))))
    text = warning(file_path)
    return 0, {"additional_context": text} if text else {}
