"""A21 contract tests — TDD: behavior locked here; adapters mocked (no live vault/Railway)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

import httpx
import pytest

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from secrets_sync.protocols import UpsertResult, VaultRef  # noqa: E402
from secrets_sync.schema import (  # noqa: E402
    assert_names_in_schema,
    load_secret_entries,
)
from secrets_sync.sync import build_plan, run_apply, run_dry_run  # noqa: E402
from secrets_sync.target_railway import (  # noqa: E402
    FootprintMissingError,
    RailwayRuntimeTarget,
)
from secrets_sync.target_vercel import VercelRuntimeTarget  # noqa: E402
from secrets_sync.vault_infisical import DictVaultBackend, InfisicalCloudBackend  # noqa: E402
import sync_runtime_secrets as cli  # noqa: E402


# ── Schema (A20 map) ─────────────────────────────────────────────────────────


def test_load_secret_entries_research_auditor_production() -> None:
    entries = load_secret_entries("research-auditor", "production")
    names = [e.name for e in entries]
    assert "OPENAI_API_KEY" in names
    assert "LOGFIRE_TOKEN" in names
    assert any(e.required and e.name == "OPENAI_API_KEY" for e in entries)


def test_load_secret_entries_unknown_app_fails() -> None:
    with pytest.raises(ValueError, match="not in secrets schema"):
        load_secret_entries("no-such-app", "production")


def test_load_secret_entries_unknown_env_fails() -> None:
    with pytest.raises(ValueError, match="not in schema"):
        load_secret_entries("smart-writer", "staging")


def test_assert_names_in_schema_rejects_unknown() -> None:
    entries = load_secret_entries("smart-writer", "production")
    with pytest.raises(ValueError, match="not in A20 schema"):
        assert_names_in_schema({"OPENAI_API_KEY", "HACKER_KEY"}, entries)


# ── Dry-run: names only, never values ─────────────────────────────────────────


def test_dry_run_lists_names_not_values() -> None:
    entries = load_secret_entries("smart-writer", "production")

    class _T:
        label = "railway project=demo service=smart-writer env=production"

        def resolve_footprint(self) -> None:
            raise AssertionError("dry-run must not resolve footprint")

        def upsert_variables(self, variables: Mapping[str, str]) -> UpsertResult:
            raise AssertionError("dry-run must not upsert")

    plan = build_plan(
        app_id="smart-writer",
        environment="production",
        entries=entries,
        target=_T(),  # type: ignore[arg-type]
    )
    lines = "\n".join(run_dry_run(plan))
    assert "OPENAI_API_KEY" in lines
    assert "LOGFIRE_TOKEN" in lines
    assert "sk-" not in lines
    assert "upsert" not in lines.lower() or "secrets" in lines.lower()


def test_cli_dry_run_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(
        ["--app-id", "research-auditor", "--environment", "production", "--dry-run"]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "OPENAI_API_KEY" in out
    assert "required" in out


def test_cli_requires_exactly_one_mode() -> None:
    with pytest.raises(SystemExit):
        cli.main(["--app-id", "smart-writer"])


# ── Apply orchestration with fake vault + fake target ─────────────────────────


class _RecordingTarget:
    def __init__(self) -> None:
        self.upserted: dict[str, str] | None = None
        self.resolved = False

    @property
    def label(self) -> str:
        return "fake-target"

    def resolve_footprint(self) -> None:
        self.resolved = True

    def upsert_variables(self, variables: Mapping[str, str]) -> UpsertResult:
        self.upserted = dict(variables)
        return {"upserted": sorted(variables.keys()), "noop": []}


def test_apply_fetches_vault_and_upserts_without_logging_values(
    capsys: pytest.CaptureFixture[str],
) -> None:
    entries = load_secret_entries("research-auditor", "production")
    store: dict[tuple[str, str, str, str], str] = {}
    for e in entries:
        r = e.vault_ref
        store[(r["project"], r["env"], r["path"], r["key"])] = f"secret-value-for-{e.name}"

    vault = DictVaultBackend(store)
    target = _RecordingTarget()
    result = run_apply(entries=entries, vault=vault, target=target)

    assert target.resolved is True
    assert target.upserted is not None
    assert "OPENAI_API_KEY" in target.upserted
    assert target.upserted["OPENAI_API_KEY"] == "secret-value-for-OPENAI_API_KEY"
    assert set(result["upserted"]) == set(target.upserted)

    # Capsys should be empty from run_apply itself (no prints of values)
    captured = capsys.readouterr()
    assert "secret-value-for-" not in captured.out
    assert "secret-value-for-" not in captured.err


def test_apply_fails_if_required_missing_from_vault() -> None:
    entries = load_secret_entries("research-auditor", "production")
    # Only optional secrets present
    store: dict[tuple[str, str, str, str], str] = {}
    for e in entries:
        if e.required:
            continue
        r = e.vault_ref
        store[(r["project"], r["env"], r["path"], r["key"])] = "x"

    with pytest.raises(ValueError, match="required secrets missing"):
        run_apply(entries=entries, vault=DictVaultBackend(store), target=_RecordingTarget())


def test_apply_skips_missing_optional() -> None:
    entries = [e for e in load_secret_entries("research-auditor", "production") if e.required]
    # Add one optional entry manually by reloading and filtering vault
    all_entries = load_secret_entries("research-auditor", "production")
    store: dict[tuple[str, str, str, str], str] = {}
    for e in all_entries:
        if e.name == "OPENAI_API_KEY":
            r = e.vault_ref
            store[(r["project"], r["env"], r["path"], r["key"])] = "only-openai"

    target = _RecordingTarget()
    result = run_apply(entries=all_entries, vault=DictVaultBackend(store), target=target)
    assert result["upserted"] == ["OPENAI_API_KEY"]
    assert "LOGFIRE_TOKEN" in result["noop"]
    assert target.upserted == {"OPENAI_API_KEY": "only-openai"}


# ── Infisical HTTP backend (mocked transport) ─────────────────────────────────


def test_infisical_backend_maps_secret_keys() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "Authorization" in request.headers
        assert request.headers["Authorization"].startswith("Bearer ")
        body = {
            "secrets": [
                {"secretKey": "OPENAI_API_KEY", "secretValue": "from-infisical"},
                {"secretKey": "OTHER", "secretValue": "nope"},
            ]
        }
        return httpx.Response(200, json=body)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    backend = InfisicalCloudBackend(token="tok", client=client)
    refs: list[VaultRef] = [
        {
            "project": "research-auditor",
            "env": "production",
            "path": "/",
            "key": "OPENAI_API_KEY",
        }
    ]
    got = backend.get_secrets(refs)
    assert got == {"OPENAI_API_KEY": "from-infisical"}
    client.close()


def test_infisical_backend_rejects_empty_token() -> None:
    with pytest.raises(ValueError, match="empty"):
        InfisicalCloudBackend(token="  ")


# ── Railway target (mocked GraphQL) ───────────────────────────────────────────


def _graphql_router(request: httpx.Request) -> httpx.Response:
    payload = json.loads(request.content.decode())
    query = payload.get("query", "")
    variables = payload.get("variables") or {}

    if "projects {" in query and "project(id" not in query:
        return httpx.Response(
            200,
            json={
                "data": {
                    "projects": {
                        "edges": [
                            {"node": {"id": "proj-1", "name": "2026-software-lab"}},
                        ]
                    }
                }
            },
        )
    if "services {" in query:
        return httpx.Response(
            200,
            json={
                "data": {
                    "project": {
                        "services": {
                            "edges": [
                                {"node": {"id": "svc-1", "name": "research-auditor"}},
                            ]
                        }
                    }
                }
            },
        )
    if "environments {" in query:
        return httpx.Response(
            200,
            json={
                "data": {
                    "project": {
                        "environments": {
                            "edges": [
                                {"node": {"id": "env-1", "name": "production"}},
                            ]
                        }
                    }
                }
            },
        )
    if "variableCollectionUpsert" in query:
        inp = variables.get("input") or {}
        # Contract: never use replace=True in A21 (merge upsert)
        assert inp.get("replace") is False
        assert inp.get("projectId") == "proj-1"
        assert inp.get("serviceId") == "svc-1"
        assert inp.get("environmentId") == "env-1"
        assert "OPENAI_API_KEY" in (inp.get("variables") or {})
        # Must not appear in response logging path — mutation returns bool
        return httpx.Response(200, json={"data": {"variableCollectionUpsert": True}})

    return httpx.Response(200, json={"data": {}})


def test_railway_resolve_and_upsert_mocked() -> None:
    transport = httpx.MockTransport(_graphql_router)
    client = httpx.Client(transport=transport)
    target = RailwayRuntimeTarget(
        app_id="research-auditor",
        environment="production",
        token="railway-tok",
        client=client,
    )
    assert "research-auditor" in target.label
    target.resolve_footprint()
    result = target.upsert_variables({"OPENAI_API_KEY": "should-not-be-logged"})
    assert result["upserted"] == ["OPENAI_API_KEY"]
    client.close()


def test_railway_footprint_missing_service() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        query = payload.get("query", "")
        if "projects {" in query and "project(id" not in query:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "projects": {
                            "edges": [
                                {"node": {"id": "proj-1", "name": "2026-software-lab"}},
                            ]
                        }
                    }
                },
            )
        if "services {" in query:
            return httpx.Response(
                200,
                json={"data": {"project": {"services": {"edges": []}}}},
            )
        return httpx.Response(200, json={"data": {}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    target = RailwayRuntimeTarget(
        app_id="research-auditor",
        environment="production",
        token="tok",
        client=client,
    )
    with pytest.raises(FootprintMissingError, match="service"):
        target.resolve_footprint()
    client.close()


# ── Vercel stub ───────────────────────────────────────────────────────────────


def test_vercel_target_not_implemented() -> None:
    t = VercelRuntimeTarget()
    with pytest.raises(NotImplementedError):
        t.resolve_footprint()
    with pytest.raises(NotImplementedError):
        t.upsert_variables({"A": "b"})


# ── CLI apply refuse without tokens ───────────────────────────────────────────


def test_cli_apply_refuses_without_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAILWAY_WORKSPACE_TOKEN", raising=False)
    monkeypatch.delenv("RAILWAY_TOKEN", raising=False)
    monkeypatch.delenv("INFISICAL_TOKEN", raising=False)
    code = cli.main(
        ["--app-id", "smart-writer", "--environment", "production", "--apply"]
    )
    assert code == 1
