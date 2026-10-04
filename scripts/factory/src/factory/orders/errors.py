"""Outcomes the order commands report (the CLI maps them to exit codes)."""

from __future__ import annotations


class OrderError(Exception):
    """Base: `message` is plain language for the person or agent running the command."""

    def __init__(
        self, message: str, *, details: object = None, stdout: list[str] | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
        self.stdout = stdout or []


class Refused(OrderError):
    """The command was understood and refused (exit 2)."""


class Usage(OrderError):
    """The command was called wrongly (exit 3)."""


class External(OrderError):
    """git remote or GitHub failed (exit 4)."""
