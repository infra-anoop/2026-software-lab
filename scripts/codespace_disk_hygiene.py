#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Codespace / local disk hygiene for Nix + Docker lab workspaces.

Default is ``--dry-run``: print planned reclaim actions and whether tools exist.
Destructive commands run only with ``--apply``. ``--apply`` is refused when
``CI`` or ``GITHUB_ACTIONS`` is truthy (tests and Actions must not prune hosts).
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class HygieneAction:
    """One reclaim step (Nix GC or Docker prune)."""

    id: str
    argv: tuple[str, ...]
    summary: str
    tool: str  # first PATH binary required


ACTIONS: tuple[HygieneAction, ...] = (
    HygieneAction(
        id="nix-gc",
        argv=("nix-collect-garbage", "-d"),
        summary="Delete unreachable Nix store paths (nix-collect-garbage -d)",
        tool="nix-collect-garbage",
    ),
    HygieneAction(
        id="docker-prune",
        argv=("docker", "system", "prune", "-f"),
        summary="Remove unused Docker containers/networks/images (docker system prune -f)",
        tool="docker",
    ),
)


def _env_truthy_from(env: Mapping[str, str], name: str) -> bool:
    return env.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def is_ci_environment(environ: Mapping[str, str] | None = None) -> bool:
    env = environ if environ is not None else os.environ
    return _env_truthy_from(env, "CI") or _env_truthy_from(env, "GITHUB_ACTIONS")


def resolve_tool(tool: str, path_env: str | None = None) -> str | None:
    """Return absolute path to ``tool`` using PATH (or ``path_env`` override)."""
    if path_env is not None:
        for part in path_env.split(os.pathsep):
            if not part:
                continue
            candidate = Path(part) / tool
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
        return None
    return shutil.which(tool)


def plan_actions(
    *,
    path_env: str | None = None,
    actions: tuple[HygieneAction, ...] = ACTIONS,
) -> list[tuple[HygieneAction, str | None]]:
    """Return (action, resolved_binary_or_None) for each planned step."""
    return [(action, resolve_tool(action.tool, path_env=path_env)) for action in actions]


def disk_report(path: str = "/") -> str:
    usage = shutil.disk_usage(path)
    free_g = usage.free / (1024**3)
    total_g = usage.total / (1024**3)
    used_pct = 100.0 * (1.0 - (usage.free / usage.total)) if usage.total else 0.0
    return f"disk {path}: {free_g:.1f}G free of {total_g:.1f}G ({used_pct:.0f}% used)"


def run_apply(
    planned: list[tuple[HygieneAction, str | None]],
    *,
    runner: Callable[..., Any] | None = None,
) -> int:
    """Execute available actions. Returns process exit code (0 = all ok / skipped)."""
    run = runner or subprocess.run
    exit_code = 0
    for action, binary in planned:
        if binary is None:
            print(f"skip {action.id}: `{action.tool}` not on PATH")
            continue
        cmd = [binary, *action.argv[1:]]
        print(f"apply {action.id}: {' '.join(cmd)}")
        completed = run(cmd, check=False)
        code = int(getattr(completed, "returncode", completed))
        if code != 0:
            print(f"error: {action.id} exited {code}", file=sys.stderr)
            exit_code = code
    return exit_code


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.set_defaults(mode="dry-run")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        dest="mode",
        action="store_const",
        const="dry-run",
        help="List planned actions only (default)",
    )
    mode.add_argument(
        "--apply",
        dest="mode",
        action="store_const",
        const="apply",
        help="Run reclaim commands (refused in CI)",
    )
    parser.add_argument(
        "--path",
        default=None,
        help="Override PATH when resolving tools (tests / constrained shells)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    apply = args.mode == "apply"
    if apply and is_ci_environment():
        print(
            "refuse --apply: CI/GITHUB_ACTIONS is set (use a Codespace shell, not Actions)",
            file=sys.stderr,
        )
        return 2

    planned = plan_actions(path_env=args.path)
    print(disk_report())
    print("mode:", args.mode)

    for action, binary in planned:
        status = f"ready ({binary})" if binary else "missing tool"
        print(f"- [{action.id}] {action.summary} — {status}")

    if not apply:
        print("dry-run only; re-run with --apply to execute available steps")
        return 0

    return run_apply(planned)


if __name__ == "__main__":
    raise SystemExit(main())
