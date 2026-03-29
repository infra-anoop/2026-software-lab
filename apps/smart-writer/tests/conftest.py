"""Shared pytest configuration and fixtures."""

import pytest


@pytest.fixture(autouse=True)
def isolated_db_and_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """No live Supabase calls in unit/integration tests; fresh ``NullRepo`` each test."""
    import app.db.client as db_client
    import app.orchestrator.run as orch

    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    monkeypatch.setenv("LOGFIRE_IGNORE_NO_CONFIG", "1")
    db_client._cached = None  # noqa: SLF001 — reset singleton for deterministic NullRepo
    db_client._initialized = False  # noqa: SLF001
    orch._repo = None  # noqa: SLF001
    yield
    orch._repo = None  # noqa: SLF001
    db_client._cached = None  # noqa: SLF001
    db_client._initialized = False  # noqa: SLF001
