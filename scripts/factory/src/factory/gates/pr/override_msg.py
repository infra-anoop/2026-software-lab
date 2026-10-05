"""`message.override` (governor-only, I-M1/I-P9): the override messages this PR adds.

Each names a registered gate, carries the registry's class as `gate_class`, is by
`actor: governor` when the gate is governor-only, and names the PR being checked.
Overrides already on the base are not this PR's change.
"""

from __future__ import annotations

import re

from factory.api import GateContext, GateResult
from factory.bus.models import Override
from factory.bus.store import BusError, parse_bus_text
from factory.gates.registry import RegistryError, load_registry
from factory.gates.repo._git import changed, outcome, read_blobs

GATE_ID = "message.override"
OVERRIDE_FILE = re.compile(r"/orders/[^/]+/override-\d{2}\.ya?ml$")


def run(ctx: GateContext) -> GateResult:
    bus_dir = ctx.config.bus_dir
    added = [
        path
        for status, path in changed(ctx.repo_path, ctx.base_sha, ctx.head_sha, f"{bus_dir}/")
        if status == "A" and OVERRIDE_FILE.search(path)
    ]
    registry = load_registry()
    problems = []
    for path, text in read_blobs(ctx.repo_path, ctx.head_sha, added).items():
        try:
            message = parse_bus_text(
                text or "", path, autonomy_horizon_minutes=ctx.config.autonomy_horizon_minutes
            )
        except BusError as exc:
            problems.append(f"{path}: invalid override ({exc.problem.splitlines()[0]})")
            continue
        if not isinstance(message, Override):
            continue
        try:
            gate = registry.get(message.gate)
        except RegistryError:
            problems.append(f"{path}: gate {message.gate!r} is not registered")
            continue
        if message.gate_class != gate.gate_class:
            problems.append(
                f"{path}: gate {gate.id!r} is {gate.gate_class} in the registry,"
                f" not {message.gate_class}"
            )
        if gate.gate_class == "governor-only" and message.actor != "governor":
            problems.append(
                f"{path}: gate {gate.id!r} is governor-only; actor {message.actor!r} cannot"
                " override it"
            )
        if ctx.pr_number is not None and message.pr != ctx.pr_number:
            problems.append(f"{path}: names PR {message.pr}, not PR {ctx.pr_number}")
    return outcome(GATE_ID, problems, f"{len(added)} added override(s) are well-formed")
