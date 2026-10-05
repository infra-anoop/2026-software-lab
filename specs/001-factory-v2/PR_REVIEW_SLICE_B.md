# PR review — Factory v2 Wave 1 Slice B

Reviewed PR: https://github.com/infra-anoop/2026-software-lab/pull/22  
Reviewed head: `68eb20c742e605fc135d61c80402f0ff0e9cb738`

## Verdict

**Reject.**

The accepted tests are untouched, the Slice B implementation tests and CI selector
are green, and the FR-023/SC-005b/eval-evidence edits match the governor locks. Two
gate-fidelity blockers remain: a deferral can point at a tracked directory instead of
an artifact, and the bootstrap gate run suppresses the PR's order id, making three
order gates and ownership pass when the real Slice C runner will fail closed. The
red-first implementation also cannot be activated under the current Slice C workflow:
it executes PR-controlled code with the inherited environment and must be split across
the read-only/trusted-base boundary locked in D5.

## Findings

| ID | Severity | Tag | Locus | Finding | Suggested resolution |
|----|----------|-----|-------|---------|----------------------|
| PR-B1 | Blocker | process | `gates/drift/deferral_words.py::Scope.exists_at_head`; `contracts/gates.md` deferral rule | An artifact pointer passes whenever `git ls-tree` returns any entry. Tree mode `040000` therefore makes lines such as `optional → scripts` pass even though the contract permits an existing **file** or a named phase, not a directory. This is a fail-open bypass of FR-015. | Accept only an allowed file mode at head. Add a red test for a tracked-directory pointer, plus regular-file and named-phase controls. Decide explicitly whether a tracked symlink counts as a file. |
| PR-B2 | Blocker | process | `effective_order`; `order-fidelity-declared`; `lock.letter-tokens`; `diff-within-owned-paths`; PR #22 branch | The handoff's vacuous pass uses `order_id=None`. That is correct only for a non-order context, where `pr-links-order` owns classification. PR #22 is on `wo/wo-20261004-factory-slice-b`; Slice C derives `order_id=wo-20261004-factory-slice-b` from that ref. Because the branch carries amendments and verdicts but no `WorkOrder`, all three order gates, `catalog-test-linkage`, and `pr-links-order` fail closed. The manual run is therefore not equivalent to the real PR run. | Record a valid immutable work order for the bootstrap branch or define and test an explicit FR-037 bootstrap-order mechanism. Re-run with the order id derived from the PR head ref. Keep the current fail-closed behavior when an identified order is absent. |
| PR-B3 | Blocker | product | `gates/drift/red_first.py`; D5 / FR-022a; current Slice C workflow | `red-first-proof` extracts and executes both trees, including PR-head pytest code. `subprocess.run` receives no `env`, so that code inherits the caller's complete environment. In the current Slice C workflow the gate also runs from head with status-write authority. This violates the 2026-10-05 lock that main's gate code judges head as data and PR-head code never runs with status-write permission. | Do not activate this gate in the current workflow. Complete the D5 split: execute head tests only in the no-secret, read-only evidence job; have main-pinned trusted code validate the bound evidence and publish statuses. Treat the evidence as hostile and fail closed on tampering or missing results. |
| PR-B4 | Should-fix | process | `gates/drift/red_first.py::BOOTSTRAP` | The child bootstrap iterates and mutates `os.environ` outside `factory.config` to remove `PYTEST_*`. This is an environment read outside the typed configuration boundary; it also sanitizes only pytest controls while every other inherited value remains visible to PR code. | Move environment construction to the typed execution boundary and pass an explicit minimal allowlist to the child. Preserve enough variables for the locked environment while excluding credentials and ambient pytest/Python controls. |

## Gate fidelity

- `order-fidelity-declared` implements the accepted pinned rule: locked and re-locked
  rows only; every qualifying bold span is an independent, case-insensitive
  whole-phrase token; multiword spans are not split. Numeric/unit-only spans, spans
  shorter than three characters, the status keyword, and the generic stop list are
  excluded. Goal ids, task OD tags, and task-path/owned-path intersections are covered.
- `lock.letter-tokens` uses rename detection off, ignores bus/Markdown and
  comment-only lines, checks per-file removal, allows a move only through an added code
  line, applies exact/min/max numeric direction, and rejects registered substitutes.
- `catalog-test-linkage` reads pytest and eval evidence from regular git blobs at head.
  Eval references use `eval:<path>#<case-id>`; absolute/dot-segment paths, tracked
  symlinks, unsupported types, malformed YAML/JSON/JSONL, wrong shapes, and bad entries
  all block. Added/edited auto rows need evidence; effective-order rows need resolving
  evidence rather than `planned`.
- `red-first-proof` judges new or changed test functions, overlays changed test support
  onto base, distinguishes qualifying added-name collection failures from broken-base
  failures, requires head green, and treats no changed tests as a pass. The whole-repo
  materialization is necessary for root-level test configuration.
- `test-seam-ban` and `decision-request-no-ids` are changed-line scoped and preserve the
  accepted test-code and untouched-request exemptions.
