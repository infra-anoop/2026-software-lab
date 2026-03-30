#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml>=6",
# ]
# ///
"""Validate apps/registry.yaml against the repo (paths, id vs directory name, pyproject names)."""

from __future__ import annotations

import argparse
import copy
import json
import sys
import tomllib
from collections import Counter
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "apps" / "registry.yaml"
REGISTRY_JSON_PATH = REPO_ROOT / "apps" / "registry.json"
SUPPORTED_SCHEMA_VERSIONS = frozenset({1})

_DEFAULT_UV_SYNC_DEV = ["--extra", "dev"]


def _err(msg: str) -> None:
    print(f"registry validation error: {msg}", file=sys.stderr)


def _load_registry() -> dict:
    raw = REGISTRY_PATH.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError("registry root must be a mapping")
    return data


def _project_name_from_pyproject(pyproject_path: Path) -> str:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    try:
        name = data["project"]["name"]
    except KeyError as e:
        raise ValueError(f"{pyproject_path}: missing [project].name") from e
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"{pyproject_path}: [project].name must be a non-empty string")
    return name


def _normalize_for_nix(data: dict) -> dict:
    """Merge defaults (e.g. python.uv) so Nix and CI see a single canonical document."""
    out = copy.deepcopy(data)
    for app in out.get("applications", []):
        if not isinstance(app, dict):
            continue
        py = app.get("python")
        if not isinstance(py, dict):
            continue
        uv = py.get("uv")
        if uv is None:
            py["uv"] = {"sync_dev_args": list(_DEFAULT_UV_SYNC_DEV)}
        elif isinstance(uv, dict) and "sync_dev_args" not in uv:
            uv["sync_dev_args"] = list(_DEFAULT_UV_SYNC_DEV)
    return out


def _json_bytes(data: dict) -> bytes:
    normalized = _normalize_for_nix(data)
    text = json.dumps(normalized, indent=2, ensure_ascii=False) + "\n"
    return text.encode("utf-8")


