"""Inferred ranking uses only closed vocabulary ids (FR-004 / FR-005)."""

from __future__ import annotations

from app.agents.infer_state import infer_property_ranking
from app.properties import SEED_PROPERTIES
from tests.contract.grant_flow import GRANT_PROMPT

# Spec seed labels that must not leak (research.md R8 dropped these).
_INVENTED = ("emotional", "visionary")

_RANKING_PROMPT = (
    GRANT_PROMPT
    + " Keep it warm, persuasive, and urgent. Also make it emotional and visionary."
)


def test_inferred_ranking_only_closed_ids() -> None:
    """Free-form with closed + invented labels → nonempty ranking of closed ids only."""
    ranking = infer_property_ranking(_RANKING_PROMPT)
    allowed = set(SEED_PROPERTIES)
    assert isinstance(ranking, list)
    assert ranking, (
        "prompt names closed properties plus invented labels; ranking must be nonempty"
    )
    assert all(item in allowed for item in ranking), ranking
    assert len(ranking) == len(set(ranking)), ranking
    for invented in _INVENTED:
        assert invented not in ranking, ranking
