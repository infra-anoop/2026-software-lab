"""Closed property vocabulary."""

from app.properties import SEED_PROPERTIES, filter_closed_ranking, is_closed_property


def test_seed_contains_required_ids() -> None:
    for item in (
        "factual",
        "persuasive",
        "concise",
        "warm",
        "formal",
        "humorous",
        "specific",
        "urgent",
    ):
        assert is_closed_property(item)
    assert SEED_PROPERTIES[0] == "factual"


def test_filter_drops_unknown_and_dupes() -> None:
    assert filter_closed_ranking(["humorous", "nope", "factual", "factual"]) == [
        "humorous",
        "factual",
    ]
