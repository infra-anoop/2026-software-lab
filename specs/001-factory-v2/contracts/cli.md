# Contract — `factory` CLI

Invocation: `uv run --project scripts/factory factory <command>`. All commands accept `--json` (machine output) and `--repo PATH`. Exit codes: `0` ok, `1` gate/validation failure, `2` refused by policy (cap, open decision, path overlap), `3` usage/config error, `4` external failure (git/GitHub unreachable).

**JSON envelope.** With `--json`, stdout is exactly one JSON object: `{"ok": true, "command": "<path>", "data": …}` on exit 0, or `{"ok": false, "command": "<path>", "error": {"code": <exit code 1–4>, "message": "<plain text>", "details": …}}` on any other exit, including refusals, usage errors, and config errors. `command` is the space-separated command path (`check schema`, `order new`, `claim`); `data` and `details` are command-specific. Diagnostics may also go to stderr. Model: `factory.cli.common.JsonEnvelope`. `factory hook` is the one exception: its stdout is always the Cursor hook response (`contracts/hooks.md`). When `--repo` is omitted, the repo root is the nearest directory holding `factory.toml`, searched from the working directory up to the git root.

| Command | Effect | Refusals (exit 2) | Spec |
|---------|--------|-------------------|------|
| `factory status` | Print board: in flight, blocked on governor (plain-language prompts), ready queue, overrides per gate, unverified governor actions | — | FR-003/004, SC-001 |
| `factory decisions` | Print open decision requests (the governor's batch) | — | FR-004, I-E2 |
| `factory order new --feature F --from-task T…` | Scaffold an order file from tasks locally; validates | size > horizon; missing fidelity for a touched named lock | FR-006/016 |
| `factory order issue <order-id>` | Create `wo/<order-id>` from `main` with the order as its first commit; push (never pushes `main`) | depends on open human decision; schema invalid | FR-005/007 |
| `factory claim <order-id>` | Fast-forward push of the claim event to `wo/<order-id>` (atomic per order) | active ≥ cap (3); owned paths overlap an active order; order blocked on governor; already claimed | FR-007/008 |
| `factory release <order-id> --reason R` | Append release event; frees capacity | — | P4 |
| `factory handoff <order-id>` | Validate handoff + `run-complete` event on branch | any registered gate for the order failing locally (FR-009) | FR-009/010 |
| `factory bus pr --message M…` | Open a bus PR (`bus/<date>-<slug>`) for decision, correction, or post-mortem messages; merge on green | non-bus paths in the change | FR-001 |
| `factory pr open <order-id>` | Open PR `wo/<order-id>` → `main` via REST; body links order + intents | no handoff; handoff invalid | FR-005, I-P1 |
| `factory verdict <order-id> --file V` | Validate verdict (family, isolation inputs) and commit it to the branch | reviewer family = author family; non-git input | FR-011/011a |
| `factory override <order-id> --gate G --reason R` | Write override message | empty reason; governor-only gate by non-governor actor | FR-020/021 |
| `factory correction new …` | Write correction; `--links-to` records the repeat link and emits a rule/check proposal order | — | FR-029 |
| `factory gate run [--gate G] [--pr N \| --base B --head H]` | Run registered gates; prints per-intent results | — | FR-012..024 |
| `factory check schema \| hooks \| registry \| immutability` | Repo-level validations | — | FR-001/002/022 |
| `factory check intent [--coverage [--require-target]]` | Presence: exit 1 naming each intent with no mapping (own `checks`, a `gates.yaml` row, or an `acceptance.md` row). `--coverage` also reports effective coverage (`share`, `covered`, `uncovered`) and stays report-only (exit 0 at any share). `--require-target` (sprint-close mode, needs `--coverage`) exits 1 below 90% and 0 at or above it (governor 2026-10-04) | — | FR-023, SC-005 |
| `factory scorecard [--sprint S]` | Compute scorecard from run records, verdicts, corrections, overrides | — | FR-035, SC-009 |
| `factory sprint close --sprint S` | Refuse unless post-mortem exists and dispositions every correction | missing post-mortem / undispositioned correction | FR-030 |
| `factory hook <name>` | Hook entrypoint (stdin JSON → stdout JSON per Cursor hooks) | per hook | FR-022 |
| `factory retro --since <ref>` | Run P1 gates retroactively on merged Wave 1 PRs; write report | — | FR-037 |
