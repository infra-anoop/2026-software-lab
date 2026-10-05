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

## Triage (PR review)

Orchestrator triage of `wo-20261004-factory-slice-b.verdict-04` (reject), recorded by the Slice B worker on 2026-10-05 together with `bus/orders/wo-20261004-factory-slice-b/amendment-05.yaml`. Context: governor lock **D5** (trusted-base CI). Its design is on Slice C's branch (`plan.md` § CI topology and trust boundary, `contracts/gates.md` § Evidence bundle, `PLAN_DELTA.md`). Phase 1 adds red tests only. No accepted test changes.

| Finding | Disposition | Phase 1 tests |
|---------|-------------|---------------|
| PR-B1 | **Fix.** A `→` pointer counts only for a regular file blob at head (mode `100644` / `100755`) or a named phase. A tracked directory, a tracked symlink (whatever it points at) and a gitlink do not count, consistent with eval evidence | `tests/unit/gates/drift/test_deferral_pointer_targets.py`: 9 red, 5 green controls |
| PR-B2 | **Investigate and propose** (Slices A, B and C). No order file is added yet | None. Proposal below |
| PR-B3 | **Fix within D5.** `red_first` becomes the evidence producer for the read-only job. It is not activated in any status-writing workflow. The trusted-side validator is Slice C's (T094–T097) | None. The bundle shape is not pinned (below) |
| PR-B4 | **Fix.** The child environment comes from an explicit minimal allowlist at the typed config boundary. Credentials, `GITHUB_*` / Actions tokens, unlisted names and ambient `PYTEST_*` / `PYTHON*` controls never reach the child. Slice B code holds no environment access | `tests/unit/gates/drift/test_red_first_child_env.py`: 13 red, 3 green |

### PR-B1 tests

- **Red (9).** A pointer to a tracked directory blocks in five forms: root-relative, trailing slash, the feature directory, a Markdown link, and file-relative (`../demo-feature`). A pointer to a tracked symlink blocks in three cases: to a tracked file, to a tracked directory, and to a file outside the repo. A pointer to a gitlink (`160000`) blocks. Each fixture asserts the tree mode it builds.
- **Green controls (5).** A regular file passes when cited root-relative, as a Markdown link, or file-relative. An executable file (`100755`) passes, and so does the named phase `→ plan`.

### PR-B4 tests

- **Approach.** The fixture's new test is red on base by assertion (buggy `clamp`). On head it also asserts that no variable in its environment carries a canary value. If a canary leaks, the test fails on head and the gate blocks. The gate test sets one canary in the caller's environment and expects a pass.
- **Red (12).** Each of these reaches the child today: `GITHUB_TOKEN`, `GH_TOKEN`, `GITHUB_PAT`, `ACTIONS_RUNTIME_TOKEN`, `ACTIONS_ID_TOKEN_REQUEST_TOKEN`, `ACTIONS_ID_TOKEN_REQUEST_URL`, `FACTORY_GITHUB_APP_PRIVATE_KEY`, `INFISICAL_TOKEN`, `PYTHONPATH`, `PYTHONSTARTUP`, `PYTHONWARNINGS`, and `LAB_SERVICE_API_KEY`. The last is a name no list knows, so only an allowlist excludes it.
- **Red (1).** A text scan of `factory/gates/drift`, `factory/intent` and `cli/intent.py` finds environment access, including inside the child bootstrap source (`red_first.py` lines 42–43).
- **Green (3).** The no-canary control passes, and so do `PYTEST_ADDOPTS` and `PYTEST_PLUGINS`. Both are stripped today by the child-side deletion that PR-B4 removes, so they guard the rewrite.

### Evidence-producer shape: not pinned, so no tests

Slice C's `contracts/gates.md` § Evidence bundle pins only this: a Pydantic-modelled JSON document with at least `schema_version`, `base_sha` and `head_sha`, plus, for red-first, each node id with its base and head outcome "and the base error class the red-first rule needs". It also fixes the trusted side's fail-closed reasons. `PLAN_DELTA.md` (M1, L1) places the model, its size limit and any `GateContext` field in T097 as a CP0 frozen-interface amendment. Before producer tests can be written, these need pinning:

