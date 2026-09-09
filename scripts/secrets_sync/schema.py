"""Load secret entries from deploy/secrets/schema.yaml (A20)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .protocols import VaultRef

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA_PATH = REPO_ROOT / "deploy" / "secrets" / "schema.yaml"


@dataclass(frozen=True)
class SecretEntry:
    name: str
    required: bool
    vault_ref: VaultRef


def load_schema(path: Path = DEFAULT_SCHEMA_PATH) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"schema root must be a mapping: {path}")
    return raw


def load_secret_entries(
    app_id: str,
    environment: str,
    *,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
) -> list[SecretEntry]:
    """Return ordered secret entries for app×env; fail closed if missing."""
    schema = load_schema(schema_path)
    apps = schema.get("applications")
    if not isinstance(apps, dict) or app_id not in apps:
        raise ValueError(f"app_id {app_id!r} not in secrets schema")
    app = apps[app_id]
    if not isinstance(app, dict):
        raise ValueError(f"applications.{app_id} must be a mapping")
    envs = app.get("environments")
    if not isinstance(envs, dict) or environment not in envs:
        raise ValueError(f"environment {environment!r} not in schema for {app_id}")
    env_body = envs[environment]
    if not isinstance(env_body, dict):
        raise ValueError(f"environments.{environment} must be a mapping")
    secrets = env_body.get("secrets")
    if not isinstance(secrets, list) or not secrets:
        raise ValueError(f"no secrets listed for {app_id}/{environment}")

    out: list[SecretEntry] = []
    seen: set[str] = set()
    for i, item in enumerate(secrets):
        if not isinstance(item, dict):
            raise ValueError(f"secrets[{i}] must be a mapping")
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"secrets[{i}].name invalid")
        if name in seen:
            raise ValueError(f"duplicate secret name {name!r}")
        seen.add(name)
        required = item.get("required")
        if not isinstance(required, bool):
            raise ValueError(f"secrets[{i}].required must be bool")
        ref_raw = item.get("vault_ref")
        if not isinstance(ref_raw, dict):
            raise ValueError(f"secrets[{i}].vault_ref must be a mapping")
        ref: VaultRef = {
            "project": str(ref_raw["project"]),
            "env": str(ref_raw["env"]),
            "path": str(ref_raw["path"]),
            "key": str(ref_raw["key"]),
        }
        out.append(SecretEntry(name=name, required=required, vault_ref=ref))
    return out


def assert_names_in_schema(names: set[str], entries: list[SecretEntry]) -> None:
    """Fail closed if any name is not in the schema entry list."""
    allowed = {e.name for e in entries}
    mystery = sorted(names - allowed)
    if mystery:
        raise ValueError(f"names not in A20 schema for this app/env: {mystery}")
