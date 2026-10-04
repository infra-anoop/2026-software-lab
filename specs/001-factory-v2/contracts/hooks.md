# Contract — Cursor hooks (convenience mirrors; CI is authoritative)

File: `.cursor/hooks.json` (version 1). Each hook calls `uv run --project scripts/factory factory hook <name>`; must run offline in < 300 ms. Every hook id appears in the gate registry as `hook_twin_of: <ci gate id>`; `hook-has-ci-twin` fails otherwise.

| Hook name | Event | Behavior | CI twin |
|-----------|-------|----------|---------|
| `spawn-guard` | `subagentStart` | **Advisory** (FR-008 waive): warn unless the prompt names a claimed order id (`wo-…`) or a review packet; warn when the last-fetched active count ≥ cap. Authoritative refusal is `factory claim` + the CI twin | `spawn-concurrency-cap` (claim replay), `pr-links-order` |
| `shell-guard` | `beforeShellExecution` | Deny `git commit` while the checked-out branch is `main`, any `git push` whose target is `main` (I-P10), `pip install`, `gh workflow run`, `git push --force`, writes to `/etc`, `/usr`, `~/.config` outside the repo, `nix-env -i` | `branch-protection-require-pr`, `diff-within-owned-paths`, `block-system-path-edits` (P2) |
| `owned-path-warn` | `afterFileEdit` | Warn (agent message) when the edited path is outside the current order's owned paths | `diff-within-owned-paths` |
| `decision-in-chat` | `stop` | Warn when the final assistant turn asks the governor a question and no new `bus/decisions/*/request.yaml` exists in the working tree | `decision-request-no-ids` (+ post-mortem routing count) |

Current order for a session is resolved from the checked-out branch `wo/<order-id>`; on `main` the orchestrator role applies.
