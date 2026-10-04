# Review packet — Factory v2 P0 contract freeze: T* test review + bootstrap verdict

## Meta

| Field | Value |
|-------|-------|
| Packet id | `2026-10-03-factory-v2-p0-test-review-t` |
| Status | ready |
| Gate | T* (plus FR-037 bootstrap verdict for the P0 PR) |
| Brief | `docs/agent-os/TEST_REVIEW_PROMPT.md` |
| Feature dir | `specs/001-factory-v2/` |
| Commit | `wo/wo-20261003-factory-p0` @ `926397b` |
| Agent mode | spawned-reviewer, GPT family (D3) |

## Context to read first

- `docs/agent-os/SPAWN_REVIEWER.md`, `docs/agent-os/TEST_REVIEW_PROMPT.md`
- `specs/001-factory-v2/{spec.md,plan.md,data-model.md,contracts/*.md,research.md,acceptance.md,tasks.md}` (tasks T001–T015 are what P0 had to deliver)
- `notes/packets/2026-10-03-factory-v2-p0-contracts.md` (the work packet: DoD, owned paths, fidelity) and its `.handoff.md` (the worker's claims — **not evidence**; verify each yourself)
- Finding IDs: start at **T1** (first T* slice for this feature)

## Artifacts under review

- Diff: `git diff origin/main...origin/wo/wo-20261003-factory-p0`
- Tests: `scripts/factory/tests/**` — especially `contract/test_cli_contract.py` (CLI exit-code contract), `seeds/test_seeds.py` (SC-002 seeds), `unit/test_bus_models.py`, fixtures `tests/fixtures/{repo_builder.py,fake_github.py,messages/}`
- Frozen interfaces: `scripts/factory/src/factory/api.py`, `bus/models.py`, `gates/registry.py`, `scripts/factory/gates.yaml`, `factory.toml`
- Commands (run them; record results): from `scripts/factory`: `uv sync --locked`; `uv run pytest -q` (expect 50 failed by assertion, the rest passing); `uv run pytest -q -m "not contract and not seed"`; `uv run ruff check .`; `uv run factory check schema --path tests/fixtures/messages/`. If `uv` is not on PATH, use `nix develop -c …` or the Nix-store `uv` binary; never `pip install`.

## Review questions (in addition to the brief)

1. Do the red contract and seed tests encode the contracts **as written** (`contracts/cli.md` refusal rows and exit codes; `data-model.md` constraints; SC-002 seed list), or do any of them encode a weaker/different behavior? Would a lazy implementation pass them?
2. Are the frozen interfaces in `api.py` sufficient for slices A/B/C (`notes/packets/2026-10-04-factory-v2-slice-{a,b,c}.md`) without amendment? Name any gap (the handoff notes `GitHubPort` cannot read commit statuses).
3. Judge the worker's 12 deviations and 7 open questions in the handoff: accept, or finding.
4. Fidelity (§I): Pydantic v2 / Typer / httpx / PyYAML; uv project at `scripts/factory/`; append-only bus with no status fields; cap 3; horizon 60.

## Owned paths (may edit) — on a new branch `review/wo-20261003-factory-p0` from `origin/wo/wo-20261003-factory-p0`

- `specs/001-factory-v2/TEST_REVIEW.md` (new; T* findings, Blocker/Debate/Later/Nit with product/process/arch tags, ≥ 1 Debate and ≥ 1 strength)
- `bus/orders/wo-20261003-factory-p0/verdict-01.yaml` — bootstrap verdict per `data-model.md` § Verdict and the P0 `bus/models.py` (`kind: verdict`, `actor: reviewer`, your `reviewer_model` / `reviewer_family`, `decision: accept|reject`, `findings`, `inputs` = git paths at the sha you read, `bootstrap: true`, `manual_equivalents` = each P1 gate you checked by hand and the result). It must pass `factory check schema` on that path.

## Forbidden paths

- Everything else (no implementation fixes; report them as findings)

## Definition of Done

- [ ] `TEST_REVIEW.md` and `verdict-01.yaml` committed on `review/wo-20261003-factory-p0` and pushed
- [ ] Commands above run, results recorded in `TEST_REVIEW.md`
- [ ] Stop — the orchestrator triages; the governor adjudicates product-tagged Debates

## Fidelity (constitution §I)

| Lock | letter \| intent | Notes |
|------|------------------|-------|
| Reviewer family ≠ author family (author: Claude) | letter | you are GPT family |
| Reviewer isolation (FR-011a) | letter | inputs are git artifacts only; no chat transcripts |
