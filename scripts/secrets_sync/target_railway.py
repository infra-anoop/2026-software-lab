"""Railway RuntimeTarget: resolve footprint + variableCollectionUpsert (A21)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Mapping

import httpx
import yaml

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import railway_graphql as rgql  # noqa: E402

from .protocols import UpsertResult

REPO_ROOT = Path(__file__).resolve().parents[2]


class FootprintMissingError(RuntimeError):
    """Project, service, or environment from deploy YAML not found on Railway."""


class RailwayRuntimeTarget:
    """Upsert service variables for deploy/railway/<environment>/<app_id>.yml."""

    def __init__(
        self,
        *,
        app_id: str,
        environment: str,
        token: str = "",
        repo_root: Path = REPO_ROOT,
        client: httpx.Client | None = None,
        graphql: rgql.RailwayGraphqlClient | None = None,
    ) -> None:
        self._app_id = app_id
        self._environment = environment
        self._token = token.strip()
        self._repo_root = repo_root
        self._cfg = self._load_yaml()
        self._ids: dict[str, str] | None = None
        if graphql is not None:
            self._gql: rgql.RailwayGraphqlClient | None = graphql
        elif self._token:
            self._gql = rgql.RailwayGraphqlClient(self._token, client=client)
        else:
            self._gql = None

    def _require_gql(self) -> rgql.RailwayGraphqlClient:
        if self._gql is None:
            raise ValueError("Railway token is empty")
        return self._gql

    @property
    def label(self) -> str:
        r = self._cfg["railway"]
        return (
            f"railway project={r['project_name']} "
            f"service={r['service_name']} env={r['environment_name']}"
        )

    def _load_yaml(self) -> dict[str, Any]:
        path = self._repo_root / "deploy" / "railway" / self._environment / f"{self._app_id}.yml"
        if not path.is_file():
            raise FileNotFoundError(f"missing deploy config: {path.relative_to(self._repo_root)}")
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or not isinstance(raw.get("railway"), dict):
            raise ValueError(f"invalid railway block in {path}")
        block = raw["railway"]
        for key in ("project_name", "service_name", "environment_name"):
            if not isinstance(block.get(key), str) or not block[key].strip():
                raise ValueError(f"{path.name}: railway.{key} required")
        return raw

    def _graphql_data(self, query: str, variables: dict[str, Any] | None = None) -> Any:
        try:
            return self._require_gql().execute_data(query, variables)
        except rgql.RailwayGraphqlError as e:
            raise RuntimeError(str(e)) from e

    def resolve_footprint(self) -> None:
        self._ids = self._resolve_ids()

    def _resolve_ids(self) -> dict[str, str]:
        r = self._cfg["railway"]
        project_name = r["project_name"]
        service_name = r["service_name"]
        env_name = r["environment_name"]

        projects = self._graphql_data("{ projects { edges { node { id name } } } }")
        edges = ((projects or {}).get("projects") or {}).get("edges") or []
        project_id = None
        for edge in edges:
            node = (edge or {}).get("node") or {}
            if node.get("name") == project_name:
                project_id = node.get("id")
                break
        if not project_id:
            raise FootprintMissingError(f"Railway project not found: {project_name!r}")

        svc_data = self._graphql_data(
            "query($id: String!) { project(id: $id) { services { edges { node { id name } } } } }",
            {"id": project_id},
        )
        svc_edges = (((svc_data or {}).get("project") or {}).get("services") or {}).get("edges") or []
        service_id = None
        for edge in svc_edges:
            node = (edge or {}).get("node") or {}
            if node.get("name") == service_name:
                service_id = node.get("id")
                break
        if not service_id:
            raise FootprintMissingError(f"Railway service not found: {service_name!r}")

        env_data = self._graphql_data(
            "query($id: String!) { project(id: $id) { environments { edges { node { id name } } } } }",
            {"id": project_id},
        )
        env_edges = (((env_data or {}).get("project") or {}).get("environments") or {}).get("edges") or []
        environment_id = None
        for edge in env_edges:
            node = (edge or {}).get("node") or {}
            if node.get("name") == env_name:
                environment_id = node.get("id")
                break
        if not environment_id:
            raise FootprintMissingError(f"Railway environment not found: {env_name!r}")

        return {
            "project_id": project_id,
            "service_id": service_id,
            "environment_id": environment_id,
        }

    def list_variable_names(self) -> frozenset[str]:
        """Return variable *names* only for the resolved service×env (A24).

        Uses the Railway ``variables`` query. Values are discarded immediately
        and must never be logged by callers.
        """
        if self._ids is None:
            self.resolve_footprint()
        assert self._ids is not None

        query = """
        query($projectId: String!, $environmentId: String!, $serviceId: String) {
          variables(
            projectId: $projectId
            environmentId: $environmentId
            serviceId: $serviceId
          )
        }
        """
        data = self._graphql_data(
            query,
            {
                "projectId": self._ids["project_id"],
                "environmentId": self._ids["environment_id"],
                "serviceId": self._ids["service_id"],
            },
        )

        raw = (data or {}).get("variables")
        if raw is None:
            raise RuntimeError(
                "Railway variables query returned null — list unavailable; fail closed"
            )
        if not isinstance(raw, dict):
            raise RuntimeError(
                "Railway variables query returned unexpected type; fail closed"
            )
        return frozenset(str(k) for k in raw.keys() if isinstance(k, str) and k)

    def upsert_variables(self, variables: Mapping[str, str]) -> UpsertResult:
        if not variables:
            return {"upserted": [], "noop": []}
        if self._ids is None:
            self.resolve_footprint()
        assert self._ids is not None

        mutation = """
        mutation($input: VariableCollectionUpsertInput!) {
          variableCollectionUpsert(input: $input)
        }
        """
        input_obj: dict[str, Any] = {
            "projectId": self._ids["project_id"],
            "environmentId": self._ids["environment_id"],
            "serviceId": self._ids["service_id"],
            "variables": dict(variables),
            "replace": False,
            "skipDeploys": True,
        }
        try:
            self._graphql_data(mutation, {"input": input_obj})
        except RuntimeError:
            input_obj.pop("skipDeploys", None)
            self._graphql_data(mutation, {"input": input_obj})

        names = sorted(variables.keys())
        return {"upserted": names, "noop": []}
