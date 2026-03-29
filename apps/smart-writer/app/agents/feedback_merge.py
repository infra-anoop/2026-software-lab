"""Deterministic merge of per-value assessor results for the writer (no extra LLM call)."""

from __future__ import annotations

from app.agents.models import AssessorResult, ComposedValues, GroundingAssessment, RUBRIC_MAX_TOTAL, ValueProvenance


def _sort_key(
    r: AssessorResult,
    weight: float,
    provenance: ValueProvenance,
) -> tuple[float, int, str]:
    """Weighted gap (§6.1): higher = more urgent; tie-break: domain rows before craft, then id."""
    score_sort = weight * float(RUBRIC_MAX_TOTAL - r.total)
    domain_like = provenance in ("task_derived", "library_canonical")
    prov_rank = 0 if domain_like else 1
    return (-score_sort, prov_rank, r.value_id)


def merge_assessor_feedback(results: list[AssessorResult], composed: ComposedValues) -> str:
    """Order by weight × gap to max score; header notes weight-aware prioritization (§6.1)."""
    meta = {v.value_id: (v.weight or 0.0, v.provenance) for v in composed.values}
    ordered = sorted(
        results,
        key=lambda r: _sort_key(r, meta[r.value_id][0], meta[r.value_id][1]),
    )
    blocks: list[str] = []
    for r in ordered:
        w, _prov = meta[r.value_id]
        keep_bullets = "\n".join(f"- {x}" for x in r.keep)
        change_bullets = "\n".join(f"- {x}" for x in r.change)
        blocks.append(
            f"### {r.value_id} — total {r.total}/25 (weight {w:.4f})\n"
            f"**Keep:**\n{keep_bullets}\n"
            f"**Change:**\n{change_bullets}"
        )
    return (
        "Prioritized by weighted gap to the rubric max (importance × urgency; address highest first).\n\n"
        + "\n\n".join(blocks)
    )


def weighted_mean_aggregate(results: list[AssessorResult], composed: ComposedValues) -> float:
    """Headline ``A`` on 0–25 scale: Σ w_i · total_i with Σ w_i = 1 (§7.1)."""
    by_id = {r.value_id: r for r in results}
    s = 0.0
    for v in composed.values:
        t = float(by_id[v.value_id].total)
        s += (v.weight or 0.0) * t
    return s


def domain_aggregate(results: list[AssessorResult], composed: ComposedValues) -> float:
    """``A_domain``: weighted mean over domain rows (task_derived + library_canonical), renormalized (§7.6)."""
    by_id = {r.value_id: r for r in results}
    domain_vals = [
        v for v in composed.values if v.provenance in ("task_derived", "library_canonical")
    ]
    if not domain_vals:
        return 0.0
    sw = sum(v.weight or 0.0 for v in domain_vals)
    if sw <= 0:
        return 0.0
    acc = 0.0
    for v in domain_vals:
        w = (v.weight or 0.0) / sw
        acc += w * float(by_id[v.value_id].total)
    return acc


def craft_aggregate(results: list[AssessorResult], composed: ComposedValues) -> float:
    """``A_craft``: weighted mean over designer_craft rows, renormalized within craft (§7.6)."""
    by_id = {r.value_id: r for r in results}
    craft_vals = [v for v in composed.values if v.provenance == "designer_craft"]
    if not craft_vals:
        return 0.0
    sw = sum(v.weight or 0.0 for v in craft_vals)
    if sw <= 0:
        return 0.0
    acc = 0.0
    for v in craft_vals:
        w = (v.weight or 0.0) / sw
        acc += w * float(by_id[v.value_id].total)
    return acc


def aggregate_sum_scores(results: list[AssessorResult]) -> float:
    """Legacy sum of per-value totals (diagnostics only; prefer weighted_mean_aggregate)."""
    return float(sum(r.total for r in results))


def _truncate_block(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    keep = max_len - 60
    head = max(keep // 2, 400)
    tail = max(keep - head, 400)
    return text[:head] + "\n\n…[truncated merged value feedback]…\n\n" + text[-tail:]


def merge_value_and_grounding_feedback(
    results: list[AssessorResult],
    grounding: GroundingAssessment | None,
    composed: ComposedValues,
    *,
    max_chars: int = 32_000,
) -> str:
    """Merge order (design §6.2): MUST_FIX + writer_instructions; value block; SHOULD_FIX.

    If over ``max_chars``, shrink the **value** section first; preserve grounding head.
    """
    value_block = merge_assessor_feedback(results, composed)
    if grounding is None:
        return value_block

    must = [i for i in grounding.issues if i.severity == "MUST_FIX"]
    should = [i for i in grounding.issues if i.severity == "SHOULD_FIX"]

    head_parts: list[str] = []
    if grounding.writer_instructions.strip():
        head_parts.append(grounding.writer_instructions.strip())
    for i in must:
        line = f"- [{i.category}] {i.fix_guidance}"
        if i.excerpt_from_draft:
            line += f' (draft: "{i.excerpt_from_draft[:200]}")'
        head_parts.append(line)
    head = ""
    if head_parts:
        head = "### Grounding — must address\n" + "\n".join(head_parts)

    tail_parts: list[str] = []
    for i in should:
        tail_parts.append(f"- [{i.category}] {i.fix_guidance}")
    tail = ""
    if tail_parts:
        tail = "### Grounding — should fix\n" + "\n".join(tail_parts)

    if not head and not tail:
        merged = value_block
    elif not head:
        merged = f"{value_block}\n\n{tail}"
    elif not tail:
        merged = f"{head}\n\n{value_block}"
    else:
        merged = f"{head}\n\n{value_block}\n\n{tail}"

    if len(merged) <= max_chars:
        return merged

    overhead = len(merged) - len(value_block)
    budget_for_value = max(2000, max_chars - overhead - 100)
    trimmed_value = _truncate_block(value_block, budget_for_value)
    if not head and not tail:
        return trimmed_value
    if not head:
        return f"{trimmed_value}\n\n{tail}"
    if not tail:
        return f"{head}\n\n{trimmed_value}"
    return f"{head}\n\n{trimmed_value}\n\n{tail}"
