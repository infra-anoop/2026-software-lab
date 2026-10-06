"""Owned-path glob helpers (conservative: an uncertain pair counts as overlapping)."""

from __future__ import annotations

import fnmatch
import re

_WILDCARD = re.compile(r"[*?\[]")


def literal_prefix(pattern: str) -> str:
    """The part of `pattern` before its first wildcard (the whole pattern when literal)."""
    match = _WILDCARD.search(pattern)
    return pattern if match is None else pattern[: match.start()]


def globs_overlap(a: str, b: str) -> bool:
    """Could some path match both `a` and `b`?"""
    if a == b or fnmatch.fnmatchcase(a, b) or fnmatch.fnmatchcase(b, a):
        return True
    pa, pb = literal_prefix(a), literal_prefix(b)
    if pa == a or pb == b:
        return False
    return pa.startswith(pb) or pb.startswith(pa)


def overlapping(mine: list[str], theirs: list[str]) -> list[tuple[str, str]]:
    return [(a, b) for a in mine for b in theirs if globs_overlap(a, b)]


def path_is_owned(path: str, owned: list[str]) -> bool:
    for pattern in owned:
        if path == pattern or fnmatch.fnmatchcase(path, pattern):
            return True
        if pattern.endswith("/**") and path.startswith(pattern[:-2]):
            return True
    return False
