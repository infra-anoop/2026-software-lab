"""`factory order new`: scaffold an order file from tasks.md lines and validate it locally.

A task tagged `[OD:<id>]` touches that Open Decision. Touching a locked decision needs a
declared fidelity (`--lock <id>=letter|intent|waived[:<lock-ref>]`); the lock's letter
tokens come from the spec's Open Decisions table (the text after "—" in `status`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from factory.bus.models import WorkOrder
from factory.config.settings import Settings
from factory.gates.registry import load_registry
from factory.orders.errors import Refused, Usage
from factory.orders.messages import build, path_of, to_yaml, utc_stamp

TASK_LINE = re.compile(r"^\s*-\s*\[[ xX]\]\s+(?P<id>T\d+[a-z]?)\b(?P<rest>.*)$")
TAG = re.compile(r"\[(?P<tag>[^\]]+)\]")
CODE = re.compile(r"`([^`]+)`")
DEFAULT_STOP_CONDITIONS = ["needs a change outside owned paths", "needs a governor decision"]
FIDELITIES = ("letter", "intent", "waived")


@dataclass(frozen=True)
class Task:
    id: str
    text: str
    tags: list[str]
    paths: list[str]

    @property
    def decisions(self) -> list[str]:
        return [tag.split(":", 1)[1].strip() for tag in self.tags if tag.startswith("OD:")]


@dataclass(frozen=True)
class OpenDecision:
    id: str
    locked: bool
    tokens: list[str]
    fidelity: str | None


def parse_tasks(text: str) -> dict[str, Task]:
    tasks: dict[str, Task] = {}
    for line in text.splitlines():
        match = TASK_LINE.match(line)
        if not match:
            continue
        rest = match["rest"]
        tags = [m["tag"].strip() for m in TAG.finditer(rest)]
        paths = [p for p in CODE.findall(rest) if "/" in p and " " not in p]
        clean = CODE.sub(lambda m: m.group(1), TAG.sub("", rest)).strip()
        tasks[match["id"]] = Task(id=match["id"], text=clean, tags=tags, paths=paths)
    return tasks


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _plain(text: str) -> str:
    return text.replace("**", "").replace("`", "").strip()


def parse_open_decisions(spec: str) -> dict[str, OpenDecision]:
    """Rows of the first markdown table whose header has `id` and `status` columns."""
    lines = spec.splitlines()
    out: dict[str, OpenDecision] = {}
    for n, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        header = [cell.lower() for cell in _cells(line)]
        if "id" not in header or "status" not in header:
            continue
        col = {name: i for i, name in enumerate(header)}
        for row in lines[n + 2 :]:
            if not row.lstrip().startswith("|"):
                break
            cells = _cells(row)
            if len(cells) < len(header):
                continue
            status = cells[col["status"]]
            locked = "locked" in status.lower()
            tail = re.split(r"\s+[—–]\s+", status, maxsplit=1)
            tokens = [_plain(t) for t in tail[1].split(",")] if locked and len(tail) > 1 else []
            fidelity = _plain(cells[col["fidelity"]]) if "fidelity" in col else None
            decision_id = _plain(cells[col["id"]])
            out[decision_id] = OpenDecision(
                id=decision_id, locked=locked, tokens=[t for t in tokens if t], fidelity=fidelity
            )
        break
    return out


def parse_lock_args(values: list[str]) -> dict[str, tuple[str, str | None]]:
    out: dict[str, tuple[str, str | None]] = {}
    for value in values:
        decision_id, sep, rest = value.partition("=")
        fidelity, _, waiver = rest.partition(":")
        if not sep or not decision_id.strip() or fidelity not in FIDELITIES:
            raise Usage(f"--lock {value!r}: expected ID=letter|intent|waived[:<lock-ref>]")
        out[decision_id.strip()] = (fidelity, waiver.strip() or None)
    return out


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _feature_dir(repo: Path, settings: Settings, feature: str) -> Path:
    for root in settings.spec_roots:
        candidate = repo / root / feature
        if (candidate / "tasks.md").is_file():
            return candidate
    raise Refused(f"no tasks.md for feature {feature!r} under {', '.join(settings.spec_roots)}")


def _default_checks() -> list[str]:
    return [gate.id for gate in load_registry().gates if gate.priority == "P1"]


def scaffold_order(
    repo: Path,
    settings: Settings,
    *,
    feature: str,
    task_ids: list[str],
    slug: str | None,
    size_minutes: int | None,
    lock_args: list[str],
    checks: list[str],
    owned_paths: list[str],
    intents: list[str],
    actor_model: str,
    now: datetime,
) -> tuple[str, WorkOrder]:
    """Write `bus/orders/<id>/order.yaml` in the working tree; returns (path, order)."""
    if not task_ids:
        raise Usage("name at least one task with --from-task")
    if size_minutes is None:
        raise Usage("give a size estimate with --size-minutes")
    horizon = settings.autonomy_horizon_minutes
    if size_minutes > horizon:
        raise Refused(
            f"size {size_minutes} minutes is over the {horizon}-minute autonomy horizon;"
            " split the work into smaller orders"
        )
    feature_dir = _feature_dir(repo, settings, feature)
    tasks = parse_tasks((feature_dir / "tasks.md").read_text(encoding="utf-8"))
    missing = [task_id for task_id in task_ids if task_id not in tasks]
    if missing:
        raise Refused(f"tasks not found in {feature}/tasks.md: {', '.join(missing)}")
    chosen = [tasks[task_id] for task_id in task_ids]

    spec = feature_dir / "spec.md"
    decisions = parse_open_decisions(spec.read_text(encoding="utf-8")) if spec.is_file() else {}
    declared = parse_lock_args(lock_args)
    locks = []
    touched = sorted({d for task in chosen for d in task.decisions} | set(declared))
    for decision_id in touched:
        decision = decisions.get(decision_id)
        if decision is None:
            raise Refused(f"decision {decision_id} is not in {feature}/spec.md Open Decisions")
        if not decision.locked:
            raise Refused(
                f"decision {decision_id} is still open; it has to be locked before this work"
                " can be ordered"
            )
        if decision_id not in declared:
            tokens = ", ".join(decision.tokens) or "its locked choice"
            raise Refused(
                f"this work touches locked decision {decision_id} ({tokens}); declare its"
                f" fidelity with --lock {decision_id}=letter|intent|waived"
            )
        fidelity, waiver = declared[decision_id]
        if fidelity == "waived" and not waiver:
            raise Refused(f"--lock {decision_id}=waived needs the governor's lock: waived:<ref>")
        locks.append(
            {
                "id": decision_id,
                "letter_tokens": decision.tokens,
                "fidelity": fidelity,
                **({"waiver_ref": waiver} if waiver else {}),
            }
        )

    paths = owned_paths or list(dict.fromkeys(p for task in chosen for p in task.paths))
    if not paths:
        raise Refused("the tasks name no file paths; give owned paths with --owned-path")
    order_slug = _slugify(slug or f"{feature}-{'-'.join(task_ids)}")
    order_id = f"wo-{now:%Y%m%d}-{order_slug}"
    goal = "; ".join(task.text.rstrip(".") for task in chosen) + "."
    data = {
        "schema_version": 1,
        "kind": "order",
        "id": order_id,
        "created": utc_stamp(now),
        "actor": "orchestrator",
        "actor_model": actor_model,
        "feature": feature,
        "goal": goal,
        "intents": intents,
        "owned_paths": paths,
        "checks": checks or _default_checks(),
        "locks": locks,
        "size_minutes": size_minutes,
        "stop_conditions": DEFAULT_STOP_CONDITIONS,
        "depends_on_decisions": [],
        "tasks": task_ids,
        "worker_runtime": "local_subagent",
        "refs": [f"{feature_dir.relative_to(repo).as_posix()}/tasks.md"],
    }
    order = build(data, settings)
    if not isinstance(order, WorkOrder):
        raise Usage(f"scaffolded a {order.kind}, not an order")
    relative = path_of(order, settings)
    target = repo / relative
    if target.exists():
        raise Refused(f"{relative} already exists; pick another --slug")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(to_yaml(order))
    return relative, order
