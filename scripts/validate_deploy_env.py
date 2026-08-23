#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml>=6",
# ]
# ///
"""Validate Railway env checklists against each app's Settings catalog (names only).

Rules (deploy.enabled apps):
  - Each existing ``deploy/railway/<env>/<app_id>.yml`` has a non-empty ``env.required``.
  - YAML ``env.required`` == Settings ``REQUIRED_ENV_NAMES`` (bidirectional).
  - YAML ``env.optional`` ⊆ Settings ``ALL_ENV_NAMES``.
  - ``.env.example`` mentions every name in ``ALL_ENV_NAMES``.
  - ``PORT`` must not appear in the checklist.
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "apps" / "registry.yaml"
RAILWAY_ROOT = REPO_ROOT / "deploy" / "railway"
FORBIDDEN_CHECKLIST_NAMES = frozenset({"PORT"})


def _err(msg: str) -> None:
    print(f"deploy env validation error: {msg}", file=sys.stderr)


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _string_tuple_assign(tree: ast.AST, name: str) -> tuple[str, ...]:
    """Extract ``NAME = ("A", "B")`` or annotated assign from a module AST."""
    for node in tree.body:
        target_id: str | None = None
        value: ast.AST | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            t0 = node.targets[0]
            if isinstance(t0, ast.Name):
                target_id, value = t0.id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_id, value = node.target.id, node.value
        if target_id != name or value is None:
            continue
        data = ast.literal_eval(value)
        if not isinstance(data, tuple) or not all(isinstance(x, str) for x in data):
            raise ValueError(f"{name} must be a tuple of strings")
        return data
    raise ValueError(f"{name} not found as a string-literal tuple")


def parse_env_catalog(config_py: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    tree = ast.parse(config_py.read_text(encoding="utf-8"), filename=str(config_py))
    required = _string_tuple_assign(tree, "REQUIRED_ENV_NAMES")
    all_names = _string_tuple_assign(tree, "ALL_ENV_NAMES")
    return required, all_names


def _as_name_list(raw: object, *, label: str) -> list[str] | str:
    if raw is None:
        return []
    if not isinstance(raw, list):
        return f"{label} must be a list"
    names: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            return f"{label} entries must be non-empty strings"
        names.append(item.strip())
    return names


def validate_env_block(
    *,
    yaml_path: Path,
    required_code: tuple[str, ...],
    all_code: frozenset[str],
    block: dict,
) -> list[str]:
    errors: list[str] = []
    rel = _rel(yaml_path)
    required = _as_name_list(block.get("required"), label=f"{rel} env.required")
    if isinstance(required, str):
        return [required]
    optional = _as_name_list(block.get("optional"), label=f"{rel} env.optional")
    if isinstance(optional, str):
        return [optional]

    if not required:
        errors.append(f"{rel}: env.required is missing or empty")
        return errors

    req_set = set(required)
    code_req = set(required_code)
    if req_set != code_req:
        missing = sorted(code_req - req_set)
        extra = sorted(req_set - code_req)
        if missing:
            errors.append(f"{rel}: env.required missing {missing} (declared required in Settings)")
        if extra:
            errors.append(f"{rel}: env.required has unknown/not-required names {extra}")

    opt_set = set(optional)
    mystery = sorted(opt_set - all_code)
    if mystery:
        errors.append(f"{rel}: env.optional names not in Settings catalog: {mystery}")

    forbidden = sorted((req_set | opt_set) & FORBIDDEN_CHECKLIST_NAMES)
    if forbidden:
        errors.append(f"{rel}: do not list platform-injected names {forbidden}")

    overlap = sorted(req_set & opt_set)
    if overlap:
        errors.append(f"{rel}: names in both required and optional: {overlap}")

    return errors


def _deploy_enabled(app: dict, default_enabled: bool) -> bool:
    deploy = app.get("deploy")
    if deploy is None:
        return default_enabled
    if not isinstance(deploy, dict):
        return default_enabled
    if "enabled" not in deploy:
        return default_enabled
    return bool(deploy["enabled"])


def collect_enabled_app_ids(registry: dict) -> list[str]:
    defaults = registry.get("defaults") if isinstance(registry.get("defaults"), dict) else {}
    default_deploy = defaults.get("deploy") if isinstance(defaults.get("deploy"), dict) else {}
    default_enabled = bool(default_deploy.get("enabled", False))
    apps = registry.get("applications")
    if not isinstance(apps, list):
        return []
    ids: list[str] = []
    for app in apps:
        if not isinstance(app, dict):
            continue
        app_id = app.get("id")
        if not isinstance(app_id, str) or not app_id.strip():
            continue
        if _deploy_enabled(app, default_enabled):
            ids.append(app_id.strip())
    return ids


def railway_yaml_paths(app_id: str) -> list[Path]:
    paths: list[Path] = []
    if not RAILWAY_ROOT.is_dir():
        return paths
    for env_dir in sorted(p for p in RAILWAY_ROOT.iterdir() if p.is_dir()):
        yml = env_dir / f"{app_id}.yml"
        if yml.is_file():
            paths.append(yml)
    return paths


def validate_example_file(example: Path, all_names: tuple[str, ...]) -> list[str]:
    errors: list[str] = []
    rel = _rel(example)
    if not example.is_file():
        return [f"missing {rel}"]
    text = example.read_text(encoding="utf-8")
    missing = [n for n in all_names if n not in text]
    if missing:
        errors.append(f"{rel} does not document Settings names: {missing}")
    return errors


def validate_repo(repo_root: Path | None = None) -> list[str]:
    root = repo_root or REPO_ROOT
    errors: list[str] = []
    registry_path = root / "apps" / "registry.yaml"
    if not registry_path.is_file():
        return [f"missing {registry_path.relative_to(root)}"]
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    if not isinstance(registry, dict):
        return ["apps/registry.yaml root must be a mapping"]

    ids = collect_enabled_app_ids(registry)
    if not ids:
        errors.append("no deploy.enabled applications found in apps/registry.yaml")
        return errors

    for app_id in ids:
        config_py = root / "apps" / app_id / "app" / "config.py"
        if not config_py.is_file():
            errors.append(f"{app_id}: missing apps/{app_id}/app/config.py")
            continue
        try:
            required, all_names = parse_env_catalog(config_py)
        except (ValueError, SyntaxError) as e:
            errors.append(f"{app_id}: {e}")
            continue
        all_set = frozenset(all_names)
        if set(required) - all_set:
            errors.append(f"{app_id}: REQUIRED_ENV_NAMES not subset of ALL_ENV_NAMES")

        example = root / "apps" / app_id / ".env.example"
        errors.extend(validate_example_file(example, all_names))

        ymls = railway_yaml_paths(app_id)
        prod = root / "deploy" / "railway" / "production" / f"{app_id}.yml"
        if not prod.is_file():
            errors.append(f"{app_id}: missing deploy/railway/production/{app_id}.yml")
        for yml in ymls:
            data = yaml.safe_load(yml.read_text(encoding="utf-8")) or {}
            if not isinstance(data, dict):
                errors.append(f"{yml.relative_to(root)}: root must be a mapping")
                continue
            env_block = data.get("env")
            if not isinstance(env_block, dict):
                errors.append(f"{yml.relative_to(root)}: missing env mapping (required/optional lists)")
                continue
            errors.extend(
                validate_env_block(
                    yaml_path=yml,
                    required_code=required,
                    all_code=all_set,
                    block=env_block,
                )
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Railway env checklists vs Settings catalogs")
    parser.parse_args()
    errors = validate_repo()
    for msg in errors:
        _err(msg)
    if errors:
        return 1
    print("OK — deploy env checklists match Settings catalogs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
