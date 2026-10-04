# Tasks: Factory v2 — intent-fidelity gates, typed bus, derived board

**Input**: `specs/001-factory-v2/` — [`plan.md`](./plan.md) (approved 2026-10-03), [`spec.md`](./spec.md), [`data-model.md`](./data-model.md), [`contracts/`](./contracts/), [`research.md`](./research.md), [`quickstart.md`](./quickstart.md), [`acceptance.md`](./acceptance.md).

**Tests (constitution §V):** `factory` is executable repo tooling, so tests are required. Every contract hook and every `how: auto` catalog row becomes a failing test before its implementation. `hybrid`/`human` rows get evidence tasks, not fake pytest.

**Open Decisions:** none open. D1 waived (P3 rows → sprint 03), D2 = 70%, D3 = GPT reviews, D4 = GitHub App during Wave 1. The `[HITL]` tasks below are governor ops steps (account and settings work agents cannot do), not content decisions.

**Path shorthand used in prose only:** "the package" = `scripts/factory/src/factory/`; "tests" = `scripts/factory/tests/`. Task lines spell out full paths.

## Format: `[ID] [P?] [HITL|OD:D#|POLICY?] [Story] Description`

- **[P]**: parallel-safe (disjoint files, no incomplete dependency)
- **[HITL]**: governor ops step; implement stops and asks in plain language
- **[POLICY]**: process adjudication the orchestrator may do under written policy
- **Slice A / B / C** (plan § Phased delivery) = worker lanes with disjoint owned paths; at most 3 workers run at once

## Wave 1 bootstrap rule (FR-037)

Wave 1 builds the gates that would otherwise govern it. So Wave 1 work runs on lab packets (`notes/packets/`) with branch `wo/<order-id>` naming. Each Wave 1 PR carries a **bootstrap verdict** from a GPT-family reviewer that lists the manual equivalents run (red-first shown by hand, owned paths checked by hand, no test seams). From the moment slice A's `factory order issue` and `factory claim` merge, new orders go through them. Phase 9 replays every P1 gate over all Wave 1 PRs.

## Integration checkpoints (review P7)

| Checkpoint | Target (working day from first order) | Max | Proof |
|------------|------|-----|-------|
| **CP0 — contracts frozen** | end of day 1 | day 1 | Phase 2 checkpoint green; interfaces in `scripts/factory/src/factory/api.py` change only via amendment |
| **CP1 — slices green alone** | end of day 2 | day 4 | each slice's own contract/unit tests green; `factory gate run` over the seeds suite runs end to end |
| **CP2 — live as required checks** | end of day 3 | day 5 | `factory-gates.yml` reports one `factory/<gate-id>` status per P1 gate on a real PR; one real order issued → claimed → PR → verdict, all derived on the board |

SC-013: Wave 1 exits by CP2 within 5 working days of the first order; dates come from run events.

---

## Phase 1: Setup (orchestrator tiny glue — P0)

**Purpose**: project skeleton so three workers can start against frozen contracts.

- [ ] T001 Create uv project `scripts/factory/pyproject.toml` (Python 3.12; deps `pydantic>=2`, `typer`, `httpx`, `pyyaml`; dev group `pytest`, `ruff`; console script `factory = "factory.cli.app:main"`; src layout `scripts/factory/src/factory/`) and commit `scripts/factory/uv.lock` from `uv sync`
- [ ] T002 Create repo config `factory.toml` (keys: `bus_dir = "bus"`, `spec_roots = ["specs"]`, `app_roots = ["apps"]`, `rule_paths` = constitution, `AGENTS.md`, `.cursor/rules/**`, `docs/agent-os/**`, `scripts/factory/gates.yaml`, `scripts/factory/rubrics/**`; `concurrency_cap = 3`; `autonomy_horizon_minutes = 60`; `stale_multiplier = 3`; `[families]` map of model-name prefixes → family, e.g. `claude` → `anthropic`, `gpt` → `openai`, `gemini` → `google`; `governor_login`) and the typed loader `scripts/factory/src/factory/config/settings.py` (Pydantic model; no `os.getenv` outside this module — I-A3)
- [ ] T003 [P] Exclude the factory from the legacy script test step: add `--ignore=scripts/factory` to the `pytest scripts/` line in `.github/workflows/verify-source.yml`
- [ ] T004 [P] Create `.github/workflows/factory-gates.yml` on `pull_request` (jobs: `factory-tests` running `uv sync --locked` + `uv run pytest` in `scripts/factory`; placeholder `factory-gates` job running `factory gate run --pr ${{ github.event.number }}` that is allowed to fail until CP2)
- [ ] T005 [P] Create empty bus layout `bus/orders/.gitkeep`, `bus/decisions/.gitkeep`, `bus/corrections/.gitkeep`, `bus/postmortems/.gitkeep`

---

## Phase 2: Foundational — contract freeze (orchestrator — P0, CP0)

**Purpose**: freeze every cross-slice interface and the shared fixtures (review P7). After CP0, changes to these files need an order amendment.

