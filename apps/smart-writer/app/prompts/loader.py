"""Load versioned prompt program (manifest + role templates) from ``programs/<id>/``."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

import tomllib

from app.prompts.models import PromptParameters
from app.prompts.render import render_prompt_template

_MANIFEST_NAME: Final = "manifest.toml"


@dataclass(frozen=True, slots=True)
class PromptProgramMetadata:
    program_id: str
    version: str
    base_path: Path


def _default_programs_root() -> Path:
    return Path(__file__).resolve().parent / "programs"


def _programs_root() -> Path:
    """Directory containing ``<program_id>/`` folders (package default or ``SMART_WRITER_PROMPTS_DIR``)."""
    override = os.getenv("SMART_WRITER_PROMPTS_DIR")
    if override and str(override).strip():
        return Path(str(override).strip()).expanduser().resolve()
    return _default_programs_root()


def _load_manifest(programs_root: Path, program_id: str) -> tuple[dict[str, Any], Path]:
    base = programs_root / program_id
    manifest_path = base / _MANIFEST_NAME
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Prompt program manifest not found: {manifest_path}")
    with open(manifest_path, "rb") as f:
        data = tomllib.load(f)
    return data, base


def _check_version_pin(manifest_version: str, program_id: str) -> None:
    raw = os.getenv("SMART_WRITER_PROMPT_PROGRAM_VERSION")
    if raw is None or not str(raw).strip():
        return
    want = str(raw).strip()
    if want != manifest_version:
        raise ValueError(
            f"Prompt program version mismatch: SMART_WRITER_PROMPT_PROGRAM_VERSION={want!r} "
            f"but manifest has {manifest_version!r} for program {program_id!r}."
        )


@lru_cache(maxsize=32)
def _get_program_metadata_cached(programs_root_str: str, program_id: str) -> PromptProgramMetadata:
    programs_root = Path(programs_root_str)
    raw, base = _load_manifest(programs_root, program_id)
    vid = str(raw.get("version") or "0.0.0").strip()
    _check_version_pin(vid, program_id)
    return PromptProgramMetadata(program_id=program_id, version=vid, base_path=base)


def clear_prompt_program_caches() -> None:
    """Clear loader caches (tests or hot-reload dev only)."""
    _get_program_metadata_cached.cache_clear()
    _cached_role_template.cache_clear()
    _research_planning_profile_defaults_cached.cache_clear()


def get_program_metadata(program_id: str | None = None) -> PromptProgramMetadata:
    """Resolved program id, version, and base path (program folder)."""
    root = _programs_root()
    pid = (program_id or os.getenv("SMART_WRITER_PROMPT_PROGRAM") or "smart_writer_default").strip()
    return _get_program_metadata_cached(str(root), pid)


def _read_role_file(base: Path, role: str) -> str:
    path = base / f"{role}.txt"
    if not path.is_file():
        raise FileNotFoundError(f"Missing role template: {path}")
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=128)
def _cached_role_template(programs_root_str: str, program_id: str, version: str, role: str) -> str:
    """Cache templates keyed by root, program, manifest version, and role."""
    _ = version  # bust cache when manifest version bumps
    programs_root = Path(programs_root_str)
    base = programs_root / program_id
    return _read_role_file(base, role)


def get_role_template(role: str, *, program_id: str | None = None) -> str:
    """Raw template text for ``role`` (decoder, rubric, planner, writer, assessor, grounding, …)."""
    meta = get_program_metadata(program_id)
    root_str = str(meta.base_path.parent)
    return _cached_role_template(root_str, meta.program_id, meta.version, role)


def _safe_profile_segment(profile_id: str) -> str | None:
    s = profile_id.strip()
    if not s or ".." in s or "/" in s or "\\" in s:
        return None
    return s


def _optional_profile_suffix(base: Path, profile_id: str | None, params: PromptParameters) -> str:
    if not profile_id or not str(profile_id).strip():
        return ""
    seg = _safe_profile_segment(str(profile_id))
    if seg is None:
        return ""
    prof = (base / "profiles" / f"{seg}.txt").resolve()
    try:
        prof.relative_to(base.resolve())
    except ValueError:
        return ""
    if not prof.is_file():
        return ""
    return "\n" + render_prompt_template(prof.read_text(encoding="utf-8"), params)


def render_system_prompt(
    role: str,
    params: PromptParameters,
    *,
    program_id: str | None = None,
    profile_id: str | None = None,
) -> str:
    """Full system prompt for ``role``: base template + optional profile fragment."""
    meta = get_program_metadata(program_id)
    root_str = str(meta.base_path.parent)
    base_text = _cached_role_template(root_str, meta.program_id, meta.version, role)
    rendered = render_prompt_template(base_text, params)
    rendered += _optional_profile_suffix(meta.base_path, profile_id, params)
    return rendered


def _env_overrides() -> dict[str, str]:
    """Optional per-field env overrides (ops tuning without API)."""
    mapping = [
        ("SMART_WRITER_PROMPT_AUDIENCE", "audience"),
        ("SMART_WRITER_PROMPT_WRITING_REGISTER", "writing_register"),
        ("SMART_WRITER_PROMPT_LENGTH_TARGET", "length_target"),
        ("SMART_WRITER_PROMPT_RISK_TOLERANCE", "risk_tolerance"),
        ("SMART_WRITER_PROMPT_FORMALITY", "formality"),
    ]
    out: dict[str, str] = {}
    for env_name, field in mapping:
        raw = os.getenv(env_name)
        if raw is not None and str(raw).strip():
            out[field] = str(raw).strip()
    return out


def resolve_prompt_parameters_for_run(initial_input: dict[str, Any]) -> PromptParameters:
    """Merge defaults, request ``prompt_parameters``, and env overrides."""
    base = PromptParameters()
    merged: dict[str, Any] = base.model_dump()
    raw = initial_input.get("prompt_parameters")
    if isinstance(raw, dict):
        for k, v in raw.items():
            if k in PromptParameters.model_fields and v is not None:
                merged[k] = v
    merged.update(_env_overrides())
    return PromptParameters.model_validate(merged)


def default_prompt_profile_id(initial_input: dict[str, Any]) -> str | None:
    """Profile id: request body, else ``SMART_WRITER_PROMPT_PROFILE`` env."""
    rid = initial_input.get("prompt_profile_id")
    if isinstance(rid, str) and rid.strip():
        return rid.strip()
    env = os.getenv("SMART_WRITER_PROMPT_PROFILE")
    return env.strip() if env and str(env).strip() else None


def _env_bool_default(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    s = str(raw).strip().lower()
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off"):
        return False
    return default


@lru_cache(maxsize=32)
def _research_planning_profile_defaults_cached(programs_root_str: str, program_id: str) -> dict[str, bool]:
    programs_root = Path(programs_root_str)
    raw, _ = _load_manifest(programs_root, program_id)
    rp = raw.get("research_planning")
    if not isinstance(rp, dict):
        return {}
    defaults = rp.get("profile_defaults")
    if not isinstance(defaults, dict):
        return {}
    out: dict[str, bool] = {}
    for k, v in defaults.items():
        if not isinstance(k, str):
            continue
        key = k.strip()
        if not key:
            continue
        if isinstance(v, bool):
            out[key] = v
    return out


def get_research_planning_default_for_profile(
    program_id: str | None,
    prompt_profile_id: str | None,
) -> bool:
    """Default planning on/off when the client omits explicit ``research_planning_*`` (§9.1)."""
    meta = get_program_metadata(program_id)
    root_str = str(meta.base_path.parent)
    table = _research_planning_profile_defaults_cached(root_str, meta.program_id)
    if prompt_profile_id and str(prompt_profile_id).strip():
        pid = str(prompt_profile_id).strip()
        if pid in table:
            return table[pid]
    return _env_bool_default("SMART_WRITER_RESEARCH_PLANNING_DEFAULT", True)


def resolve_research_planning_enabled(
    *,
    requested: bool | None,
    program_id: str | None,
    prompt_profile_id: str | None,
) -> bool:
    """Explicit request wins; else manifest profile default; else env (§9.2)."""
    if requested is not None:
        return requested
    return get_research_planning_default_for_profile(program_id, prompt_profile_id)
