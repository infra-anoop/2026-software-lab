"""Unit: Logfire configure is a noop when LOGFIRE_TOKEN is unset."""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.obs import configure_observability, empty_usage, reset_observability_for_tests


@pytest.fixture(autouse=True)
def _reset_obs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOGFIRE_TOKEN", raising=False)
    get_settings.cache_clear()
    reset_observability_for_tests()
    yield
    reset_observability_for_tests()
    get_settings.cache_clear()


def test_configure_noop_without_token() -> None:
    assert configure_observability() is False
    # Second call stays latched / still False without a token.
    assert configure_observability() is False


def test_empty_usage_has_required_keys() -> None:
    usage = empty_usage()
    assert usage["input_tokens"] is None
    assert usage["output_tokens"] is None
    assert usage["estimated_cost_usd"] is None
