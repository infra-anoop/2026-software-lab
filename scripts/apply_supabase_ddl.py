#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "psycopg[binary]>=3.2",
# ]
# ///
"""Apply versioned Supabase DDL from ``db/supabase/`` for a registered app.

Transaction model: one Postgres transaction per SQL file (ordered). A failure
in a later file does not roll back earlier files.

``--dry-run`` prints repo-relative paths in apply order and exits 0 without
opening a database connection (wins over ``--database-url`` if both are set).
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DDL_DIR = REPO_ROOT / "db" / "supabase"

# App → ordered repo-relative SQL paths (order matters for research-auditor).
APP_DDL_REL_PATHS: dict[str, tuple[str, ...]] = {
    "smart-writer": ("db/supabase/runs_turns.sql",),
    "research-auditor": (
        "db/supabase/runs_turns.sql",
        "db/supabase/research_audits.sql",
    ),
}

KNOWN_APPS = frozenset(APP_DDL_REL_PATHS)


def _err(msg: str) -> None:
    print(f"apply_supabase_ddl error: {msg}", file=sys.stderr)


def ddl_rel_paths(app: str) -> tuple[str, ...]:
    """Return ordered repo-relative DDL paths for ``app``."""
    try:
        return APP_DDL_REL_PATHS[app]
    except KeyError as e:
        known = ", ".join(sorted(KNOWN_APPS))
        raise ValueError(f"unknown --app {app!r}; expected one of: {known}") from e


def ddl_abs_paths(app: str, *, repo_root: Path = REPO_ROOT) -> list[Path]:
    """Resolve ordered absolute paths; raise if a file is missing."""
    paths: list[Path] = []
    for rel in ddl_rel_paths(app):
        path = repo_root / rel
        if not path.is_file():
            raise FileNotFoundError(f"DDL file not found: {rel}")
        paths.append(path)
    return paths


def apply_files(app: str, database_url: str, *, repo_root: Path = REPO_ROOT) -> None:
    """Apply each DDL file in order; one transaction per file."""
    import psycopg

    paths = ddl_abs_paths(app, repo_root=repo_root)
    with psycopg.connect(database_url) as conn:
        for path in paths:
            sql = path.read_text(encoding="utf-8")
            with conn.transaction():
                # Connection.execute uses the simple query protocol (multi-statement OK).
                conn.execute(sql)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Print or apply db/supabase DDL for an app. "
            "Apply uses one transaction per SQL file."
        ),
    )
    parser.add_argument(
        "--app",
        required=True,
        choices=sorted(KNOWN_APPS),
        help="App id selecting the ordered DDL file set",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Print repo-relative DDL paths in apply order; exit 0; "
            "no DB connection (overrides --database-url)"
        ),
    )
    parser.add_argument(
        "--database-url",
        default=None,
        metavar="URL",
        help="Postgres URL for apply (required unless --dry-run)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        rels = ddl_rel_paths(args.app)
    except ValueError as e:
        _err(str(e))
        return 1

    if args.dry_run:
        for rel in rels:
            print(rel)
        return 0

    if not args.database_url:
        _err("apply requires --database-url (or pass --dry-run)")
        return 1

    try:
        apply_files(args.app, args.database_url)
    except (FileNotFoundError, OSError) as e:
        _err(str(e))
        return 1
    except Exception as e:  # noqa: BLE001 — surface driver/SQL errors cleanly
        _err(f"apply failed: {e}")
        return 1

    print(f"OK — applied {len(rels)} file(s) for {args.app}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
