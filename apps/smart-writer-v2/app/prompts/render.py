"""Weave closed property ranking into a prompt-program role text (T050 / FR-006)."""

from __future__ import annotations


def weave_property_ranking(program_text: str, ranking: list[str]) -> str:
    """Append ranking instructions. ``factual`` is tone-only (F3)."""
    ids = ", ".join(ranking) if ranking else "(none; grant default de-emphasizes humorous)"
    extra = (
        "Closed property ranking (preference order): "
        f"{ids}. Do not invent property labels. "
        "factual is tone/emphasis only; do not disable research or provenance."
    )
    return f"{program_text.rstrip()}\n\n{extra}\n"