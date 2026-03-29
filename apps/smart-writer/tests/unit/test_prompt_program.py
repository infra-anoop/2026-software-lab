"""Prompt program: rendering, resolution, env pins, and optional prompts dir (no LLM)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from app.prompts.loader import (
    clear_prompt_program_caches,
    default_prompt_profile_id,
    get_program_metadata,
    render_system_prompt,
    resolve_prompt_parameters_for_run,
)
from app.prompts.models import PromptParameters
from app.prompts.render import render_prompt_template


@pytest.fixture(autouse=True)
def _clear_prompt_caches() -> None:
    clear_prompt_program_caches()
    yield
    clear_prompt_program_caches()


def test_render_prompt_template_inserts_fields() -> None:
    t = "A={audience} R={writing_register}"
    p = PromptParameters(audience="kids", writing_register="casual")
    assert render_prompt_template(t, p) == "A=kids R=casual"


def test_render_prompt_template_unknown_placeholder_empty() -> None:
    """Unknown {keys} become empty via format_map defaults."""
    t = "x={not_a_field}"
    p = PromptParameters()
    assert render_prompt_template(t, p) == "x="


def test_resolve_prompt_parameters_merges_request() -> None:
    out = resolve_prompt_parameters_for_run(
        {"prompt_parameters": {"audience": "investors", "writing_register": "formal"}}
    )
    assert out.audience == "investors"
    assert out.writing_register == "formal"
    assert out.length_target == "medium"


def test_resolve_prompt_parameters_env_overrides_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_PROMPT_AUDIENCE", "ops_audience")
    out = resolve_prompt_parameters_for_run({"prompt_parameters": {"audience": "from_request"}})
    assert out.audience == "ops_audience"


def test_get_program_metadata_default() -> None:
    meta = get_program_metadata()
    assert meta.program_id == "smart_writer_default"
    assert meta.version == "1.1.0"
    assert (meta.base_path / "writer.txt").is_file()


def test_render_system_prompt_writer_includes_defaults() -> None:
    text = render_system_prompt("writer", PromptParameters(audience="teachers"))
    assert "teachers" in text
    assert "professional" in text


@pytest.mark.parametrize(
    "role",
    ["decoder", "rubric", "planner", "writer", "assessor", "grounding", "refresh_rubric_anchors"],
)
def test_all_role_templates_load(role: str) -> None:
    s = render_system_prompt(role, PromptParameters())
    assert len(s) > 20


def test_default_prompt_profile_id_from_request() -> None:
    assert default_prompt_profile_id({"prompt_profile_id": "  grant  "}) == "grant"


def test_default_prompt_profile_id_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_PROMPT_PROFILE", "memo_executive")
    assert default_prompt_profile_id({}) == "memo_executive"


def test_default_prompt_profile_id_request_wins_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_PROMPT_PROFILE", "env_profile")
    assert default_prompt_profile_id({"prompt_profile_id": "req_profile"}) == "req_profile"


def test_prompt_program_version_pin_match(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_PROMPT_PROGRAM_VERSION", "1.1.0")
    meta = get_program_metadata()
    assert meta.version == "1.1.0"


def test_prompt_program_version_pin_mismatch_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_WRITER_PROMPT_PROGRAM_VERSION", "9.9.9")
    with pytest.raises(ValueError, match="version mismatch"):
        get_program_metadata()


def test_smart_writer_prompt_program_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Alternate program id under a custom prompts root."""
    prog = tmp_path / "alt_prog"
    prog.mkdir(parents=True)
    (prog / "manifest.toml").write_text(
        'program_id = "alt_prog"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    for role in ("decoder", "rubric", "planner", "writer", "assessor", "grounding", "refresh_rubric_anchors"):
        (prog / f"{role}.txt").write_text(
            f"You are {role}. Audience {{audience}}.\n", encoding="utf-8"
        )
    monkeypatch.setenv("SMART_WRITER_PROMPTS_DIR", str(tmp_path))
    monkeypatch.setenv("SMART_WRITER_PROMPT_PROGRAM", "alt_prog")
    clear_prompt_program_caches()
    meta = get_program_metadata()
    assert meta.program_id == "alt_prog"
    assert meta.version == "0.1.0"
    text = render_system_prompt("writer", PromptParameters(audience="X"))
    assert "writer" in text
    assert "X" in text


def test_profile_suffix_appended(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prog = tmp_path / "p1"
    prog.mkdir(parents=True)
    (prog / "manifest.toml").write_text('program_id = "p1"\nversion = "1.0.0"\n', encoding="utf-8")
    (prog / "writer.txt").write_text("BASE {audience}\n", encoding="utf-8")
    prof_dir = prog / "profiles"
    prof_dir.mkdir()
    (prof_dir / "extra.txt").write_text("SUFFIX_LINE {length_target}", encoding="utf-8")
    monkeypatch.setenv("SMART_WRITER_PROMPTS_DIR", str(tmp_path))
    monkeypatch.setenv("SMART_WRITER_PROMPT_PROGRAM", "p1")
    clear_prompt_program_caches()
    text = render_system_prompt("writer", PromptParameters(audience="A", length_target="long"), profile_id="extra")
    assert "BASE A" in text
    assert "SUFFIX_LINE long" in text


def test_profile_path_traversal_ignored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prog = tmp_path / "safe"
    prog.mkdir(parents=True)
    (prog / "manifest.toml").write_text('program_id = "safe"\nversion = "1.0.0"\n', encoding="utf-8")
    (prog / "writer.txt").write_text("ONLY_BASE\n", encoding="utf-8")
    monkeypatch.setenv("SMART_WRITER_PROMPTS_DIR", str(tmp_path))
    monkeypatch.setenv("SMART_WRITER_PROMPT_PROGRAM", "safe")
    clear_prompt_program_caches()
    text = render_system_prompt("writer", PromptParameters(), profile_id="../evil")
    assert text.strip() == "ONLY_BASE"


@patch.dict(os.environ, {"SMART_WRITER_PROMPT_PROGRAM_VERSION": ""}, clear=False)
def test_empty_version_pin_skipped() -> None:
    """Empty env pin must not raise (treat as unset)."""
    clear_prompt_program_caches()
    meta = get_program_metadata()
    assert meta.version == "1.1.0"