1. **Per-test record.** Its key names and outcome vocabulary: call `passed` / `failed` / `skipped`, setup error, not collected, parametrized cases.
2. **Base error class.** Is it a class the producer assigns, or the raw facts (missing module and symbol names from the collection error)? Deciding "a name the PR adds" needs the diff, and every producer output is forgeable anyway. So the trusted judge should derive the class from raw facts plus git data (recommended).
3. **Run-level failures.** How a base or head run that did not complete is represented (crash, timeout, pytest abort).
4. **Unparseable test files.** How a head test file that does not parse is represented. The gate blocks on this today.
5. **Container.** The `schema_version` value, the file name inside the artifact directory, the model's module, and the size-limit setting name.
6. **Owner.** T097 (Slice C) says it splits `red_first.py` into producer and judge after A and B merge into C. This triage gives the producer to Slice B. One owner is needed, and the model has to be pinned before either side writes tests.

### PR-B2 investigation

Method: a throwaway worktree of this branch at `55dfa3f`. It ran Slice B's gates (this package) and Slice C's PR gates (C's package at `62e449d`) with `order_id = wo-20261004-factory-slice-b`, PR 22, and base `origin/main`. Messages were built through the frozen bus models.

| Gate | No order (today) | + order | + order, claim, handoff |
|------|------------------|---------|--------------------------|
| `pr-links-order` (C) | block | pass | pass |
| `order-blocked-on-open-human-od` (C) | block | pass (`depends_on_decisions: []`) | pass |
| `spawn-concurrency-cap` (C) | block: no claim | block: no claim | pass |
| `verdict.reviewer-family-differs` (C) | block: no handoff | block: no handoff | pass (openai vs anthropic) |
| `verdict.inputs-isolated`, `bus.immutable` (C) | pass | pass | pass |
| `order-fidelity-declared`, `lock.letter-tokens` (B) | block | pass (no lock touched) | pass |
| `diff-within-owned-paths` (B) | block | block: `PR_REVIEW_SLICE_B.md` is outside amend-04 (amend-05 adds it) | same |
| `catalog-test-linkage` (B) | block | block: gate-id `checks` have no catalog row (W1) | same. With catalog-row `checks`, only `seed.substitution_undeclared` blocks (evidence `planned`, T049) |

Findings:

- **No gate needs the order in the branch's first commit.** `pr-links-order`, Slice C's `order-blocked-on-open-human-od` / verdict gates and Slice B's `effective_order` read the bus at head. Slice A's lifecycle (`load_order`) reads the order at the branch tip. `spawn-concurrency-cap` replays `claimed_at` timestamps, not commit order. Only the writer, `factory order issue`, makes the order the first commit.
- **An order alone is not enough.** The cap gate needs a `Claim`, and the verdict-family gate needs a bus `Handoff`. None of the three bootstrap branches carries either.
- **Side effects of adding the order now:**
  - Slice A's scorecard takes `issued_at` from the commit that added `order.yaml`. A reconstructed order would move the Wave 1 start to its commit date (W3).
  - `size_minutes` must be at most the 60-minute horizon, so the true slice size is not representable (W4).
  - Spec Open Decisions (D1–D6) are not bus decisions, and `main`'s bus has none. Any `depends_on_decisions` entry therefore blocks as "unknown decision", so the order must list none.

### PR-B2 proposal (for the orchestrator, all three slices)

Minimal mechanism: per bootstrap branch, add three immutable bus messages in one commit at the branch tip. All are ordinary, schema-valid messages, so no frozen interface changes.

1. **`order.yaml`.** Reconstructed from the packet's Goal, Owned paths, Tasks, Stop conditions and locks, with `actor: orchestrator`, `actor_verified: false`, `size_minutes: 60` and `depends_on_decisions: []`. `refs` holds the packet path and `FR-037`, and a header comment says "FR-037 bootstrap; reconstructed <date>; true size exceeds the horizon". The amendments already on the branch then apply on top, as they do now.
2. **`claim.yaml`.** `claimed_at` is the first worker commit on the branch (for Slice B, `236ab09`, 2026-10-04T19:14:28Z), with the same bootstrap comment.
3. **`handoff.yaml`.** A run-complete summary pointing at the handoff Markdown, `author_model` = the implementer model.

Decisions it needs:

- **`checks`: gate ids or catalog row ids?** See W1.
- **Wave 1 start date.** Either accept the scorecard shift as disclosed, or have the retro use the packet date. Backdating commits is not proposed.

Red tests the mechanism needs (owners in brackets):

- [B] Order gates with a bootstrap order added at the tip, not as the first commit, and amendments that precede it in history. Fidelity, letter tokens, ownership and catalog linkage judge the effective order, not `order_id=None`.
- [C] `pr-links-order`, `spawn-concurrency-cap` and the verdict gates pass with order, claim and handoff added in one tip commit, and still fail closed when any one of the three is missing.
- [A] Lifecycle and board derive a state for a branch whose order, claim and amendments were all added after its verdicts. Scorecard behaviour for that order is pinned either way the Wave 1 start decision goes.
- [all] `factory check schema` accepts the three messages, and `bus.immutable` stays green because the commit only adds files.

### Worker-found items (not in verdict-04; for orchestrator triage)

- **W1: `checks` semantics diverge across slices.** `data-model.md` says `checks` holds "gate ids or catalog row ids". Slice B's `catalog-test-linkage` blocks every `checks` id without a catalog row, gate ids included. Slice A's lifecycle requires a `factory/<id>` status for every `checks` id, catalog row ids included. Proposal: each consumer judges only its own kind. Registered gate ids need statuses (A) and catalog row ids need evidence (B), and an id that is neither is refused when the order is issued. The accepted test `test_blocks_when_the_orders_catalog_row_is_deleted` uses a catalog id and still holds. This would be a new Slice B fix plus a test.
- **W2: ownership.** `PR_REVIEW_SLICE_B.md` arrived through the review merge and is outside amend-04. Amend-05 adds it with Triage-section line scope. The real-order-id run caught this; the `order_id=None` run hid it.
- **W3: scorecard date.** Covered under PR-B2.
- **W4: horizon.** Covered under PR-B2.
- **W5: the allowlist is defence in depth, not the boundary.** A child can still read `/proc/<parent pid>/environ` and the runner's files. The D5 boundary is the read-only job: no secrets, and no status write. The read-only job holds `ACTIONS_RUNTIME_TOKEN` for the artifact upload, so head code can rewrite the bundle. That is already disclosed in `PLAN_DELTA.md` (H1).

### Phase 2 requests

- **R1.** Owned paths for an additive child-environment builder in `factory/config/settings.py` (+ `__init__.py` export). This is CP0-frozen, and the env read has to sit there (I-A3).
- **R2.** A pinned evidence-bundle model (items 1–6 above) and one owner before producer tests are written.

### Orchestrator decisions on this triage (2026-10-05, `amendment-06.yaml`)

| # | Decision | Applied in phase 1 |
|---|----------|--------------------|
| 1 | **PR-B2 accepted as proposed, Slice B only.** The branch tip gets a commit with three schema-valid messages: an order, a claim and a handoff. The order is an FR-037 bootstrap: `actor_verified: false`, `depends_on_decisions: []`, and `checks` lists gate ids only, reconstructed from the packet DoD. The claim's `claimed_at` is the first worker commit. The handoff points at the handoff doc. The scorecard's Wave 1 start distortion is accepted and corrected by hand in the retro. The messages need no tests | `bus/orders/wo-20261004-factory-slice-b/{order,claim,handoff}.yaml`. `checks` and `size_minutes` are below |
| 2 | **`checks` kinds.** `catalog-test-linkage` judges only catalog-row ids. A registered gate id is not a catalog miss, and an id that is neither still blocks. The Slice A side is follow-up task T105 | `tests/unit/gates/drift/test_catalog_check_kinds.py`: 4 red, 1 green guard. T105 added to `tasks.md` |
| 3 | **R1 approved.** An additive CP0 frozen-interface amendment to `factory/config/settings.py` adds a child-environment allowlist builder, the only place that reads the environment, with no signature changes. The `/proc` and upload-token residuals stay as disclosed in Slice C's `PLAN_DELTA.md` | Owned path added in amend-06 for phase 2 |
| 4 | **Evidence bundle: Slice C owns it (T097).** `red_first` only returns raw per-test facts as a plain value: node id, base and head outcome, raw error text. No bundle-shape tests | Minimal seam test `tests/unit/gates/drift/test_red_first_facts.py` (`collect_facts(ctx)`): 2 red |

**Order `checks` (gate ids, one per DoD or packet line):**

| Gate | Packet line it enforces |
|------|-------------------------|
| `red-first-proof` | DoD "Red first" |
| `catalog-test-linkage` | DoD "`acceptance.md` evidence filled (real test ids)" |
| `diff-within-owned-paths` | DoD "checkboxes for this slice's tasks only"; § Owned / Forbidden paths |
| `pr-links-order` | DoD "Commits on the packet branch only" |
| `order-fidelity-declared`, `lock.letter-tokens` | § Fidelity (constitution §I, required) |
| `verdict.reviewer-family-differs`, `verdict.inputs-isolated` | DoD "Handoff … (bootstrap verdict input, FR-037)" |

Two DoD items have no registered gate: "pytest green / ruff / type hints / no `os.getenv`" (the `Factory tests` job check and ruff) and the CP0 seeds suite. Every other registered P1 gate still judges this PR as a required check; it is just not part of this order's acceptance.

**`size_minutes`.** The schema has free-text `refs`, so the order's `refs` states the true size: about 19.5 h wall-clock from the claim (`236ab09`) to the pre-PR head (`68eb20c`), plus the rework. `size_minutes` is `1`, the schema minimum.

**`locks`.** The order's `locks` are the packet's § Fidelity table, all at letter fidelity, each with the literal tokens Slice B's code carries:
- red-first rule: `base broken`;
- deferral-words rule: the six words;
- decision-request id rule: the five id patterns.

The packet's "Governor locks required" table (cap, horizon, reviewer family, identity) is context this slice does not implement. A first draft declared the reviewer-family and identity decisions as letter locks, and `lock.letter-tokens` rightly blocked: no Slice B code line carries the reviewer-family value. That draft was replaced before push.

### Worker-found item W6 (for orchestrator triage)

- **W6: one import-red file hides every other test in the run.** On base, `red_first` runs all of a project's judged node ids in one pytest call. When a new test file is red because it imports a module the PR adds, its collection error interrupts the whole run before any test executes. A sibling assertion-red test then reads "not collected on base", and the gate blocks a valid PR. A probe on the current gate put `tests/test_clamp.py` (assertion-red) and `tests/test_money.py` (imports the added `app.money`) in one PR. Result: `test_clamp_caps_high: base broken, not red: not collected on base`. The accepted tests cover each case only on its own. Proposed fix: a red test with both files in one PR expecting a pass, and phase 2 runs by file (or deselects within files) so that one file's collection error cannot suppress another's tests. The `collect_facts` seam tests use one file per case so they do not depend on this fix.
- **W6 at full scale.** The first gate run on this PR with the real order (head `dacf2c0`, not pushed) put a module-level `from factory.gates.drift import red_first` in `test_red_first_facts.py`. Its base collection error interrupted the base run, and about 150 accepted, previously red Slice B tests read "base broken, not red: not collected on base". The seam test now imports inside the test body, the way every accepted test reaches gates through `factory.api`. The gate defect stands.
- **W7: a module the PR adds, imported from its package, reads as base broken.** On base, `from factory.gates.drift import red_first` fails with `ImportError: cannot import name 'red_first' from 'factory.gates.drift'`. `red_first` is a module the PR adds (`src/factory/gates/drift/red_first.py`), so by the red-first rule this is red. The gate classifies it as "base broken", because its added-name check does not treat a submodule as a name the package adds. Proposed fix: a red test for that import form expecting a pass, and phase 2 counts a submodule the PR adds under a package as an added name.

**Orchestrator triage of W6/W7 (2026-10-05).** The order's `locks` are accepted as pushed, matching the packet's Fidelity table. W6 and W7 are approved as one root cause under §J: red-first misclassifies base-side collection and import errors. The single base run collapses on a per-file error, and an import error is not attributed to its own test. There is one regression test, `tests/unit/gates/drift/test_red_first_base_errors.py`, parametrized:
- **W6:** a sibling file that fails import on base, beside an assertion-red test.
- **W7:** `from app import money`, where the PR adds `app/money.py`.

Each case asserts that the gate passes the valid PR, then checks the raw `collect_facts` record for each test. Both are red now by assertion: W6 because `test_clamp_caps_high` is "not collected on base", W7 because the import reads "base broken". The fix is task T106 in phase 2. The T\* review is one final round 4, covering phase 1, amendment-06, the `checks`-kinds tests, this test and the fixture amendment that follows the Slice A merge.
