"""Minimal unit smoke test so pytest and coverage run. Expand with real tests."""

import pytest


def test_import_app() -> None:
    """App package is importable."""
    import app  # noqa: F401

    assert app is not None
