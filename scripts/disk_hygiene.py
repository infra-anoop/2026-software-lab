#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Nix + Docker disk reclaim for lab CI and Codespace.

Default is ``--dry-run`` (print plan). ``--apply`` runs reclaim — used by
verify-source and the Codespace postStartCommand.

Codespace postStart invokes this with system ``python3`` (not ``uv run``):
``uv`` is only on PATH inside ``nix develop``, so a uv-based postStart never
ran and disk filled until rebuild.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
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
        # -a: unused images (not only dangling) — nested/rebuild leftovers
        argv=("docker", "system", "prune", "-af"),
        summary="Remove unused Docker data (docker system prune -af)",
        tool="docker",
    ),
)


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


def docker_daemon_ready(
    docker_bin: str,
    *,
    runner: Callable[..., Any] | None = None,
) -> bool:
    """True when ``docker info`` can talk to a running daemon."""
    run = runner or subprocess.run
    try:
        completed = run(
            [docker_bin, "info"],
            check=False,
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return int(getattr(completed, "returncode", 1)) == 0


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
        if action.id == "docker-prune" and not docker_daemon_ready(binary, runner=run):
            print(
                f"skip {action.id}: docker CLI present but daemon unreachable "
                "(no socket / DinD not ready)"
            )
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
        help="Run reclaim commands (CI / Codespace lifecycle)",
    )
    parser.add_argument(
        "--path",
        default=None,
        help="Override PATH when resolving tools (tests / constrained shells)",
    )
    parser.add_argument(
        "--best-effort",
        action="store_true",
        help="After --apply, always exit 0 (Codespace postStart; CI should omit)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    apply = args.mode == "apply"
    planned = plan_actions(path_env=args.path)
    print(disk_report())
    print("mode:", args.mode)

    for action, binary in planned:
        if binary is None:
            status = "missing tool"
        elif action.id == "docker-prune" and not docker_daemon_ready(binary):
            status = f"daemon down ({binary})"
        else:
            status = f"ready ({binary})"
        print(f"- [{action.id}] {action.summary} — {status}")

    if not apply:
        print("dry-run only; re-run with --apply to execute available steps")
        return 0

    code = run_apply(planned)
    if args.best_effort and code != 0:
        print(f"best-effort: suppressing exit {code} for lifecycle")
        return 0
    return code


if __name__ == "__main__":
    raise SystemExit(main())
