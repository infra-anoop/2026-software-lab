"""Tests for scripts/ops_runtime_tag.py (no live push / no vault)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import ops_runtime_tag as ort  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
OPS_WF = REPO / ".github" / "workflows" / "ops-runtime.yml"
SYNC_WF = REPO / ".github" / "workflows" / "sync-runtime-secrets.yml"
PROVISION_WF = REPO / ".github" / "workflows" / "provision-runtime.yml"
VERIFY_WF = REPO / ".github" / "workflows" / "verify-runtime-bootstrap.yml"


def test_parse_valid_sync() -> None:
    tag = ort.parse_ops_tag("sync/smart-writer-v2/production")
    assert tag.kind == "sync"
    assert tag.app_id == "smart-writer-v2"
    assert tag.environment == "production"
    assert tag.name == "sync/smart-writer-v2/production"


def test_parse_valid_bootstrap_staging() -> None:
    tag = ort.parse_ops_tag("bootstrap/research-auditor/staging")
    assert tag.kind == "bootstrap"
    assert tag.app_id == "research-auditor"
    assert tag.environment == "staging"


def test_parse_valid_ship() -> None:
    tag = ort.parse_ops_tag("ship/smart-writer-v2/production")
    assert tag.kind == "ship"
    assert tag.app_id == "smart-writer-v2"
    assert tag.environment == "production"
    assert tag.name == "ship/smart-writer-v2/production"


def test_parse_rejects_ship_extra_segments() -> None:
    with pytest.raises(ort.OpsTagError, match="extra|invalid|expected"):
        ort.parse_ops_tag("ship/smart-writer-v2/production/v1.2.3")


def test_parse_rejects_extra_segments() -> None:
    with pytest.raises(ort.OpsTagError, match="extra|invalid|expected"):
        ort.parse_ops_tag("sync/smart-writer-v2/production/extra")


def test_parse_rejects_bad_environment() -> None:
    with pytest.raises(ort.OpsTagError, match="environment"):
        ort.parse_ops_tag("sync/smart-writer-v2/prod")


def test_parse_rejects_v_star_shape() -> None:
    with pytest.raises(ort.OpsTagError):
        ort.parse_ops_tag("v1.2.3")


def test_build_ops_tag_roundtrip() -> None:
    tag = ort.build_ops_tag("sync", "smart-writer-v2", "production")
    assert ort.parse_ops_tag(tag.name) == tag


def test_validate_enabled_app_ok() -> None:
    ort.validate_app_environment("smart-writer-v2", "production", repo_root=REPO)


def test_validate_unknown_app_fails() -> None:
    with pytest.raises(ort.OpsTagError, match="deploy.enabled|not"):
        ort.validate_app_environment("not-an-app", "production", repo_root=REPO)


def test_validate_missing_schema_env_fails() -> None:
    # smart-writer-v2 has no staging secrets schema entry today
    with pytest.raises(ort.OpsTagError, match="schema|environment"):
        ort.validate_app_environment("smart-writer-v2", "staging", repo_root=REPO)


def test_dry_run_sync(capsys: pytest.CaptureFixture[str]) -> None:
    code = ort.main(
        [
            "sync",
            "--app-id",
            "smart-writer-v2",
            "--environment",
            "production",
            "--dry-run",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "sync/smart-writer-v2/production" in out
    assert "dry-run" in out
    assert "ops-runtime.yml" in out


def test_dry_run_bootstrap(capsys: pytest.CaptureFixture[str]) -> None:
    code = ort.main(
        [
            "bootstrap",
            "--app-id",
            "research-auditor",
            "--environment",
            "production",
            "--dry-run",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "bootstrap/research-auditor/production" in out


def test_dry_run_ship(capsys: pytest.CaptureFixture[str]) -> None:
    code = ort.main(
        [
            "ship",
            "--app-id",
            "smart-writer-v2",
            "--environment",
            "production",
            "--dry-run",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "ship/smart-writer-v2/production" in out
    assert "dry-run" in out
    assert "ship-one.yml" in out
    assert "ops-runtime.yml" not in out


def test_dry_run_ship_staging_without_yaml_fails(capsys: pytest.CaptureFixture[str]) -> None:
    code = ort.main(
        [
            "ship",
            "--app-id",
            "smart-writer-v2",
            "--environment",
            "staging",
            "--dry-run",
        ]
    )
    assert code == 1
    err = capsys.readouterr().err.lower()
    assert "schema" in err or "environment" in err or "missing" in err


def test_dry_run_unknown_app_fails(capsys: pytest.CaptureFixture[str]) -> None:
    code = ort.main(
        ["sync", "--app-id", "nope", "--environment", "production", "--dry-run"]
    )
    assert code == 1
    err = capsys.readouterr().err.lower()
    assert "deploy.enabled" in err or "not" in err


def test_parse_cli_github_output(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    code = ort.main(
        [
            "parse",
            "--ref-name",
            "sync/smart-writer-v2/production",
            "--github-output",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "kind=sync" in out
    assert "app_id=smart-writer-v2" in out
    assert "environment=production" in out


def test_parse_cli_ship_github_output(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    code = ort.main(
        [
            "parse",
            "--ref-name",
            "ship/smart-writer-v2/production",
            "--github-output",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "kind=ship" in out
    assert "app_id=smart-writer-v2" in out
    assert "nix_attr=container-smart-writer-v2" in out
    assert "image_name=smart-writer-v2" in out


def test_parse_cli_invalid(capsys: pytest.CaptureFixture[str]) -> None:
    code = ort.main(["parse", "--ref-name", "sync/only-one"])
    assert code == 1
    assert "ops_runtime_tag error" in capsys.readouterr().err


def test_actions_filter_url() -> None:
    url = ort.actions_filter_url("infra-anoop/2026-software-lab", "sync/a/production")
    assert url.startswith("https://github.com/infra-anoop/2026-software-lab/actions/")
    assert "ops-runtime.yml" in url
    assert "sync%2Fa%2Fproduction" in url or "branch%3Async/a/production" in url


def test_actions_filter_url_ship() -> None:
    url = ort.actions_filter_url(
        "infra-anoop/2026-software-lab", "ship/smart-writer-v2/production"
    )
    assert "ship-one.yml" in url
    assert "ops-runtime.yml" not in url


def _load_yaml(path: Path) -> dict:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return raw


def test_ops_runtime_workflow_tag_push_only() -> None:
    assert OPS_WF.is_file()
    data = _load_yaml(OPS_WF)
    triggers = data.get("on", data.get(True))
    assert isinstance(triggers, dict)
    assert set(triggers.keys()) == {"push"}
    tags = triggers["push"]["tags"]
    assert "sync/**" in tags
    assert "bootstrap/**" in tags
    text = OPS_WF.read_text(encoding="utf-8")
    assert "id-token: write" in text
    assert "contents: read" in text
    assert "ops_runtime_tag.py" in text
    assert "sync_runtime_secrets.py" in text
    assert "provision_runtime.py" in text
    assert "verify_runtime_bootstrap.py" in text
    triggers_on = data.get("on", data.get(True))
    assert isinstance(triggers_on, dict)
    assert "workflow_dispatch" not in triggers_on


def test_break_glass_dispatch_workflows_retained() -> None:
    for path in (SYNC_WF, PROVISION_WF, VERIFY_WF):
        data = _load_yaml(path)
        triggers = data.get("on", data.get(True))
        assert isinstance(triggers, dict)
        assert "workflow_dispatch" in triggers
        text = path.read_text(encoding="utf-8")
        assert "ops tag" in text.lower() or "ops-runtime" in text.lower()
