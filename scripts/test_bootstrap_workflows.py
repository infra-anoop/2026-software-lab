"""Light workflow contract tests for A23/A24 (dispatch-only; no live vault/Railway)."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SYNC_WF = REPO / ".github" / "workflows" / "sync-runtime-secrets.yml"
VERIFY_WF = REPO / ".github" / "workflows" / "verify-runtime-bootstrap.yml"
CI_CD = REPO / ".github" / "workflows" / "ci-cd-pipeline.yml"


def _load(path: Path) -> dict:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return raw


def test_sync_runtime_secrets_workflow_dispatch_only() -> None:
    assert SYNC_WF.is_file()
    data = _load(SYNC_WF)
    triggers = data.get("on", data.get(True))
    assert isinstance(triggers, dict)
    assert set(triggers.keys()) == {"workflow_dispatch"}
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert "app_id" in inputs
    assert "environment" in inputs
    assert "dry_run" in inputs
    assert inputs["dry_run"].get("default") is False
    text = SYNC_WF.read_text(encoding="utf-8")
    assert "id-token: write" in text
    assert "sync_runtime_secrets.py" in text
    assert "INFISICAL_MACHINE_IDENTITY_ID" in text
    assert "infisical_oidc_login.py" in text


def test_verify_runtime_bootstrap_workflow_dispatch_only() -> None:
    assert VERIFY_WF.is_file()
    data = _load(VERIFY_WF)
    triggers = data.get("on", data.get(True))
    assert isinstance(triggers, dict)
    assert set(triggers.keys()) == {"workflow_dispatch"}
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert "app_id" in inputs
    assert "environment" in inputs
    assert "dry_run" in inputs
    text = VERIFY_WF.read_text(encoding="utf-8")
    assert "verify_runtime_bootstrap.py" in text
    assert "variableCollectionUpsert" not in text
    assert "sync_runtime_secrets" not in text


def test_ci_cd_pipeline_does_not_call_sync_or_verify_bootstrap() -> None:
    if not CI_CD.is_file():
        return
    text = CI_CD.read_text(encoding="utf-8")
    assert "sync-runtime-secrets" not in text
    assert "verify-runtime-bootstrap" not in text
    assert "sync_runtime_secrets.py" not in text
    assert "verify_runtime_bootstrap.py" not in text
