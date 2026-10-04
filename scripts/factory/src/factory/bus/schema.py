"""JSON Schema export for bus messages and bus-file validation (`factory check schema`)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel

from factory import PROJECT_DIR
from factory.bus.models import KIND_MODELS
from factory.bus.store import BusError, list_bus_paths, load_file, parse_bus_text
from factory.config.settings import Settings

SCHEMA_DIR = PROJECT_DIR / "schemas"
SCHEMA_SUFFIX = ".schema.json"


def render_schemas(models: Mapping[str, type[BaseModel]] = KIND_MODELS) -> dict[str, str]:
    """`<kind>.schema.json` filename -> canonical JSON text, one per message kind."""
    return {
        f"{kind}{SCHEMA_SUFFIX}": json.dumps(model.model_json_schema(), indent=2, sort_keys=True)
        + "\n"
        for kind, model in sorted(models.items())
    }


def write_schemas(
    schema_dir: Path = SCHEMA_DIR, models: Mapping[str, type[BaseModel]] = KIND_MODELS
) -> list[Path]:
    schema_dir.mkdir(parents=True, exist_ok=True)
    rendered = render_schemas(models)
    for stale in schema_dir.glob(f"*{SCHEMA_SUFFIX}"):
        if stale.name not in rendered:
            stale.unlink()
    written = []
    for name, text in rendered.items():
        path = schema_dir / name
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written


def stale_schemas(
    schema_dir: Path = SCHEMA_DIR, models: Mapping[str, type[BaseModel]] = KIND_MODELS
) -> list[str]:
    """Problems when committed schemas differ from the models (empty list = fresh)."""
    rendered = render_schemas(models)
    problems = []
    for name, text in rendered.items():
        path = schema_dir / name
        if not path.is_file():
            problems.append(f"{path}: missing (run `factory check schema --write`)")
        elif path.read_text(encoding="utf-8") != text:
            problems.append(f"{path}: stale (run `factory check schema --write`)")
    for path in sorted(schema_dir.glob(f"*{SCHEMA_SUFFIX}")):
        if path.name not in rendered:
            problems.append(f"{path}: no message kind (run `factory check schema --write`)")
    return problems


def validate_message_dir(directory: Path, *, autonomy_horizon_minutes: int) -> list[str]:
    """Validate every YAML file under a loose directory (content only, no layout)."""
    problems = []
    files = sorted(p for p in directory.rglob("*") if p.suffix in (".yaml", ".yml"))
    if not files:
        problems.append(f"{directory}: no message files")
    for path in files:
        try:
            parse_bus_text(
                path.read_text(encoding="utf-8"),
                str(path),
                autonomy_horizon_minutes=autonomy_horizon_minutes,
            )
        except BusError as exc:
            problems.append(str(exc))
    return problems


def validate_bus(repo: Path, settings: Settings, ref: str | None = None) -> list[str]:
    """Validate every bus file in `repo` (schema + layout); collects all problems."""
    problems = []
    for path in list_bus_paths(repo, ref, settings.bus_dir):
        try:
            load_file(repo, ref, path, settings)
        except BusError as exc:
            problems.append(str(exc))
    return problems
