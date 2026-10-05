#!/bin/sh
# Cursor hook entry for the factory (specs/001-factory-v2/contracts/hooks.md § Invocation).
# Fast path: the venv's `factory-hook` console script. Fallbacks, slow but correct: `uv run`
# when `uv sync` has not run yet, then the repo's Nix env when `uv` is not on PATH either.
# When nothing can answer, print the hook's quiet fail-open response and exit 0 (hooks are
# advisory; CI is authoritative). Hook JSON passes through on stdin/stdout.
root="$(cd "$(dirname "$0")/../.." && pwd)"
hook="$root/scripts/factory/.venv/bin/factory-hook"
if [ -x "$hook" ]; then
  exec "$hook" "$@"
fi
cd "$root" || exit 0
if command -v uv >/dev/null 2>&1; then
  exec uv run --project scripts/factory factory hook "$@"
fi

fail_open() {
  echo "factory-hook: $1; failing open" >&2
  case "$2" in
    spawn-guard | shell-guard) echo '{"permission": "allow"}' ;;
    *) echo '{}' ;;
  esac
  exit 0
}

if ! command -v nix >/dev/null 2>&1; then
  fail_open "no project venv, uv or nix on PATH" "$1"
fi
answer="$(nix develop "$root" -c uv run --project scripts/factory factory hook "$@")"
status=$?
if [ "$status" -ne 0 ] || [ -z "$answer" ]; then
  fail_open "nix develop exited $status without an answer" "$1"
fi
printf '%s\n' "$answer"
