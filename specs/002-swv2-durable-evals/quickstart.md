# Quickstart — validating 002

Prereqs: `nix develop`; `cd apps/smart-writer-v2 && uv sync --locked`; local Postgres (`SMART_WRITER_V2_TEST_DATABASE_URL`) for the Postgres-backed tests in `tests/pg/` (kept out of `tests/integration/`, which the Nix check runs without a database).

1. **Truthful tests (SC-008):** `uv run pytest` → green with no network; `rg -n "openai_generate_enabled|_run_generate_without_llm|openai_revise_enabled|write_turn_canned|openai_assess_enabled|assess_draft_heuristic" app` → no matches; `uv run pytest tests/integration/test_node_coverage.py` lists every node.
2. **Durability (SC-001/002/003):** `uv run pytest tests/pg -v` (real Postgres): restart simulation, two-owner isolation, 30-day sweep with every owned row type, touch-on-use.
3. **Migrations (SC-012):** `uv run python -m app.migrate up && uv run python -m app.migrate rollback && uv run python -m app.migrate up` (renders `{{app_schema}}`, then runs dbmate); `schema.sql` unchanged after round trip.
4. **No silent loss (SC-004):** `uv run pytest tests/pg/test_job_recovery.py` kills a job after `materials` and asserts resume or `interrupted_retry`.
5. **Spend stop (SC-009):** `FunctionModel` reporting large usage → job `failed`, `fail_reason=spend_ceiling`.
6. **Evals (SC-005/006):** `uv run python -m evals.run --subset --dry-run` (cost estimate); seeded-regression fixture (writer prompt that drops voice only) → paired gate decision `block` in `lab_shared.evals` unit tests; fewer than 10 no-change pairs → `report_only`; `rg heldout .github apps/smart-writer-v2/evals/*.yaml` shows only the post-mortem runner.
7. **UI in image (FR-022):** `git ls-files apps/smart-writer-v2/app/static/ui apps/smart-writer-v2/web/out` → empty; `nix build .#container-smart-writer-v2` + offline boot smoke serves `/`.
