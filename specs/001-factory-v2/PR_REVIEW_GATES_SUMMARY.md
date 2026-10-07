# PR review — `wo-20261006-factory-gates-summary` (round 1)

Reviewed PR: https://github.com/infra-anoop/2026-software-lab/pull/27  
Reviewed head: `c172954`

## Verdict

**Accept.**

The implementation matches the Round 5 governor lock. A full PR run with no
`--gate` computes `factory/gates` from the installed registry and the returned
report, posts it after every per-gate status, and fails it for any missing or
non-passing/non-overridden gate. Explicit `--gate` runs and moved-head runs post
no summary. The ruleset snapshot replaces the per-gate requirements with the
three pinned contexts, and the branch-protection gate still fails closed when
the head registry is absent.

## Findings

None.

## Required scope checks

- The summary is based on `ci_gates(load_registry())`, not the head registry.
  The CLI passes the report returned by the real runner to `summary_status`.
- `factory/gates` is posted only after the per-gate posting loop. An exception
  or crash before that point leaves the required summary absent.
- Any explicit `--gate` list suppresses the summary, including a list naming
  every installed gate. A moved head returns before any status is posted.
- Missing report entries and outcomes other than `pass` or `overridden` produce
  `failure`; the description is bounded by `STATUS_DESCRIPTION_LIMIT` (140).
- `deploy/github/branch-protection.json` has the live ruleset 24554609 shape and
  exactly `Factory tests`, `Verify Source / verify`, and `factory/gates`, each
  pinned to integration `15368`. The backup comparison file was empty, so it
  supplied no additional live payload to compare.
- `branch-protection-require-pr` requires the pinned summary and continues to
  load the head registry before evaluating the snapshot.
- `contracts/gates.md` consistently describes installed-registry selection,
  status ordering, subset behavior, moved-head behavior, source pinning, and
  the three-context snapshot.
- The amended trust-boundary test still exercises the installed-registry
  behavior and now expects the failing summary in addition to all per-gate
  statuses.
- No production source contains a test-only seam. The report-omission seam is
  confined to the contract test and wraps the existing runner boundary.
- The pre-decided Later items remain Later: stale prior status on a crashed
  rerun, reserving gate id `gates`, and the same-repository fake-green gap
  assigned to T065.

## Verification

- `nix develop /workspaces/2026-software-lab -c bash -c 'cd scripts/factory && uv run --locked pytest -q'`
  — **1056 passed, 7 xfailed**.
- `uv run --locked ruff check .` — pass.
- `uv run --locked ruff format --check .` — pass, 137 files formatted.
- `git diff --check ac60d43..c172954` — pass.
