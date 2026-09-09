#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "httpx>=0.27",
#   "pyyaml>=6",
# ]
# ///
"""Ensure Railway project / environment / service footprint from deploy YAML.

Manual bootstrap only (local CLI or workflow_dispatch). Not part of v* ship.

Auth: RAILWAY_WORKSPACE_TOKEN (preferred) or RAILWAY_TOKEN.
API: https://backboard.railway.com/graphql/v2

Exactly one of --dry-run | --apply is required.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import yaml

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import railway_graphql as rgql  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
API_URL = rgql.RAILWAY_API_URL

# Primary create mutations; short fallbacks if schema drifts.
PROJECT_CREATE_CANDIDATES = ("projectCreate",)
ENVIRONMENT_CREATE_CANDIDATES = ("environmentCreate",)
SERVICE_CREATE_CANDIDATES = ("serviceCreate",)


class ProvisionError(Exception):
    """Fail-closed provision / ensure error (safe to print; never contains tokens)."""


@dataclass(frozen=True)
class FootprintNames:
    """Runtime names from deploy/railway/<environment>/<app_id>.yml."""

    project_name: str
    service_name: str
    environment_name: str


@dataclass(frozen=True)
class EnsureResult:
    """Ids after ensure; created_* is True when this run issued a create."""

    project_id: str
    environment_id: str
    service_id: str
    project_created: bool
    environment_created: bool
    service_created: bool


@runtime_checkable
class GraphqlClient(Protocol):
    def execute(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return GraphQL JSON body; raise ProvisionError on transport/API errors."""


@runtime_checkable
class RuntimeProvisioner(Protocol):
    """Thin boundary for a later Vercel provisioner (A26: Railway only)."""

    def ensure(self, names: FootprintNames) -> EnsureResult:
        """Idempotent ensure of project → environment → service."""


def _err(msg: str) -> None:
    print(f"provision_runtime error: {msg}", file=sys.stderr)


def select_railway_token(environ: Mapping[str, str]) -> str | None:
    """Prefer RAILWAY_WORKSPACE_TOKEN, else RAILWAY_TOKEN (same as deploy.yml)."""
    return rgql.select_railway_token(environ)


def _deploy_enabled(app: dict[str, Any], default_enabled: bool) -> bool:
    deploy = app.get("deploy")
    if deploy is None:
        return default_enabled
    if not isinstance(deploy, dict):
        return default_enabled
    if "enabled" not in deploy:
        return default_enabled
    return bool(deploy["enabled"])


def collect_enabled_app_ids(
    registry: dict[str, Any] | None = None,
    *,
    repo_root: Path = REPO_ROOT,
) -> frozenset[str]:
    """Return deploy.enabled application ids from apps/registry.yaml."""
    if registry is None:
        path = repo_root / "apps" / "registry.yaml"
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ProvisionError("apps/registry.yaml root must be a mapping")
        registry = loaded

    defaults = registry.get("defaults") if isinstance(registry.get("defaults"), dict) else {}
    default_deploy = defaults.get("deploy") if isinstance(defaults.get("deploy"), dict) else {}
    default_enabled = bool(default_deploy.get("enabled", False))
    apps = registry.get("applications")
    if not isinstance(apps, list):
        return frozenset()

    ids: list[str] = []
    for app in apps:
        if not isinstance(app, dict):
            continue
        app_id = app.get("id")
        if not isinstance(app_id, str) or not app_id.strip():
            continue
        if _deploy_enabled(app, default_enabled):
            ids.append(app_id.strip())
    return frozenset(ids)


def railway_config_path(
    app_id: str,
    environment: str,
    *,
    repo_root: Path = REPO_ROOT,
) -> Path:
    return repo_root / "deploy" / "railway" / environment / f"{app_id}.yml"


