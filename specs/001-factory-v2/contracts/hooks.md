# Contract — Cursor hooks (convenience mirrors; CI is authoritative)

File: `.cursor/hooks.json` (version 1). Each hook calls `uv run --project scripts/factory factory hook <name>`; must run offline in < 300 ms. Every hook id appears in the gate registry as `hook_twin_of: <ci gate id>`; `hook-has-ci-twin` fails otherwise.

| Hook name | Event | Behavior | CI twin |
|-----------|-------|----------|---------|
| `spawn-guard` | `subagentStart` | Deny unless the prompt names a claimed order id (`wo-…`) or is a reviewer spawn naming a review packet/order; deny when active orders ≥ cap | `spawn-concurrency-cap`, `pr-links-order` |
| `shell-guard` | `beforeShellExecution` | Deny `pip install`, `gh workflow run`, `git push --force`, writes to `/etc`, `/usr`, `~/.config` outside the repo, `nix-env -i` | `diff-within-owned-paths`, `block-system-path-edits` (P2) |
| `owned-path-warn` | `afterFileEdit` | Warn (agent message) when the edited path is outside the current order's owned paths | `diff-within-owned-paths` |
| `decision-in-chat` | `stop` | Warn when the final assistant turn asks the governor a question and no new `bus/decisions/*/request.yaml` exists in the working tree | `decision-request-no-ids` (+ post-mortem routing count) |

Current order for a session is resolved from the checked-out branch `wo/<order-id>`; on `main` the orchestrator role applies.
