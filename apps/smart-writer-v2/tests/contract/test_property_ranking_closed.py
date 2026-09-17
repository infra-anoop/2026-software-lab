"""Inferred ranking uses only closed vocabulary ids (FR-004 / FR-005; T23/T24)."""

from __future__ import annotations

from app.agents.infer_state import infer_property_ranking
from app.properties import SEED_PROPERTIES
from tests.contract.grant_flow import FACTUAL_LOW_PROMPT, RANKING_CLOSED_PROMPT

_INVENTED = ("emotional", "visionary")
_NAMED_CLOSED = frozenset({"warm", "persuasive", "urgent"})


def test_inferred_ranking_only_closed_ids() -> None:
    """Free-form with closed + invented labels → named closed ids, no invented."""
    ranking = infer_property_ranking(RANKING_CLOSED_PROMPT)
    allowed = set(SEED_PROPERTIES)
    assert isinstance(ranking, list)
    assert ranking, (
        "prompt names closed properties plus invented labels; ranking must be nonempty"
    )
    assert all(item in allowed for item in ranking), ranking
    assert len(ranking) == len(set(ranking)), ranking
    assert _NAMED_CLOSED <= set(ranking), ranking
    for invented in _INVENTED:
        assert invented not in ranking, ranking


def test_factual_low_prompt_ranks_factual_not_first() -> None:
    """T24 seam: factual-low fixture infers factual present and not first."""
    ranking = infer_property_ranking(FACTUAL_LOW_PROMPT)
    assert "factual" in ranking, ranking
    assert ranking[0] != "factual", ranking
    assert all(item in SEED_PROPERTIES for item in ranking), ranking
