"""Gate `test-seam-ban` (T043; FR-013; I-A8).

Added code lines of application code under `app_roots` must not branch on test-only
signals: `PYTEST_CURRENT_TEST`, `"pytest" in sys.modules`, `TESTING` / `IS_TEST` flags,
or fake-key sniffing such as `startswith("sk-test")`. Test code (files named
`test_*.py`, `*_test.py`, `conftest.py`, or under a `tests`/`test` directory) is not
application code.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from factory.api import GateContext, GateResult
from factory.gates.drift._common import is_comment_only, verdict
from factory.gates.drift._git import Change

GATE = "test-seam-ban"
SIGNALS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("PYTEST_CURRENT_TEST", re.compile(r"PYTEST_CURRENT_TEST")),
    ("pytest in sys.modules", re.compile(r"""["']pytest["']\s+in\s+sys\.modules""")),
    ("TESTING flag", re.compile(r"(?<!\w)TESTING(?!\w)")),
    ("IS_TEST flag", re.compile(r"(?<!\w)IS_TEST(?!\w)")),
    ("test-key sniffing", re.compile(r"""startswith\(\s*["']sk-test""")),
    ("fake-key sniffing", re.compile(r"""["']fake["']\s+in\s""")),
)
TEST_DIRS = frozenset({"tests", "test"})


def is_test_code(path: str) -> bool:
    pure = PurePosixPath(path)
    name = pure.name
    if name == "conftest.py" or name.startswith("test_") or name.endswith("_test.py"):
        return True
    return any(part in TEST_DIRS for part in pure.parts[:-1])


def run(ctx: GateContext) -> GateResult:
    roots = [root.rstrip("/") + "/" for root in ctx.config.app_roots]
    problems: list[str] = []
    for path, lines in sorted(Change.of(ctx).added_lines.items()):
        if not any(path.startswith(root) for root in roots) or is_test_code(path):
            continue
        for number, line in lines:
            if is_comment_only(line):
                continue
            for name, pattern in SIGNALS:
                if pattern.search(line):
                    problems.append(
                        f"{path}:{number}: application code branches on a test-only signal"
                        f" ({name}): {line.strip()!r}"
                    )
    return verdict(GATE, problems, "no test-only branches in added application code")
