"""Manifest + env resolution for research planning defaults."""

import pytest

from app.prompts.loader import (
    clear_prompt_program_caches,
    get_research_planning_default_for_profile,
    resolve_research_planning_enabled,
)


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    clear_prompt_program_caches()
    yield
    clear_prompt_program_caches()


def test_resolve_explicit_requested_wins_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_RESEARCH_PLANNING_DEFAULT", "true")
    assert (
        resolve_research_planning_enabled(
            requested=False,
            program_id="smart_writer_default",
            prompt_profile_id="grant",
        )
        is False
    )


def test_profile_grant_default_true() -> None:
    assert get_research_planning_default_for_profile("smart_writer_default", "grant") is True


def test_profile_short_email_default_false() -> None:
    assert get_research_planning_default_for_profile("smart_writer_default", "short_email") is False


def test_unknown_profile_uses_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_RESEARCH_PLANNING_DEFAULT", "false")
    assert get_research_planning_default_for_profile("smart_writer_default", "unknown_profile_xyz") is False


def test_unknown_profile_env_unset_defaults_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SMART_WRITER_RESEARCH_PLANNING_DEFAULT", raising=False)
    assert get_research_planning_default_for_profile("smart_writer_default", "unknown_profile_xyz") is True


def test_resolve_omitted_uses_profile() -> None:
    assert (
        resolve_research_planning_enabled(
            requested=None,
            program_id="smart_writer_default",
            prompt_profile_id="short_email",
        )
        is False
    )
