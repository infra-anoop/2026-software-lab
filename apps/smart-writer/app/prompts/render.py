"""str.format-style rendering with safe defaults for missing placeholders."""

from __future__ import annotations

from app.prompts.models import PromptParameters


class _FormatDefaults(dict[str, str]):
    """Mapping for str.format_map: unknown keys become empty strings."""

    def __missing__(self, key: str) -> str:  # type: ignore[override]
        return ""


def render_prompt_template(template: str, params: PromptParameters) -> str:
    """Render ``template`` with ``params``. Extra ``{placeholders}`` without a value become ``\"\"``."""
    mapping = _FormatDefaults()
    mapping.update({k: str(v) for k, v in params.model_dump().items()})
    return template.format_map(mapping)
