"""Tests for scripts/ops_runtime_tag.py (no live push / no vault)."""

from __future__ import annotations

import re
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


# ── db/<app_id>/<environment> (spec 002 T109; packet 2026-10-03-lab-db-bootstrap) ──


def test_parse_valid_db() -> None:
    tag = ort.parse_ops_tag("db/smart-writer-v2/staging")
    assert tag.kind == "db"
    assert tag.app_id == "smart-writer-v2"
    assert tag.environment == "staging"
    assert tag.name == "db/smart-writer-v2/staging"


def test_parse_rejects_db_extra_segments() -> None:
    with pytest.raises(ort.OpsTagError, match="extra|invalid|expected"):
        ort.parse_ops_tag("db/smart-writer-v2/production/extra")


def test_parse_rejects_db_bad_environment() -> None:
    with pytest.raises(ort.OpsTagError, match="environment"):
        ort.parse_ops_tag("db/smart-writer-v2/prod")


def test_build_ops_tag_db_roundtrip() -> None:
    tag = ort.build_ops_tag("db", "smart-writer-v2", "production")
    assert tag.kind == "db"
    assert ort.parse_ops_tag(tag.name) == tag


def test_db_tag_uses_ops_runtime_workflow() -> None:
    assert ort.workflow_for_tag("db/smart-writer-v2/production") == "ops-runtime.yml"
    assert ort.workflow_for_tag(ort.parse_ops_tag("db/smart-writer-v2/staging")) == (
        "ops-runtime.yml"
    )


