"""Owned-path globs: `**` crosses directories, `*` and `?` stay within one, `{a,b}` and
`[...]` as in shells; a pattern ending in `/` owns that whole directory."""

from __future__ import annotations

import re
from functools import lru_cache


def _expand_braces(pattern: str) -> list[str]:
    start = pattern.find("{")
    if start < 0:
        return [pattern]
    depth = 0
    for end in range(start, len(pattern)):
        if pattern[end] == "{":
            depth += 1
        elif pattern[end] == "}":
            depth -= 1
            if depth == 0:
                break
    else:
        return [pattern]
    body, parts, depth, last = pattern[start + 1 : end], [], 0, 0
    for i, char in enumerate(body):
        depth += {"{": 1, "}": -1}.get(char, 0)
        if char == "," and depth == 0:
            parts.append(body[last:i])
            last = i + 1
    parts.append(body[last:])
    head, tail = pattern[:start], pattern[end + 1 :]
    return [expanded for part in parts for expanded in _expand_braces(head + part + tail)]


def _translate(pattern: str) -> str:
    out: list[str] = []
    i, n = 0, len(pattern)
    while i < n:
        char = pattern[i]
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif char == "*":
            out.append("[^/]*")
            i += 1
        elif char == "?":
            out.append("[^/]")
            i += 1
        elif char == "[" and (close := pattern.find("]", i + 2)) > 0:
            body = pattern[i + 1 : close]
            negate = body[:1] in {"!", "^"}
            body = body[1:] if negate else body
            out.append(f"[{'^' if negate else ''}{body.replace(chr(92), chr(92) * 2)}]")
            i = close + 1
        else:
            out.append(re.escape(char))
            i += 1
    return "".join(out)


@lru_cache(maxsize=256)
def _compiled(pattern: str) -> re.Pattern[str]:
    pattern = pattern.strip().removeprefix("./")
    if pattern.endswith("/"):
        pattern += "**"
    alternatives = "|".join(_translate(p) for p in _expand_braces(pattern))
    return re.compile(f"^(?:{alternatives})$")


def matches(path: str, patterns: list[str]) -> bool:
    """Whether the repo-relative POSIX `path` is owned by any of `patterns`."""
    return any(_compiled(pattern).match(path) for pattern in patterns)
