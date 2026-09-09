"""Tests for scripts/verify_runtime_bootstrap.py (mocked Railway; no live API)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import verify_runtime_bootstrap as vrb  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def test_required_names_union_research_auditor() -> None:
    names = vrb.required_secret_names("research-auditor", "production", repo_root=REPO)
    assert "OPENAI_API_KEY" in names
    # Union may equal YAML-only or schema-only required today
    assert names == frozenset({"OPENAI_API_KEY"})


def test_dry_run_prints_planned_checks(capsys: pytest.CaptureFixture[str]) -> None:
    code = vrb.main(
        ["--app-id", "research-auditor", "--environment", "production", "--dry-run"]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "2026-software-lab" in out
    assert "research-auditor" in out
    assert "OPENAI_API_KEY" in out
    assert "sk-" not in out


def test_dry_run_missing_yaml_refuses(capsys: pytest.CaptureFixture[str]) -> None:
    code = vrb.main(
        ["--app-id", "smart-writer", "--environment", "staging", "--dry-run"]
    )
    assert code == 1
    assert "missing" in capsys.readouterr().err.lower()


def test_live_refuses_without_token(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("RAILWAY_WORKSPACE_TOKEN", raising=False)
    monkeypatch.delenv("RAILWAY_TOKEN", raising=False)
    code = vrb.main(["--app-id", "research-auditor", "--environment", "production"])
    assert code == 1
    assert "token" in capsys.readouterr().err.lower()


def _ok_transport(*, var_map: dict[str, str]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode()
        if "projects {" in body:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "projects": {
                            "edges": [
                                {"node": {"id": "proj-1", "name": "2026-software-lab"}}
                            ]
                        }
                    }
                },
            )
        if "services {" in body:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "project": {
                            "services": {
                                "edges": [
                                    {"node": {"id": "svc-1", "name": "research-auditor"}}
                                ]
                            }
                        }
                    }
                },
            )
        if "environments {" in body:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "project": {
                            "environments": {
                                "edges": [
                                    {"node": {"id": "env-1", "name": "production"}}
                                ]
                            }
                        }
                    }
                },
            )
        if "variables(" in body or "variables (" in body:
            # Return values — verify must never print them
            return httpx.Response(200, json={"data": {"variables": var_map}})
        return httpx.Response(200, json={"data": {}})

    return httpx.MockTransport(handler)


def test_verify_pass_names_only(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("RAILWAY_TOKEN", "tok")
    client = httpx.Client(
        transport=_ok_transport(
            var_map={"OPENAI_API_KEY": "sk-SECRET-VALUE", "LOGFIRE_TOKEN": "lf-x"}
        )
    )
    monkeypatch.setattr(
        vrb,
        "build_railway_client",
        lambda token: client,
    )
    code = vrb.main(["--app-id", "research-auditor", "--environment", "production"])
    assert code == 0
    out = capsys.readouterr().out
    assert "OPENAI_API_KEY" in out
    assert "ok" in out.lower() or "pass" in out.lower() or "verify" in out.lower()
    assert "sk-SECRET-VALUE" not in out
    assert "lf-x" not in out
    client.close()


def test_verify_missing_required_name(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("RAILWAY_TOKEN", "tok")
    client = httpx.Client(transport=_ok_transport(var_map={"LOGFIRE_TOKEN": "lf-x"}))
    monkeypatch.setattr(vrb, "build_railway_client", lambda token: client)
    code = vrb.main(["--app-id", "research-auditor", "--environment", "production"])
    assert code == 1
    err = capsys.readouterr().err
    assert "OPENAI_API_KEY" in err
    assert "sk-" not in err
    assert "lf-x" not in err
    client.close()


def test_verify_missing_footprint_exit_2(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("RAILWAY_TOKEN", "tok")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"data": {"projects": {"edges": []}}},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(vrb, "build_railway_client", lambda token: client)
    code = vrb.main(["--app-id", "research-auditor", "--environment", "production"])
    assert code == 2
    assert "footprint" in capsys.readouterr().err.lower()
    client.close()


def test_list_variable_names_discards_values() -> None:
    names = vrb.variable_names_from_payload(
        {"OPENAI_API_KEY": "sk-leak", "OTHER": "x"}
    )
    assert names == frozenset({"OPENAI_API_KEY", "OTHER"})