- `factory-check-intent` passes with 81 mapped intents. Coverage counts only an
  importable, successful registered check or `kind: human, status: exists`.
  `--coverage` is report-only; `--coverage --require-target` blocks below 90%.
- PR-B1 is the remaining direct contract bypass. PR-B2 is the context/integration
  failure that the bootstrap run hides.

## Order-context and owned-path judgment

The implementation's behavior is internally consistent:

- `order_id=None` passes order-specific gates because another gate classifies the PR.
- A named order absent from the head bus fails closed.

The second case is the correct one for PR #22. A direct probe using the branch-derived
order id failed `order-fidelity-declared`, `lock.letter-tokens`,
`catalog-test-linkage`, and `diff-within-owned-paths`, each naming the absent order.

The manual ownership equivalent itself passes: all **37** pre-review changed paths
match amendment-04's effective `owned_paths`. Frozen CP0 source and existing fixture
paths are untouched. `scripts/factory/gates.yaml` is unchanged. `acceptance.md`
changes only the Slice B evidence rows plus the expressly amended lifecycle/schema
wording. `tasks.md` changes Slice B checkboxes and the expressly amended sprint-close
line under T081.

## Spec and contract edits

- FR-023 and SC-005b correctly say a human mapping counts only at
  `kind: human, status: exists`; `planned` does not count.
- SC-005b and `contracts/cli.md` correctly keep sprint coverage report-only and make
  `--coverage --require-target` exit 1 below 90%.
- `contracts/gates.md` and `acceptance.md` agree on
  `eval:<repo-relative path>#<case-id>`, head-blob custody, strict file shapes, and
  symlink rejection.
- No governor-lock drift was found in these edits.

## Security and safety

- All production subprocess calls use argument vectors; no `shell=True` path was
  found.
- Eval evidence uses git object data, not checkout paths, and rejects symlink modes.
- Whole-tree extraction uses `tarfile`'s `filter="data"` and both trees/results live
  under `TemporaryDirectory`, so normal, exception, and timeout exits clean the
  temporary directory.
- PR-B3 is the material trust-boundary issue. Running pytest necessarily executes
  repository code and dependency hooks. The execution half must have no status-write
  credential or secrets; the trusted half must run main's gate code and never execute
  head.
- PR-B4 records the only environment access outside config. The code removes
  `PYTEST_*` names but otherwise inherits the environment.
- The real `red-first-proof` run completed in about **107 seconds** on four cores,
  consistent with the handoff's approximately 110-second cost.

## Cross-slice integration

- Current A (`d8f2c47`) merges with B (`68eb20c`) without a textual conflict. A
  supplies the GitHub adapter required by `factory check intent --coverage`; B supplies
  the drift entrypoints and `group_by_intent()` consumed by C.
- Current C (`2d7e412`) merged after the virtual A+B result conflicts in
  `specs/001-factory-v2/acceptance.md` and `specs/001-factory-v2/tasks.md`. Preserve
  A/B evidence and checkboxes, C's exact editor-advisory wording, and C's D5 task
  additions. `scripts/factory/pyproject.toml`, plan, research, and spec auto-merge.
- C's current runner derives the order id from `wo/...`, exposing PR-B2. Its
  `pr-links-order` gate also blocks this branch because no base work-order message
  exists. FR-037 retro will reproduce this unless bootstrap order identity is defined.
- C's current workflow still has the unsafe head-code/status-write topology. The D5
  plan delta explicitly assigns a post-A/B split of `red_first.py`; those changes must
  land before the factory statuses are activated.
- `factory-status-test` is still absent from current A, B, and C, and D6 remains an
  open human decision governing activation around C's bootstrap merge.

## Verification record

| Check | Result |
|-------|--------|
| Worktree setup discovery | Checked repository root and worktree; no `.cursor/worktrees.json`, so setup was skipped. |
| Locked sync | PASS — `nix develop ../.. -c uv sync --locked`; 25 locked packages installed. |
| Accepted-test immutability | PASS — `git diff a68b95d HEAD -- scripts/factory/tests` is empty. |
| Full `pytest -q` | **509 passed, 62 failed** in 82.78 s. All failures are contract commands not implemented on isolated B: A 39, C 18, US7/Wave 2 5. No Slice B implementation failure. |
| CI selector | PASS — **424 passed, 147 deselected** in 56.30 s. |
| Direct Slice B gates, bootstrap context | 9/9 pass; red-first judges 130 tests, intent maps 81. Three order gates pass only because `order_id=None`. |
| Realistic missing-order probe | Correctly fail-closed: order fidelity, letter tokens, catalog linkage, and ownership all reject the absent `wo-20261004-factory-slice-b` order. |
| `ruff check` / `ruff format --check` | PASS — all checks passed; 57 files formatted. |
| `factory check schema --repo ../..` | PASS — `schema ok` before verdict-04. |
| Scope / frozen files | PASS — 37/37 paths amendment-owned; frozen CP0 files untouched; `gates.yaml` unchanged. |
| Cross-slice merge simulation | A+B clean; C after A+B conflicts in `acceptance.md` and `tasks.md`. |