def load_footprint_names(
    app_id: str,
    environment: str,
    *,
    repo_root: Path = REPO_ROOT,
) -> FootprintNames:
    """Resolve names from YAML; refuse unknown app or missing config."""
    enabled = collect_enabled_app_ids(repo_root=repo_root)
    if app_id not in enabled:
        known = ", ".join(sorted(enabled)) or "(none)"
        raise ProvisionError(
            f"unknown or deploy.disabled --app-id {app_id!r}; expected one of: {known}"
        )

    path = railway_config_path(app_id, environment, repo_root=repo_root)
    if not path.is_file():
        rel = path.relative_to(repo_root)
        raise ProvisionError(
            f"missing config: {rel} "
            f"(add deploy/railway/{environment}/{app_id}.yml — same as deploy)"
        )

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ProvisionError(f"{path.relative_to(repo_root)}: root must be a mapping")
    railway = data.get("railway")
    if not isinstance(railway, dict):
        raise ProvisionError(f"{path.relative_to(repo_root)}: missing railway mapping")

    def _req(key: str) -> str:
        val = railway.get(key)
        if not isinstance(val, str) or not val.strip():
            raise ProvisionError(
                f"{path.relative_to(repo_root)}: railway.{key} missing or empty"
            )
        return val.strip()

    return FootprintNames(
        project_name=_req("project_name"),
        service_name=_req("service_name"),
        environment_name=_req("environment_name"),
    )


def _relay_nodes(connection: Any) -> list[dict[str, Any]]:
    if not isinstance(connection, dict):
        return []
    edges = connection.get("edges")
    if not isinstance(edges, list):
        return []
    nodes: list[dict[str, Any]] = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        node = edge.get("node")
        if isinstance(node, dict):
            nodes.append(node)
    return nodes


def _first_id_by_name(nodes: Sequence[Mapping[str, Any]], name: str) -> str | None:
    for node in nodes:
        if node.get("name") == name:
            nid = node.get("id")
            if isinstance(nid, str) and nid:
                return nid
    return None


