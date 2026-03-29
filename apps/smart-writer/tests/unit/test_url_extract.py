"""URL extraction from prompts."""

from app.retrieval.url_extract import extract_urls


def test_extract_urls_dedupes_and_orders() -> None:
    text = "See https://example.com/a and https://example.com/b — also https://example.com/a."
    urls = extract_urls(text)
    assert urls == ["https://example.com/a", "https://example.com/b"]


def test_extract_urls_strips_trailing_punct() -> None:
    text = "Link: https://example.com/path)."
    assert extract_urls(text) == ["https://example.com/path"]
