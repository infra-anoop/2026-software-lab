#!/bin/sh
# Cursor hook entry for the factory (specs/001-factory-v2/contracts/hooks.md).
# Fast path: the venv's `factory-hook` console script. Fallback: `uv run` (slow, but correct)
# when `uv sync` has not run yet. Hook JSON passes through on stdin/stdout.
root="$(cd "$(dirname "$0")/../.." && pwd)"
hook="$root/scripts/factory/.venv/bin/factory-hook"
if [ -x "$hook" ]; then
  exec "$hook" "$@"
fi
cd "$root" && exec uv run --project scripts/factory factory hook "$@"
