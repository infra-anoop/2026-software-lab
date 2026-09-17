"""Load versioned prompt program files from disk."""

from __future__ import annotations

from pathlib import Path

_PROGRAMS = Path(__file__).resolve().parent / "programs"


def program_dir(program_id: str) -> Path:
    """Return the directory for a prompt program id."""
    return _PROGRAMS / program_id


def load_role_prompt(program_id: str, role: str) -> str:
    """Read ``{role}.txt`` from the program directory."""
    path = program_dir(program_id) / f"{role}.txt"
    return path.read_text(encoding="utf-8")