**⚠️ No slice work starts until this phase's checkpoint passes.**

- [ ] T006 Envelope + every message kind as Pydantic v2 models in `scripts/factory/src/factory/bus/models.py`, with fields verbatim from `data-model.md`: envelope (`schema_version: 1`; `kind` ∈ order, amendment, handoff, verdict, decision_request, decision_lock, correction, override, claim, release, run_complete; `actor` ∈ governor, orchestrator, worker, reviewer; `actor_model` required when actor ≠ governor); `model_config = ConfigDict(extra="forbid")`; forbidden keys `status`, `state`, `done`, `progress` rejected anywhere in a message (FR-003); WorkOrder `goal` ≤ 3 sentences, `owned_paths` non-empty, `size_minutes` ≤ config horizon, `stop_conditions` non-empty, Lock `fidelity: waived` requires `waiver_ref`; Verdict findings `severity` ∈ `blocker`, `debate`, `later`, `nit` and `tag` ∈ product, process, arch; Override `reason` non-empty; id patterns (`wo-YYYYMMDD-<slug>`, `<order-id>.amend-NN`, `<order-id>.verdict-NN`, `<order-id>.override-NN`, `corr-YYYYMMDD-<slug>`)
- [ ] T007 Bus loader + layout resolver in `scripts/factory/src/factory/bus/store.py` (paths per `contracts/messages.md` § Layout; `load_all(repo, ref) -> list[Message]`; read-only)
- [ ] T008 JSON Schema export `factory check schema --write` → `scripts/factory/schemas/<kind>.schema.json`, plus `factory check schema` (validate every bus file and fail when schemas are stale) in `scripts/factory/src/factory/cli/checks.py`
- [ ] T009 Gate registry model + loader in `scripts/factory/src/factory/gates/registry.py` (fields from `data-model.md` § Gate plus `entrypoint: "module:function"`; rule `class: governor-only` ⇔ `category ∈ {spend, secrets, irreversible, governor_decision}`), and `scripts/factory/gates.yaml` listing every P1 gate id from `contracts/gates.md` with class, category, intents, scope, entrypoint, `priority: P1`; add `entrypoint` to the Gate line of `specs/001-factory-v2/data-model.md`
- [ ] T010 Frozen cross-slice interfaces in `scripts/factory/src/factory/api.py`: `GateContext` (repo path, base sha, head sha, PR number?, order id?, config, bus snapshot), `GateResult` (gate id, passed, messages, per-intent ids), `run_gate(gate_id, ctx) -> GateResult` (dispatch via registry entrypoint, no override logic), `LifecycleSnapshot` + `OrderState` enum (issued, claimed, in_review, accepted, rejected, merged, released; overlays stale, blocked_on_governor), `GitHubPort` Protocol (list PRs by head, PR reviews, check runs, create PR, set commit status), `IdentityPort` Protocol (`is_governor_verified(message, pr) -> bool`)
- [ ] T011 CLI skeleton `scripts/factory/src/factory/cli/app.py` registering every command in `contracts/cli.md` from per-slice modules `cli/board.py` (A), `cli/orders.py` (A), `cli/intent.py` (B), `cli/gates.py` (C), `cli/checks.py` (P0/C), `cli/mining.py` (US7); unimplemented commands exit `3` with "not implemented"; common `--json` and `--repo` options; exit-code constants `0/1/2/3/4` in `scripts/factory/src/factory/cli/exit_codes.py`
- [ ] T012 Shared fixture builder `scripts/factory/tests/fixtures/repo_builder.py`: temp bare `origin` + clone; helpers `write_message`, `commit`, `branch`, `push`, `make_pr` (backed by `FakeGitHub` implementing `GitHubPort` in `scripts/factory/tests/fixtures/fake_github.py`); `base_head_pair(base_files, head_files)` for gate tests; sample messages of every kind in `scripts/factory/tests/fixtures/messages/`
- [ ] T013 Contract test for exit codes of every command in `scripts/factory/tests/contract/test_cli_contract.py` (red except `check schema`): one case per refusal row of `contracts/cli.md`
- [ ] T014 Seeds suite skeleton `scripts/factory/tests/seeds/test_seeds.py` — one red test per SC-002 seed (`undeclared_substitution`, `declared_lock_violated`, `hidden_deferral`, `not_red_first`, `test_seam`, `outside_owned_paths`, `jargon_to_governor`, `catalog_unlinked`), each building its violating fixture with `repo_builder` and asserting `run_gate(<gate-id>, ctx).passed is False` and the gate id appears in the message
- [ ] T015 Unit tests for models in `scripts/factory/tests/unit/test_bus_models.py` (forbidden keys at any depth; extra keys rejected; each constraint quoted in T006) — green at CP0 together with T006–T008
- [ ] T016 Write review packet `notes/packets/<date>-factory-v2-p0-test-review-t.md` and **spawn** the T* reviewer (GPT family) on T013–T015 per `docs/agent-os/SPAWN_REVIEWER.md` + `TEST_REVIEW_PROMPT.md`; triage into `specs/001-factory-v2/TEST_REVIEW.md` before slice packets go `ready`

