# Tasks: Factory v2 — intent-fidelity gates, typed bus, derived board

**Input**: `specs/001-factory-v2/` — [`plan.md`](./plan.md) (approved 2026-10-03), [`spec.md`](./spec.md), [`data-model.md`](./data-model.md), [`contracts/`](./contracts/), [`research.md`](./research.md), [`quickstart.md`](./quickstart.md), [`acceptance.md`](./acceptance.md).

**Tests (constitution §V):** `factory` is executable repo tooling, so tests are required. Every contract hook and every `how: auto` catalog row becomes a failing test before its implementation. `hybrid`/`human` rows get evidence tasks, not fake pytest.

**Open Decisions:** D1 waived (P3 rows → sprint 03), D2 = 70%, D3 = GPT reviews, D4 = GitHub App during Wave 1, D5 = trusted-base CI, D6 = probe, then pin (T101, T103), D7 = red-first self-reported in Wave 1 and a sealed trusted run in Wave 2 (T094, T104), D8 = agents' App has no `statuses: write` (T065). D5–D8 were all locked 2026-10-05, all architecture-affecting, and reconciled in Phase 6a ([`PLAN_DELTA.md`](./PLAN_DELTA.md)). None open. The `[HITL]` tasks below are governor ops steps (account and settings work agents cannot do), not content decisions.

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
| **CP2 — live as required checks** | end of day 3 | day 5 | `factory-gates.yml` reports one `factory/<gate-id>` status per P1 gate on a real PR; one real order issued → claimed → PR → verdict, all derived on the board. **D5/D6:** after Slice C's bootstrap merge, with merges frozen, a non-merging probe PR gets its statuses from the trusted `workflow_run` job running `main`'s code; its edit making a gate always pass is still failed by `main`'s gate. Every `factory/*` context then becomes required, pinned to GitHub Actions, and the live rule is verified before merges reopen (T103) |

SC-013: Wave 1 exits by CP2 within 5 working days of the first order; dates come from run events.

---

## Phase 1: Setup (orchestrator tiny glue — P0)

**Purpose**: project skeleton so three workers can start against frozen contracts.

- [x] T001 Create uv project `scripts/factory/pyproject.toml` (Python 3.12; deps `pydantic>=2`, `typer`, `httpx`, `pyyaml`; dev group `pytest`, `ruff`; console script `factory = "factory.cli.app:main"`; src layout `scripts/factory/src/factory/`) and commit `scripts/factory/uv.lock` from `uv sync`
- [x] T002 Create repo config `factory.toml` (keys: `bus_dir = "bus"`, `spec_roots = ["specs"]`, `app_roots = ["apps"]`, `rule_paths` = constitution, `AGENTS.md`, `.cursor/rules/**`, `docs/agent-os/**`, `scripts/factory/gates.yaml`, `scripts/factory/rubrics/**`; `concurrency_cap = 3`; `autonomy_horizon_minutes = 60`; `stale_multiplier = 3`; `[families]` map of model-name prefixes → family, e.g. `claude` → `anthropic`, `gpt` → `openai`, `gemini` → `google`; `governor_login`) and the typed loader `scripts/factory/src/factory/config/settings.py` (Pydantic model; no `os.getenv` outside this module — I-A3)
- [x] T003 [P] Exclude the factory from the legacy script test step: add `--ignore=scripts/factory` to the `pytest scripts/` line in `.github/workflows/verify-source.yml`
- [x] T004 [P] Create `.github/workflows/factory-gates.yml` on `pull_request` (jobs: `factory-tests` running `uv sync --locked` + `uv run pytest` in `scripts/factory`; placeholder `factory-gates` job running `factory gate run --pr ${{ github.event.number }}` that is allowed to fail until CP2)
- [x] T005 [P] Create empty bus layout `bus/orders/.gitkeep`, `bus/decisions/.gitkeep`, `bus/corrections/.gitkeep`, `bus/postmortems/.gitkeep`

---

## Phase 2: Foundational — contract freeze (orchestrator — P0, CP0)

**Purpose**: freeze every cross-slice interface and the shared fixtures (review P7). After CP0, changes to these files need an order amendment.

**⚠️ No slice work starts until this phase's checkpoint passes.**

- [x] T006 Envelope + every message kind as Pydantic v2 models in `scripts/factory/src/factory/bus/models.py`, with fields verbatim from `data-model.md`: envelope (`schema_version: 1`; `kind` ∈ order, amendment, handoff, verdict, decision_request, decision_lock, correction, override, claim, release, run_complete; `actor` ∈ governor, orchestrator, worker, reviewer; `actor_model` required when actor ≠ governor); `model_config = ConfigDict(extra="forbid")`; forbidden keys `status`, `state`, `done`, `progress` rejected anywhere in a message (FR-003); WorkOrder `goal` ≤ 3 sentences, `owned_paths` non-empty, `size_minutes` ≤ config horizon, `stop_conditions` non-empty, Lock `fidelity: waived` requires `waiver_ref`; Verdict findings `severity` ∈ `blocker`, `debate`, `later`, `nit` and `tag` ∈ product, process, arch; Override `reason` non-empty; id patterns (`wo-YYYYMMDD-<slug>`, `<order-id>.amend-NN`, `<order-id>.verdict-NN`, `<order-id>.override-NN`, `corr-YYYYMMDD-<slug>`)
- [x] T007 Bus loader + layout resolver in `scripts/factory/src/factory/bus/store.py` (paths per `contracts/messages.md` § Layout; `load_all(repo, ref) -> list[Message]`; read-only)
- [x] T008 JSON Schema export `factory check schema --write` → `scripts/factory/schemas/<kind>.schema.json`, plus `factory check schema` (validate every bus file and fail when schemas are stale) in `scripts/factory/src/factory/cli/checks.py`
- [x] T009 Gate registry model + loader in `scripts/factory/src/factory/gates/registry.py` (fields from `data-model.md` § Gate plus `entrypoint: "module:function"`; rule `class: governor-only` ⇔ `category ∈ {spend, secrets, irreversible, governor_decision}`), and `scripts/factory/gates.yaml` listing every P1 gate id from `contracts/gates.md` with class, category, intents, scope, entrypoint, `priority: P1`; add `entrypoint` to the Gate line of `specs/001-factory-v2/data-model.md`
- [x] T010 Frozen cross-slice interfaces in `scripts/factory/src/factory/api.py`: `GateContext` (repo path, base sha, head sha, PR number?, order id?, config, bus snapshot), `GateResult` (gate id, passed, messages, per-intent ids), `run_gate(gate_id, ctx) -> GateResult` (dispatch via registry entrypoint, no override logic), `LifecycleSnapshot` + `OrderState` enum (issued, claimed, in_review, accepted, rejected, merged, released; overlays stale, blocked_on_governor), `GitHubPort` Protocol (list PRs by head, PR reviews, check runs, create PR, set commit status), `IdentityPort` Protocol (`is_governor_verified(message, pr) -> bool`)
- [x] T011 CLI skeleton `scripts/factory/src/factory/cli/app.py` registering every command in `contracts/cli.md` from per-slice modules `cli/board.py` (A), `cli/orders.py` (A), `cli/intent.py` (B), `cli/gates.py` (C), `cli/checks.py` (P0/C), `cli/mining.py` (US7); unimplemented commands exit `3` with "not implemented"; common `--json` and `--repo` options; exit-code constants `0/1/2/3/4` in `scripts/factory/src/factory/cli/exit_codes.py`
- [x] T012 Shared fixture builder `scripts/factory/tests/fixtures/repo_builder.py`: temp bare `origin` + clone; helpers `write_message`, `commit`, `branch`, `push`, `make_pr` (backed by `FakeGitHub` implementing `GitHubPort` in `scripts/factory/tests/fixtures/fake_github.py`); `base_head_pair(base_files, head_files)` for gate tests; sample messages of every kind in `scripts/factory/tests/fixtures/messages/`
- [x] T013 Contract test for exit codes of every command in `scripts/factory/tests/contract/test_cli_contract.py` (red except `check schema`): one case per refusal row of `contracts/cli.md`
- [x] T014 Seeds suite skeleton `scripts/factory/tests/seeds/test_seeds.py` — one red test per SC-002 seed (`undeclared_substitution`, `declared_lock_violated`, `hidden_deferral`, `not_red_first`, `test_seam`, `outside_owned_paths`, `jargon_to_governor`, `catalog_unlinked`), each building its violating fixture with `repo_builder` and asserting `run_gate(<gate-id>, ctx).passed is False` and the gate id appears in the message
- [x] T015 Unit tests for models in `scripts/factory/tests/unit/test_bus_models.py` (forbidden keys at any depth; extra keys rejected; each constraint quoted in T006) — green at CP0 together with T006–T008
- [x] T016 Write review packet `notes/packets/<date>-factory-v2-p0-test-review-t.md` and **spawn** the T* reviewer (GPT family) on T013–T015 per `docs/agent-os/SPAWN_REVIEWER.md` + `TEST_REVIEW_PROMPT.md`; triage into `specs/001-factory-v2/TEST_REVIEW.md` before slice packets go `ready`

