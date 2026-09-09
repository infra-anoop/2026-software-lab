"""Unit tests for scripts/validate_secrets_schema.py (no live vault)."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import validate_secrets_schema as vss  # noqa: E402


def _minimal_secret(name: str, *, required: bool = False) -> dict:
    return {
        "name": name,
        "required": required,
        "vault_ref": {
            "project": "app",
            "env": "production",
            "path": "/",
            "key": name,
        },
    }


def _base_schema() -> dict:
    return {
        "schema_version": 1,
        "vault": {"provider": "infisical_cloud"},
        "applications": {
            "demo-app": {
                "environments": {
                    "production": {
                        "secrets": [
                            _minimal_secret("OPENAI_API_KEY", required=True),
                            _minimal_secret("LOGFIRE_TOKEN"),
                        ]
                    }
                }
            }
        },
    }


def test_validate_schema_ok() -> None:
    schema = _base_schema()
    errors = vss.validate_schema(
        schema,
        enabled_app_ids=["demo-app"],
        catalogs={"demo-app": (("OPENAI_API_KEY",), ("OPENAI_API_KEY", "LOGFIRE_TOKEN"))},
        railway_envs_by_app={"demo-app": {"production"}},
    )
    assert errors == []


def test_unknown_name_fails() -> None:
    schema = _base_schema()
    schema["applications"]["demo-app"]["environments"]["production"]["secrets"].append(
        _minimal_secret("NOT_IN_CATALOG")
    )
    errors = vss.validate_schema(
        schema,
        enabled_app_ids=["demo-app"],
        catalogs={"demo-app": (("OPENAI_API_KEY",), ("OPENAI_API_KEY", "LOGFIRE_TOKEN"))},
        railway_envs_by_app={"demo-app": {"production"}},
    )
    assert any("NOT_IN_CATALOG" in e for e in errors)


def test_missing_logfire_fails_a25() -> None:
    schema = _base_schema()
    secrets = schema["applications"]["demo-app"]["environments"]["production"]["secrets"]
    schema["applications"]["demo-app"]["environments"]["production"]["secrets"] = [
        s for s in secrets if s["name"] != "LOGFIRE_TOKEN"
    ]
    errors = vss.validate_schema(
        schema,
        enabled_app_ids=["demo-app"],
        catalogs={"demo-app": (("OPENAI_API_KEY",), ("OPENAI_API_KEY", "LOGFIRE_TOKEN"))},
        railway_envs_by_app={"demo-app": {"production"}},
    )
    assert any("LOGFIRE_TOKEN" in e for e in errors)


def test_missing_deploy_enabled_app_fails() -> None:
    schema = _base_schema()
    errors = vss.validate_schema(
        schema,
        enabled_app_ids=["demo-app", "other-app"],
        catalogs={
            "demo-app": (("OPENAI_API_KEY",), ("OPENAI_API_KEY", "LOGFIRE_TOKEN")),
            "other-app": (("OPENAI_API_KEY",), ("OPENAI_API_KEY", "LOGFIRE_TOKEN")),
        },
        railway_envs_by_app={"demo-app": {"production"}, "other-app": {"production"}},
    )
    assert any("other-app" in e for e in errors)


def test_wrong_provider_fails() -> None:
    schema = _base_schema()
    schema["vault"]["provider"] = "doppler"
    errors = vss.validate_schema(
        schema,
        enabled_app_ids=["demo-app"],
        catalogs={"demo-app": (("OPENAI_API_KEY",), ("OPENAI_API_KEY", "LOGFIRE_TOKEN"))},
        railway_envs_by_app={"demo-app": {"production"}},
    )
    assert any("infisical_cloud" in e for e in errors)


def test_missing_railway_env_in_schema_fails() -> None:
    schema = _base_schema()
    errors = vss.validate_schema(
        schema,
        enabled_app_ids=["demo-app"],
        catalogs={"demo-app": (("OPENAI_API_KEY",), ("OPENAI_API_KEY", "LOGFIRE_TOKEN"))},
        railway_envs_by_app={"demo-app": {"production", "staging"}},
    )
    assert any("staging" in e for e in errors)


def test_repo_schema_main_exits_zero() -> None:
    assert vss.main([]) == 0


def test_required_flag_must_match_settings() -> None:
    schema = _base_schema()
    for s in schema["applications"]["demo-app"]["environments"]["production"]["secrets"]:
        if s["name"] == "OPENAI_API_KEY":
            s["required"] = False
    errors = vss.validate_schema(
        schema,
        enabled_app_ids=["demo-app"],
        catalogs={"demo-app": (("OPENAI_API_KEY",), ("OPENAI_API_KEY", "LOGFIRE_TOKEN"))},
        railway_envs_by_app={"demo-app": {"production"}},
    )
    assert any("OPENAI_API_KEY" in e and "required: true" in e for e in errors)


def test_copy_isolation() -> None:
    """sanity: mutating a copy does not break base fixture shape."""
    a = _base_schema()
    b = copy.deepcopy(a)
    b["vault"]["provider"] = "x"
    assert a["vault"]["provider"] == "infisical_cloud"
