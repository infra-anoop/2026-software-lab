#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml>=6",
# ]
# ///
"""Validate deploy/secrets/schema.yaml against registry + Settings catalogs (A20/A25).

No live vault. Fail-closed on unknown names or missing deploy-enabled apps / LOGFIRE_TOKEN.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import validate_deploy_env as vde  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "deploy" / "secrets" / "schema.yaml"
REQUIRED_PROVIDER = "infisical_cloud"
MUST_HAVE_SECRET = "LOGFIRE_TOKEN"


def _err(msg: str) -> None:
    print(f"secrets schema error: {msg}", file=sys.stderr)


def _as_mapping(raw: object, label: str) -> dict[str, Any] | str:
    if not isinstance(raw, dict):
        return f"{label} must be a mapping"
    return raw


def _secret_entries(raw: object, label: str) -> list[dict[str, Any]] | str:
    if not isinstance(raw, list) or not raw:
        return f"{label} must be a non-empty list"
    out: list[dict[str, Any]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            return f"{label}[{i}] must be a mapping"
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            return f"{label}[{i}].name must be a non-empty string"
        if "required" not in item or not isinstance(item["required"], bool):
            return f"{label}[{i}].required must be a bool"
        ref = item.get("vault_ref")
        if not isinstance(ref, dict):
            return f"{label}[{i}].vault_ref must be a mapping"
        for key in ("project", "env", "path", "key"):
            val = ref.get(key)
            if not isinstance(val, str) or not val.strip():
                return f"{label}[{i}].vault_ref.{key} must be a non-empty string"
        out.append(item)
    return out


def validate_schema(
    schema: dict[str, Any],
    *,
    enabled_app_ids: list[str],
    catalogs: dict[str, tuple[tuple[str, ...], tuple[str, ...]]],
    railway_envs_by_app: dict[str, set[str]],
) -> list[str]:
    errors: list[str] = []

    if schema.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    vault = _as_mapping(schema.get("vault"), "vault")
    if isinstance(vault, str):
        errors.append(vault)
    elif vault.get("provider") != REQUIRED_PROVIDER:
        errors.append(f"vault.provider must be {REQUIRED_PROVIDER!r} (locked A20)")

    apps_block = _as_mapping(schema.get("applications"), "applications")
    if isinstance(apps_block, str):
        return [apps_block, *errors]

    for app_id in enabled_app_ids:
        if app_id not in apps_block:
            errors.append(f"missing applications.{app_id} (deploy.enabled in registry)")
            continue
        app_entry = _as_mapping(apps_block[app_id], f"applications.{app_id}")
        if isinstance(app_entry, str):
            errors.append(app_entry)
            continue
        envs = _as_mapping(app_entry.get("environments"), f"applications.{app_id}.environments")
        if isinstance(envs, str):
            errors.append(envs)
            continue

        required_code, all_code = catalogs[app_id]
        all_set = frozenset(all_code)
        required_set = frozenset(required_code)
        expected_envs = railway_envs_by_app.get(app_id, set())

        for env_name in sorted(expected_envs):
            if env_name not in envs:
                errors.append(
                    f"applications.{app_id}.environments missing {env_name!r} "
                    f"(deploy/railway/{env_name}/{app_id}.yml exists)"
                )

        for env_name, env_body in sorted(envs.items()):
            label = f"applications.{app_id}.environments.{env_name}"
            env_map = _as_mapping(env_body, label)
            if isinstance(env_map, str):
                errors.append(env_map)
                continue
            secrets = _secret_entries(env_map.get("secrets"), f"{label}.secrets")
            if isinstance(secrets, str):
                errors.append(secrets)
                continue

            names = [str(s["name"]) for s in secrets]
            if len(names) != len(set(names)):
                errors.append(f"{label}: duplicate secret names")

            unknown = sorted(set(names) - all_set)
            if unknown:
                errors.append(f"{label}: names not in Settings ALL_ENV_NAMES: {unknown}")

            present = set(names)
            missing_req = sorted(required_set - present)
            if missing_req:
                errors.append(f"{label}: missing Settings REQUIRED names: {missing_req}")

            for s in secrets:
                if s["name"] in required_set and s["required"] is not True:
                    errors.append(f"{label}: {s['name']} must have required: true")

            if MUST_HAVE_SECRET not in present:
                errors.append(f"{label}: missing {MUST_HAVE_SECRET} (A25)")
            elif MUST_HAVE_SECRET not in all_set:
                errors.append(f"{label}: {MUST_HAVE_SECRET} not in Settings catalog")

    mystery_apps = sorted(set(apps_block) - set(enabled_app_ids))
    if mystery_apps:
        errors.append(f"applications has non-deploy-enabled ids: {mystery_apps}")

    return errors


def railway_env_names_by_app(enabled_app_ids: list[str]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {app_id: set() for app_id in enabled_app_ids}
    for app_id in enabled_app_ids:
        for yml in vde.railway_yaml_paths(app_id):
            out[app_id].add(yml.parent.name)
    return out


def load_catalogs(enabled_app_ids: list[str], registry: dict[str, Any]) -> dict[str, tuple[tuple[str, ...], tuple[str, ...]]]:
    apps_by_id = {
        a["id"]: a
        for a in registry.get("applications", [])
        if isinstance(a, dict) and isinstance(a.get("id"), str)
    }
    catalogs: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {}
    for app_id in enabled_app_ids:
        app = apps_by_id[app_id]
        path = app.get("path")
        if not isinstance(path, str):
            raise ValueError(f"registry app {app_id} missing path")
        config_py = REPO_ROOT / path / "app" / "config.py"
        catalogs[app_id] = vde.parse_env_catalog(config_py)
    return catalogs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--schema",
        type=Path,
        default=SCHEMA_PATH,
        help="Path to secrets schema YAML",
    )
    args = parser.parse_args(argv)

    if not args.schema.is_file():
        _err(f"missing schema file: {args.schema}")
        return 1

    registry = yaml.safe_load(vde.REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(registry, dict):
        _err("registry.yaml must be a mapping")
        return 1

    enabled = vde.collect_enabled_app_ids(registry)
    if not enabled:
        _err("no deploy.enabled applications in registry")
        return 1

    try:
        catalogs = load_catalogs(enabled, registry)
    except (OSError, ValueError, SyntaxError) as exc:
        _err(str(exc))
        return 1

    raw = yaml.safe_load(args.schema.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        _err("schema root must be a mapping")
        return 1

    errors = validate_schema(
        raw,
        enabled_app_ids=enabled,
        catalogs=catalogs,
        railway_envs_by_app=railway_env_names_by_app(enabled),
    )
    if errors:
        for msg in errors:
            _err(msg)
        return 1

    print(f"secrets schema OK ({args.schema.relative_to(REPO_ROOT)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
