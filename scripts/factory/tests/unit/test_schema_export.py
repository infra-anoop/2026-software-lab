"""T008 — JSON Schema export and the stale-schema check."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import pytest

from factory.bus.models import KIND_MODELS, WorkOrder
from factory.bus.schema import SCHEMA_DIR, render_schemas, stale_schemas, write_schemas
from tests.fixtures.cli_runner import FactoryCli

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_one_schema_per_kind() -> None:
    assert set(render_schemas()) == {f"{kind}.schema.json" for kind in KIND_MODELS}


def test_committed_schemas_are_fresh() -> None:
    assert stale_schemas(SCHEMA_DIR) == []


def test_schemas_forbid_additional_properties() -> None:
    schema = json.loads(render_schemas()["order.schema.json"])
    assert schema["additionalProperties"] is False


def test_write_then_check_is_fresh(tmp_path: Path) -> None:
    write_schemas(tmp_path)
    assert stale_schemas(tmp_path) == []


def test_model_change_without_regeneration_is_stale(tmp_path: Path) -> None:
    write_schemas(tmp_path)

    class ChangedOrder(WorkOrder):
        kind: Literal["order"]
        priority: int = 0

    changed = {**KIND_MODELS, "order": ChangedOrder}
    problems = stale_schemas(tmp_path, changed)
    assert len(problems) == 1
    assert "order.schema.json" in problems[0]
    assert "stale" in problems[0]


def test_missing_and_orphan_schema_files_are_reported(tmp_path: Path) -> None:
    write_schemas(tmp_path)
    (tmp_path / "claim.schema.json").unlink()
    (tmp_path / "status.schema.json").write_text("{}\n", encoding="utf-8")
    problems = "\n".join(stale_schemas(tmp_path))
    assert "claim.schema.json: missing" in problems
    assert "status.schema.json: no message kind" in problems


def test_cli_check_schema_fails_when_committed_schema_is_stale(
    tmp_path: Path, factory_cli: FactoryCli, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_schemas(tmp_path)
    order_schema = tmp_path / "order.schema.json"
    order_schema.write_text(order_schema.read_text(encoding="utf-8").replace("goal", "aim"))
    monkeypatch.setattr("factory.cli.checks.SCHEMA_DIR", tmp_path)
    fixtures = REPO_ROOT / "scripts/factory/tests/fixtures/messages"
    result = factory_cli("check", "schema", "--path", str(fixtures), repo=REPO_ROOT)
    assert result.exit_code == 1
    assert "order.schema.json: stale" in result.stdout