def validate_registry() -> tuple[dict, list[str]]:
    """Return (data, errors). errors non-empty means validation failed."""
    errors: list[str] = []
    try:
        data = _load_registry()
    except Exception as e:
        return {}, [str(e)]

    ver = data.get("registry_schema_version")
    if ver not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(
            f"unsupported registry_schema_version {ver!r}; "
            f"supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )
        return data, errors

    apps = data.get("applications")
    if not isinstance(apps, list) or not apps:
        errors.append("applications must be a non-empty list")
        return data, errors

    ids: list[str] = []

    raw_ids = [
        a.get("id")
        for a in apps
        if isinstance(a, dict) and isinstance(a.get("id"), str)
    ]
    if len(raw_ids) != len(set(raw_ids)):
        dupes = [k for k, v in Counter(raw_ids).items() if v > 1]
        errors.append(f"duplicate application ids: {dupes}")

    id_universe = set(raw_ids)

    for i, app in enumerate(apps):
        prefix = f"applications[{i}]"
        if not isinstance(app, dict):
            errors.append(f"{prefix}: must be a mapping")
            continue

        app_id = app.get("id")
        if not isinstance(app_id, str) or not app_id.strip():
            errors.append(f"{prefix}: id must be a non-empty string")
            continue

        path_s = app.get("path")
        if not isinstance(path_s, str) or not path_s.strip():
            errors.append(f"{app_id}: path must be a non-empty string")
            continue

        rel = Path(path_s)
        if rel.is_absolute() or ".." in rel.parts:
            errors.append(f"{app_id}: path must be relative with no '..' components: {path_s!r}")
            continue

        expected_apps_prefix = Path("apps") / app_id
        if rel != expected_apps_prefix:
            errors.append(
                f"{app_id}: path must be apps/<id> with id as directory name; "
                f"expected {expected_apps_prefix.as_posix()!r}, got {path_s!r}"
            )
            continue

        dir_name = rel.name
        if dir_name != app_id:
            errors.append(
                f"{app_id}: id must equal directory name (last path segment); got {dir_name!r}"
            )
            continue

        app_dir = REPO_ROOT / rel
        if not app_dir.is_dir():
            errors.append(f"{app_id}: directory missing: {app_dir}")
            continue

        pyproject = app_dir / "pyproject.toml"
        if not pyproject.is_file():
            errors.append(f"{app_id}: missing {pyproject.relative_to(REPO_ROOT)}")
            continue

        py = app.get("python")
        if not isinstance(py, dict):
            errors.append(f"{app_id}: python must be a mapping")
            continue
        declared = py.get("project_name")
        if not isinstance(declared, str) or not declared.strip():
            errors.append(f"{app_id}: python.project_name must be a non-empty string")
            continue

        uv = py.get("uv")
        if uv is None:
            pass  # optional; default applied in _normalize_for_nix
        elif not isinstance(uv, dict):
            errors.append(f"{app_id}: python.uv must be a mapping when present")
        else:
            sda = uv.get("sync_dev_args", _DEFAULT_UV_SYNC_DEV)
            if not isinstance(sda, list) or not sda:
                errors.append(f"{app_id}: python.uv.sync_dev_args must be a non-empty list")
            else:
                for p in sda:
                    if not isinstance(p, str) or not p.strip():
                        errors.append(
                            f"{app_id}: python.uv.sync_dev_args entries must be non-empty strings"
                        )
                        break

        try:
            actual = _project_name_from_pyproject(pyproject)
        except ValueError as e:
            errors.append(str(e))
            continue

        if actual != declared:
            errors.append(
                f"{app_id}: python.project_name {declared!r} does not match "
                f"pyproject.toml [project].name {actual!r}"
            )

        ids.append(app_id)

    for app in apps:
        if not isinstance(app, dict):
            continue
        app_id = app.get("id")
        if not isinstance(app_id, str):
            continue
        ci = app.get("ci")
        if ci is None:
            continue
        if not isinstance(ci, dict):
            errors.append(f"{app_id}: ci must be a mapping when present")
            continue
        deps = ci.get("depends_on")
        if deps is None:
            continue
        if not isinstance(deps, list):
            errors.append(f"{app_id}: ci.depends_on must be a list")
            continue
        for ref in deps:
            if not isinstance(ref, str) or not ref.strip():
                errors.append(f"{app_id}: ci.depends_on entries must be non-empty strings")
                continue
            if ref not in id_universe:
                errors.append(f"{app_id}: ci.depends_on references unknown id {ref!r}")
            if ref == app_id:
                errors.append(f"{app_id}: ci.depends_on must not include itself")

    return data, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate apps/registry.yaml")
    parser.add_argument(
        "--write-json",
        action="store_true",
        help=f"Write canonical {REGISTRY_JSON_PATH.relative_to(REPO_ROOT)} for Nix (after validation).",
    )
    parser.add_argument(
        "--check-json",
        action="store_true",
        help="Fail if registry.json is missing or differs from the canonical JSON for registry.yaml.",
    )
    args = parser.parse_args()

    data, errors = validate_registry()

    for msg in errors:
        _err(msg)

    if errors:
        return 1

    if args.write_json:
        REGISTRY_JSON_PATH.write_bytes(_json_bytes(data))

    if args.check_json:
        if not REGISTRY_JSON_PATH.is_file():
            _err(f"missing {REGISTRY_JSON_PATH.relative_to(REPO_ROOT)}; run with --write-json")
            return 1
        on_disk = REGISTRY_JSON_PATH.read_bytes()
        canonical = _json_bytes(data)
        if on_disk != canonical:
            _err(
                f"{REGISTRY_JSON_PATH.relative_to(REPO_ROOT)} is out of sync with registry.yaml; "
                "run: uv run scripts/validate_app_registry.py --write-json"
            )
            return 1

    print(f"OK — {REGISTRY_PATH.relative_to(REPO_ROOT)} ({len(data.get('applications', []))} application(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