- [x] T016a Write the three slice work packets `notes/packets/<date>-factory-v2-slice-{a,b,c}.md` from `notes/packets/_TEMPLATE.md`: owned paths from § Owned paths per slice, DoD = that slice's tests green + catalog evidence filled, Fidelity table (letter for every named lock: cap 3, 70% mutation, GPT reviewer family, GitHub App identity, Semgrep CE / import-linter / mutmut 3), bootstrap-verdict requirement (FR-037)

**Checkpoint CP0**: `factory check schema` exits 0 on the sample messages; JSON Schemas generated; contract + seeds tests collected and red for unimplemented commands; T* triaged.

---

## Phase 3: User Story 1 — See at a glance (P1) 🎯 MVP · Slice A

**Goal**: one board derived from git + PR + check reality.

**Independent test**: fixture repo with orders in every lifecycle state → `factory status --json` equals the expected derivation; no bus file has a status field.

### Tests (write first, must fail)

- [x] T017 [P] [US1] Contract test `scripts/factory/tests/contract/test_status.py`: fixture with one order per state (issued, claimed, in_review with running checks, accepted, rejected, merged, released, stale, blocked_on_governor); assert board JSON sections in flight / blocked / waiting on governor (plain-language prompt text) / ready queue / overrides per gate / unverified governor actions — catalog `board.matches_reality`
- [x] T018 [P] [US1] Unit tests for derivation rules `scripts/factory/tests/unit/test_lifecycle.py` (rules verbatim from `data-model.md` § Lifecycle: stale = claimed, no PR, no commit for > `3 × size_minutes`, still counts toward cap; `released` = release event OR PR closed unmerged; ready queue = issued ∧ ¬claimed ∧ ¬blocked_on_governor)
- [x] T019 [P] [US1] Unit test `scripts/factory/tests/unit/test_github_adapter.py` against recorded REST responses in `scripts/factory/tests/fixtures/github_recorded/`
- [x] T020 [P] [US1] Unit test `scripts/factory/tests/unit/test_no_bookkeeping.py`: commits whose only change rewrites status or SHAs inside `bus/` are counted — catalog `history.no_bookkeeping`

### Implementation

- [x] T021 [P] [US1] GitHub REST adapter implementing `GitHubPort` with httpx in `scripts/factory/src/factory/github/rest.py` (token from typed settings; the only module that calls GitHub — I-A4)
- [x] T022 [US1] Lifecycle derivation `scripts/factory/src/factory/lifecycle/derive.py` → `LifecycleSnapshot` (reads `bus.store` on each `wo/*` branch + `GitHubPort`; writes nothing)
- [x] T023 [US1] Board rendering `scripts/factory/src/factory/board/render.py` (markdown + JSON) and `factory status`, `factory decisions` in `scripts/factory/src/factory/cli/board.py`
- [x] T024 [US1] Bookkeeping-commit counter `scripts/factory/src/factory/metrics/history.py` (consumed by `factory scorecard`)
- [x] T025 [US1] Update `acceptance.md` evidence for `board.matches_reality`, `bus.no_handwritten_status`, `history.no_bookkeeping` with the test ids above

**Checkpoint**: `factory status` shows real orders; T017–T020 green.

- [x] T105 [US1] Slice A follow-up to the Slice B PR review (`checks` kinds, orchestrator 2026-10-05, `bus/orders/wo-20261004-factory-slice-b/amendment-06.yaml`): in `scripts/factory/src/factory/lifecycle/derive.py`, a registered gate id in an order's `checks` needs its own green `factory/<gate-id>` status (or a counted override). A catalog row id is satisfied by the `factory/catalog-test-linkage` status, which judges catalog rows. Test first in `scripts/factory/tests/unit/test_lifecycle.py`. Wave 1 orders carry gate ids only, so this must land before the first order whose `checks` names a catalog row
- [x] T106 [US3] Slice B fix (W6 + W7, one root cause, orchestrator 2026-10-05, §J): `red-first-proof` attributes base-side collection and import errors to their own tests. A sibling file failing import on base must not leave other tests "not collected", and `from pkg import mod` for a module the PR adds is red, not "base broken". The regression test is `scripts/factory/tests/unit/gates/drift/test_red_first_base_errors.py` (2 cases, red); the fix is in `scripts/factory/src/factory/gates/drift/red_first.py`

---

## Phase 4: User Story 2 — Hand off and trust the result (P1) · Slice A (+ C for PR gates)

**Goal**: orders are issued on their own branch, claimed atomically under cap 3, handed off with deviations, opened as one PR, and accepted on checks + a different-family verdict.

**Independent test**: issue → claim → handoff → PR → verdict on a fixture remote; the 4th claim is refused; an order depending on an open governor decision is refused; a handoff with failing checks is refused; a same-family verdict is rejected.

