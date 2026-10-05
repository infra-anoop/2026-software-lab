"""Markdown tables in specs: Open Decisions rows, lock tokens, and task lines."""

from __future__ import annotations

import re
from dataclasses import dataclass

OD_ID_RE = re.compile(r"^D\d+$")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
STATUS_RE = re.compile(r"^\W*(re-locked|locked|waived|open)\b", re.IGNORECASE)
NUMERIC_SPAN_RE = re.compile(r"^[$€£]?\s*\d+(?:[.,]\d+)?\s*(?:%|[A-Za-z]+)?$")
STOP_WORDS = frozenset(
    {"yes", "no", "on", "off", "all", "none", "locked", "re-locked", "waived", "open"}
)
TASK_RE = re.compile(r"^\s*- \[[ xX]\] (T\d+)\b(.*)$")
OD_TAG_RE = re.compile(r"\[OD:(D\d+)\]")
CODE_SPAN_RE = re.compile(r"`([^`]+)`")


@dataclass(frozen=True)
class TableRow:
    cells: dict[str, str]
    line: str


def split_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")) or len(stripped) < 2:
        return None
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def is_rule_row(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells if cell)


def tables(text: str) -> list[list[TableRow]]:
    """Every pipe table in `text`, rows keyed by lower-cased header names."""
    found: list[list[TableRow]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines) - 1:
        header = split_row(lines[i])
        rule = split_row(lines[i + 1])
        if header is None or rule is None or not is_rule_row(rule):
            i += 1
            continue
        names = [name.lower() for name in header]
        rows: list[TableRow] = []
        i += 2
        while i < len(lines):
            cells = split_row(lines[i])
            if cells is None:
                break
            padded = cells + [""] * (len(names) - len(cells))
            rows.append(TableRow(dict(zip(names, padded, strict=False)), lines[i]))
            i += 1
        found.append(rows)
    return found


def plain(cell: str) -> str:
    return cell.replace("*", "").strip()


@dataclass(frozen=True)
class OpenDecision:
    id: str
    status: str
    """`locked`, `re-locked`, `waived`, `open`, or `` when unrecognized."""
    status_cell: str

    @property
    def is_locked(self) -> bool:
        return self.status in {"locked", "re-locked"}

    @property
    def is_waived(self) -> bool:
        return self.status == "waived"

    def lock_tokens(self) -> list[str]:
        """Discovery tokens of a locked row (T-B2-1, orchestrator 2026-10-05).

        Each bold span of the status cell is a whole-phrase token, except numeric or
        unit-only spans, spans under 3 characters, generic stop words, and the
        status keyword. Rows that are not locked have none.
        """
        if not self.is_locked:
            return []
        tokens: list[str] = []
        for span in BOLD_RE.findall(self.status_cell):
            text = span.strip()
            if len(text) < 3 or text.lower() in STOP_WORDS or NUMERIC_SPAN_RE.match(text):
                continue
            tokens.append(text)
        return tokens


def open_decisions(spec_text: str) -> dict[str, OpenDecision]:
    """Rows `D<n>` of every table with `id` and `status` columns."""
    decisions: dict[str, OpenDecision] = {}
    for table in tables(spec_text):
        for row in table:
            if "id" not in row.cells or "status" not in row.cells:
                continue
            decision_id = plain(row.cells["id"])
            if not OD_ID_RE.match(decision_id):
                continue
            cell = row.cells["status"]
            match = STATUS_RE.match(cell)
            status = match.group(1).lower() if match else ""
            decisions.setdefault(decision_id, OpenDecision(decision_id, status, cell))
    return decisions


@dataclass(frozen=True)
class TaskLine:
    id: str
    text: str

    @property
    def decision_ids(self) -> list[str]:
        return OD_TAG_RE.findall(self.text)

    @property
    def named_paths(self) -> list[str]:
        return [span for span in CODE_SPAN_RE.findall(self.text) if "/" in span]


def task_lines(tasks_text: str) -> dict[str, TaskLine]:
    found: dict[str, TaskLine] = {}
    for line in tasks_text.splitlines():
        match = TASK_RE.match(line)
        if match:
            found.setdefault(match.group(1), TaskLine(match.group(1), match.group(2)))
    return found
