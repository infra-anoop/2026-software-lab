"""`bus.schema` (I-M2): every bus file at head validates and sits at its layout path."""

from __future__ import annotations

from factory.api import GateContext, GateResult
from factory.bus.schema import validate_bus
from factory.gates.repo._git import outcome

GATE_ID = "bus.schema"


def run(ctx: GateContext) -> GateResult:
    problems = validate_bus(ctx.repo_path, ctx.config, ref=ctx.head_sha)
    return outcome(GATE_ID, problems, "every bus file validates")
