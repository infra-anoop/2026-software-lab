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

## Triage (PR review)

Recorded 2026-10-05 by the Slice C worker on the orchestrator's instruction, against verdict-04 (reject). Product-tagged findings were adjudicated by the governor; process-tagged findings by the orchestrator under constitution §F. Architecture effects are reconciled in [`PLAN_DELTA.md`](./PLAN_DELTA.md) (§G.1); owned paths for this triage are in `bus/orders/wo-20261004-factory-slice-c/amendment-03.yaml`.

| ID | Disposition | Adjudicator | Resolution | Task |
|----|-------------|-------------|------------|------|
| PR-C1 | accept — **governor lock D5** (architecture-affecting, letter) | governor 2026-10-05 | Trusted base: `main`'s gate code judges every PR in CI and the head is only data (diff, files, bus messages, tests). PR-head code never runs with status-write permission; the PR's own tests run in a separate read-only job that cannot post `factory/*` statuses. A PR that changes the gates is judged by `main`'s current gates, and its gates take effect after merge. Slice C's own PR bootstraps through the FR-037 bootstrap verdict plus governor approval. `pull_request_target` combined with head checkout or execution is banned. Shape: untrusted `factory-pr-evidence.yml` (`pull_request`, `contents: read`) + trusted `factory-gates.yml` (`workflow_run`, `main`'s code, `statuses: write`); red-first execution evidence crosses as an untrusted, validated bundle (plan § CI topology and trust boundary; `contracts/gates.md`). Spec FR-022a; catalog `ci.trusted_base`. The bootstrap sequence against branch protection is opened as **D6** (governor) | T094 (red) → T096 (T*) → T097; T103 |
| PR-C2 | accept | orchestrator (process) | When neither the venv nor an ambient `uv` exists, the wrapper runs the fallback in the repository's Nix environment (`nix develop <repo root> -c uv run --project scripts/factory factory hook <name>`). If bootstrap fails, the wrapper prints the hook's quiet fail-open JSON, exits 0 and never exits 127. Integration test with both `.venv` and ambient `uv` absent. `contracts/hooks.md` § Invocation and `research.md` § Editor hooks amended | T095 (red) → T096 → T098 |
| PR-C3 | accept — separate small order | orchestrator (product finding; placement is sequencing, not product content) | `factory-status-test` keeps its P1 row. Its entrypoint `factory.gates.repo.status_test:run` is built test-first as its own small order after Slice A merges and before Slice C merges; it judges with `main`'s code over head data (D5) and carries a bootstrap verdict. Slice C does not create that file | T102 |
| PR-C4 | accept | orchestrator (process) | Revert the packet `Status` line to its `main` text; progress stays in the append-only handoff and verdicts | T099 |
| PR-C5 | accept | orchestrator (process) | Once Slices A and B are merged into C, `factory-tests` (now in the read-only workflow) runs the full suite with no selector, and the CP1 bootstrap comment goes | T100 |
| PR-C6 | accept — pre-merge dependency | orchestrator (process); activation timing → governor **D6** | T066 (branch-protection walkthrough + snapshot) runs between the Slice B merge and the Slice C merge, as a dependency of C's merge. The required checks name each P1 `factory/<gate-id>` context individually plus `Factory tests`. When the `factory/*` requirement switches on relative to C's merge is D6 (open) | T101 `[OD:D6]` |

**Merge order:** A → B → (T101 + T102) → C, with C's merge (T103) after the delta P* review, the T* review of T094–T095, T097–T100 green and D6 locked.

**Next:** spawn the delta P* review of the D5 amendment (`PLAN_REVIEW_PROMPT.md` + `STACK_POSTURE.md`), then red tests T094–T095 and T* (T096). No implementation in this triage run.

## Round 2

Reviewed PR #21 at `28e3aa30fba3992e7182d42dc6db633ba5ad9bf0` under the normal
round-2 bar in constitution §J.

### Verdict

**Accept with Later items.**

No Blocker remains. The privileged workflow is pinned to `workflow_run`, runs the
default branch's code, treats the head and its evidence as data, and is the sole holder
of `statuses: write`. The round-4 T* root cause is fixed once by an exact step/command
allowlist: `env bash -c`, `command bash -c`, `git -C … checkout`, and an arbitrary
unlisted command all fail its oracle. The evidence judge, ruleset snapshot/gate, hook
fallback, and A+B integration seams are fail-closed or advisory exactly where locked.

### Blockers

None.

### Later

| ID | Owner / review point | Finding |
|----|----------------------|---------|
| PR-C2-L1 | Slice C / Wave 1 retro | Bind the evidence bundle's full `base_sha` to the trusted run. The judge currently validates its shape but not equality with the base it judges. This is the already-recorded T-C4-2 hardening item; Wave 1 remains explicitly `self-reported:` and the independent T* run is the proof of record. |
| PR-C2-L2 | Slice C / Wave 1 retro | Prove in the workflow oracle that the evidence producer executable comes from the intended checkout. This is the already-recorded T-C4-3 contract-precision item; it adds no authority to Wave 1's explicitly self-reported bundle. |
| PR-C2-L3 | Slice C / Wave 1 retro | Normalize exit-zero malformed/non-JSON output from the Nix hook fallback to the hook's quiet fail-open JSON. Hooks are advisory and CI remains authoritative, so the uncovered degraded response is not blocking. |
| PR-C2-L4 | Factory trust-boundary hardening / Wave 1 retro | `SECRETS_REF` detects `secrets.NAME` but not valid indexed expressions such as `secrets['NAME']` or whitespace variants. The current `factory-pr-evidence.yml` contains no secret reference and has workflow-level `contents: read`, so no credential is exposed in this PR. Extend the detector and its self-check table before relying on it for future workflow edits. |

### Explicit scope checks

- **PR-C1 / D5:** `factory-pr-evidence.yml` is `pull_request`, workflow-level
  `contents: read`, has no secret reference and cannot post statuses.
  `factory-gates.yml` is `workflow_run`, checks out the default branch without
  credentials, downloads only `factory-evidence` from
  `github.event.workflow_run.id`, runs the default branch's locked factory package,
  and is the only workflow job with `statuses: write`. `ci-cd-pipeline.yml` now has
  workflow-level `contents: read`.
- **Round-4 oracle:** workflow/job/step keys, env names, pinned action identities and
  `with:` keys are allowlisted; the six steps must be exactly three actions and three
  parsed commands. The four required bypass/unlisted controls are rejected and the
  focused trust suite passes.
- **T097 evidence:** Pydantic uses strict, frozen, `extra="forbid"` models at every
  level; the loader rejects missing, extra, non-regular, over-size, non-UTF-8,
  non-JSON and schema-invalid inputs. The judge derives the expected test set from git,
  rejects duplicates, omissions, additions, a wrong head SHA, producer crashes,
  non-red bases and non-green heads, and labels success `self-reported:`.
- **P9:** the live ruleset `24554609` is the RULESET shape recorded in
  `deploy/github/branch-protection.json`; after removing GitHub server metadata, the
  only intended delta is the 25 `factory/*` contexts targeted by T103. Every required
  check is pinned to GitHub Actions integration `15368`. The gate requires code-owner
  review exactly when `identity.mode == "verified"`, matching amendment-07.
- **PR-C2:** the hook wrapper tries the project venv, ambient `uv`, then
  `nix develop`; missing tools or a failed/empty Nix answer returns event-appropriate
  fail-open JSON and exit 0.
- **A+B integration:** the REST `get_pr` adapter returns `None` only for 404;
  handoff skips registry hook rows rather than weakening their CI twins; the secrets
  regex no longer mistakes filenames for context references (with PR-C2-L4 retained);
  `RepoBuilder.plant_lab_inputs` plants realistic inputs and skips a source-tree input
  absent on the copied side; evidence calls the real `red_first.collect_facts` seam.
- **CODEOWNERS:** the constitution, `AGENTS.md`, Cursor rules, agent-OS docs, factory
  registry/gate/rubric paths, both factory workflows and CODEOWNERS itself are covered.

### Verification

| Check | Result |
|-------|--------|
| `nix develop ../.. -c uv sync --locked` | PASS — 30 locked packages resolved, 29 installed |
| Full `pytest -q -p no:cacheprovider` | Expected partial red — **1034 passed, 9 failed** in 212.68 s; all nine are the stated T102/T069/T081 `test_cli_contract.py` facts |
| Focused trust / ruleset / hook / adapter suite | PASS — **133 passed** in 24.05 s |
| `ruff check .` | PASS |
| `ruff format --check .` | PASS — 135 files formatted |
| Live ruleset read | PASS — ruleset `24554609`; live body matches the snapshot apart from snapshot-only T103 `factory/*` targets and omitted server metadata |
| `git diff --check origin/main...HEAD` | One pre-existing trailing-space line in this review file's original PR URL; no code defect |
