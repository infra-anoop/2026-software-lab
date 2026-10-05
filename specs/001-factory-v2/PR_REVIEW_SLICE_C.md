# PR review — Factory v2 Wave 1 Slice C

Reviewed PR: https://github.com/infra-anoop/2026-software-lab/pull/21  
Reviewed head: `1284ea60d4f20aec7019b87c9b35086a021937db`

## Verdict

**Reject.**

The gate implementations and hook decision logic are generally faithful, and the
accepted tests are untouched. Four blockers remain: the status-writing workflow runs
PR-controlled code with its write token, hooks fail before their fail-open handler in a
fresh worktree, `factory-status-test` is registered but unimplemented, and the packet is
edited outside the effective owned paths.

## Findings

| ID | Severity | Tag | Locus | Finding | Suggested resolution |
|----|----------|-----|-------|---------|----------------------|
| PR-C1 | Blocker | product | `.github/workflows/factory-gates.yml`; `factory gate run --pr` | The `factory-gates` job gives `statuses: write` and `GITHUB_TOKEN` to code checked out from the PR head, then executes that code through `uv sync` and `factory gate run`. A same-repository PR can alter the factory package or dependency graph to steal the token or post arbitrary successful `factory/*` statuses, defeating the authority the token exists to provide. `pull_request` avoids the more dangerous `pull_request_target` checkout trap, but does not make write credentials safe for untrusted head code. | Separate untrusted evaluation from trusted status publication. For example, produce a result artifact under read-only `pull_request`, then let a base-branch-pinned `workflow_run` publisher validate and post statuses. Do not switch to `pull_request_target` while checking out or executing PR code. |
| PR-C2 | Blocker | process | `.cursor/hooks/factory-hook.sh`; all four live hook commands | With no project venv, the wrapper executes ambient `uv`. This repository explicitly requires `uv` through Nix, and ambient `uv` is absent in a fresh worktree. The wrapper exits 127 before `factory.hooks.entry.run_hook` can return its documented quiet fail-open response. The CI selector reproduced four Slice C failures, and every hook is absent precisely when a new worktree needs it most. | Make the unsynced fallback executable in the supported environment and return the event's quiet JSON on bootstrap failure. Options include a worktree setup that creates the venv, or a wrapper fallback through the repository's Nix environment. Add an integration test with both `.venv` and ambient `uv` absent. |
| PR-C3 | Blocker | product | `scripts/factory/gates.yaml` `factory-status-test`; missing `factory.gates.repo.status_test:run` | `factory-status-test` is a P1 CI gate selected by `gate run`, but its entrypoint does not exist in Slice A, B, or C. The runner correctly fails closed, so the authoritative workflow remains red even after A and B merge. `factory check registry` also remains red. | Assign this to Slice A because it is the repository gate for the Slice A board/status implementation and I-M4, then merge it before C. Alternatively amend Slice C explicitly. Add a real gate test and acceptance evidence; do not remove the P1 row. |
| PR-C4 | Blocker | process | `notes/packets/2026-10-04-factory-v2-slice-c.md` | The PR mutates the packet's hand-maintained `Status`, but the packet itself is absent from the original and amended owned paths. The handoff incorrectly says every changed path is amendment-owned. | Revert the packet change and keep progress/completion in the append-only handoff and verdict artifacts. |
| PR-C5 | Should-fix | process | `.github/workflows/factory-gates.yml` `factory-tests` job | The supposedly authoritative workflow still excludes every contract and seed test with `-m "not contract and not seed"`. That was a CP1 bootstrap allowance. Since the planned merge order makes C the final Slice PR, leaving the selector in C would preserve the temporary blind spot after CP1. | After A and B merge into C, run the complete factory suite in `factory-tests` and remove the stale bootstrap comment/selector. |
| PR-C6 | Should-fix | process | `scripts/factory/gates.yaml` `branch-protection-require-pr`; missing `deploy/github/branch-protection.json` | The gate is authoritative and fail-closed, but its required T066 snapshot is absent. Even after A/B and `factory-status-test`, C remains red until the governor/orchestrator completes T066. | Treat T066 as an explicit pre-merge dependency for C, or stage registration/requirement activation so the bootstrap PR can be green without weakening the final required gate. |

## Security

- No `os.getenv`/`os.environ` read was introduced outside `factory.config`.
- Subprocess calls use argument arrays; no production `shell=True` path consumes PR input.
- The workflow interpolates only `github.event.number` into `run:`; no title, body, or
  branch-name expression is injected into shell.
- `pull_request` is safer than executing head code under `pull_request_target`, and the
  declared permissions are otherwise narrow (`contents: read`, `pull-requests: read`,
  `statuses: write`). PR-C1 remains critical because status write is the factory's trust
  boundary and is available to PR-controlled executable code.
- Gate failures may be printed and shortened into status descriptions, but no secret
  values are intentionally logged. Existing validators operate on git archives and use
  argument-vector subprocesses.

