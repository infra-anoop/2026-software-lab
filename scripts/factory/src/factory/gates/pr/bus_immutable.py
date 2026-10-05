"""`bus.immutable` (I-M2): a PR only adds bus files; it never modifies or deletes one.

Covers every file under the bus directory, including kinds the loader skips
(post-mortems). Renames are off, so a move is a delete of the old path.
"""

from __future__ import annotations

from pathlib import Path

from factory.api import GateContext, GateResult
from factory.gates.repo._git import changed, outcome

GATE_ID = "bus.immutable"
CHANGE_WORDS = {"M": "modified", "D": "deleted", "T": "changed type"}


def immutability_problems(repo: Path, base: str, head: str, bus_dir: str) -> list[str]:
    return [
        f"{path}: {CHANGE_WORDS.get(status, f'changed ({status})')}; bus files are append-only"
        for status, path in changed(repo, base, head, f"{bus_dir}/")
        if status != "A"
    ]


def run(ctx: GateContext) -> GateResult:
    problems = immutability_problems(ctx.repo_path, ctx.base_sha, ctx.head_sha, ctx.config.bus_dir)
    return outcome(GATE_ID, problems, "no existing bus file modified or deleted")