- [ ] T016a Write the three slice work packets `notes/packets/<date>-factory-v2-slice-{a,b,c}.md` from `notes/packets/_TEMPLATE.md`: owned paths from § Owned paths per slice, DoD = that slice's tests green + catalog evidence filled, Fidelity table (letter for every named lock: cap 3, 70% mutation, GPT reviewer family, GitHub App identity, Semgrep CE / import-linter / mutmut 3), bootstrap-verdict requirement (FR-037)

**Checkpoint CP0**: `factory check schema` exits 0 on the sample messages; JSON Schemas generated; contract + seeds tests collected and red for unimplemented commands; T* triaged.

---

## Phase 3: User Story 1 — See at a glance (P1) 🎯 MVP · Slice A

**Goal**: one board derived from git + PR + check reality.

**Independent test**: fixture repo with orders in every lifecycle state → `factory status --json` equals the expected derivation; no bus file has a status field.

### Tests (write first, must fail)

- [ ] T017 [P] [US1] Contract test `scripts/factory/tests/contract/test_status.py`: fixture with one order per state (issued, claimed, in_review with running checks, accepted, rejected, merged, released, stale, blocked_on_governor); assert board JSON sections in flight / blocked / waiting on governor (plain-language prompt text) / ready queue / overrides per gate / unverified governor actions — catalog `board.matches_reality`
- [ ] T018 [P] [US1] Unit tests for derivation rules `scripts/factory/tests/unit/test_lifecycle.py` (rules verbatim from `data-model.md` § Lifecycle: stale = claimed, no PR, no commit for > `3 × size_minutes`, still counts toward cap; `released` = release event OR PR closed unmerged; ready queue = issued ∧ ¬claimed ∧ ¬blocked_on_governor)
- [ ] T019 [P] [US1] Unit test `scripts/factory/tests/unit/test_github_adapter.py` against recorded REST responses in `scripts/factory/tests/fixtures/github_recorded/`
- [ ] T020 [P] [US1] Unit test `scripts/factory/tests/unit/test_no_bookkeeping.py`: commits whose only change rewrites status or SHAs inside `bus/` are counted — catalog `history.no_bookkeeping`

### Implementation

- [ ] T021 [P] [US1] GitHub REST adapter implementing `GitHubPort` with httpx in `scripts/factory/src/factory/github/rest.py` (token from typed settings; the only module that calls GitHub — I-A4)
- [ ] T022 [US1] Lifecycle derivation `scripts/factory/src/factory/lifecycle/derive.py` → `LifecycleSnapshot` (reads `bus.store` on each `wo/*` branch + `GitHubPort`; writes nothing)
- [ ] T023 [US1] Board rendering `scripts/factory/src/factory/board/render.py` (markdown + JSON) and `factory status`, `factory decisions` in `scripts/factory/src/factory/cli/board.py`
- [ ] T024 [US1] Bookkeeping-commit counter `scripts/factory/src/factory/metrics/history.py` (consumed by `factory scorecard`)
- [ ] T025 [US1] Update `acceptance.md` evidence for `board.matches_reality`, `bus.no_handwritten_status`, `history.no_bookkeeping` with the test ids above

**Checkpoint**: `factory status` shows real orders; T017–T020 green.

---

## Phase 4: User Story 2 — Hand off and trust the result (P1) · Slice A (+ C for PR gates)

**Goal**: orders are issued on their own branch, claimed atomically under cap 3, handed off with deviations, opened as one PR, and accepted on checks + a different-family verdict.

**Independent test**: issue → claim → handoff → PR → verdict on a fixture remote; the 4th claim is refused; an order depending on an open governor decision is refused; a handoff with failing checks is refused; a same-family verdict is rejected.

### Tests (write first, must fail)