## Gate and override fidelity

- Registry validation fails closed on missing, malformed, duplicate, or class/category
  invalid rows.
- Drift overrides require an orchestrator/governor actor and a matching gate/PR.
  Governor-only overrides require `actor: governor`; recorded mode honors them as
  unverified, while verified mode additionally calls `IdentityPort`.
- The registry class, not the message's copied `gate_class`, decides override policy.
- Missing or crashing gate entrypoints fail closed.
- `gate run --pr` runs every non-hook registry row and posts one
  `factory/<gate-id>` status per completed report entry. A gate failure posts failure;
  an honored override posts success with the reason.
- PR gates cover bus immutability/status fields, order linkage/open decisions, claim
  replay, verdict family/input isolation, and override-message validity.
- PR-C3 and PR-C6 are the remaining fail-closed integration gaps.

## Hooks

- Direct probes confirmed that the ops command
  `nix develop -c uv run scripts/ops_runtime_tag.py ... --push --force` is allowed: the
  flag belongs to the Python program, not an executed `git push`.
- Ordinary work/review branch pushes, tag pushes, and commits on `review/*` are allowed.
  A push whose destination is `main` is denied with exit 2.
- `spawn-guard` always returns `permission: allow`; its advisory is log-only, matching
  the governor lock and the catalog wording.
- Internal hook exceptions return quiet fail-open responses. PR-C2 records the wrapper
  bootstrap failure that occurs before this handler.
- With the venv present, the accepted end-to-end tests establish the 300 ms median
  budget. The `uv run` fallback is intentionally exempt, but currently cannot start in
  the supported ambient environment.
- `acceptance.md` correctly preserves **“editor launch logged (advisory)”**.

## Workflow

- The workflow uses `pull_request`, not `pull_request_target`.
- No PR-controlled string field is embedded in a shell command.
- The board step runs under `!cancelled()` and appends `factory status` output to
  `$GITHUB_STEP_SUMMARY`, so it runs after gate failure when Slice A is present.
- `continue-on-error` is absent and `statuses: write` is declared only on the gate job.
- PR-C1 is the credential/trust defect; PR-C5 is the remaining test-selection defect.

## Scope and cross-slice integration

- Accepted tests are unchanged after `9445788`; frozen CP0 files are untouched.
- All implementation/spec changes fit amendment-02 except the packet mutation in PR-C4.
- Pairwise merge simulation found one textual conflict for A→B→C:
  `specs/001-factory-v2/acceptance.md`. Resolve it by preserving C's governor-locked
  **“editor launch logged (advisory)”** wording, appending A's claim evidence, and
  appending C's PR/editor evidence. Do not take A/B's stale “warned” wording.
- `scripts/factory/pyproject.toml` auto-merges: preserve Slice A's `pyjwt[crypto]`
  dependency and C's `factory-hook` console script.
- After A merges, Slice A CLI/status dependencies and board summary become available.
  After B merges, the 52 seeds, intent check, and drift entrypoints become available.
- Even after both merges, `factory-status-test` remains absent (PR-C3);
  `branch-protection-require-pr` remains blocked on T066 (PR-C6); T064 still needs its
  planned post-B integration; Phase 9 `retro` and US7 commands remain intentionally red.

## Verification record

| Check | Result |
|-------|--------|
| Worktree setup discovery | Checked repository root and worktree; no `.cursor/worktrees.json`, so setup was skipped. |
| Accepted-test immutability | `git diff 9445788 HEAD -- scripts/factory/tests` was empty. |
| Frozen CP0 files | No changes to `api.py`, `bus/`, `config/`, `cli/app.py`, `cli/exit_codes.py`, `gates/registry.py`, or `tests/fixtures/`. |
| Diff hygiene | `git diff --check origin/main...HEAD` passed. |
| `nix develop ../.. -c uv sync --locked` | Environment-blocked: sandbox could not open `/nix/var/nix/db/big-lock`. No dependency change was made. |
| Full `pytest -q` | Using an existing locked Slice C venv with this worktree's `src` on `PYTHONPATH`: **501 passed, 106 failed**. |
| Failure classification | **50 contract + 52 seed** are the expected A/B/US7/T069/unowned-gate failures; **4 Slice C hook integration failures** are PR-C2 (`uv: not found`). |
| CI selector `pytest -q -m "not contract and not seed"` | **447 passed, 4 failed, 156 deselected**; the four failures are PR-C2. |
| `ruff check .` | Passed. |
| `factory check schema --repo ../..` | Passed before verdict-04 was added. |
| Hook probes | Ops runtime-tag command, tag push, review-branch push, and review-branch commit allowed; main push denied; spawn always allowed and logged. |
| Cross-slice merge simulation | A↔C, B↔C, and A↔B each conflict only in `acceptance.md`; other inspected paths auto-merge. |
