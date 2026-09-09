#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "httpx>=0.27",
#   "pyyaml>=6",
# ]
# ///
"""Read-only bootstrap verify: Railway footprint + required env *names* (A24).

Never creates resources or upserts secrets. Never prints secret values.

Checks:
  1. Project / service / environment from deploy/railway/<env>/<app_id>.yml exist
  2. Required names present on the service for that environment —
     union of YAML env.required and A20 schema required: true

Modes:
  --dry-run  print planned checks from git only (no Railway)
  (default)  live GraphQL verify (requires RAILWAY_WORKSPACE_TOKEN or RAILWAY_TOKEN)

Exit codes: 0 ok; 2 footprint missing; 1 other failures.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import httpx
import yaml

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import railway_graphql as rgql  # noqa: E402
from secrets_sync.schema import load_secret_entries  # noqa: E402
from secrets_sync.target_railway import (  # noqa: E402
    FootprintMissingError,
    RailwayRuntimeTarget,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _err(msg: str) -> None:
    print(f"verify_runtime_bootstrap error: {msg}", file=sys.stderr)


def select_railway_token(environ: Mapping[str, str]) -> str | None:
    return rgql.select_railway_token(environ)


def load_deploy_yaml(
    app_id: str,
    environment: str,
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    path = repo_root / "deploy" / "railway" / environment / f"{app_id}.yml"
    if not path.is_file():
        raise FileNotFoundError(
            f"missing config: {path.relative_to(repo_root)} "
            f"(add deploy/railway/{environment}/{app_id}.yml — same as deploy)"
        )
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path.relative_to(repo_root)}: root must be a mapping")
    return raw


def yaml_required_names(deploy: dict[str, Any]) -> frozenset[str]:
    env_block = deploy.get("env")
    if not isinstance(env_block, dict):
        return frozenset()
    required = env_block.get("required")
    if not isinstance(required, list):
        return frozenset()
    return frozenset(
        item.strip()
        for item in required
        if isinstance(item, str) and item.strip()
    )


def schema_required_names(
    app_id: str,
    environment: str,
    *,
    repo_root: Path = REPO_ROOT,
) -> frozenset[str]:
    schema_path = repo_root / "deploy" / "secrets" / "schema.yaml"
    entries = load_secret_entries(app_id, environment, schema_path=schema_path)
    return frozenset(e.name for e in entries if e.required)


def required_secret_names(
    app_id: str,
    environment: str,
    *,
    repo_root: Path = REPO_ROOT,
) -> frozenset[str]:
    """Union of deploy YAML env.required and schema required: true."""
    deploy = load_deploy_yaml(app_id, environment, repo_root=repo_root)
    return yaml_required_names(deploy) | schema_required_names(
        app_id, environment, repo_root=repo_root
    )


def footprint_names(deploy: dict[str, Any]) -> tuple[str, str, str]:
    railway = deploy.get("railway")
    if not isinstance(railway, dict):
        raise ValueError("missing railway mapping")

    def _req(key: str) -> str:
        val = railway.get(key)
        if not isinstance(val, str) or not val.strip():
            raise ValueError(f"railway.{key} missing or empty")
        return val.strip()

    return _req("project_name"), _req("service_name"), _req("environment_name")


def variable_names_from_payload(payload: Any) -> frozenset[str]:
    """Extract names from a Railway variables JSON object; discard values."""
    if not isinstance(payload, dict):
        return frozenset()
    return frozenset(str(k) for k in payload.keys() if isinstance(k, str) and k)


def build_railway_client(token: str) -> httpx.Client:
    """Factory hook for tests (inject MockTransport client)."""
    return httpx.Client(
        timeout=60.0,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Read-only verify: Railway project/service/env exist and required "
            "env names are present (YAML env.required ∪ schema required:true). "
            "Auth: RAILWAY_WORKSPACE_TOKEN (preferred) or RAILWAY_TOKEN. "
            "Never prints secret values. Exit 2 = footprint missing (run A26)."
        )
    )
    p.add_argument("--app-id", required=True, help="Application id")
    p.add_argument(
        "--environment",
        default="production",
        help="deploy/railway/<environment>/ and secrets schema env (default: production)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned footprint + required names from git; no Railway calls",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)

    try:
        deploy = load_deploy_yaml(args.app_id, args.environment)
        project, service, env_name = footprint_names(deploy)
        required = required_secret_names(args.app_id, args.environment)
    except FileNotFoundError as e:
        _err(str(e))
        return 1
    except (OSError, ValueError) as e:
        _err(str(e))
        return 1

    if args.dry_run:
        print("dry-run — planned verify checks (no Railway calls):")
        print(f"  project:     {project}")
        print(f"  environment: {env_name}")
        print(f"  service:     {service}")
        print(f"  required names ({len(required)}):")
        for name in sorted(required):
            print(f"    - {name}")
        return 0

    token = select_railway_token(os.environ)
    if not token:
        _err(
            "live verify requires RAILWAY_WORKSPACE_TOKEN (preferred) or RAILWAY_TOKEN "
            "(or pass --dry-run)"
        )
        return 1

    client = build_railway_client(token)
    try:
        target = RailwayRuntimeTarget(
            app_id=args.app_id,
            environment=args.environment,
            token=token,
            client=client,
        )
        try:
            target.resolve_footprint()
            present = target.list_variable_names()
        except FootprintMissingError as e:
            _err(f"footprint missing (run A26 provision): {e}")
            return 2
        except RuntimeError as e:
            _err(str(e))
            return 1
    finally:
        client.close()

    missing = sorted(required - present)
    print(f"verify footprint ok: project={project} service={service} env={env_name}")
    print(f"required names checked ({len(required)}): {', '.join(sorted(required))}")
    if missing:
        _err(f"required env names missing on Railway service: {missing}")
        return 1
    print("all required names present (values redacted)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