- [ ] T026 [P] [US2] Contract test `scripts/factory/tests/contract/test_orders.py` — `order new` refuses `size_minutes` > 60 and a touched named lock without fidelity (seed `undeclared_substitution`); `order issue` creates `wo/<id>` whose first commit adds only `bus/orders/<id>/order.yaml`, never pushes `main`, refuses an order whose `depends_on_decisions` has an open `who: human` decision (exit 2, decision named in plain language) — catalogs `seed.substitution_undeclared`, `handoff.open_od_refused`
- [ ] T027 [P] [US2] Contract test `scripts/factory/tests/contract/test_claim.py` — claim is a fast-forward push (two concurrent claims of one order: exactly one succeeds); refuses at `active ≥ 3`, on owned-path overlap with an active order, when blocked on governor, when already claimed; `release` frees capacity — catalog `handoff.concurrency_cap` (claim half)
- [ ] T028 [P] [US2] Contract test `scripts/factory/tests/contract/test_handoff.py` — `factory handoff` refuses while any registered gate for the order fails locally (FR-009); `deviations` key required; each open question classed `blocker_governor` or `non_blocking`; a `blocker_governor` question makes the command exit 2 with the plain-language question on stdout and puts the order under "waiting on governor" on the board (the orchestrator relays it on the worker's completion notice — US2 #3); writes `run-complete` event (`wall_minutes`, `governor_interrupts`, `cost_usd` with estimate flag, `deviations_count`) — catalog `handoff.done_requires_green`
- [ ] T029 [P] [US2] Contract test `scripts/factory/tests/contract/test_pr_and_verdict.py` — `pr open` refuses without a valid handoff and writes a body linking order + intents; `verdict` refuses reviewer family = author family (family via `factory.toml [families]`) and any input that is not a git path at a sha — catalogs `handoff.reviewer_family`, `handoff.reviewer_isolated` (machine half)
- [ ] T030 [P] [US2] Contract test `scripts/factory/tests/contract/test_bus_pr.py` — `bus pr` refuses changes outside `bus/decisions/`, `bus/corrections/`, `bus/postmortems/`
- [ ] T031 [P] [US2] Unit test `scripts/factory/tests/unit/test_scorecard.py` — scorecard from events, verdicts, overrides, corrections, decision locks: drift, first-pass acceptance, decision points per feature, governor minutes, rework loops, Wave 1 start/exit dates — catalogs `scorecard.computed`, `wave1.timebox`
- [ ] T032 [P] [US2] Unit test `scripts/factory/tests/unit/test_identity.py` — recorded-only mode marks governor actions unverified; verified mode counts a governor message only when its PR has an approving review by `governor_login`; App token minting builds a JWT from `FACTORY_GITHUB_APP_ID` + `FACTORY_GITHUB_APP_PRIVATE_KEY` and exchanges it (recorded response)
- [ ] T033 [US2] Spawn T* review for T017–T032 (packet `notes/packets/<date>-factory-v2-slice-a-test-review-t.md`); triage into `TEST_REVIEW.md` before T034

### Implementation

- [ ] T034 [US2] `order new` / `order issue` / `claim` / `release` / `handoff` / `pr open` / `verdict` / `bus pr` in `scripts/factory/src/factory/cli/orders.py` with logic in `scripts/factory/src/factory/orders/` (git plumbing via subprocess in `scripts/factory/src/factory/orders/git.py`; no business logic in the CLI module — I-A1)
- [ ] T035 [US2] Scorecard `scripts/factory/src/factory/metrics/scorecard.py` + `factory scorecard` in `scripts/factory/src/factory/cli/board.py`
- [ ] T036 [US2] Identity adapter `scripts/factory/src/factory/identity/adapter.py` (implements `IdentityPort`; mode from config: `recorded` until the App exists, then `verified`) and App token minting + repo-local git credential helper `scripts/factory/src/factory/identity/app_token.py` (1-hour installation tokens)
- [ ] T037 [US2] Secret names: add a `tooling:` section to `deploy/secrets/schema.yaml` with `factory` → Codespace target, names `FACTORY_GITHUB_APP_ID` and `FACTORY_GITHUB_APP_PRIVATE_KEY` (no values), and teach `scripts/validate_secrets_schema.py` + `scripts/test_validate_secrets_schema.py` to accept the section
- [ ] T038 [US2] Update `acceptance.md` evidence for every row tested in T026–T032

**Checkpoint (part of CP1)**: one fixture order runs issue → merge, derived end to end; T026–T032 green.

---

## Phase 5: User Story 3 — Machines catch sprint-01 drift (P1) · Slice B

**Goal**: every SC-002 seed is blocked by a drift gate.

**Independent test**: `uv run --project scripts/factory pytest scripts/factory/tests/seeds` — all 8 seeds blocked, gate id in output.

### Tests (write first, must fail)

- [ ] T039 [P] [US3] Unit tests per gate in `scripts/factory/tests/unit/gates/drift/` (one file per gate below), each with a passing and a violating `base_head_pair` fixture; seeds in T014 are the SC-002 subset
- [ ] T040 [P] [US3] Red-first edge cases `scripts/factory/tests/unit/gates/drift/test_red_first.py` (rule verbatim from `research.md` § Red-first): new test passing on base → fail; assertion failure on base → pass; import error for a symbol the PR adds → counts as red; import error for an unrelated broken module → reported "base broken", not red; PR with no new/changed tests → pass
- [ ] T041 [US3] Spawn T* review for T039–T040 (packet `notes/packets/<date>-factory-v2-slice-b-test-review-t.md`); triage before T042

### Implementation (one module each under `scripts/factory/src/factory/gates/drift/`; each registered in `scripts/factory/gates.yaml`)

- [ ] T042 [P] [US3] `red_first.py` — gate `red-first-proof`: collect node ids head vs base; run new/changed tests on base code with head tests overlaid, then on head
- [ ] T043 [P] [US3] `test_seam.py` — gate `test-seam-ban`: changed app lines under `app_roots` matching test-only branching (`PYTEST_CURRENT_TEST`, `"pytest" in sys.modules`, `TESTING`/`IS_TEST` flags, fake-key sniffing such as `startswith("sk-test")`)
- [ ] T044 [P] [US3] `owned_paths.py` — gate `diff-within-owned-paths`: every changed path matches the effective order's `owned_paths` or `bus/orders/<order-id>/**`
- [ ] T045 [P] [US3] `deferral_words.py` — gate `deferral-words-need-od`: rule verbatim from `contracts/gates.md` § Deferral-words rule (the listed words in `specs/**` and `notes/sprints/**` need an existing `D\d+`, a `→ <artifact>` pointer, or `[governor-judged]` on the same line/row; words inside backtick code spans are exempt)
- [ ] T046 [P] [US3] `fidelity.py` — gates `order-fidelity-declared` (every named lock the order's owned paths or goal touch has a Lock entry) + `lock.letter-tokens` (for `fidelity: letter`, the PR diff contains each `letter_tokens` entry and does not introduce a registered substitute; seed `declared_lock_violated`)
- [ ] T047 [P] [US3] `decision_ids.py` — gate `decision-request-no-ids`: regexes verbatim from `contracts/messages.md` (`\b[TFRPD]\d+\b`, `FR-\d+`, `SC-\d+`, `US\d+`, `§`) plus a jargon list in `factory.toml` applied to `prompt` and `options[].label`
- [ ] T048 [P] [US3] `catalog_linkage.py` — gate `catalog-test-linkage`: every `how: auto` row in any `acceptance.md` has `evidence`; rows whose id appears in the PR's order `checks` must name an existing pytest node id or eval id (not `planned`) before merge (FR-018)
- [ ] T049 [US3] Update `acceptance.md` evidence for all `seed.*` rows

**Checkpoint (part of CP1)**: seeds suite 100% green (all blocked).

---

## Phase 6: User Story 4 — Hard gates, governor not the unblocker (P1) · Slice C

**Goal**: gate framework with two classes, reasoned overrides, per-gate counts, hook twins, and PR-level gates live as required checks.

**Independent test**: drift gate overridden with reason → passes, counted on board; empty reason rejected; orchestrator override of governor-only gate rejected; a governor-only gate in a disallowed category fails registration; a hook without a CI twin fails.

### Tests (write first, must fail)

- [ ] T050 [P] [US4] Contract test `scripts/factory/tests/contract/test_gate_run.py` — `gate run --base --head` runs every registered gate, prints per-intent results, exit 1 on any un-overridden failure; override resolution per `contracts/gates.md` § Override resolution — catalogs `override.reason_required`, `override.surfaced_counted`, `override.governor_only`
- [ ] T051 [P] [US4] Unit tests `scripts/factory/tests/unit/gates/test_registry_checks.py` — `gate.fail-mode-category`, `hook-has-ci-twin` (every hook in `.cursor/hooks.json` has a registry entry with `hook_twin_of`) — catalogs `gate.fail_mode_category`, `gate.hook_has_twin`
- [ ] T052 [P] [US4] Unit tests `scripts/factory/tests/unit/gates/pr/` — `bus.immutable` (modify/delete of an existing bus file fails), `bus.no-handwritten-status`, `pr-links-order` (head `wo/<id>` + order exists), `order-blocked-on-open-human-od`, `spawn-concurrency-cap` (CI twin: replays claim events in timestamp order across all `wo/*` branches; blocks the PR whose claim exceeded 3 or that has no claim — catalog `handoff.concurrency_cap` merge half), `verdict.reviewer-family-differs` + `verdict.inputs-isolated`, `message.override`
- [ ] T053 [P] [US4] Hook tests `scripts/factory/tests/unit/hooks/test_hooks.py` — `spawn-guard` (subagentStart; advisory warning unless the prompt names a claimed `wo-…` id or a review packet, and when the last-fetched active count ≥ 3 — catalog `handoff.concurrency_cap` editor half, FR-008); `shell-guard` denies `pip install`, `gh workflow run`, `git push --force`, writes to `/etc`, `/usr`, `~/.config` outside the repo, `nix-env -i`; `owned-path-warn` warns outside owned paths; `decision-in-chat` warns per `contracts/hooks.md`; each runs offline in < 300 ms
- [ ] T054 [US4] Spawn T* review for T050–T053 (packet `notes/packets/<date>-factory-v2-slice-c-test-review-t.md`); triage before T055

### Implementation

- [ ] T055 [US4] Runner + override resolution + per-intent report in `scripts/factory/src/factory/gates/runner.py` and `scripts/factory/src/factory/gates/overrides.py` (uses `api.run_gate`; governor-only overrides need `actor: governor` and `IdentityPort` verification when mode is `verified`)
- [ ] T056 [P] [US4] PR/repo gates in `scripts/factory/src/factory/gates/pr/` (`bus_immutable.py`, `no_status.py`, `links_order.py`, `open_od.py`, `concurrency_cap.py`, `verdict.py`, `override_msg.py`) and `scripts/factory/src/factory/gates/repo/` (`fail_mode.py`, `hook_twin.py`)
- [ ] T057 [P] [US4] Hooks: entrypoints `scripts/factory/src/factory/hooks/` + `factory hook <name>` in `scripts/factory/src/factory/cli/gates.py`; `.cursor/hooks.json` registering `spawn-guard` (subagentStart), `shell-guard` (beforeShellExecution), `owned-path-warn` (afterFileEdit), `decision-in-chat` (stop) — format per `/home/vscode/.cursor/skills-cursor/create-hook/SKILL.md`
- [ ] T058 [US4] `factory override` and `factory gate run` in `scripts/factory/src/factory/cli/gates.py`; `factory check hooks|registry|immutability` in `scripts/factory/src/factory/cli/checks.py`
- [ ] T059 [US4] Make `.github/workflows/factory-gates.yml` authoritative: run `factory gate run --pr`, post one commit status `factory/<gate-id>` per gate via `GitHubPort`, publish the board in the job summary; register existing `validate-secrets-schema` (governor-only, secrets), `validate-deploy-env`, `uv-sync-locked` in `scripts/factory/gates.yaml`
- [ ] T060 [US4] Update `acceptance.md` evidence for override/gate rows

**Checkpoint (part of CP1/CP2)**: required statuses appear on a real PR.

---

## Phase 7: User Story 5 — Intent traceability (P1) · Slice B

**Goal**: presence invariant, effective coverage, per-intent PR results.

**Independent test**: drop all mappings from one intent in a fixture → `factory check intent` exits 1; mark a mapped check planned-only → coverage drops.

- [ ] T061 [P] [US5] Contract test `scripts/factory/tests/contract/test_intent.py` — presence over `specs/*/intent.yaml` + `scripts/factory/gates.yaml` + every `acceptance.md`; `--coverage` = share of intents backed by an implemented (registered, entrypoint importable), passing, non-human check or an explicit governor-judged mapping — catalogs `trace.presence`, `trace.effective_coverage`
- [ ] T062 [US5] Spawn T* review for T061 (may share the slice-B packet from T041 if written together)
- [ ] T063 [US5] `scripts/factory/src/factory/intent/coverage.py` + `factory check intent [--coverage]` in `scripts/factory/src/factory/cli/intent.py`; register `factory-check-intent`
- [ ] T064 [US5] Per-intent PR results: runner groups `GateResult` by intent ids in the job summary (`scripts/factory/src/factory/gates/runner.py` report section — coordinate: slice C owns the file; slice B supplies `intent.coverage.group_by_intent()`) — catalog `handoff.per_intent_results`

**Checkpoint CP2**: all P1 gates live as required checks after T065–T066; one real order run end to end.

---

## Phase 8: Ops — governor steps for Wave 1 [HITL]

- [ ] T065 [HITL] Governor creates the GitHub App (repo contents/PRs/checks/statuses read-write), installs it on this repo, stores `FACTORY_GITHUB_APP_ID` + `FACTORY_GITHUB_APP_PRIVATE_KEY` in Infisical (names from T037); orchestrator then flips `identity.mode = "verified"` in `factory.toml` — before Phase 9
- [ ] T066 [HITL] Governor sets branch protection on `main`: require each `factory/<gate-id>` P1 status + existing checks, require code-owner review; orchestrator snapshots settings to `deploy/github/branch-protection.json` (record only; live drift check is P3 → sprint 03 per D1)
- [ ] T067 [P] Add `.github/CODEOWNERS` naming `governor_login` on every `rule_paths` entry from `factory.toml`

---

## Phase 9: Bootstrap close — P1b (Wave 1 → 2 boundary)

**Goal**: SC-012 — prove the gates on the PRs that built them.

- [ ] T068 Contract test `scripts/factory/tests/contract/test_retro.py` — report lists each merged Wave 1 PR, each P1 gate result, and per failure a remediation order id or override — catalog `bootstrap.verdicts`
- [ ] T069 `factory retro --since <ref>` in `scripts/factory/src/factory/gates/retro.py` + `scripts/factory/src/factory/cli/gates.py`; writes `bus/postmortems/wave1-retro.yaml` via `factory bus pr`
- [ ] T070 [POLICY] Run retro; for each failure issue a remediation order or record an override with reason; no Wave 2 order is issued until every failure is dispositioned
- [ ] T071 Verify every Wave 1 PR has a bootstrap verdict (`bootstrap: true`, `manual_equivalents` listed) in its `bus/orders/<id>/verdict-NN.yaml`

**Checkpoint**: Wave 1 exit — SC-013 dates computed by `factory scorecard`.

---

## Phase 10: User Story 6 — Architecture religion (P2, Wave 2)

**Goal**: mechanical pattern lints on changed lines + pattern-catalog rubric.

**Independent test**: one seeded violation per pattern is flagged; a reviewer run cites pattern ids.

- [ ] T072 [P] [US6] Seed tests `scripts/factory/tests/seeds/test_arch_seeds.py` (one per gate: `import-layers`, `agent-has-output-type`, `banned-getenv-outside-config`, `vendor-imports-only-in-adapters`, `generic-identifier-ban` — names `utils`, `helpers`, `data`, `result`, `lab-shared-declares-consumers`, `new-dependency-needs-decision-ref`, `research-decision-has-nonsibling-alt`, `od.arch-options-have-consequences`, `od.plain-options`) — catalog `arch.patterns_flagged`
- [ ] T073 [US6] Spawn T* review for T072
- [ ] T074 [P] [US6] Semgrep CE rule pack `scripts/factory/semgrep/*.yaml` + changed-lines wrapper `scripts/factory/src/factory/gates/arch/semgrep_gate.py`
- [ ] T075 [P] [US6] import-linter contracts for `apps/*` layers in `scripts/factory/importlinter.ini` + `scripts/factory/src/factory/gates/arch/import_layers.py`
- [ ] T076 [P] [US6] Decision-reference gates in `scripts/factory/src/factory/gates/arch/decisions.py` (new dependency in any `pyproject.toml` / new pattern needs a `research.md` row with ≥ 1 non-sibling alternative; arch decision requests list services, secrets, ops steps, cost per option — I-A10)
- [ ] T077 [US6] Pattern catalog `scripts/factory/rubrics/patterns.yaml` (versioned; ids `PAT-NNN`; seeded from I-A1..I-A11) + reviewer rubric section in `docs/agent-os/SPAWN_REVIEWER.md` requiring `pattern_id` on arch findings — catalog `arch.reviewer_cites_catalog` (hybrid)

---

## Phase 11: User Story 7 — Religion-mining loop (P2, Wave 2)

**Goal**: corrections recorded, repeats propose rules immediately, post-mortem gates sprint close, rule changes need governor approval.

**Independent test**: linked correction → proposal order; `factory decisions` shows the link; rejected link withdraws the proposal; `sprint close` without a full post-mortem exits 2; rule-path PR without governor approval cannot merge.

- [ ] T078 [P] [US7] Contract test `scripts/factory/tests/contract/test_mining.py` — `correction new --links-to` writes the correction + a proposal order; next `factory decisions` batch includes the link for confirmation; a `decision_lock` rejecting the link withdraws the proposal (release event); `sprint close` refuses without a post-mortem dispositioning every correction and reviewing overrides, reversed locks, rework — catalogs `mining.repeat_proposes`, `mining.postmortem_gate`
- [ ] T079 [P] [US7] Unit test `scripts/factory/tests/unit/gates/test_codeowners_gate.py` — gate `codeowners-governor-on-rule-paths` (governor-only): rule-path changes need an approving review from `governor_login` (verified identity)
- [ ] T080 [US7] Spawn T* review for T078–T079
- [ ] T081 [US7] `scripts/factory/src/factory/mining/` (corrections, proposals, post-mortem) + `factory correction new`, `factory sprint close` in `scripts/factory/src/factory/cli/mining.py`
- [ ] T082 [US7] Gate `scripts/factory/src/factory/gates/pr/codeowners.py` + registry entry (class governor-only, category governor_decision)
- [ ] T083 [US7] Evidence: `mining.correction_recorded` (hybrid) — every governor correction this sprint has a `bus/corrections/` record; checked at post-mortem

---

## Phase 12: User Story 8 — Rules are code, context is lean (P2, Wave 2)

**Goal**: every MUST/NEVER cites a check or `[governor-judged]`; constitution 2.0; lean always-applied rules; remaining hooks.

**Independent test**: add an uncited MUST to `AGENTS.md` in a fixture → `process-rule-cites-check` fails.

- [ ] T084 [P] [US8] Unit test `scripts/factory/tests/unit/gates/test_process_rules.py` — scope verbatim from FR-032 (constitution, `AGENTS.md`, always-applied editor rules, `docs/agent-os/`); accepted forms `[check: <id>]` with an existing gate id, `[governor-judged]` — catalog `rules.cite_checks`
- [ ] T085 [P] [US8] Hook tests: `block-system-path-edits` (hook + CI twin) in `scripts/factory/tests/unit/hooks/test_hooks_p2.py`
- [ ] T086 [US8] Spawn T* review for T084–T085
- [ ] T087 [US8] Gate `scripts/factory/src/factory/gates/repo/process_rules.py`; hook `block-system-path-edits` in `scripts/factory/src/factory/hooks/` + `.cursor/hooks.json`
- [ ] T088 [US8] **Constitution 2.0 — its own order with an independent GPT verdict (FR-033):** rewrite `.specify/memory/constitution.md` to v2.0: one section per `intent.yaml` conflict resolution (shared-code rule, ambiguity split by owner, two-class fail modes, repeat-correction trigger); prose now enforced replaced by `[check: <id>]` pointers; every still-unenforceable invariant kept — catalogs `constitution.c1_shared_code` … `constitution.invariants_preserved` (hybrid; verdict is the evidence)
- [ ] T089 [US8] Lean always-applied guidance: reduce `AGENTS.md`, `.cursor/rules/agent-os.mdc`, `.cursor/rules/lab-invariants.mdc`, `.cursorrules` to pointers + not-yet-enforceable rules; move deep rules into phase-loaded skills under `.cursor/skills/` (FR-034); same order as T088 or its successor, with its own verdict

---

## Phase 13: Polish & cross-cutting (Wave 2)

- [ ] T090 [P] Mutation gate `mutation-changed-lines` (mutmut 3, **70%** of mutants killed on changed lines — D2) in `scripts/factory/src/factory/gates/drift/mutation.py`, test first in `scripts/factory/tests/unit/gates/drift/test_mutation.py`; runs in the SWV2 Models lane CI job
- [ ] T091 [P] Spec Kit hook bridge: `.specify/extensions.yml` `after_tasks` hook calling `factory check intent` and `deferral-words-need-od` so the base stays swappable
- [ ] T092 Run every `quickstart.md` section on the live repo; record results in `specs/001-factory-v2/quickstart.md` § Results
- [ ] T093 [POLICY] Sprint post-mortem `bus/postmortems/2026-10-sprint-02.yaml` via `factory bus pr`: disposition every correction; review overrides per gate, reversed locks, rework; record `routing.zero` and `capture.budget` evidence (hybrid); scorecard vs `intent.yaml` targets; then `factory sprint close`

---

## Dependencies & execution order

- **Phase 1 → Phase 2 (CP0)** block everything.
- After CP0, three lanes run in parallel (cap 3):
  - **Slice A**: Phase 3 → Phase 4 (US1, US2)
  - **Slice B**: Phase 5 → Phase 7 (US3, US5)
  - **Slice C**: Phase 6 (US4)
- **T064** needs T055 (slice C runner) and T063 (slice B coverage). It runs after both, in slice C's lane.
- **T059** needs T021 (slice A `GitHubPort` REST adapter) for commit statuses. Until it merges, slice C codes against `FakeGitHub`.
- **Phase 8**: T067 can run any time after CP0. T065 is needed before T036's verified mode goes live. T066 is needed after T059 lands.
- **Phase 9** after CP2 and T065–T066. **No Wave 2 order is issued until T070 is complete.**
- **Phases 10–13** (Wave 2) share the 3-worker cap with SWV2 lanes; US6, US7, US8 are mutually independent except T089 follows T088.

### Owned paths per slice (disjoint)

| Lane | Owns |
|------|------|
| Orchestrator (P0) | `scripts/factory/{pyproject.toml,uv.lock,gates.yaml,schemas/}`, `scripts/factory/src/factory/{api.py,bus/,config/,cli/app.py,cli/exit_codes.py,cli/checks.py,gates/registry.py}`, `scripts/factory/tests/{fixtures/,seeds/test_seeds.py,contract/test_cli_contract.py,unit/test_bus_models.py}`, `factory.toml`, `bus/`, workflows (T003–T004) |
| Slice A | `scripts/factory/src/factory/{lifecycle,board,metrics,github,identity,orders}/`, `cli/{board,orders}.py`, matching tests, `deploy/secrets/schema.yaml`, `scripts/validate_secrets_schema.py`, `scripts/test_validate_secrets_schema.py` |
| Slice B | `scripts/factory/src/factory/{gates/drift,intent}/`, `cli/intent.py`, matching tests, `gates.yaml` entries for its gates (amendment to orchestrator-owned file — append-only rows) |
| Slice C | `scripts/factory/src/factory/{gates/runner.py,gates/overrides.py,gates/pr,gates/repo,gates/retro.py,hooks}/`, `cli/gates.py`, matching tests, `.cursor/hooks.json`, `.github/workflows/factory-gates.yml` (after T004) |

`scripts/factory/gates.yaml` is shared: slices only **append** their own rows; the orchestrator resolves conflicts at merge.

## Parallel example (after CP0)

```text
Worker A (packet wo-…-factory-slice-a): T017–T020, T026–T032 red → T033 T* → T021–T025, T034–T038
Worker B (packet wo-…-factory-slice-b): T039–T040, T061 red → T041/T062 T* → T042–T049, T063
Worker C (packet wo-…-factory-slice-c): T050–T053 red → T054 T* → T055–T060, then T064
```

## Implementation strategy

1. **MVP = CP2**: issue → claim (cap 3, open-decision refusal) → PR from `wo/<id>` → board derived from reality; every SC-002 seed blocked in CI; every override reasoned and counted.
2. Wave 1 exits at CP2 + Phase 9 retro, ≤ 5 working days (3 targeted).
3. Wave 2 adds US6–US8 + mutation by sprint close (SC-005b ≥ 90% effective coverage, SC-006, SC-007).
4. US9 (portability proof) is P3 → sprint 03 per D1; FR-036 still applies now as a design rule (no repo specifics outside `factory.toml`).
