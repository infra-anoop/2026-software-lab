#!/usr/bin/env bash
# A1 follow-up 2: rule out pattern spelling. Deny writes with an absolute path and with a match-anywhere glob.
set -u
ROOT=/workspaces/a1-trials
AGENT="$HOME/.local/bin/cursor-agent"
MODEL=composer-2.5-fast
ALLOW='"Read(**)","Write(out/**)","Shell(ls)","Shell(cat)","Shell(date)"'
PROMPT='Using your file editing tool (not the shell), create the file scratch/hello.txt containing the word hi. Report whether it now exists. Nobody will answer questions. If anything is refused or fails, report the exact message you received, then stop.'

setup() { # name deny-entry
  mkdir -p "$ROOT/$1/.cursor"
  printf '{"permissions":{"allow":[%s],"deny":["Shell(curl)",%s]}}\n' "$ALLOW" "$2" > "$ROOT/$1/.cursor/cli.json"
}
setup write-denied-abs "\"Write($ROOT/write-denied-abs/scratch/**)\""
setup write-denied-any '"Write(**/scratch/**)","Write(scratch)","Write(scratch/hello.txt)"'

for name in write-denied-abs write-denied-any; do
  ( cd "$ROOT/$name" && timeout 300 "$AGENT" -p --output-format stream-json --model "$MODEL" --trust "$PROMPT" > log.jsonl 2>&1; echo "exit=$?" > result.txt ) &
done
wait
for name in write-denied-abs write-denied-any; do
  echo "=== $name $(cat "$ROOT/$name/result.txt")"; cat "$ROOT/$name/.cursor/cli.json"
  jq -r 'select(.type=="result") | .result' "$ROOT/$name/log.jsonl" | head -c 300; echo
  ls "$ROOT/$name/scratch" 2>/dev/null || echo "(no scratch folder)"
done
