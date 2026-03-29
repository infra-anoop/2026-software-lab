"""Deterministic rubric digest for the research planner (no extra LLM)."""

from __future__ import annotations

import re

from app.agents.models import BuiltRubrics, ComposedValues, RubricDimension, ValueRubric


def _first_sentence_or_chars(s: str, max_chars: int) -> str:
    t = (s or "").strip()
    if not t:
        return ""
    # First "sentence": up to . ! ? or newline, else first max_chars.
    m = re.match(r"[^.!?\n]+[.!?]?", t)
    first = m.group(0).strip() if m else t
    if len(first) > max_chars:
        return first[: max_chars - 1].rstrip() + "…"
    return first


def _dimension_digest_line(dim: RubricDimension) -> str:
    name = dim.name.strip()
    desc = _first_sentence_or_chars(dim.description, 160)
    if not desc:
        return f"- **{name}**"
    return f"- **{name}**: {desc}"


def _value_block(
    value_id: str,
    value_name: str,
    rubric: ValueRubric | None,
    *,
    max_chars_per_value: int,
) -> str:
    header = f"### {value_id} — {value_name.strip()}"
    if rubric is None:
        body = "- *(no rubric row in this run)*"
        block = f"{header}\n{body}"
        return block[:max_chars_per_value] if len(block) > max_chars_per_value else block

    lines: list[str] = [header]
    for d in rubric.dimensions:
        lines.append(_dimension_digest_line(d))
    # Reduce bullets from the end until under per-value budget (never drop header).
    while len("\n".join(lines)) > max_chars_per_value and len(lines) > 2:
        lines.pop()
    if len("\n".join(lines)) > max_chars_per_value:
        # Hard truncate (rare): keep header + one shortened line.
        block = "\n".join(lines[:2])
        if len(block) > max_chars_per_value:
            return block[: max_chars_per_value - 1].rstrip() + "…"
        return block
    return "\n".join(lines)


def build_rubric_digest_for_planner(
    composed: ComposedValues,
    rubrics: BuiltRubrics,
    *,
    max_chars_per_value: int = 400,
    max_total_digest_chars: int = 4000,
) -> str:
    """Build stable markdown-ish text: one block per value, dimension summaries only (no score ladders)."""
    by_id: dict[str, ValueRubric] = {r.value_id: r for r in rubrics.rubrics}
    blocks: list[str] = []
    for v in composed.values:
        r = by_id.get(v.value_id)
        blocks.append(
            _value_block(
                v.value_id,
                v.name,
                r,
                max_chars_per_value=max_chars_per_value,
            )
        )

    def total_len(bs: list[str]) -> int:
        return len("\n\n".join(bs))

    while total_len(blocks) > max_total_digest_chars and any(len(b) > 80 for b in blocks):
        # Truncate longest block first by stripping from end (blocks are already bullet-capped).
        longest_i = max(range(len(blocks)), key=lambda i: len(blocks[i]))
        b = blocks[longest_i]
        if len(b) <= 80:
            break
        blocks[longest_i] = b[: max(40, len(b) - 200)].rstrip() + "…"

    return "\n\n".join(blocks)
