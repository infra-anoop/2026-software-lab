"""Tests for scripts/provision_runtime.py (mocked Railway; no live API)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import provision_runtime as pr  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_dry_run_research_auditor_production(capsys: pytest.CaptureFixture[str]) -> None:
    code = pr.main(
        [
            "--app-id",
            "research-auditor",
            "--environment",
            "production",
            "--dry-run",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "2026-software-lab" in out
    assert "research-auditor" in out
    assert "production" in out
    assert "project" in out.lower()
    assert "service" in out.lower()
    assert "environment" in out.lower()


def test_dry_run_research_auditor_staging(capsys: pytest.CaptureFixture[str]) -> None:
    code = pr.main(
        [
            "--app-id",
            "research-auditor",
            "--environment",
            "staging",
            "--dry-run",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "research-auditor-staging" in out
    assert "staging" in out


def test_dry_run_smart_writer_staging_missing_yaml(capsys: pytest.CaptureFixture[str]) -> None:
    code = pr.main(
        [
            "--app-id",
            "smart-writer",
            "--environment",
            "staging",
            "--dry-run",
        ]
    )
    assert code == 1
    err = capsys.readouterr().err.lower()
    assert "missing" in err or "not found" in err


def test_unknown_app_fails(capsys: pytest.CaptureFixture[str]) -> None:
    code = pr.main(["--app-id", "not-an-app", "--dry-run"])
    assert code == 1
    err = capsys.readouterr().err.lower()
    assert "unknown" in err or "not" in err


def test_refuse_neither_mode(capsys: pytest.CaptureFixture[str]) -> None:
    code = pr.main(["--app-id", "research-auditor"])
    assert code == 2  # argparse error
    err = capsys.readouterr().err.lower()
    assert "dry-run" in err or "apply" in err


def test_refuse_both_modes(capsys: pytest.CaptureFixture[str]) -> None:
    code = pr.main(
        [
            "--app-id",
            "research-auditor",
            "--dry-run",
            "--apply",
        ]
    )
    assert code == 2
    err = capsys.readouterr().err.lower()
    assert "dry-run" in err or "apply" in err or "not allowed" in err


def test_apply_without_token_refuses(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RAILWAY_WORKSPACE_TOKEN", raising=False)
    monkeypatch.delenv("RAILWAY_TOKEN", raising=False)
    code = pr.main(["--app-id", "research-auditor", "--apply"])
    assert code == 1
    err = capsys.readouterr().err.lower()
    assert "token" in err


def test_select_token_prefers_workspace() -> None:
    assert (
        pr.select_railway_token(
            {
                "RAILWAY_WORKSPACE_TOKEN": "ws",
                "RAILWAY_TOKEN": "legacy",
            }
        )
        == "ws"
    )


def test_select_token_falls_back() -> None:
    assert pr.select_railway_token({"RAILWAY_TOKEN": "legacy"}) == "legacy"


def test_select_token_missing() -> None:
    assert pr.select_railway_token({}) is None


def test_load_footprint_from_repo_yaml() -> None:
    names = pr.load_footprint_names(
        "research-auditor",
        "production",
        repo_root=REPO_ROOT,
    )
    assert names.project_name == "2026-software-lab"
    assert names.service_name == "research-auditor"
    assert names.environment_name == "production"


def test_vercel_stub_not_implemented() -> None:
    stub = pr.VercelProvisioner()
    with pytest.raises(NotImplementedError):
        stub.ensure(
            pr.FootprintNames(
                project_name="p",
                service_name="s",
                environment_name="e",
            )
        )


def _edges(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    return {"edges": [{"node": n} for n in nodes]}


class FakeGraphql:
    """Minimal GraphQL stub for ensure create / exists paths."""

    def __init__(self, *, mode: str) -> None:
        self.mode = mode
        self.calls: list[tuple[str, dict[str, Any] | None]] = []
        self._created_project = False
        self._created_env = False
        self._created_service = False

    def execute(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        self.calls.append((query, variables))
        q = " ".join(query.split())

        if "__type(name: \"Mutation\")" in q or '__type(name: "Mutation")' in q:
            return {
                "data": {
                    "__type": {
                        "fields": [
                            {"name": "projectCreate"},
                            {"name": "environmentCreate"},
                            {"name": "serviceCreate"},
                        ]
                    }
                }
            }

        if "workspaces" in q and "projectCreate" not in q:
            return {"data": {"workspaces": [{"id": "ws-1", "name": "Lab"}]}}

        if "projects {" in q or "projects{" in q:
            if self.mode == "exists" or self._created_project:
                return {
                    "data": {
                        "projects": _edges(
                            [{"id": "proj-1", "name": "2026-software-lab"}]
                        )
                    }
                }
            return {"data": {"projects": _edges([])}}

        if "projectCreate" in q:
            self._created_project = True
            return {
                "data": {
                    "projectCreate": {
                        "id": "proj-1",
                        "name": "2026-software-lab",
                        "environments": _edges(
                            [{"id": "env-prod", "name": "production"}]
                        ),
                    }
                }
            }

        if "project(id" in q and "environments" in q and "services" not in q:
            envs = [{"id": "env-prod", "name": "production"}]
            if self.mode == "exists" or self._created_env or self._created_project:
                pass
            else:
                envs = []
            if self._created_env and not any(e["name"] == "staging" for e in envs):
                # staging create path may request staging
                pass
            # Include target env once created or in exists mode
            if variables and self.mode != "create_all":
                pass
            nodes = list(envs)
            if self.mode == "exists":
                nodes = [
                    {"id": "env-prod", "name": "production"},
                    {"id": "env-stg", "name": "staging"},
                ]
            elif self._created_project and not self._created_env:
                nodes = [{"id": "env-prod", "name": "production"}]
            elif self._created_env:
                # After environmentCreate, include both
                nodes = [
                    {"id": "env-prod", "name": "production"},
                    {"id": "env-stg", "name": "staging"},
                ]
            return {"data": {"project": {"environments": _edges(nodes)}}}

        if "environmentCreate" in q:
            self._created_env = True
            name = (variables or {}).get("input", {}).get("name", "staging")
            eid = "env-stg" if name == "staging" else "env-new"
            return {"data": {"environmentCreate": {"id": eid, "name": name}}}

        if "project(id" in q and "services" in q:
            services: list[dict[str, Any]] = []
            if self.mode == "exists" or self._created_service:
                env_id = "env-prod"
                services = [
                    {
                        "id": "svc-1",
                        "name": "research-auditor",
                        "serviceInstances": _edges([{"environmentId": env_id}]),
                    }
                ]
            return {"data": {"project": {"services": _edges(services)}}}

        if "serviceCreate" in q:
            self._created_service = True
            env_id = (variables or {}).get("input", {}).get("environmentId", "env-prod")
            return {
                "data": {
                    "serviceCreate": {
                        "id": "svc-1",
                        "name": "research-auditor",
                        "serviceInstances": _edges([{"environmentId": env_id}]),
                    }
                }
            }

        raise AssertionError(f"unexpected query: {q[:200]}")


def test_ensure_already_exists() -> None:
    fake = FakeGraphql(mode="exists")
    provisioner = pr.RailwayProvisioner(client=fake)
    result = provisioner.ensure(
        pr.FootprintNames(
            project_name="2026-software-lab",
            service_name="research-auditor",
            environment_name="production",
        )
    )
    assert result.project_id == "proj-1"
    assert result.environment_id == "env-prod"
    assert result.service_id == "svc-1"
    assert result.project_created is False
    assert result.environment_created is False
    assert result.service_created is False
    assert not any("Create" in c[0] for c in fake.calls if "projectCreate" in c[0])


def test_ensure_create_path() -> None:
    fake = FakeGraphql(mode="create_all")
    provisioner = pr.RailwayProvisioner(client=fake)
    result = provisioner.ensure(
        pr.FootprintNames(
            project_name="2026-software-lab",
            service_name="research-auditor",
            environment_name="production",
        )
    )
    assert result.project_id == "proj-1"
    assert result.environment_id == "env-prod"
    assert result.service_id == "svc-1"
    assert result.project_created is True
    assert result.service_created is True
    # production often comes with projectCreate; may or may not count as created
    assert any("projectCreate" in c[0] for c in fake.calls)
    assert any("serviceCreate" in c[0] for c in fake.calls)


def test_ensure_workspace_zero_fails() -> None:
    class NoWs(FakeGraphql):
        def execute(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
            q = " ".join(query.split())
            if "workspaces" in q and "projectCreate" not in q:
                return {"data": {"workspaces": []}}
            if "projects" in q:
                return {"data": {"projects": _edges([])}}
            return super().execute(query, variables)

    provisioner = pr.RailwayProvisioner(client=NoWs(mode="create_all"))
    with pytest.raises(pr.ProvisionError, match="workspace"):
        provisioner.ensure(
            pr.FootprintNames(
                project_name="2026-software-lab",
                service_name="research-auditor",
                environment_name="production",
            )
        )


def test_ensure_workspace_many_fails() -> None:
    class ManyWs(FakeGraphql):
        def execute(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
            q = " ".join(query.split())
            if "workspaces" in q and "projectCreate" not in q:
                return {
                    "data": {
                        "workspaces": [
                            {"id": "ws-1", "name": "A"},
                            {"id": "ws-2", "name": "B"},
                        ]
                    }
                }
            if "projects" in q:
                return {"data": {"projects": _edges([])}}
            return super().execute(query, variables)

    provisioner = pr.RailwayProvisioner(client=ManyWs(mode="create_all"))
    with pytest.raises(pr.ProvisionError, match="workspace"):
        provisioner.ensure(
            pr.FootprintNames(
                project_name="2026-software-lab",
                service_name="research-auditor",
                environment_name="production",
            )
        )


def test_apply_uses_provisioner(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RAILWAY_TOKEN", "test-token-not-logged")
    fake = FakeGraphql(mode="exists")
    monkeypatch.setattr(
        pr,
        "build_railway_provisioner",
        lambda token: pr.RailwayProvisioner(client=fake),
    )
    code = pr.main(["--app-id", "research-auditor", "--apply"])
    assert code == 0
    out = capsys.readouterr().out
    assert "proj-1" in out
    assert "svc-1" in out
    assert "env-prod" in out
    assert "test-token-not-logged" not in out
    err = capsys.readouterr().err
    assert "test-token-not-logged" not in err


def test_mutation_probe_fail_closed() -> None:
    class NoMutations:
        def execute(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
            q = " ".join(query.split())
            if "__type" in q:
                return {"data": {"__type": {"fields": [{"name": "deploymentCancel"}]}}}
            if "workspaces" in q:
                return {"data": {"workspaces": [{"id": "ws-1", "name": "Lab"}]}}
            if "projects" in q:
                return {"data": {"projects": _edges([])}}
            raise AssertionError(q[:120])

    provisioner = pr.RailwayProvisioner(client=NoMutations())
    with pytest.raises(pr.ProvisionError, match="projectCreate|create"):
        provisioner.ensure(
            pr.FootprintNames(
                project_name="missing-proj",
                service_name="s",
                environment_name="production",
            )
        )