class HttpxGraphqlClient(rgql.RailwayGraphqlClient):
    """Back-compat alias — shared client lives in ``railway_graphql``."""

    def __init__(self, token: str, *, api_url: str = API_URL) -> None:
        super().__init__(token, api_url=api_url)

    def execute(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            return super().execute(query, variables)
        except rgql.RailwayGraphqlError as e:
            raise ProvisionError(str(e)) from e


class RailwayProvisioner:
    """Idempotent ensure: project → environment → service (Railway GraphQL)."""

    def __init__(self, client: GraphqlClient) -> None:
        self._client = client
        self._mutation_names: frozenset[str] | None = None

    def ensure(self, names: FootprintNames) -> EnsureResult:
        project_id, project_created = self._ensure_project(names.project_name)
        environment_id, environment_created = self._ensure_environment(
            project_id,
            names.environment_name,
        )
        service_id, service_created = self._ensure_service(
            project_id,
            environment_id,
            names.service_name,
        )
        self._assert_service_visible_for_env(
            project_id,
            environment_id,
            names.service_name,
            service_id,
            created_this_run=service_created,
        )
        return EnsureResult(
            project_id=project_id,
            environment_id=environment_id,
            service_id=service_id,
            project_created=project_created,
            environment_created=environment_created,
            service_created=service_created,
        )

    def _mutation_field_names(self) -> frozenset[str]:
        if self._mutation_names is not None:
            return self._mutation_names
        body = self._client.execute(
            '{ __type(name: "Mutation") { fields { name } } }'
        )
        fields = (body.get("data") or {}).get("__type", {}) or {}
        raw = fields.get("fields") if isinstance(fields, dict) else None
        names: set[str] = set()
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict) and isinstance(item.get("name"), str):
                    names.add(item["name"])
        self._mutation_names = frozenset(names)
        return self._mutation_names

    def _pick_mutation(self, candidates: Sequence[str], *, kind: str) -> str:
        available = self._mutation_field_names()
        for name in candidates:
            if name in available:
                return name
        raise ProvisionError(
            f"Railway GraphQL has no usable {kind} create mutation "
            f"(tried {list(candidates)}); fail closed"
        )

    def _resolve_workspace_id(self) -> str:
        body = self._client.execute("{ workspaces { id name } }")
        data = body.get("data") or {}
        workspaces = data.get("workspaces")
        nodes: list[dict[str, Any]] = []
        if isinstance(workspaces, list):
            nodes = [w for w in workspaces if isinstance(w, dict)]
        elif isinstance(workspaces, dict):
            nodes = _relay_nodes(workspaces)

        ids = [
            w["id"]
            for w in nodes
            if isinstance(w.get("id"), str) and w["id"]
        ]
        if len(ids) == 0:
            raise ProvisionError(
                "no usable Railway workspace for this token "
                "(need exactly one; RAILWAY_WORKSPACE_ID not in A26)"
            )
        if len(ids) > 1:
            raise ProvisionError(
                f"ambiguous Railway workspaces ({len(ids)}); "
                "token must see exactly one usable workspace "
                "(RAILWAY_WORKSPACE_ID not in A26)"
            )
        return ids[0]

    def _list_projects(self) -> list[dict[str, Any]]:
        body = self._client.execute("{ projects { edges { node { id name } } } }")
        data = body.get("data") or {}
        return _relay_nodes(data.get("projects"))

    def _ensure_project(self, project_name: str) -> tuple[str, bool]:
        existing = _first_id_by_name(self._list_projects(), project_name)
        if existing is not None:
            return existing, False

        workspace_id = self._resolve_workspace_id()
        mutation = self._pick_mutation(PROJECT_CREATE_CANDIDATES, kind="project")
        # Prefer workspaceId (current CLI); fall back to teamId on schema drift.
        for workspace_key in ("workspaceId", "teamId"):
            query = f"""
            mutation ($input: ProjectCreateInput!) {{
              {mutation}(input: $input) {{ id name }}
            }}
            """
            try:
                body = self._client.execute(
                    query,
                    {
                        "input": {
                            "name": project_name,
                            workspace_key: workspace_id,
                        }
                    },
                )
            except ProvisionError:
                continue
            created = (body.get("data") or {}).get(mutation)
            if isinstance(created, dict) and isinstance(created.get("id"), str):
                return created["id"], True

        raise ProvisionError(
            f"failed to create project {project_name!r} "
            f"(tried workspaceId/teamId on {mutation})"
        )

    def _list_environments(self, project_id: str) -> list[dict[str, Any]]:
        body = self._client.execute(
            """
            query ($id: String!) {
              project(id: $id) {
                environments { edges { node { id name } } }
              }
            }
            """,
            {"id": project_id},
        )
        project = (body.get("data") or {}).get("project") or {}
        return _relay_nodes(project.get("environments") if isinstance(project, dict) else None)

    def _ensure_environment(
        self,
        project_id: str,
        environment_name: str,
    ) -> tuple[str, bool]:
        existing = _first_id_by_name(self._list_environments(project_id), environment_name)
        if existing is not None:
            return existing, False

        mutation = self._pick_mutation(ENVIRONMENT_CREATE_CANDIDATES, kind="environment")
        query = f"""
        mutation ($input: EnvironmentCreateInput!) {{
          {mutation}(input: $input) {{ id name }}
        }}
        """
        body = self._client.execute(
            query,
            {"input": {"projectId": project_id, "name": environment_name}},
        )
        created = (body.get("data") or {}).get(mutation)
        if not isinstance(created, dict) or not isinstance(created.get("id"), str):
            raise ProvisionError(f"environment create returned no id for {environment_name!r}")
        return created["id"], True

    def _list_services(self, project_id: str) -> list[dict[str, Any]]:
        body = self._client.execute(
            """
            query ($id: String!) {
              project(id: $id) {
                services {
                  edges {
                    node {
                      id
                      name
                      serviceInstances {
                        edges { node { environmentId } }
                      }
                    }
                  }
                }
              }
            }
            """,
            {"id": project_id},
        )
        project = (body.get("data") or {}).get("project") or {}
        return _relay_nodes(project.get("services") if isinstance(project, dict) else None)

    def _ensure_service(
        self,
        project_id: str,
        environment_id: str,
        service_name: str,
    ) -> tuple[str, bool]:
        for node in self._list_services(project_id):
            if node.get("name") == service_name and isinstance(node.get("id"), str):
                return node["id"], False

        mutation = self._pick_mutation(SERVICE_CREATE_CANDIDATES, kind="service")
        query = f"""
        mutation ($input: ServiceCreateInput!) {{
          {mutation}(input: $input) {{
            id
            name
            serviceInstances {{ edges {{ node {{ environmentId }} }} }}
          }}
        }}
        """
        body = self._client.execute(
            query,
            {
                "input": {
                    "projectId": project_id,
                    "name": service_name,
                    "environmentId": environment_id,
                }
            },
        )
        created = (body.get("data") or {}).get(mutation)
        if not isinstance(created, dict) or not isinstance(created.get("id"), str):
            raise ProvisionError(f"service create returned no id for {service_name!r}")
        return created["id"], True

    def _assert_service_visible_for_env(
        self,
        project_id: str,
        environment_id: str,
        service_name: str,
        service_id: str,
        *,
        created_this_run: bool,
    ) -> None:
        services = self._list_services(project_id)
        match: dict[str, Any] | None = None
        for node in services:
            if node.get("id") == service_id or node.get("name") == service_name:
                match = node
                break
        if match is None:
            raise ProvisionError(
                f"service {service_name!r} ({service_id}) not visible under project after ensure"
            )

        instances = _relay_nodes(match.get("serviceInstances"))
        env_ids = {
            i.get("environmentId")
            for i in instances
            if isinstance(i.get("environmentId"), str)
        }
        if environment_id in env_ids:
            return
        if not instances and created_this_run:
            # Create used environmentId; empty instance list still OK for empty service.
            return
        if not instances and not created_this_run:
            raise ProvisionError(
                f"service {service_name!r} has no serviceInstances for environment "
                f"{environment_id}; fail closed"
            )
        raise ProvisionError(
            f"service {service_name!r} not associated with environment {environment_id}; "
            "fail closed"
        )


