"""Shared pytest fixtures."""

import pytest


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    """Settings is cached; env patches in tests must not see a stale snapshot."""
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
