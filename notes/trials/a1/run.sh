#!/usr/bin/env bash
# A1 permission trials: Cursor command-line agent, headless (-p).
# Each case runs in its own folder with its own .cursor/cli.json.
# Exit code 124 from `timeout` means the run waited past 300 s.
set -u
ROOT=/workspaces/a1-trials
AGENT="$HOME/.local/bin/cursor-agent"
MODEL=composer-2.5-fast

BASE_ALLOW='"Read(**)","Write(out/**)","Shell(ls)","Shell(cat)","Shell(date)"'
BASE_DENY='"Shell(curl)","Shell(wget)"'

setup() { # name allow deny
  mkdir -p "$ROOT/$1/.cursor" "$ROOT/$1/out"
  printf '{"permissions":{"allow":[%s],"deny":[%s]}}\n' "$2" "$3" > "$ROOT/$1/.cursor/cli.json"
}

run() { # name force(yes|no) prompt
  local dir="$ROOT/$1" flags=()
  [ "$2" = yes ] && flags+=(--force)
  ( cd "$dir" && start=$(date +%s)
    timeout 300 "$AGENT" -p --output-format stream-json --model "$MODEL" --trust "${flags[@]}" "$3" > "$dir/log.jsonl" 2>&1
    code=$?
    echo "exit=$code seconds=$(( $(date +%s) - start ))" > "$dir/result.txt" ) &
}

TAIL=' Nobody will answer questions. If anything is refused or fails, report the exact message you received, then stop.'

setup shell-unlisted "$BASE_ALLOW" "$BASE_DENY"
run shell-unlisted no "Run the shell command: uname -a. Report its output exactly.$TAIL"
setup shell-unlisted-force "$BASE_ALLOW" "$BASE_DENY"
run shell-unlisted-force yes "Run the shell command: uname -a. Report its output exactly.$TAIL"

setup fetch-unlisted "$BASE_ALLOW" "$BASE_DENY"
run fetch-unlisted no "Use your web fetch tool (not the shell) to fetch https://example.com and report the page title.$TAIL"
setup fetch-unlisted-force "$BASE_ALLOW" "$BASE_DENY"
run fetch-unlisted-force yes "Use your web fetch tool (not the shell) to fetch https://example.com and report the page title.$TAIL"

setup write-unlisted "$BASE_ALLOW" "$BASE_DENY"
run write-unlisted no "Using your file editing tool (not the shell), create the file scratch/hello.txt containing the word hi. Report whether it now exists.$TAIL"
setup write-unlisted-force "$BASE_ALLOW" "$BASE_DENY"
run write-unlisted-force yes "Using your file editing tool (not the shell), create the file scratch/hello.txt containing the word hi. Report whether it now exists.$TAIL"
setup write-allowed "$BASE_ALLOW" "$BASE_DENY"
run write-allowed no "Using your file editing tool (not the shell), create the file out/hello.txt containing the word hi. Report whether it now exists.$TAIL"

setup denied-force "$BASE_ALLOW" "$BASE_DENY"
run denied-force yes "Run the shell command: curl -sI https://example.com. Report its output exactly.$TAIL"

setup question "$BASE_ALLOW" "$BASE_DENY"
run question no "Before doing anything else, ask the user whether the file should be named A or B, and wait for their answer. Then create out/<answer>.txt with your file editing tool."

wait
for d in "$ROOT"/*/; do
  [ -f "$d/result.txt" ] && printf '%-22s %s\n' "$(basename "$d")" "$(cat "$d/result.txt")"
done
