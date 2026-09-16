"""Reset settings cache between tests."""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.store import STORE


@pytest.fixture(autouse=True)
def _reset_settings_and_store() -> None:
    get_settings.cache_clear()
    STORE.reset()
    yield
    STORE.reset()
    get_settings.cache_clear()
