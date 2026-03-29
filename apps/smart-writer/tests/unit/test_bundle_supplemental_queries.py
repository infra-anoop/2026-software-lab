"""Planner supplemental queries merged into retrieval query string."""

from app.retrieval.bundle_builder import _merge_retrieval_query


def test_merge_retrieval_query_appends_supplemental() -> None:
    base = _merge_retrieval_query("hello world", None)
    merged = _merge_retrieval_query("hello world", ["extra one", "extra two"])
    assert "hello world" in merged
    assert "extra one" in merged
    assert "extra two" in merged
    assert len(merged) <= 500
