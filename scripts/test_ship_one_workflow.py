"""Contract tests for one-app ship tags (no live GHCR / Railway)."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SHIP_ONE = REPO / ".github" / "workflows" / "ship-one.yml"
SHIP_REG = REPO / ".github" / "workflows" / "ship-registry.yml"
CI_CD = REPO / ".github" / "workflows" / "ci-cd-pipeline.yml"
PLAYBOOK = REPO / "notes" / "codespace-a23-dispatch.md"
RAILWAY_README = REPO / "deploy" / "railway" / "README.md"
SWV2_README = REPO / "apps" / "smart-writer-v2" / "README.md"
AGENTS = REPO / "AGENTS.md"


def _load(path: Path) -> dict:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return raw


def _on(data: dict) -> dict:
    triggers = data.get("on", data.get(True))
    assert isinstance(triggers, dict)
    return triggers


def test_ship_one_workflow_tag_push_only() -> None:
    assert SHIP_ONE.is_file()
    data = _load(SHIP_ONE)
    triggers = _on(data)
    assert set(triggers.keys()) == {"push"}
    assert triggers["push"]["tags"] == ["ship/**"]
    assert "workflow_dispatch" not in triggers
    text = SHIP_ONE.read_text(encoding="utf-8")
    assert "verify-source.yml" in text
    assert "ship-registry.yml" in text
    assert "deploy.yml" in text
    assert "smoke-test.yml" in text
    assert "image_tag" in text
    assert "sync_runtime_secrets" not in text
    assert "INFISICAL" not in text
    assert "provision_runtime.py" not in text


def test_ship_registry_workflow_call_has_optional_image_tag() -> None:
    data = _load(SHIP_REG)
    triggers = _on(data)
    call = triggers["workflow_call"]["inputs"]
    assert "image_tag" in call
    assert call["image_tag"].get("required") is not True
    ci = CI_CD.read_text(encoding="utf-8")
    ship_block = ci.split("uses: ./.github/workflows/ship-registry.yml", 1)[1]
    ship_with = ship_block.split("secrets:", 1)[0]
    assert "image_tag:" not in ship_with


def test_ci_cd_pipeline_push_tags_v_star_only() -> None:
    data = _load(CI_CD)
    push = _on(data)["push"]
    assert isinstance(push, dict)
    assert push.get("tags") == ["v*"]
    assert "branches" in push


def test_agent_docs_prefer_ship_helper() -> None:
    playbook = PLAYBOOK.read_text(encoding="utf-8")
    assert "ops_runtime_tag.py ship" in playbook
    railway = RAILWAY_README.read_text(encoding="utf-8")
    assert "ops_runtime_tag.py ship" in railway
    assert "Use `workflow_dispatch` on `ship-registry.yml`" not in railway
    swv2 = SWV2_README.read_text(encoding="utf-8")
    assert "ops_runtime_tag.py ship" in swv2
    agents = AGENTS.read_text(encoding="utf-8")
    assert "ops_runtime_tag.py ship" in agents or "ship/<app" in agents
