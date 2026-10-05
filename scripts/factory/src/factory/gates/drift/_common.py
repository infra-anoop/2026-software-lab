"""Shared drift-gate pieces: results, the effective order, path globs, and code lines."""

from __future__ import annotations

import re
from collections.abc import Iterable
from functools import lru_cache
from pathlib import PurePosixPath

from factory.api import GateContext, GateResult
from factory.bus.models import Amendment, Lock, WorkOrder, WorkOrderFields

COMMENT_PREFIXES = ("#", "//", "/*", "*", "--")


def passed(gate_id: str, *notes: str) -> GateResult:
    return GateResult(gate_id=gate_id, passed=True, messages=[f"{gate_id}: {n}" for n in notes])


def failed(gate_id: str, problems: Iterable[str]) -> GateResult:
    lines = [f"{gate_id}: {problem}" for problem in problems]
    return GateResult(gate_id=gate_id, passed=False, messages=lines or [f"{gate_id}: failed"])


def verdict(gate_id: str, problems: list[str], ok_note: str) -> GateResult:
    return failed(gate_id, problems) if problems else passed(gate_id, ok_note)


class OrderMissing(Exception):
    """The context names an order that is not in the head bus snapshot."""


def effective_order(ctx: GateContext) -> WorkOrderFields | None:
    """The order named by `ctx.order_id` with its amendments applied in number order.

    Returns None when the context names no order; raises `OrderMissing` when it names
    one that the head bus does not hold (gates fail closed on that).
    """
    if ctx.order_id is None:
        return None
    order = next(
        (m for m in ctx.bus_snapshot if isinstance(m, WorkOrder) and m.id == ctx.order_id),
        None,
    )
    if order is None:
        raise OrderMissing(f"order {ctx.order_id} is not on the bus at head")
    values = order.model_dump(include=set(WorkOrderFields.model_fields))
    prefix = f"{ctx.order_id}.amend-"
    amendments = sorted(
        (m for m in ctx.bus_snapshot if isinstance(m, Amendment) and m.id.startswith(prefix)),
        key=lambda m: int(m.id.rsplit("-", 1)[1]),
    )
    for amendment in amendments:
        values.update(amendment.values)
    return WorkOrderFields.model_validate(values)


def lock_ids(locks: Iterable[Lock]) -> set[str]:
    return {lock.id for lock in locks}


@lru_cache(maxsize=256)
def glob_regex(pattern: str) -> re.Pattern[str]:
    """`**` spans directories, `*` and `?` stay inside one path segment."""
    out: list[str] = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("/**", i) and i + 3 == len(pattern):
            out.append("(?:/.*)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def matches_any(path: str, patterns: Iterable[str]) -> bool:
    return any(glob_regex(pattern).match(path) for pattern in patterns)


def is_comment_only(line: str) -> bool:
    return line.strip().startswith(COMMENT_PREFIXES)


def is_code_path(path: str, bus_dir: str) -> bool:
    """Code files are outside the bus and not Markdown (data-model § Lock)."""
    parts = PurePosixPath(path).parts
    return not (parts and parts[0] == bus_dir) and not path.endswith(".md")


def code_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip() and not is_comment_only(line)]


def whole_word(phrase: str) -> re.Pattern[str]:
    """Case-insensitive match of `phrase` not touching a word character on either side."""
    return re.compile(rf"(?<!\w){re.escape(phrase)}(?!\w)", re.IGNORECASE)
