# Quickstart — validating 002

Prereqs: `nix develop`; `cd apps/smart-writer-v2 && uv sync --locked`; local Postgres (`DATABASE_URL`) for integration tests.

1. **Truthful tests (SC-008):** `uv run pytest` → green with no network; `rg -n "openai_generate_enabled|_run_generate_without_llm" app` → no matches; `uv run pytest tests/integration/test_node_coverage.py` lists every node.
2. **Durability (SC-001/002/003):** `uv run pytest tests/integration/persistence -v` (real Postgres): restart simulation, two-owner isolation, 30-day sweep with every owned row type, touch-on-use.
3. **Migrations (SC-012):** `dbmate --migrations-dir db/migrations up && dbmate rollback && dbmate up`; `schema.sql` unchanged after round trip.
4. **No silent loss (SC-004):** `uv run pytest tests/integration/test_job_recovery.py` kills a job after `materials` and asserts resume or `interrupted_retry`.
5. **Spend stop (SC-009):** `FunctionModel` reporting large usage → job `failed`, `fail_reason=spend_ceiling`.
6. **Evals (SC-005/006):** `uv run python -m evals.run --subset --dry-run` (cost estimate); seeded-regression fixture (writer prompt that drops voice only) → gate decision `block` in `lab_shared.evals` unit tests.
7. **UI in image (FR-022):** `git ls-files apps/smart-writer-v2/app/static/ui apps/smart-writer-v2/web/out` → empty; `nix build .#container-smart-writer-v2` + offline boot smoke serves `/`.
