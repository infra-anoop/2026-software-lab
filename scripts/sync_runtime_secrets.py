#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "httpx>=0.27",
#   "pyyaml>=6",
# ]
# ///
"""Sync A20 schema secrets from vault → runtime target (A21).

Exactly one of ``--dry-run`` | ``--apply``. Dry-run prints names only.
Apply fetches Infisical and upserts Railway (never logs values).

Auth for apply:
  Railway: RAILWAY_WORKSPACE_TOKEN (preferred) or RAILWAY_TOKEN
  Infisical: INFISICAL_TOKEN (short-lived OIDC from Actions preferred;
  long-lived token is non-preferred — see sync-runtime-secrets.yml)

Exit 2 = Railway footprint missing (run A26 provision first).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from secrets_sync.schema import load_secret_entries  # noqa: E402
from secrets_sync.sync import build_plan, run_apply, run_dry_run  # noqa: E402
from secrets_sync.target_railway import FootprintMissingError, RailwayRuntimeTarget  # noqa: E402
from secrets_sync.target_vercel import VercelRuntimeTarget  # noqa: E402
from secrets_sync.vault_infisical import InfisicalCloudBackend  # noqa: E402
import railway_graphql as rgql  # noqa: E402


def _err(msg: str) -> None:
    print(f"sync_runtime_secrets error: {msg}", file=sys.stderr)


def _railway_token() -> str:
    return rgql.select_railway_token(os.environ) or ""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--app-id", required=True, help="Registry / secrets-schema application id")
    p.add_argument(
        "--environment",
        default="production",
        help="Schema + deploy/railway/<environment>/ folder (default: production)",
    )
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Print secret names only; no vault/target I/O")
    mode.add_argument("--apply", action="store_true", help="Fetch vault + upsert onto runtime target")
    p.add_argument(
        "--target",
        choices=("railway", "vercel"),
        default="railway",
        help="Runtime target adapter (default: railway)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        entries = load_secret_entries(args.app_id, args.environment)
    except (OSError, ValueError) as e:
        _err(str(e))
        return 1

    if args.target == "vercel":
        target: Any = VercelRuntimeTarget()
    else:
        try:
            target = RailwayRuntimeTarget(
                app_id=args.app_id,
                environment=args.environment,
                token=_railway_token(),
            )
        except (OSError, ValueError) as e:
            _err(str(e))
            return 1

    plan = build_plan(
        app_id=args.app_id,
        environment=args.environment,
        entries=entries,
        target=target,
    )

    if args.dry_run:
        for line in run_dry_run(plan):
            print(line)
        return 0

    # --apply
    if args.target == "vercel":
        _err("vercel target not implemented")
        return 1

    railway_token = _railway_token()
    if not railway_token:
        _err("apply requires RAILWAY_WORKSPACE_TOKEN or RAILWAY_TOKEN")
        return 1

    infisical_token = os.environ.get("INFISICAL_TOKEN", "").strip()
    if not infisical_token:
        _err("apply requires INFISICAL_TOKEN")
        return 1

    target = RailwayRuntimeTarget(
        app_id=args.app_id,
        environment=args.environment,
        token=railway_token,
    )
    vault = InfisicalCloudBackend(token=infisical_token)

    try:
        result = run_apply(entries=entries, vault=vault, target=target)
    except FootprintMissingError as e:
        _err(f"footprint missing (run A26 provision): {e}")
        return 2
    except (OSError, ValueError, RuntimeError) as e:
        _err(str(e))
        return 1

    print(f"OK upserted={len(result['upserted'])} noop/skipped={len(result['noop'])}")
    print("upserted names:", ", ".join(result["upserted"]) or "(none)")
    if result["noop"]:
        print("skipped/noop names:", ", ".join(result["noop"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
