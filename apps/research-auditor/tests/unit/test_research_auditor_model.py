"""Research Auditor agents read RESEARCH_AUDITOR_MODEL from Settings (no live LLM)."""

from pathlib import Path

from app.config import DEFAULT_RESEARCH_AUDITOR_MODEL, get_settings

_AGENTS = Path(__file__).resolve().parents[2] / "app" / "agents"


def test_settings_model_default() -> None:
    assert get_settings().research_auditor_model == DEFAULT_RESEARCH_AUDITOR_MODEL
    assert DEFAULT_RESEARCH_AUDITOR_MODEL == "openai:gpt-4o"


def test_agent_constructors_read_settings() -> None:
    """Constructors must take the Settings model id; do not hardcode openai:gpt-4o."""
    for filename in ("researcher.py", "critic.py"):
        text = (_AGENTS / filename).read_text(encoding="utf-8")
        assert "get_settings().research_auditor_model" in text
        assert "openai:gpt-4o" not in text
