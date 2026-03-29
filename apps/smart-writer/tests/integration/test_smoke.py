"""Minimal integration smoke test. Expand with HTTP/CLI tests."""

def test_app_module_importable() -> None:
    """App entrypoints are importable (no env required)."""
    import app.entrypoints.http  # noqa: F401

    assert app.entrypoints.http is not None