class VercelProvisioner:
    """Stub second backend — not implemented in A26."""

    def ensure(self, names: FootprintNames) -> EnsureResult:
        raise NotImplementedError("Vercel provisioner is not implemented in A26")


def build_railway_provisioner(token: str) -> RailwayProvisioner:
    return RailwayProvisioner(client=HttpxGraphqlClient(token))


def print_dry_run(names: FootprintNames) -> None:
    print("dry-run — planned ensure (no Railway calls):")
    print(f"  project:     {names.project_name}")
    print(f"  environment: {names.environment_name}")
    print(f"  service:     {names.service_name}")


def print_ensure_result(names: FootprintNames, result: EnsureResult) -> None:
    def _flag(created: bool) -> str:
        return "created" if created else "exists"

    print("ensure complete:")
    print(
        f"  project:     {names.project_name} id={result.project_id} "
        f"({_flag(result.project_created)})"
    )
    print(
        f"  environment: {names.environment_name} id={result.environment_id} "
        f"({_flag(result.environment_created)})"
    )
    print(
        f"  service:     {names.service_name} id={result.service_id} "
        f"({_flag(result.service_created)})"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ensure Railway project/environment/service from "
            "deploy/railway/<environment>/<app_id>.yml. "
            "Auth: RAILWAY_WORKSPACE_TOKEN (preferred) or RAILWAY_TOKEN. "
            "Workspace for project create: auto-resolve when the token sees "
            "exactly one workspace (fail closed on 0/N)."
        ),
    )
    parser.add_argument(
        "--app-id",
        required=True,
        help="Application id (must be deploy.enabled in apps/registry.yaml)",
    )
    parser.add_argument(
        "--environment",
        default="production",
        help="Config folder under deploy/railway/ (default: production)",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned project/service/env names from YAML; no Railway calls",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Perform idempotent ensure via Railway GraphQL (requires token)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as e:
        code = e.code
        return int(code) if isinstance(code, int) else 1

    try:
        names = load_footprint_names(args.app_id, args.environment)
    except ProvisionError as e:
        _err(str(e))
        return 1

    if args.dry_run:
        print_dry_run(names)
        return 0

    # --apply
    import os

    token = select_railway_token(os.environ)
    if not token:
        _err(
            "apply requires RAILWAY_WORKSPACE_TOKEN (preferred) or RAILWAY_TOKEN "
            "(or pass --dry-run)"
        )
        return 1

    try:
        provisioner = build_railway_provisioner(token)
        result = provisioner.ensure(names)
    except ProvisionError as e:
        _err(str(e))
        return 1

    print_ensure_result(names, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
