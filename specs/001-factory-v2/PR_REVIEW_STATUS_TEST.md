# PR review — `wo-20261006-factory-status-test` (round 1)

Reviewed draft PR: https://github.com/infra-anoop/2026-software-lab/pull/25  
Reviewed head: `9dececbca38f6aed4837c5b3e65f31d91d86e6ce`

## Verdict

**Reject.**

The gate obeys D5 in its normal path: it reads the head through git-object loaders from
installed `main` code, never checks out or imports the head, derives through
`derive_from_view`/`derive_order`, and uses an offline GitHub implementation whose write
methods raise. The reconstructed P0 order and I-M4 evidence are faithful. One fail-closed
defect remains: valid git data outside the loader's two normalized exception classes can
escape `run`.

## Blockers

| ID | Severity | Tag | Locus | Finding | Smallest sufficient fix |
|----|----------|-----|-------|---------|-------------------------|
| PR-ST1 | Blocker | process | `scripts/factory/src/factory/gates/repo/status_test.py::run` | **Root-cause class: incomplete exception normalization at the gate boundary.** `run` catches only `BusError` and `GitError`, although object decoding and installed derivation can raise other exceptions. A head containing a tracked `.yaml` blob with invalid UTF-8 reproducibly lets `UnicodeDecodeError` escape instead of returning a failed `GateResult`; an attempted future write through `NoGitHub` would similarly escape `RuntimeError`. **Consequence:** the gate violates T102's explicit “fails closed, and no exception escapes” contract, so a contributor-controlled head can crash the judge rather than receive the gate's auditable failure result. **Likelihood:** medium-low accidentally, but direct and trivial for a PR author. | Catch unexpected `Exception` at the `run` boundary and return a generic failed result that names the head without echoing unsafe content. Add at most one regression for this class, preferably an invalid-UTF-8 bus blob; retain the narrower messages for `BusError` and `GitError`. |

## Later

| ID | Owner / review point | Finding |
|----|----------------------|---------|
| PR-ST-L1 | Factory trust-boundary hardening / Wave 1 retro | Git object reads have no subprocess timeout and bus blobs have no size/resource bound before UTF-8/YAML parsing. A pathological head can consume the trusted job's time or memory, although it cannot make this gate pass falsely and the hosted-job timeout eventually contains it. Address this once in the shared git/bus loader rather than in this gate. |

## Required scope checks

### Gate and D5

- `status_test.py` imports only the installed package and treats `head_sha` as a git
  object reference. It performs no checkout, worktree creation, import, test execution,
  or package installation from the head.
- `head_view` strictly loads every head bus file through `main`'s `load_messages` and
  `load_order`. It does not trust the runner's tolerant `ctx.bus_snapshot`.
- `derive.derive_from_view` is the actual oracle and reaches `derive_order` per record.
  Comparing folder ids with derived ids detects missing, duplicate and invented board
  entries. No reviewed path can pass falsely without influencing that derivation.
- `NoGitHub` supplies no PRs, reviews, checks or statuses. Its two write methods refuse
  writes. PR-ST1 is why those refusals are not yet fully fail-closed at the gate boundary.
- No deterministic hang appeared in the suite or manual run. PR-ST-L1 records the shared
  unbounded-input/subprocess exposure rather than requiring per-gate timeout machinery.

### Reconstructed P0 order

- The goal, tasks T001–T015, pre-amendment owned paths, I-A3/I-M2 intents, stop
  conditions, runtime, stack/location/no-status/cap locks, and manual-equivalent checks
  trace to `notes/packets/2026-10-03-factory-v2-p0-contracts.md` and amendments 01–03.
- The order follows the Slice A/B FR-037 bootstrap shape: `actor_verified: false`,
  schema-minimum `size_minutes: 1`, true timing in refs, no decision dependencies, and
  no synthetic claim or handoff.
- The disclosure is honest about retrospective creation time, scorecard dating and true
  multi-hour size. The cited packet issue and accepting-verdict timestamps match git.
- It adds P0 to the **unscoped** Wave 1 cohort and therefore adds a future run-record
  requirement, exactly as the handoff discloses. It has no sprint ref, so sprint-scoped
  membership and exit are unchanged.

### Acceptance evidence

All four newly linked I-M4 node ids exist in
`scripts/factory/tests/unit/gates/repo/test_status_test.py` and were collected by the
full suite. They cover a valid board, dropped order events, sabotaged installed
derivation, and D5 hostile-head isolation. The parked missing-decision test is not cited.

## Verification

| Check | Result |
|-------|--------|
| `nix develop ../.. -c uv sync --locked` | Pass — 30 packages resolved, 29 installed |
| Full `uv run pytest` | Expected partial red — **690 passed, 24 failed** in 140.70 s; 23 are the disclosed Slice C/T069/T081 CLI contract reds and one is parked T-ST3 |
| `uv run ruff check .` | Pass |
| `uv run ruff format --check .` | Pass — 99 files already formatted |
| `git diff --check origin/main...HEAD` | Pass |
| Manual gate equivalent at PR head | Pass — `factory-status-test: every order folder on the head bus is on main's derived board` |
| Unexpected-exception probe | Fail-closed defect reproduced — invalid UTF-8 in a tracked head bus YAML blob escapes as `UnicodeDecodeError` |

