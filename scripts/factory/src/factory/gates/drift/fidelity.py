"""Gates `order-fidelity-declared` and `lock.letter-tokens` (T046; FR-016; I-B5).

`order-fidelity-declared`: every locked Open Decision the effective order touches has
a Lock entry. An order touches a decision through a task tagged `[OD:<id>]`, an owned
path matching a path that such a task names, or a goal naming the decision id or one
of its lock tokens (T-B1, T-B2-1).

`lock.letter-tokens` (data-model § Lock): over code lines of the change, renames off,
each `fidelity: letter` lock must be honored by a changed file at head, must not be
removed from a file that honored it at base (unless an added line elsewhere honors it),
must not be weakened by an added numeric counterpart, and no registered substitute may
appear on an added code line.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property

from factory.api import GateContext, GateResult
from factory.bus.models import LOCK_NUMBER_RE, Lock, is_numeric_token
from factory.gates.drift._common import (
    OrderMissing,
    code_lines,
    effective_order,
    failed,
    is_code_path,
    is_comment_only,
    lock_ids,
    matches_any,
    passed,
    verdict,
    whole_word,
)
from factory.gates.drift._git import Change
from factory.gates.drift._specs import OpenDecision, open_decisions, task_lines

DECLARED = "order-fidelity-declared"
TOKENS = "lock.letter-tokens"


# --- order-fidelity-declared ------------------------------------------------------------


def touched_decisions(
    decisions: dict[str, OpenDecision],
    tasks_text: str,
    *,
    goal: str,
    tasks: list[str],
    owned_paths: list[str],
) -> dict[str, str]:
    """Locked decision id -> how the order touches it."""
    touched: dict[str, str] = {}
    locked = {d.id: d for d in decisions.values() if d.is_locked}
    lines = task_lines(tasks_text)
    for task_id in tasks:
        line = lines.get(task_id)
        for decision_id in line.decision_ids if line else []:
            if decision_id in locked:
                touched.setdefault(decision_id, f"task {task_id} is tagged [OD:{decision_id}]")
    for line in lines.values():
        for decision_id in line.decision_ids:
            if decision_id not in locked:
                continue
            for path in line.named_paths:
                if matches_any(path, owned_paths):
                    touched.setdefault(
                        decision_id, f"owned path covers {path} (task {line.id} [OD:{decision_id}])"
                    )
    for decision in locked.values():
        if whole_word(decision.id).search(goal):
            touched.setdefault(decision.id, f"the goal names {decision.id}")
            continue
        for token in decision.lock_tokens():
            if whole_word(token).search(goal):
                touched.setdefault(decision.id, f"the goal names its locked value {token!r}")
                break
    return touched


def run_order_fidelity_declared(ctx: GateContext) -> GateResult:
    try:
        order = effective_order(ctx)
    except OrderMissing as exc:
        return failed(DECLARED, [str(exc)])
    if order is None:
        return passed(DECLARED, "no order linked; nothing to declare")
    change = Change.of(ctx)
    spec_root = ctx.config.spec_roots[0] if ctx.config.spec_roots else "specs"
    feature_dir = f"{spec_root}/{order.feature}"
    spec = change.head_text(f"{feature_dir}/spec.md")
    if spec is None:
        return failed(
            DECLARED, [f"feature {order.feature}: {feature_dir}/spec.md is missing at head"]
        )
    touched = touched_decisions(
        open_decisions(spec),
        change.head_text(f"{feature_dir}/tasks.md") or "",
        goal=order.goal,
        tasks=order.tasks,
        owned_paths=order.owned_paths,
    )
    declared = lock_ids(order.locks)
    problems = [
        f"order {ctx.order_id} touches locked decision {decision_id} ({how}) but declares"
        f" no Lock entry for {decision_id}"
        for decision_id, how in sorted(touched.items())
        if decision_id not in declared
    ]
    return verdict(DECLARED, problems, f"{len(touched)} touched lock(s), all declared")


# --- lock.letter-tokens -----------------------------------------------------------------


@dataclass(frozen=True)
class Token:
    text: str
    direction: str | None

    @cached_property
    def number(self) -> float | None:
        match = LOCK_NUMBER_RE.search(self.text)
        return float(match.group(0)) if match and is_numeric_token(self.text) else None

    @cached_property
    def counterpart(self) -> re.Pattern[str] | None:
        """For a numeric token: its text around the number, matched case- and
        whitespace-insensitively; group 1 is the number on the matching line."""
        match = LOCK_NUMBER_RE.search(self.text)
        if match is None or self.number is None:
            return None
        before = "".join(ch for ch in self.text[: match.start()] if not ch.isspace())
        after = "".join(ch for ch in self.text[match.end() :] if not ch.isspace())
        lead = r"(?<!\w)" if _is_word(before[:1]) else r"(?<![\d.])"
        head = r"\s*".join(re.escape(ch) for ch in before)
        number = r"\s*(\d+(?:\.\d+)?)(?!\d)(?!\.\d)"
        tail = (r"\s*" + r"\s*".join(re.escape(ch) for ch in after)) if after else ""
        end = r"(?!\w)" if _is_word(after[-1:]) else ""
        return re.compile(lead + head + number + tail + end, re.IGNORECASE)

    def numbers_on(self, line: str) -> list[float]:
        if self.counterpart is None:
            return []
        return [float(m.group(1)) for m in self.counterpart.finditer(line)]

    def honored_by(self, line: str) -> bool:
        if self.text.lower() in line.lower():
            return True
        if self.direction is None:
            return False
        return any(self.at_least_as_strong(value) for value in self.numbers_on(line))

    def weakened_by(self, line: str) -> bool:
        """An added counterpart carries a different (exact) or weaker (min/max) number."""
        return any(not self.at_least_as_strong(value) for value in self.numbers_on(line))

    def at_least_as_strong(self, value: float) -> bool:
        assert self.number is not None
        if self.direction == "min":
            return value >= self.number
        if self.direction == "max":
            return value <= self.number
        return value == self.number


def _is_word(char: str) -> bool:
    return bool(char) and (char.isalnum() or char == "_")


def lock_problems(lock: Lock, change: Change, bus_dir: str) -> list[str]:
    tokens = [Token(text, lock.direction) for text in lock.letter_tokens]
    code_changes = [c for c in change.files if is_code_path(c.path, bus_dir)]
    added = {
        path: [text for _n, text in lines if text.strip() and not is_comment_only(text)]
        for path, lines in change.added_lines.items()
        if is_code_path(path, bus_dir)
    }
    head_lines = {
        c.path: code_lines(change.head_text(c.path) or "") for c in code_changes if c.status != "D"
    }
    problems: list[str] = []
    for token in tokens:
        if not any(token.honored_by(line) for lines in head_lines.values() for line in lines):
            problems.append(
                f"{lock.id}: no changed code line honors {token.text!r} (letter fidelity)"
            )
        for change_file in code_changes:
            if change_file.status == "A":
                continue
            base_lines = code_lines(change.base_text(change_file.path) or "")
            if not any(token.honored_by(line) for line in base_lines):
                continue
            if any(token.honored_by(line) for line in head_lines.get(change_file.path, [])):
                continue
            moved = any(
                token.honored_by(line)
                for path, lines in added.items()
                if path != change_file.path
                for line in lines
            )
            if not moved:
                problems.append(
                    f"{lock.id}: {change_file.path} honored {token.text!r} at base and no"
                    " longer does (removed)"
                )
        for path, lines in added.items():
            for line in lines:
                if token.weakened_by(line):
                    problems.append(
                        f"{lock.id}: {path} adds {line.strip()!r}, weaker than {token.text!r}"
                    )
    for substitute in lock.substitutes:
        for path, lines in added.items():
            if any(substitute.lower() in line.lower() for line in lines):
                problems.append(
                    f"{lock.id}: {path} adds registered substitute {substitute!r} in code"
                )
    return problems


def run_lock_letter_tokens(ctx: GateContext) -> GateResult:
    try:
        order = effective_order(ctx)
    except OrderMissing as exc:
        return failed(TOKENS, [str(exc)])
    if order is None:
        return passed(TOKENS, "no order linked; no locks to honor")
    letter = [lock for lock in order.locks if lock.fidelity == "letter"]
    if not letter:
        return passed(TOKENS, "the order declares no letter-fidelity lock")
    change = Change.of(ctx)
    problems = [p for lock in letter for p in lock_problems(lock, change, ctx.config.bus_dir)]
    return verdict(TOKENS, problems, f"{len(letter)} letter lock(s) honored")