### Tests (write first, must fail)

- [x] T026 [P] [US2] Contract test `scripts/factory/tests/contract/test_orders.py` — `order new` refuses `size_minutes` > 60 and a touched named lock without fidelity (seed `undeclared_substitution`); `order issue` creates `wo/<id>` whose first commit adds only `bus/orders/<id>/order.yaml`, never pushes `main`, refuses an order whose `depends_on_decisions` has an open `who: human` decision (exit 2, decision named in plain language) — catalogs `seed.substitution_undeclared`, `handoff.open_od_refused`
- [x] T027 [P] [US2] Contract test `scripts/factory/tests/contract/test_claim.py` — claim is a fast-forward push (two concurrent claims of one order: exactly one succeeds); refuses at `active ≥ 3`, on owned-path overlap with an active order, when blocked on governor, when already claimed; `release` frees capacity — catalog `handoff.concurrency_cap` (claim half)
- [x] T028 [P] [US2] Contract test `scripts/factory/tests/contract/test_handoff.py` — `factory handoff` refuses while any registered gate for the order fails locally (FR-009); `deviations` key required; each open question classed `blocker_governor` or `non_blocking`; a `blocker_governor` question makes the command exit 2 with the plain-language question on stdout and puts the order under "waiting on governor" on the board (the orchestrator relays it on the worker's completion notice — US2 #3); writes `run-complete` event (`wall_minutes`, `governor_interrupts`, `cost_usd` with estimate flag, `deviations_count`) — catalog `handoff.done_requires_green`
- [x] T029 [P] [US2] Contract test `scripts/factory/tests/contract/test_pr_and_verdict.py` — `pr open` refuses without a valid handoff and writes a body linking order + intents; `verdict` refuses reviewer family = author family (family via `factory.toml [families]`) and any input that is not a git path at a sha — catalogs `handoff.reviewer_family`, `handoff.reviewer_isolated` (machine half)
- [x] T030 [P] [US2] Contract test `scripts/factory/tests/contract/test_bus_pr.py` — `bus pr` refuses changes outside `bus/decisions/`, `bus/corrections/`, `bus/postmortems/`
- [x] T031 [P] [US2] Unit test `scripts/factory/tests/unit/test_scorecard.py` — scorecard from events, verdicts, overrides, corrections, decision locks: drift, first-pass acceptance, decision points per feature, governor minutes, rework loops, Wave 1 start/exit dates — catalogs `scorecard.computed`, `wave1.timebox`
- [x] T032 [P] [US2] Unit test `scripts/factory/tests/unit/test_identity.py` — recorded-only mode marks governor actions unverified; verified mode counts a governor message only when its PR has an approving review by `governor_login`; App token minting builds a JWT from `FACTORY_GITHUB_APP_ID` + `FACTORY_GITHUB_APP_PRIVATE_KEY` and exchanges it (recorded response)
- [x] T033 [US2] Spawn T* review for T017–T032 (packet `notes/packets/<date>-factory-v2-slice-a-test-review-t.md`); triage into `TEST_REVIEW.md` before T034

### Implementation

- [x] T034 [US2] `order new` / `order issue` / `claim` / `release` / `handoff` / `pr open` / `verdict` / `bus pr` in `scripts/factory/src/factory/cli/orders.py` with logic in `scripts/factory/src/factory/orders/` (git plumbing via subprocess in `scripts/factory/src/factory/orders/git.py`; no business logic in the CLI module — I-A1)
- [x] T035 [US2] Scorecard `scripts/factory/src/factory/metrics/scorecard.py` + `factory scorecard` in `scripts/factory/src/factory/cli/board.py`
- [x] T036 [US2] Identity adapter `scripts/factory/src/factory/identity/adapter.py` (implements `IdentityPort`; mode from config: `recorded` until the App exists, then `verified`) and App token minting + repo-local git credential helper `scripts/factory/src/factory/identity/app_token.py` (1-hour installation tokens)
- [x] T036b [US2] Wire the App installation token into the git credential helper and the REST client (`scripts/factory/src/factory/identity/app_token.py`, `scripts/factory/src/factory/github/rest.py`, callers in `scripts/factory/src/factory/orders/`), including how the installation id is obtained (config amendment if needed); a recorded-response end-to-end test proves the token is never logged, persisted, or put in exceptions. MUST land before T065 flips `identity.mode = "verified"`
- [x] T037 [US2] Secret names: add a `tooling:` section to `deploy/secrets/schema.yaml` with `factory` → Codespace target, names `FACTORY_GITHUB_APP_ID` and `FACTORY_GITHUB_APP_PRIVATE_KEY` (no values), and teach `scripts/validate_secrets_schema.py` + `scripts/test_validate_secrets_schema.py` to accept the section
- [x] T038 [US2] Update `acceptance.md` evidence for every row tested in T026–T032

**Checkpoint (part of CP1)**: one fixture order runs issue → merge, derived end to end; T026–T032 green.

---

## Phase 5: User Story 3 — Machines catch sprint-01 drift (P1) · Slice B

**Goal**: every SC-002 seed is blocked by a drift gate.

**Independent test**: `uv run --project scripts/factory pytest scripts/factory/tests/seeds` — all 8 seeds blocked, gate id in output.

### Tests (write first, must fail)

- [x] T039 [P] [US3] Unit tests per gate in `scripts/factory/tests/unit/gates/drift/` (one file per gate below), each with a passing and a violating `base_head_pair` fixture; seeds in T014 are the SC-002 subset
- [x] T040 [P] [US3] Red-first edge cases `scripts/factory/tests/unit/gates/drift/test_red_first.py` (rule verbatim from `research.md` § Red-first): new test passing on base → fail; assertion failure on base → pass; import error for a symbol the PR adds → counts as red; import error for an unrelated broken module → reported "base broken", not red; PR with no new/changed tests → pass
- [x] T041 [US3] Spawn T* review for T039–T040 (packet `notes/packets/<date>-factory-v2-slice-b-test-review-t.md`); triage before T042

### Implementation (one module each under `scripts/factory/src/factory/gates/drift/`; each registered in `scripts/factory/gates.yaml`)

- [x] T042 [P] [US3] `red_first.py` — gate `red-first-proof`: collect node ids head vs base; run new/changed tests on base code with head tests overlaid, then on head
- [x] T043 [P] [US3] `test_seam.py` — gate `test-seam-ban`: changed app lines under `app_roots` matching test-only branching (`PYTEST_CURRENT_TEST`, `"pytest" in sys.modules`, `TESTING`/`IS_TEST` flags, fake-key sniffing such as `startswith("sk-test")`)
- [x] T044 [P] [US3] `owned_paths.py` — gate `diff-within-owned-paths`: every changed path matches the effective order's `owned_paths` or `bus/orders/<order-id>/**`
- [x] T045 [P] [US3] `deferral_words.py` — gate `deferral-words-need-od`: rule verbatim from `contracts/gates.md` § Deferral-words rule (the listed words in `specs/**` and `notes/sprints/**` need an existing `D\d+`, a `→ <artifact>` pointer, or `[governor-judged]` on the same line/row; words inside backtick code spans are exempt)
- [x] T046 [P] [US3] `fidelity.py` — gates `order-fidelity-declared` (every named lock the order's owned paths or goal touch has a Lock entry) + `lock.letter-tokens` (for `fidelity: letter`, the PR diff contains each `letter_tokens` entry and does not introduce a registered substitute; seed `declared_lock_violated`)
- [x] T047 [P] [US3] `decision_ids.py` — gate `decision-request-no-ids`: regexes verbatim from `contracts/messages.md` (`\b[TFRPD]\d+\b`, `FR-\d+`, `SC-\d+`, `US\d+`, `§`) plus a jargon list in `factory.toml` applied to `prompt` and `options[].label`
- [x] T048 [P] [US3] `catalog_linkage.py` — gate `catalog-test-linkage`: every `how: auto` row in any `acceptance.md` has `evidence`; rows whose id appears in the PR's order `checks` must name an existing pytest node id or eval id (not `planned`) before merge (FR-018)
- [x] T049 [US3] Update `acceptance.md` evidence for all `seed.*` rows (8 of 9 linked; `seed.code_before_test_review` stays `planned` with its Wave 2 requirement, FR-012b)

**Checkpoint (part of CP1)**: seeds suite 100% green (all blocked).

---

## Phase 6: User Story 4 — Hard gates, governor not the unblocker (P1) · Slice C

**Goal**: gate framework with two classes, reasoned overrides, per-gate counts, hook twins, and PR-level gates live as required checks.

**Independent test**: drift gate overridden with reason → passes, counted on board; empty reason rejected; orchestrator override of governor-only gate rejected; a governor-only gate in a disallowed category fails registration; a hook without a CI twin fails.

### Tests (write first, must fail)

- [x] T050 [P] [US4] Contract test `scripts/factory/tests/contract/test_gate_run.py` — `gate run --base --head` runs every registered gate, prints per-intent results, exit 1 on any un-overridden failure; override resolution per `contracts/gates.md` § Override resolution — catalogs `override.reason_required`, `override.surfaced_counted`, `override.governor_only`
- [x] T051 [P] [US4] Unit tests `scripts/factory/tests/unit/gates/test_registry_checks.py` — `gate.fail-mode-category`, `hook-has-ci-twin` (every hook in `.cursor/hooks.json` has a registry entry with `hook_twin_of`) — catalogs `gate.fail_mode_category`, `gate.hook_has_twin`
- [x] T052 [P] [US4] Unit tests `scripts/factory/tests/unit/gates/pr/` — `bus.immutable` (modify/delete of an existing bus file fails), `bus.no-handwritten-status`, `pr-links-order` (head `wo/<id>` + order exists), `order-blocked-on-open-human-od`, `spawn-concurrency-cap` (CI twin: replays claim events in timestamp order across all `wo/*` branches; blocks the PR whose claim exceeded 3 or that has no claim — catalog `handoff.concurrency_cap` merge half), `verdict.reviewer-family-differs` + `verdict.inputs-isolated`, `message.override`
- [x] T053 [P] [US4] Hook tests `scripts/factory/tests/unit/hooks/test_hooks.py` — `spawn-guard` (subagentStart; advisory warning unless the prompt names a claimed `wo-…` id or a review packet, and when the last-fetched active count ≥ 3 — catalog `handoff.concurrency_cap` editor half, FR-008); `shell-guard` denies `git commit` on `main` and any `git push` targeting `main` (refspecs `main`, `HEAD:main`, `refs/heads/main`, and a bare `git push` while on `main` — catalog `branch.no_direct_main`, I-P10), `pip install`, `gh workflow run`, `git push --force`, writes to `/etc`, `/usr`, `~/.config` outside the repo, `nix-env -i`; `owned-path-warn` warns outside owned paths; `decision-in-chat` warns per `contracts/hooks.md`; each runs offline in < 300 ms
- [x] T054 [US4] Spawn T* review for T050–T053 (packet `notes/packets/<date>-factory-v2-slice-c-test-review-t.md`); triage before T055

### Implementation

- [x] T055 [US4] Runner + override resolution + per-intent report in `scripts/factory/src/factory/gates/runner.py` and `scripts/factory/src/factory/gates/overrides.py` (uses `api.run_gate`; governor-only overrides need `actor: governor` and `IdentityPort` verification when mode is `verified`)
- [x] T056 [P] [US4] PR/repo gates in `scripts/factory/src/factory/gates/pr/` (`bus_immutable.py`, `no_status.py`, `links_order.py`, `open_od.py`, `concurrency_cap.py`, `verdict.py`, `override_msg.py`) and `scripts/factory/src/factory/gates/repo/` (`fail_mode.py`, `hook_twin.py`)
- [x] T057 [P] [US4] Hooks: entrypoints `scripts/factory/src/factory/hooks/` + lightweight console script `factory-hook = "factory.hooks.entry:main"` (`scripts/factory/pyproject.toml` + `uv.lock`; no Typer app, no other slices' modules) + slow-path `factory hook <name>` in `scripts/factory/src/factory/cli/gates.py`; wrapper `.cursor/hooks/factory-hook.sh` (venv `factory-hook`, else `uv run --project scripts/factory factory hook <name>`); `.cursor/hooks.json` registering `spawn-guard` (subagentStart, log-only), `shell-guard` (beforeShellExecution), `owned-path-warn` (postToolUse, anchored `Write|Delete` matcher, `additional_context`), `decision-in-chat` (stop, `followup_message`) — format per `/home/vscode/.cursor/skills-cursor/create-hook/SKILL.md` and the Cursor hooks docs; amendments `wo-20261004-factory-slice-c.amend-01`, `.amend-02`
- [x] T058 [US4] `factory override` and `factory gate run` in `scripts/factory/src/factory/cli/gates.py`; `factory check hooks|registry|immutability` in `scripts/factory/src/factory/cli/checks.py`
- [x] T059 [US4] Make `.github/workflows/factory-gates.yml` authoritative: run `factory gate run --pr`, post one commit status `factory/<gate-id>` per gate via `GitHubPort`, publish the board in the job summary; register existing `validate-secrets-schema` (governor-only, secrets), `validate-deploy-env`, `uv-sync-locked` in `scripts/factory/gates.yaml` — workflow topology superseded by T097 (D5; PR review PR-C1)
- [x] T060 [US4] Update `acceptance.md` evidence for override/gate rows

**Checkpoint (part of CP1/CP2)**: required statuses appear on a real PR.

---

## Phase 6a: Slice C PR-review remediation + trusted-base CI (D5, P1) · Slice C

**Source**: PR review [`PR_REVIEW_SLICE_C.md`](./PR_REVIEW_SLICE_C.md) (verdict-04, reject) and its § Triage; spec D5 (locked 2026-10-05, architecture-affecting) reconciled in [`PLAN_DELTA.md`](./PLAN_DELTA.md). Appended 2026-10-05; no earlier IDs renumbered.

**Gate**: no test or implement work here starts until the delta P* review of the D5 amendment is triaged (constitution §G.1 step 4). It was triaged 2026-10-05 (`PLAN_REVIEW.md` § Triage (delta P*); locks D6–D8); the narrow P* confirmation (verdict-06) confirmed it, and its one Blocker, P19, concerns Wave 2's T104 only and is agent-closed for Wave 1 (`PLAN_DELTA.md` § Round 3). Tests come first (§V); T096 T* triage comes before T097–T098.

### Tests (write first, must fail)

- [x] T094 [P] [US4] [OD:D5] PR-C1 red tests. New `scripts/factory/tests/contract/test_ci_trust_boundary.py`, which replaces the three T-C1 workflow assertions in `scripts/factory/tests/contract/test_gate_run.py` (`test_workflow_gate_run_on_the_pr_is_not_allowed_to_fail`, `test_workflow_can_post_commit_statuses`, `test_workflow_publishes_the_board_in_the_job_summary`); accepted tests change only through this task and T096. Assertions, per `contracts/gates.md` § CI topology and trust boundary and `contracts/cli.md` § CI mode:
  - **Untrusted workflow:** `factory-pr-evidence.yml` runs on `pull_request` with workflow-level permissions exactly `contents: read`, references no `secrets.*`, and posts no status.
  - **Trusted workflow:** `factory-gates.yml` runs on `workflow_run` of "Factory PR evidence" `completed` and is the only job with `statuses: write`. Its checkout has no `ref:` and `persist-credentials: false`. The head is fetched by SHA only. No step runs `uv`/`python`/`pytest`/a script against a head path. `${{ }}` inside `run:` is limited to the allowed set, delivered via `env:`.
  - **Repo-wide:** no `pull_request_target` with a head checkout or execution; no `pull_request` job holds `statuses: write` or secrets.
  - **Gate run (fixture repos + `FakeGitHub`):** the registry comes from the installed package. A head that rewires a gate's entrypoint, deletes a row, or edits a gate module to always pass is still judged by the installed gate, and the head registry is still validated as data (T-C2). With `--expect-head`, a mismatch posts nothing and exits 0. Statuses go only to the expected head.
  - **Validators:** a head whose copy of a validator script is replaced by `sys.exit(0)` and whose schema is invalid still fails.
  - **Evidence bundle** (model in `contracts/gates.md` § Evidence bundle): red-first fails closed, naming the reason, on a bundle that is absent, unreadable, over the size limit, fails its schema (including any extra key such as a verdict, a PR number or an order id, and any outcome word outside the vocabulary), is for another `head_sha`, reports a crashed producer, lists a node that is not a new or changed test function, or omits one. A valid red→green bundle passes; the red-first rule is applied to the raw facts by the judge. The other selected gates still run.
  - **`factory gate evidence`:** serializes Slice B's `red_first.collect_facts(ctx)` raw facts (sorted by node id) into `factory-evidence.json`, exits 0 with failing tests, records a crash or an unknown outcome as `status: crashed`, builds no GitHub adapter and records no status call; without `--out` it is a usage error.
  - **Head as data:** CI-mode runs work with no head branch present (the PR is looked up by number) and leave the checkout on `main`, clean, with no extra worktree; no head code runs (planted conftest, test module, validator scripts and gate module never execute).
  - **Artifact provenance (P12):** the trusted workflow's download step names `run-id: github.event.workflow_run.id`, this repository and `name: factory-evidence`, with no `pattern:` and no `merge-multiple`, into a fresh directory outside the checkout. A run whose `workflow_run.repository` or `head_repository` is not this repository posts nothing and exits 0. `--evidence` with zero or with two bundle files fails red-first closed, naming the reason.
  - **Cache isolation (P12):** the trusted workflow has no `actions/cache` step, `setup-uv` sets `enable-cache: false`, and no `setup-python` cache is used.
  - **Red-first strength (D7, Wave 1):** every `red-first-proof` status description starts `self-reported:`, whether it passes or fails.
  - **Status source (P9):** `branch-protection-require-pr` fails a snapshot in which any required `factory/*` context lacks the GitHub Actions app id as its expected source, or in which a `factory/*` context is missing. It passes a snapshot where every one is pinned. These tests go in `scripts/factory/tests/unit/gates/test_registry_checks.py`; existing branch-protection fixtures gain the app id.
  - Catalog `ci.trusted_base`, `ci.status_source_pinned`.
- [x] T095 [P] [US4] PR-C2 red test `scripts/factory/tests/unit/hooks/test_hook_wrapper.py`: integration test running `.cursor/hooks/factory-hook.sh <name>` for each of the four hooks, in a repo with no `scripts/factory/.venv` and a `PATH` without `uv`:
  - With a stub `nix` on `PATH`, the wrapper calls `nix develop <repo root> -c uv run --project scripts/factory factory hook <name>` and relays its stdout.
  - With no `nix`, or a `nix` that exits non-zero without output, stdout is exactly that hook's quiet fail-open JSON, the exit code is 0 and the reason is on stderr. Never exit 127.
- [x] T096 [US4] Spawn T* review for T094–T095 (packet `notes/packets/<date>-factory-v2-slice-c-rework-test-review-t.md`) after the delta P* review is triaged; triage into `TEST_REVIEW_SLICE_C.md` before T097

### Implementation

- [x] T097 [US4] [OD:D5] PR-C1 rework per `contracts/gates.md` § CI topology and trust boundary:
  - Split `.github/workflows/factory-gates.yml` into the untrusted `.github/workflows/factory-pr-evidence.yml` and the trusted `workflow_run` `factory-gates.yml`.
  - Add `factory gate run --expect-head --evidence` and `factory gate evidence` in `scripts/factory/src/factory/cli/gates.py` + `scripts/factory/src/factory/gates/runner.py`.
  - Split red-first into an evidence producer and a bundle judge in `scripts/factory/src/factory/gates/drift/red_first.py`. That is Slice B's path, so it waits until B is merged into C and needs an order amendment.
  - Validators run `main`'s scripts against the exported head tree (`scripts/factory/src/factory/gates/repo/existing.py`); add a repo-root argument to `scripts/validate_secrets_schema.py` / `scripts/validate_deploy_env.py` if missing (order amendment).
  - The evidence-bundle model, its size limit in typed config and any `GateContext` field are CP0 frozen-interface changes (`api.py`, `config/`), made by amendment. The phase-1 red tests also need, by amendment: typed config `evidence_max_bytes` and `github.actions_app_id` (`config/settings.py`); a PR lookup by number on `GitHubPort` plus `FakeGitHub` (`api.py`, `tests/fixtures/`), since the trusted job has no head branch; the `gate evidence` command registered in `cli/app.py`; explicit read-only `permissions:` in `.github/workflows/ci-cd-pipeline.yml` (its `pull_request` jobs inherit the repository's default token today).
  - Artifact provenance and cache isolation per `contracts/gates.md` § Artifact provenance / § Privileged environment (P12).
  - The `self-reported:` prefix on `red-first-proof` statuses (D7).
  - `branch-protection-require-pr` asserts the GitHub Actions app id as expected source on every required `factory/*` context (`scripts/factory/src/factory/gates/repo/branch_protection.py`, P9).
  - Fill `ci.trusted_base` and `ci.status_source_pinned` evidence.
  - **Status 2026-10-05:** done except the `red_first.py` producer/judge split, which waits for Slice B's merge into C (the producer imports `collect_facts` lazily meanwhile); `ci.status_source_pinned`'s live-rule half waits for T103.
- [x] T098 [US4] PR-C2: wrapper `.cursor/hooks/factory-hook.sh` per `contracts/hooks.md` § Invocation (Nix fallback; wrapper-level quiet fail-open)
- [x] T099 [POLICY] PR-C4: revert the `Status` line of `notes/packets/2026-10-04-factory-v2-slice-c.md` to its `main` text (no net diff on the packet vs `main`); progress stays in the append-only handoff and verdicts
- [x] T100 [US4] PR-C5: once Slices A and B are merged into `wo/wo-20261004-factory-slice-c`, `factory-tests` (now in `factory-pr-evidence.yml`) runs the full factory suite with no `-m` / `-k` / `--deselect` selector, and the CP1 bootstrap comment goes; T094's workflow test asserts no selector
  - Done 2026-10-06, after A (`d573721`) and B (`2a591f9`) were merged in. `factory-tests` runs plain `uv run pytest`, with no bootstrap comment left. `test_evidence_workflow_runs_the_full_factory_suite` asserts there is one pytest call and no selector. The full suite still fails on the tasks that are not built yet: T102 (`factory-status-test` entrypoint, its own order), T069 (`factory retro`) and T081 (`factory correction new`, `factory sprint close`). `Factory tests` stays red until those land.
  - Amended 2026-10-06 (orchestrator): `Factory tests` is a required check on `main` with no bypass, so "stays red" would block every PR until Wave 2. T102 has landed (PR #25). The 7 remaining T069/T081 contract tests are strict expected failures through `UNBUILT` in `tests/contract/test_cli_contract.py`. The suite still runs in full with no selector, and an unexpected pass fails it.

### Cross-order dependencies for the C merge

- [x] T101 [HITL] [OD:D6] PR-C6 = T066, moved earlier. Between the Slice B merge and the Slice C merge, the governor walks through branch protection with the orchestrator:
  - **Amended 2026-10-06 — governor decisions, verbatim:**
    - "**Mechanism: a repository RULESET** (Settings → Rules), not classic branch protection. The codespace token can read rulesets (`GET /repos/{o}/{r}/rulesets` returns 200) but not classic protection (403)."
      - "Change `deploy/github/branch-protection.json` and the `branch-protection-require-pr` gate to the ruleset shape: target `main`; empty bypass list; rules `pull_request` and `required_status_checks`, each `{context, integration_id}` pinned to the GitHub Actions app id (P9); `non_fast_forward` and `deletion`."
      - "Update the gate's tests and fixtures to this shape. This is a governor-decided amendment to accepted tests; keep each test's intent and list old → new."
    - "**Code-owner review is deferred until the factory's GitHub App (T065) authors PRs.** PRs are authored under the governor's own account today, and GitHub won't let them approve their own PR."
      - "So T101 now turns on: PR required, required checks, and no bypass for anyone."
      - "A `.github/CODEOWNERS` file is added now, listing the rule paths under the governor (constitution, AGENTS.md, `.cursor/rules/`, `docs/agent-os/`, `scripts/factory/gates.yaml`, `scripts/factory/src/factory/gates/`, and the factory workflows)."
      - "'Require code-owner review' is switched on after T065. This is a governor-approved fidelity deviation; record it as such."
      - "The gate must accept a snapshot without code-owner review until a config flag (or T065 state) says it's required. Pick the smallest clean form and say which you chose."
    - **Chosen form (agent):** T065 state. The gate requires code-owner review exactly when `identity.mode = "verified"`, the flip T065 already makes. No new config field and no CP0 change.
    - **Fidelity deviation (governor-approved 2026-10-06):** the letter "require code-owner review" (T066) is not met at T101; it is met after T065.
  - **Live (done 2026-10-06, ruleset id 24554609 `main-protection`, created by the governor):** a repository ruleset on `~DEFAULT_BRANCH` (`main`) with an empty bypass list; rules `pull_request` (code-owner review off), `required_status_checks` (`Factory tests` and `Verify Source / verify`, each pinned to integration 15368; "require branches up to date" deliberately off), `non_fast_forward`, `deletion`. The `factory/*` contexts are **not** required live; per D6 they are switched on in T103 step 3, after the probe.
  - **Snapshot (committed in C by amend-07, aligned with the live ruleset by amend-08):** `deploy/github/branch-protection.json` is the live `GET /repos/{o}/{r}/rulesets/24554609` body without server metadata that changes on every edit (`node_id`, `created_at`, `updated_at`, `_links`, `current_user_can_bypass`), **plus the T103 target**: each P1 `factory/<gate-id>` context listed individually with `integration_id` 15368 (P9). Until T103 step 3 the live rule is expected to lack exactly those `factory/*` entries; nothing in Wave 1 compares live with the snapshot before T103 step 4. The gate reads only the snapshot and ignores keys it does not check.
  - This task is a pre-merge dependency for C.
- [x] T102 PR-C3 as its own small order (`wo-<date>-factory-status-test`), after Slice A merges and before Slice C merges:
  - Done 2026-10-06: order `wo-20261006-factory-status-test`, merged to `main` as [PR #25](https://github.com/infra-anoop/2026-software-lab/pull/25) (`916fc64`), with a reconstructed P0 bootstrap `order.yaml`. Merged into Slice C's branch from `origin/main`.
  - Test first `scripts/factory/tests/unit/gates/repo/test_status_test.py` (T* reviewed), then the entrypoint `factory.gates.repo.status_test:run` in `scripts/factory/src/factory/gates/repo/status_test.py`.
  - It judges the board derivation over the head's bus data with `main`'s code and executes no head code (D5).
  - It fills acceptance evidence for the I-M4 board row it serves and carries a bootstrap verdict (a pre-C PR).
  - Slice C's branch does not create that file.
- [x] T103 [HITL] [OD:D5] [OD:D6] Slice C bootstrap merge, then the CP2 proof, in exactly this order (D6: probe, then pin):
  1. C merges on a bootstrap verdict over the reworked head plus governor approval. **The orchestrator freezes all other merges from this moment.**
  2. The orchestrator opens a **non-merging probe PR** whose head also edits one gate to always pass. The trusted run posts one `factory/<gate-id>` status per P1 gate as GitHub Actions, and the edited gate still fails under `main`'s code.
  3. The governor switches on the required `factory/*` contexts, each pinned to GitHub Actions as expected source, matching the T101 snapshot. **Amended 2026-10-06 (governor: "a repository RULESET (Settings → Rules), not classic branch protection"):** the contexts go into the `main` ruleset's `required_status_checks` rule as `{context, integration_id: 15368}`; code-owner review stays off until T065 (governor-approved fidelity deviation, T101).
  4. The orchestrator reads the live rule back through the API (`GET /repos/{o}/{r}/rulesets/24554609`, readable by the Codespace token; classic protection is 403) and compares it with the snapshot, ignoring the server metadata the snapshot omits. This is the first live-versus-snapshot comparison; before step 3 the live rule lacks the `factory/*` entries by design. The probe PR shows every `factory/*` check required and satisfied only by the GitHub Actions source.
  5. The probe PR closes unmerged; merges reopen.
  - Progress 2026-10-06: steps 1–2 done. PR #21 merged (`ac60d43`). The probe is PR #26 (`probe/t103-trust-split`): 25 `factory/*` statuses from `github-actions[bot]`, and `factory/pr-links-order` failed under `main`'s code although the head's copy always passes. **Amended 2026-10-06 (governor, `PLAN_DELTA.md` Round 5):** step 3 requires the single summary context `factory/gates` (T107) instead of 25 per-gate contexts. T107 merges during the freeze; then the probe is re-run and steps 3–5 proceed against `factory/gates`.
  - Done 2026-10-06 (`PLAN_DELTA.md` Round 6). T107 merged (`c7fc5ee`). The re-run probe (`af72f98`) got `factory/gates` = failure from `github-actions`. The governor required `factory/gates` pinned to GitHub Actions in ruleset 24554609, and the read-back equals `deploy/github/branch-protection.json` in every rule. PR #26 was blocked by it and closed unmerged; the freeze was lifted. A green trusted summary making a PR mergeable is first confirmed by the merge of order `wo-20261007-factory-t103-close`.
- [x] T107 [OD:D6] Summary status `factory/gates` (governor 2026-10-06, `PLAN_DELTA.md` Round 5), test first. `factory gate run --pr` posts `factory/gates` on the head SHA after the per-gate statuses. It is `success` only when every CI gate in `main`'s registry ran in that invocation and each outcome is `pass` or `overridden`; otherwise `failure`, naming the failing gates within the description limit. No summary for a `--gate` subset, and none when the head moved. `branch-protection-require-pr` requires `factory/gates` (pinned, P9) instead of a context per P1 gate. `deploy/github/branch-protection.json` and `contracts/gates.md` follow. Per-gate statuses are unchanged
  - Done 2026-10-07 on `wo/wo-20261006-factory-gates-summary`: red tests `ba78e9a` + T* round 1 fixes `bd1a2f8` (T* round 2 accepted); implementation and snapshot `4becd75`; amendment-01 (`3015313`) let the accepted `test_ci_trust_boundary.py` full-run status set gain `factory/gates`; contracts and this tick in the follow-up commit. Every explicit `--gate` run is a subset run (orchestrator ruling); a failing summary also exits 1 (accepted).

  Record the steps on `ci.trusted_base` and `ci.status_source_pinned`. If step 4 fails, the freeze holds until it passes.

**Checkpoint (Phase 6a)**: delta P* triaged and confirmed; T094–T095 red then T* triaged; T097–T100 green; T101 done; T102 merged; then T103 in D6 order.

---

## Phase 7: User Story 5 — Intent traceability (P1) · Slice B

**Goal**: presence invariant, effective coverage, per-intent PR results.

**Independent test**: drop all mappings from one intent in a fixture → `factory check intent` exits 1; mark a mapped check planned-only → coverage drops.

- [x] T061 [P] [US5] Contract test `scripts/factory/tests/contract/test_intent.py` — presence over `specs/*/intent.yaml` + `scripts/factory/gates.yaml` + every `acceptance.md`; `--coverage` = share of intents backed by an implemented (registered, entrypoint importable), passing, non-human check or an explicit governor-judged mapping — catalogs `trace.presence`, `trace.effective_coverage`
- [x] T062 [US5] Spawn T* review for T061 (may share the slice-B packet from T041 if written together)
- [x] T063 [US5] `scripts/factory/src/factory/intent/coverage.py` + `factory check intent [--coverage]` in `scripts/factory/src/factory/cli/intent.py`; register `factory-check-intent`
- [x] T064 [US5] Per-intent PR results: runner groups `GateResult` by intent ids in the job summary (`scripts/factory/src/factory/gates/runner.py` report section — coordinate: slice C owns the file; slice B supplies `intent.coverage.group_by_intent()`) — catalog `handoff.per_intent_results`

**Checkpoint CP2**: all P1 gates live as required checks after T065–T066; one real order run end to end.

---

## Phase 8: Ops — governor steps for Wave 1 [HITL]

- [ ] T065 [HITL] Governor creates the GitHub App (repo contents/PRs/checks read-write; **no `statuses: write`**, D8 2026-10-05: only CI posts `factory/*` statuses), installs it on this repo, stores `FACTORY_GITHUB_APP_ID` + `FACTORY_GITHUB_APP_PRIVATE_KEY` in Infisical (names from T037); orchestrator then flips `identity.mode = "verified"` in `factory.toml` — before Phase 9. **Amended 2026-10-06 (governor):** that flip is also what makes `branch-protection-require-pr` require code-owner review, so the same PR updates the snapshot to `require_code_owner_review: true` (and an approving-review count of at least 1) and the governor switches it on in the `main` ruleset
- [ ] T066 [HITL] Governor sets branch protection on `main`: **require a pull request before merging, with bypass off for everyone including admins** (I-P10), require each `factory/<gate-id>` P1 status + existing checks, require code-owner review; orchestrator snapshots settings to `deploy/github/branch-protection.json`, and gate `branch-protection-require-pr` (slice C, `scripts/factory/src/factory/gates/repo/branch_protection.py`, test first) checks the snapshot holds the expected settings (live drift check is P3 → sprint 03 per D1). **Amended 2026-10-05 (D5, PR-C6):** done as T101, between the Slice B and Slice C merges, as a pre-merge dependency for C. The required checks name each P1 `factory/<gate-id>` context individually, each pinned to GitHub Actions as expected source (P9), plus `Factory tests`. The `factory/*` requirement switches on after C's merge and the probe, per D6 (T103). **Amended 2026-10-06 (governor, verbatim):** "**Mechanism: a repository RULESET** (Settings → Rules), not classic branch protection. The codespace token can read rulesets (`GET /repos/{o}/{r}/rulesets` returns 200) but not classic protection (403)." "**Code-owner review is deferred until the factory's GitHub App (T065) authors PRs.** PRs are authored under the governor's own account today, and GitHub won't let them approve their own PR." "'Require code-owner review' is switched on after T065. This is a governor-approved fidelity deviation; record it as such." The snapshot is the ruleset body; the gate requires code-owner review once `identity.mode = "verified"` (T065). Full text: T101, `wo-20261004-factory-slice-c.amend-07`; delta note: `PLAN_DELTA.md` § Round 4
- [ ] T066a [US1] After T066: lifecycle (`scripts/factory/src/factory/lifecycle/`) reads the branch's required checks from GitHub branch protection and adds non-factory required check runs to the acceptance set; tests in `scripts/factory/tests/unit/test_lifecycle.py` for a failed required run and a pending required run (both stay `in_review`)
- [x] T067 [P] Add `.github/CODEOWNERS` naming `governor_login` on every `rule_paths` entry from `factory.toml` — done 2026-10-06 in Slice C (amend-07): the governor's list (constitution, `AGENTS.md`, `.cursor/rules/`, `docs/agent-os/`, `scripts/factory/gates.yaml`, `scripts/factory/src/factory/gates/`, the factory workflows) plus `scripts/factory/rubrics/` (a `rule_paths` entry) and `.github/CODEOWNERS` itself. Enforcement waits for code-owner review (after T065)

---

## Phase 9: Bootstrap close — P1b (Wave 1 → 2 boundary)

**Goal**: SC-012 — prove the gates on the PRs that built them.

- [ ] T068 Contract test `scripts/factory/tests/contract/test_retro.py` — report lists each merged Wave 1 PR, each P1 gate result, and per failure a remediation order id or override — catalog `bootstrap.verdicts`
- [ ] T069 `factory retro --since <ref>` in `scripts/factory/src/factory/gates/retro.py` + `scripts/factory/src/factory/cli/gates.py`; writes `bus/postmortems/wave1-retro.yaml` via `factory bus pr`; deletes the `retro` entry from `UNBUILT` in `tests/contract/test_cli_contract.py`
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
- [ ] T081 [US7] `scripts/factory/src/factory/mining/` (corrections, proposals, post-mortem) + `factory correction new`, `factory sprint close` in `scripts/factory/src/factory/cli/mining.py`; deletes the `correction new` and `sprint close` entries from `UNBUILT` in `tests/contract/test_cli_contract.py`
  - `sprint-close-requires-postmortem`: `factory sprint close` must call `factory check intent --coverage --require-target` and must not close when it exits non-zero (SC-005b ≥ 90%; governor 2026-10-04)
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
- [ ] T104 [OD:D7] Sealed trusted red-first run (Wave 2, P2, D7), test first:
  - **Shape (P19, adopted verbatim):** "move the sealed runner and runner-owned outcome capture to a separate job with no status-write permission, then have the privileged publisher validate that exact job/run result without executing head code." "Keep the sealed parent-owned result, but run the child in a separate job with no status-write permission; let the status-writing job consume only the parent-recorded result as hostile data."
  - **Gate before implement:** a Wave 2 P* confirmation of this design (the sealed job, how its result reaches the publisher, and the publisher's validation) is required before any T104 implementation. No Wave 1 task depends on T104.
  - **Red tests** in `scripts/factory/tests/contract/test_red_first_sealed.py`, then T* review:
    - the sealed job's `permissions:` grant no `statuses: write` (nor `checks: write`, `contents: write`, `pull-requests: write`);
    - the status-writing job executes no head code: it only reads the sealed job's parent-recorded result, from that exact job/run, as hostile data, and fails closed when it is missing, malformed, from another run or bound to another head SHA;
    - the sandbox has no reachable credential: no persisted git credential, no job token or `ACTIONS_*` variable, no runner work or temp directory mounted;
    - it runs as a separate user or container;
    - the head tree is read-only: a head test that writes the tree, the harness or the outcome file fails to;
    - outcomes come from the parent: a head test that prints or writes a fake "passed" record does not change the recorded outcome;
    - a sandbox start failure fails red-first closed.
  - **Implement:** the sealed runner in `main`'s harness, in its own job without status-write permission; the publisher validates its result as data. `red-first-proof` judges from it and the `self-reported:` prefix goes. The evidence bundle stops feeding red-first.
  - Amend `contracts/gates.md` § Red-first strength and plan § CI topology if the Wave 2 P* confirmation changes the shape.
  - Catalog `ci.redfirst_sealed`.
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
- **Phase 8**: T067 can run any time after CP0. T065 is needed before T036's verified mode goes live. T036b (App token wired into git + REST) MUST land before T065 flips `identity.mode = "verified"`. T066 runs as T101 (D5 amendment below).
- **Phase 6a (D5–D8, 2026-10-05)**: delta P* triage (done) → narrow P* confirmation → T094–T095 → T096 → T097–T099. T100 after A and B are merged into C. T101 needs the B merge and must finish before the C merge. T102 needs the A merge and must merge before C. C's merge (T103 step 1) needs T097–T102. Merge order: A → B → T101 + T102 → C → merge freeze → probe → pin → verify → merges reopen (D6). T065's App gets no `statuses: write` (D8). T104 (Wave 2) follows T097.
- **Phase 9** after CP2 and T065–T066. **No Wave 2 order is issued until T070 is complete.**
- **Phases 10–13** (Wave 2) share the 3-worker cap with SWV2 lanes; US6, US7, US8 are mutually independent except T089 follows T088.

### Owned paths per slice (disjoint)

| Lane | Owns |
|------|------|
| Orchestrator (P0) | `scripts/factory/{pyproject.toml,uv.lock,gates.yaml,schemas/}`, `scripts/factory/src/factory/{api.py,bus/,config/,cli/app.py,cli/exit_codes.py,cli/checks.py,gates/registry.py}`, `scripts/factory/tests/{fixtures/,seeds/test_seeds.py,contract/test_cli_contract.py,unit/test_bus_models.py}`, `factory.toml`, `bus/`, workflows (T003–T004) |
| Slice A | `scripts/factory/src/factory/{lifecycle,board,metrics,github,identity,orders}/`, `cli/{board,orders}.py`, matching tests, `deploy/secrets/schema.yaml`, `scripts/validate_secrets_schema.py`, `scripts/test_validate_secrets_schema.py` |
| Slice B | `scripts/factory/src/factory/{gates/drift,intent}/`, `cli/intent.py`, matching tests, `gates.yaml` entries for its gates (amendment to orchestrator-owned file — append-only rows) |
| Slice C | `scripts/factory/src/factory/{gates/runner.py,gates/overrides.py,gates/pr,gates/repo,gates/retro.py,hooks}/`, `cli/gates.py`, matching tests, `.cursor/hooks.json`, `.github/workflows/factory-gates.yml` (after T004); Phase 6a adds `.github/workflows/factory-pr-evidence.yml`, `scripts/factory/tests/contract/test_ci_trust_boundary.py`, and, by amendment once A/B are merged, `gates/drift/red_first.py` and the validator root argument (not `gates/repo/status_test.py`, which belongs to T102's order) |

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
