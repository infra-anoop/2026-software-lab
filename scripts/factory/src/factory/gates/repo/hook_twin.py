"""`hook-has-ci-twin` (I-G5): every Cursor hook has a CI twin in the registry.

Each entry in `.cursor/hooks.json` must be a factory hook command
(`.cursor/hooks/factory-hook.sh <name>`, amendment A1). The registry needs a row
`id: <name>` whose `hook_twin_of` names a registered CI gate (a row that is not itself a
hook row). No hooks file means no hooks to twin.
"""

from __future__ import annotations

import json
import shlex
from typing import Any

from factory.api import GateContext, GateResult
from factory.gates.registry import Gate
from factory.gates.repo._git import outcome, show
from factory.gates.repo.fail_mode import REGISTRY_FILE, parse_registry

GATE_ID = "hook-has-ci-twin"
HOOKS_FILE = ".cursor/hooks.json"
HOOK_WRAPPER = ".cursor/hooks/factory-hook.sh"


def _hook_names(hooks_text: str) -> tuple[list[tuple[str, str]], list[str]]:
    """`(event, hook name)` per factory hook entry, plus problems for every other entry."""
    try:
        data: Any = json.loads(hooks_text)
    except ValueError as exc:
        return [], [f"{HOOKS_FILE}: unreadable JSON ({exc})"]
    hooks = data.get("hooks") if isinstance(data, dict) else None
    if not isinstance(hooks, dict):
        return [], [f"{HOOKS_FILE}: expected a mapping with a `hooks` object"]
    names: list[tuple[str, str]] = []
    problems = []
    for event, entries in hooks.items():
        for entry in entries if isinstance(entries, list) else [entries]:
            command = entry.get("command") if isinstance(entry, dict) else None
            try:
                argv = shlex.split(command) if isinstance(command, str) else []
            except ValueError:
                argv = []
            if len(argv) == 2 and argv[0] in {HOOK_WRAPPER, f"./{HOOK_WRAPPER}"}:
                names.append((event, argv[1]))
            else:
                problems.append(
                    f"{HOOKS_FILE} {event}: {command!r} is not a factory hook"
                    f" (`{HOOK_WRAPPER} <name>`), so it has no CI twin"
                )
    return names, problems


def twin_problems(registry_text: str | None, hooks_text: str | None) -> list[str]:
    if hooks_text is None:
        return []
    names, problems = _hook_names(hooks_text)
    gates, registry_problems = parse_registry(registry_text, REGISTRY_FILE)
    if registry_text is None or not gates and registry_problems:
        return [*problems, *registry_problems]
    by_id: dict[str, Gate] = {gate.id: gate for gate in gates}
    for event, name in names:
        row = by_id.get(name)
        if row is None:
            problems.append(f"hook {name!r} ({event}) has no row in {REGISTRY_FILE}")
        elif row.hook_twin_of is None:
            problems.append(f"hook {name!r} ({event}): its registry row has no hook_twin_of")
        elif row.hook_twin_of not in by_id:
            problems.append(
                f"hook {name!r} ({event}): twin {row.hook_twin_of!r} is not a registered gate"
            )
        elif by_id[row.hook_twin_of].hook_twin_of is not None:
            problems.append(
                f"hook {name!r} ({event}): twin {row.hook_twin_of!r} is itself a hook row,"
                " not a CI gate"
            )
    return problems


def run(ctx: GateContext) -> GateResult:
    problems = twin_problems(
        show(ctx.repo_path, ctx.head_sha, REGISTRY_FILE),
        show(ctx.repo_path, ctx.head_sha, HOOKS_FILE),
    )
    return outcome(GATE_ID, problems, "every hook has a CI twin")
