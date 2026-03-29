"""Extract HTTP(S) URLs from free-form user text."""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

# Rough URL token; excludes trailing punctuation common in prose.
_URL_RE = re.compile(
    r"https?://[^\s\]>)\],\"']+",
    re.IGNORECASE,
)


def _normalize_url(raw: str) -> str | None:
    s = raw.strip().rstrip(".,;:!?)")
    if not s.startswith(("http://", "https://")):
        return None
    try:
        p = urlparse(s)
    except ValueError:
        return None
    if not p.netloc:
        return None
    return urlunparse(p)


def extract_urls(text: str, *, max_urls: int = 16) -> list[str]:
    """Return unique normalized URLs in first-seen order (cap ``max_urls``)."""
    seen: set[str] = set()
    out: list[str] = []
    for m in _URL_RE.finditer(text):
        u = _normalize_url(m.group(0))
        if u is None or u in seen:
            continue
        seen.add(u)
        out.append(u)
        if len(out) >= max_urls:
            break
    return out
