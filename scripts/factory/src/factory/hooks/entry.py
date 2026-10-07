"""`factory-hook <name>`: Cursor hook JSON on stdin, one JSON object on stdout.

Console script `factory-hook = "factory.hooks.entry:main"` (amendment A1); `factory hook
<name>` calls `run_hook` too, so both paths give the same answer. A hook that crashes
fails open with its quiet response: CI is authoritative.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from importlib import import_module
from pathlib import Path

HOOK_MODULES = {
    "spawn-guard": "factory.hooks.spawn_guard",
    "shell-guard": "factory.hooks.shell_guard",
    "owned-path-warn": "factory.hooks.owned_path",
    "decision-in-chat": "factory.hooks.decision_chat",
}
QUIET: dict[str, dict[str, str]] = {
    "spawn-guard": {"permission": "allow"},
    "shell-guard": {"permission": "allow"},
    "owned-path-warn": {},
    "decision-in-chat": {},
}
USAGE_EXIT = 3


def workspace_root(payload: dict[str, object], fallback: Path) -> Path:
    roots = payload.get("workspace_roots")
    if isinstance(roots, list) and roots and isinstance(roots[0], str) and roots[0]:
        return Path(roots[0])
    return fallback


def run_hook(name: str, stdin_text: str, *, fallback_root: Path) -> tuple[int, dict[str, str]]:
    """`(exit code, response)` for hook `name` given the raw stdin payload."""
    module = HOOK_MODULES.get(name)
    if module is None:
        sys.stderr.write(f"factory-hook: unknown hook {name!r} (known: {sorted(HOOK_MODULES)})\n")
        return USAGE_EXIT, {}
    try:
        payload = json.loads(stdin_text) if stdin_text.strip() else {}
    except ValueError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    root = workspace_root(payload, fallback_root)
    try:
        code, response = import_module(module).handle(payload, root)
    except Exception as exc:
        sys.stderr.write(f"factory-hook {name}: failed open ({type(exc).__name__}: {exc})\n")
        return 0, dict(QUIET[name])
    return code, response


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        sys.stderr.write(f"usage: factory-hook <{'|'.join(HOOK_MODULES)}>\n")
        sys.stdout.write("{}\n")
        return USAGE_EXIT
    code, response = run_hook(args[0], sys.stdin.read(), fallback_root=Path.cwd())
    sys.stdout.write(json.dumps(response) + "\n")
    return code