def test_dry_run_db_staging(capsys: pytest.CaptureFixture[str]) -> None:
    code = ort.main(
        ["db", "--app-id", "smart-writer-v2", "--environment", "staging", "--dry-run"]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "db/smart-writer-v2/staging" in out
    assert "dry-run" in out
    assert "ops-runtime.yml" in out


def test_dry_run_db_without_declaration_fails(capsys: pytest.CaptureFixture[str]) -> None:
    code = ort.main(
        ["db", "--app-id", "research-auditor", "--environment", "production", "--dry-run"]
    )
    assert code == 1
    assert "deploy/db/research-auditor.yml" in capsys.readouterr().err


def test_parse_cli_db_github_output(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    code = ort.main(
        ["parse", "--ref-name", "db/smart-writer-v2/staging", "--github-output"]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "kind=db" in out
    assert "app_id=smart-writer-v2" in out
    assert "environment=staging" in out


def test_parse_cli_db_without_declaration_fails(capsys: pytest.CaptureFixture[str]) -> None:
    code = ort.main(["parse", "--ref-name", "db/research-auditor/production"])
    assert code == 1
    assert "deploy/db/research-auditor.yml" in capsys.readouterr().err


def test_parse_db_staging_does_not_require_secrets_schema(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """smart-writer-v2 staging has no secrets-schema row; a db tag must still parse."""
    code = ort.main(["parse", "--ref-name", "db/smart-writer-v2/staging"])
    assert code == 0
    out = capsys.readouterr().out
    assert "kind=db" in out
    assert "environment=staging" in out


def test_dry_run_sync_staging_still_requires_secrets_schema(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Contrast: sync still fail-closes on a missing secrets-schema environment."""
    code = ort.main(
        ["sync", "--app-id", "smart-writer-v2", "--environment", "staging", "--dry-run"]
    )
    assert code == 1
    err = capsys.readouterr().err.lower()
    assert "schema" in err or "environment" in err


@pytest.mark.parametrize(
    ("ref", "flag"),
    [
        ("bootstrap/smart-writer-v2/production", "db_bootstrap=true"),
        ("bootstrap/research-auditor/production", "db_bootstrap=false"),
    ],
)
def test_parse_cli_bootstrap_reports_db_bootstrap_flag(
    ref: str, flag: str, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    code = ort.main(["parse", "--ref-name", ref, "--github-output"])
    assert code == 0
    assert flag in capsys.readouterr().out.splitlines()


def _ops_steps() -> list[dict]:
    data = _load_yaml(OPS_WF)
    steps = data["jobs"]["ops"]["steps"]
    assert isinstance(steps, list)
    return steps


def _step_index(steps: list[dict], name_part: str) -> int:
    hits = [i for i, s in enumerate(steps) if name_part.lower() in str(s.get("name", "")).lower()]
    assert len(hits) == 1, f"expected exactly one step named like {name_part!r}, got {hits}"
    return hits[0]


def _step_runs(step: dict, outputs: dict[str, str]) -> bool:
    """Evaluate a step ``if:`` that only uses steps.tag.outputs.*, ==, !=, &&, ||, !, ()."""
    expr = step.get("if")
    if expr is None:
        return True
    s = str(expr).strip()
    m = re.fullmatch(r"\$\{\{(.*)\}\}", s, flags=re.DOTALL)
    if m:
        s = m.group(1)
    s = re.sub(
        r"steps\.tag\.outputs\.(\w+)",
        lambda mm: repr(outputs.get(mm.group(1), "")),
        s,
    )
    s = s.replace("success()", "True").replace("&&", " and ").replace("||", " or ")
    s = re.sub(r"!(?!=)", " not ", s)
    assert re.fullmatch(r"[\s\w'\-/=!()]*", s), f"unsupported if: expression {expr!r}"
    return bool(eval(s, {"__builtins__": {}}, {}))


def test_ops_runtime_triggers_include_db_tags() -> None:
    triggers = _load_yaml(OPS_WF).get("on", _load_yaml(OPS_WF).get(True))
    assert "db/**" in triggers["push"]["tags"]


def test_ops_runtime_db_kind_runs_only_the_database_step() -> None:
    steps = _ops_steps()
    out = {"kind": "db", "app_id": "smart-writer-v2", "environment": "staging"}
    assert _step_runs(steps[_step_index(steps, "Checkout")], out)
    assert _step_runs(steps[_step_index(steps, "Install uv")], out)
    assert _step_runs(steps[_step_index(steps, "Parse and validate")], out)
    assert _step_runs(steps[_step_index(steps, "Infisical auth")], out)
    assert _step_runs(steps[_step_index(steps, "Database login (ensure)")], out)
    assert not _step_runs(steps[_step_index(steps, "Select Railway token")], out)
    assert not _step_runs(steps[_step_index(steps, "Provision")], out)
    assert not _step_runs(steps[_step_index(steps, "Sync (apply)")], out)
    assert not _step_runs(steps[_step_index(steps, "Verify bootstrap")], out)


def test_ops_runtime_sync_kind_skips_database_step() -> None:
    steps = _ops_steps()
    out = {"kind": "sync", "app_id": "smart-writer-v2", "environment": "production"}
    assert not _step_runs(steps[_step_index(steps, "Database login (ensure)")], out)
    assert _step_runs(steps[_step_index(steps, "Select Railway token")], out)
    assert _step_runs(steps[_step_index(steps, "Sync (apply)")], out)


def test_ops_runtime_bootstrap_runs_database_step_between_provision_and_sync() -> None:
    steps = _ops_steps()
    out = {
        "kind": "bootstrap",
        "app_id": "smart-writer-v2",
        "environment": "production",
        "db_bootstrap": "true",
    }
    i_prov = _step_index(steps, "Provision")
    i_db = _step_index(steps, "Database login (ensure)")
    i_sync = _step_index(steps, "Sync (apply)")
    assert i_prov < i_db < i_sync
    for i in (i_prov, i_db, i_sync):
        assert _step_runs(steps[i], out)


def test_ops_runtime_bootstrap_without_declaration_skips_database_step() -> None:
    steps = _ops_steps()
    out = {
        "kind": "bootstrap",
        "app_id": "research-auditor",
        "environment": "production",
        "db_bootstrap": "false",
    }
    assert not _step_runs(steps[_step_index(steps, "Database login (ensure)")], out)
    assert _step_runs(steps[_step_index(steps, "Sync (apply)")], out)


def test_ops_runtime_database_step_shape() -> None:
    steps = _ops_steps()
    step = steps[_step_index(steps, "Database login (ensure)")]
    run = str(step.get("run", ""))
    assert "db_bootstrap.py ensure" in " ".join(run.split())
    assert "steps.tag.outputs.app_id" in run
    assert "steps.tag.outputs.environment" in run
    assert "GITHUB_ENV" not in run and "GITHUB_OUTPUT" not in run
    env = step.get("env") or {}
    assert "INFISICAL_TOKEN" in env
    assert "RAILWAY_TOKEN" not in env
    step_text = yaml.safe_dump(step)
    assert "secrets." not in step_text and "vars." not in step_text
    assert "environment" not in _load_yaml(OPS_WF)["jobs"]["ops"]
