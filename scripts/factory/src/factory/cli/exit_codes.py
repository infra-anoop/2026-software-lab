"""CLI exit codes (contracts/cli.md). Frozen at CP0."""

from typing import Final

OK: Final = 0
"""Success."""
GATE_FAILURE: Final = 1
"""A gate or validation failed."""
REFUSED: Final = 2
"""Refused by policy (cap, open decision, path overlap, ...)."""
USAGE: Final = 3
"""Usage or config error; also every not-yet-implemented command."""
EXTERNAL: Final = 4
"""External failure (git or GitHub unreachable)."""
