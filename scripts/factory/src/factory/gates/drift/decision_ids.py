"""Gate `decision-request-no-ids` (T047; FR-017; I-B3).

Regexes verbatim from contracts/messages.md (`\\b[TFRPD]\\d+\\b`, `FR-\\d+`, `SC-\\d+`,
`US\\d+`, `§`) plus `factory.toml [decision_lint].jargon` (whole words, any case),
applied to `prompt` and `options[].label` of every decision request the change adds or
modifies. A modified request is judged whole, at head (T-B2).
"""

from __future__ import annotations

import re
from typing import Any

import yaml

from factory.api import GateContext, GateResult
from factory.gates.drift._common import verdict, whole_word
from factory.gates.drift._git import Change

GATE = "decision-request-no-ids"
ID_PATTERNS = tuple(re.compile(p) for p in (r"\b[TFRPD]\d+\b", r"FR-\d+", r"SC-\d+", r"US\d+", "§"))


def governor_text(data: Any) -> list[tuple[str, str]]:
    """`(field, text)` for the prompt and every option label."""
    if not isinstance(data, dict):
        return []
    found: list[tuple[str, str]] = []
    if isinstance(data.get("prompt"), str):
        found.append(("prompt", data["prompt"]))
    options = data.get("options")
    for index, option in enumerate(options if isinstance(options, list) else []):
        if isinstance(option, dict) and isinstance(option.get("label"), str):
            found.append((f"options[{index}].label", option["label"]))
    return found


def offenders(text: str, jargon: list[str]) -> list[str]:
    hits = [m.group(0) for pattern in ID_PATTERNS for m in pattern.finditer(text)]
    hits += [m.group(0) for term in jargon for m in whole_word(term).finditer(text)]
    return list(dict.fromkeys(hits))


def run(ctx: GateContext) -> GateResult:
    change = Change.of(ctx)
    prefix = f"{ctx.config.bus_dir}/decisions/"
    requests = [
        c.path
        for c in change.files
        if c.status != "D" and c.path.startswith(prefix) and c.path.endswith("/request.yaml")
    ]
    problems: list[str] = []
    for path in requests:
        try:
            data = yaml.safe_load(change.head_text(path) or "")
        except yaml.YAMLError as exc:
            problems.append(f"{path}: unreadable decision request ({exc})")
            continue
        for field, text in governor_text(data):
            hits = offenders(text, ctx.config.decision_lint.jargon)
            if hits:
                problems.append(
                    f"{path} {field} quotes {', '.join(repr(h) for h in hits)}; say it in"
                    " plain language"
                )
    return verdict(GATE, problems, f"{len(requests)} changed decision request(s) read plainly")
