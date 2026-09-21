#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml>=6",
# ]
# ///
"""Create annotated agent tags for ops (A23/A26) and one-app ship.

Preferred agent path from a Codespace: push ``sync/<app>/<env>``,
``bootstrap/<app>/<env>`` (``ops-runtime.yml``) or ``ship/<app>/<env>``
(``ship-one.yml``).

Does **not** need ``INFISICAL_TOKEN``, ``RAILWAY_*``, or ``actions:write``.
Ordinary git push auth is enough for ``--push``.

Exactly one of ``--dry-run`` (no tag/push) or a real tag create (optional ``--push``).
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ENVIRONMENTS = frozenset({"production", "staging"})
ALLOWED_KINDS = frozenset({"sync", "bootstrap", "ship"})
OPS_TAG_RE = re.compile(
    r"^(?P<kind>sync|bootstrap|ship)/(?P<app_id>[^/]+)/(?P<environment>[^/]+)$"
)
SHIP_WORKFLOW = "ship-one.yml"
OPS_WORKFLOW = "ops-runtime.yml"

Kind = Literal["sync", "bootstrap", "ship"]


class OpsTagError(Exception):
    """Fail-closed validation / git error (safe to print)."""


@dataclass(frozen=True)
class OpsTag:
    """Parsed ops runtime tag."""

    kind: Kind
    app_id: str
    environment: str

    @property
    def name(self) -> str:
        return f"{self.kind}/{self.app_id}/{self.environment}"


def _err(msg: str) -> None:
    print(f"ops_runtime_tag error: {msg}", file=sys.stderr)


def parse_ops_tag(ref_name: str) -> OpsTag:
    """Parse ``sync|bootstrap|ship/<app_id>/<environment>``. Fail closed on extras."""
    raw = ref_name.strip()
    if not raw:
        raise OpsTagError("empty ops tag")
    if raw.count("/") != 2:
        raise OpsTagError(
            f"invalid ops tag {raw!r}: expected "
            "sync|bootstrap|ship/<app_id>/<environment> "
            "(no extra path segments)"
        )
    m = OPS_TAG_RE.fullmatch(raw)
    if m is None:
        raise OpsTagError(
            f"invalid ops tag {raw!r}: expected "
            "sync|bootstrap|ship/<app_id>/<environment>"
        )
    kind = m.group("kind")
    app_id = m.group("app_id").strip()
    environment = m.group("environment").strip()
    if kind not in ALLOWED_KINDS:
        raise OpsTagError(f"unknown kind {kind!r}")
    if not app_id or "/" in app_id:
        raise OpsTagError(f"invalid app_id in tag {raw!r}")
    if environment not in ALLOWED_ENVIRONMENTS:
        raise OpsTagError(
            f"environment must be one of {sorted(ALLOWED_ENVIRONMENTS)}; got {environment!r}"
        )
    return OpsTag(kind=kind, app_id=app_id, environment=environment)  # type: ignore[arg-type]


def build_ops_tag(kind: str, app_id: str, environment: str) -> OpsTag:
    """Build and validate a tag from CLI pieces."""
    if kind not in ALLOWED_KINDS:
        raise OpsTagError(f"kind must be one of {sorted(ALLOWED_KINDS)}; got {kind!r}")
    app = app_id.strip()
    env = environment.strip()
    if not app or "/" in app:
        raise OpsTagError(f"invalid app_id {app_id!r}")
    if env not in ALLOWED_ENVIRONMENTS:
        raise OpsTagError(
            f"environment must be one of {sorted(ALLOWED_ENVIRONMENTS)}; got {environment!r}"
        )
    return OpsTag(kind=kind, app_id=app, environment=env)  # type: ignore[arg-type]


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
    *,
    repo_root: Path = REPO_ROOT,
    registry: dict[str, Any] | None = None,
) -> frozenset[str]:
    """Return deploy.enabled application ids from apps/registry.yaml."""
    if registry is None:
        path = repo_root / "apps" / "registry.yaml"
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise OpsTagError("apps/registry.yaml root must be a mapping")
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


def assert_schema_has_app_env(
    app_id: str,
    environment: str,
    *,
    repo_root: Path = REPO_ROOT,
    schema: Mapping[str, Any] | None = None,
) -> None:
    """Fail closed unless deploy/secrets/schema.yaml lists app×env secrets."""
    if schema is None:
        path = repo_root / "deploy" / "secrets" / "schema.yaml"
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise OpsTagError("deploy/secrets/schema.yaml root must be a mapping")
        schema = loaded

    apps = schema.get("applications")
    if not isinstance(apps, dict) or app_id not in apps:
        raise OpsTagError(f"app_id {app_id!r} not in deploy/secrets/schema.yaml")
    body = apps[app_id]
    if not isinstance(body, dict):
        raise OpsTagError(f"schema applications.{app_id} must be a mapping")
    envs = body.get("environments")
    if not isinstance(envs, dict) or environment not in envs:
        raise OpsTagError(
            f"environment {environment!r} not in secrets schema for {app_id}"
        )
    env_body = envs[environment]
    if not isinstance(env_body, dict):
        raise OpsTagError(f"schema environments.{environment} must be a mapping")
    secrets = env_body.get("secrets")
    if not isinstance(secrets, list) or not secrets:
        raise OpsTagError(f"no secrets listed for {app_id}/{environment}")


def validate_app_environment(
    app_id: str,
    environment: str,
    *,
    repo_root: Path = REPO_ROOT,
) -> None:
    """Registry deploy.enabled + secrets schema presence for app×env."""
    if environment not in ALLOWED_ENVIRONMENTS:
        raise OpsTagError(
            f"environment must be one of {sorted(ALLOWED_ENVIRONMENTS)}; got {environment!r}"
        )
    enabled = collect_enabled_app_ids(repo_root=repo_root)
    if app_id not in enabled:
        raise OpsTagError(
            f"app_id {app_id!r} is not deploy.enabled in apps/registry.yaml "
            f"(enabled: {', '.join(sorted(enabled)) or 'none'})"
        )
    assert_schema_has_app_env(app_id, environment, repo_root=repo_root)


def _load_registry(*, repo_root: Path) -> dict[str, Any]:
    path = repo_root / "apps" / "registry.yaml"
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise OpsTagError("apps/registry.yaml root must be a mapping")
    return loaded


def _app_entry(app_id: str, *, repo_root: Path) -> dict[str, Any]:
    registry = _load_registry(repo_root=repo_root)
    apps = registry.get("applications")
    if not isinstance(apps, list):
        raise OpsTagError("apps/registry.yaml applications must be a list")
    for app in apps:
        if isinstance(app, dict) and app.get("id") == app_id:
            return app
    raise OpsTagError(f"app_id {app_id!r} not in apps/registry.yaml")


def lookup_ship_image(
    app_id: str,
    *,
    repo_root: Path = REPO_ROOT,
) -> tuple[str, str]:
    """Return ``(nix_attr, image_name)``. Fail if ``publish_container`` is not true."""
    app = _app_entry(app_id, repo_root=repo_root)
    ship = app.get("ship")
    if not isinstance(ship, dict) or not bool(ship.get("publish_container")):
        raise OpsTagError(
            f"app_id {app_id!r} does not have ship.publish_container in "
            "apps/registry.yaml"
        )
    oci = app.get("oci")
    image_name = oci.get("image_name") if isinstance(oci, dict) else None
    if not isinstance(image_name, str) or not image_name.strip():
        raise OpsTagError(f"app_id {app_id!r} missing oci.image_name")
    return f"container-{app_id}", image_name.strip()


def assert_deploy_yaml_exists(
    app_id: str,
    environment: str,
    *,
    repo_root: Path = REPO_ROOT,
) -> None:
    rel = Path("deploy") / "railway" / environment / f"{app_id}.yml"
    if not (repo_root / rel).is_file():
        raise OpsTagError(f"missing config: {rel.as_posix()}")


def validate_ship_app_environment(
    app_id: str,
    environment: str,
    *,
    repo_root: Path = REPO_ROOT,
) -> tuple[str, str]:
    """deploy.enabled + schema + publish_container + Railway YAML. Returns image fields."""
    validate_app_environment(app_id, environment, repo_root=repo_root)
    nix_attr, image_name = lookup_ship_image(app_id, repo_root=repo_root)
    assert_deploy_yaml_exists(app_id, environment, repo_root=repo_root)
    return nix_attr, image_name


def workflow_for_tag(tag: OpsTag | str) -> str:
    """Actions workflow filename for a tag (ship vs ops)."""
    name = tag.name if isinstance(tag, OpsTag) else tag
    if name.startswith("ship/") or (isinstance(tag, OpsTag) and tag.kind == "ship"):
        return SHIP_WORKFLOW
    return OPS_WORKFLOW


def actions_filter_url(repo_slug: str, tag_name: str) -> str:
    """GitHub Actions runs filtered by the matching workflow + branch/tag."""
    workflow = workflow_for_tag(tag_name)
    return (
        f"https://github.com/{repo_slug}/actions/workflows/{workflow}"
        f"?query=branch%3A{tag_name}"
    )


def detect_repo_slug(*, repo_root: Path = REPO_ROOT) -> str:
    """Best-effort owner/repo from origin URL; fall back to lab default."""
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo_root), "remote", "get-url", "origin"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "infra-anoop/2026-software-lab"
    # https://github.com/owner/repo(.git) or git@github.com:owner/repo.git
    m = re.search(r"github\.com[:/](?P<slug>[^/\s]+/[^/\s]+?)(?:\.git)?$", out)
    if m:
        return m.group("slug")
    return "infra-anoop/2026-software-lab"


def current_head_sha(*, repo_root: Path = REPO_ROOT) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        text=True,
    ).strip()


def remote_tag_exists(tag_name: str, *, repo_root: Path = REPO_ROOT) -> bool:
    """True if origin already has refs/tags/<tag_name>."""
    try:
        out = subprocess.check_output(
            [
                "git",
                "-C",
                str(repo_root),
                "ls-remote",
                "--tags",
                "origin",
                f"refs/tags/{tag_name}",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        # Offline / no remote: treat as absent so dry-run still works locally.
        return False
    return bool(out)


def local_tag_exists(tag_name: str, *, repo_root: Path = REPO_ROOT) -> bool:
    code = subprocess.call(
        ["git", "-C", str(repo_root), "rev-parse", "-q", "--verify", f"refs/tags/{tag_name}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return code == 0


def delete_tag(tag_name: str, *, remote: bool, repo_root: Path = REPO_ROOT) -> None:
    if local_tag_exists(tag_name, repo_root=repo_root):
        subprocess.check_call(
            ["git", "-C", str(repo_root), "tag", "-d", tag_name],
        )
    if remote:
        subprocess.check_call(
            ["git", "-C", str(repo_root), "push", "origin", f":refs/tags/{tag_name}"],
        )


def create_annotated_tag(
    tag: OpsTag,
    *,
    sha: str,
    repo_root: Path = REPO_ROOT,
) -> None:
    message = f"ops {tag.kind} {tag.app_id} {tag.environment}"
    subprocess.check_call(
        [
            "git",
            "-C",
            str(repo_root),
            "tag",
            "-a",
            tag.name,
            sha,
            "-m",
            message,
        ],
    )


def push_tag(tag_name: str, *, repo_root: Path = REPO_ROOT) -> None:
    subprocess.check_call(
        ["git", "-C", str(repo_root), "push", "origin", f"refs/tags/{tag_name}"],
    )


def print_success(
    tag: OpsTag,
    *,
    sha: str,
    repo_slug: str,
    pushed: bool,
) -> None:
    url = actions_filter_url(repo_slug, tag.name)
    workflow = workflow_for_tag(tag)
    print(f"tag: {tag.name}")
    print(f"commit: {sha}")
    print(f"actions: {url}")
    if pushed:
        print("pushed: yes")
        print(
            f"hint: gh run list --workflow={workflow} --branch "
            f"{tag.name!r}  # if gh is available"
        )
    else:
        print("pushed: no (pass --push to push origin refs/tags/...)")


def _validate_for_kind(tag: OpsTag) -> tuple[str, str] | None:
    """Validate registry/schema (and ship extras). Return nix/image for ship."""
    if tag.kind == "ship":
        return validate_ship_app_environment(
            tag.app_id, tag.environment, repo_root=REPO_ROOT
        )
    validate_app_environment(tag.app_id, tag.environment, repo_root=REPO_ROOT)
    return None


def cmd_parse(args: argparse.Namespace) -> int:
    try:
        tag = parse_ops_tag(args.ref_name)
        ship_fields = _validate_for_kind(tag)
    except OpsTagError as e:
        _err(str(e))
        return 1

    extra = ""
    if ship_fields is not None:
        nix_attr, image_name = ship_fields
        extra = f"nix_attr={nix_attr}\nimage_name={image_name}\n"

    lines = (
        f"kind={tag.kind}\n"
        f"app_id={tag.app_id}\n"
        f"environment={tag.environment}\n"
        f"tag={tag.name}\n"
        f"{extra}"
    )
    if args.github_output:
        out_path = os.environ.get("GITHUB_OUTPUT")
        if out_path:
            with open(out_path, "a", encoding="utf-8") as fh:
                fh.write(lines)
        else:
            sys.stdout.write(lines)
    else:
        sys.stdout.write(lines)
    return 0


def cmd_tag(args: argparse.Namespace) -> int:
    try:
        tag = build_ops_tag(args.kind, args.app_id, args.environment)
        _validate_for_kind(tag)
    except OpsTagError as e:
        _err(str(e))
        return 1

    sha = current_head_sha(repo_root=REPO_ROOT)
    repo_slug = detect_repo_slug(repo_root=REPO_ROOT)

    if args.dry_run:
        print(f"dry-run: would create annotated tag {tag.name} on {sha}")
        print(f"kind={tag.kind} app_id={tag.app_id} environment={tag.environment}")
        print(f"actions: {actions_filter_url(repo_slug, tag.name)}")
        if remote_tag_exists(tag.name, repo_root=REPO_ROOT):
            print(
                f"note: remote tag {tag.name!r} already exists "
                "(use --force on a real run to replace)"
            )
        return 0

    exists_remote = remote_tag_exists(tag.name, repo_root=REPO_ROOT)
    exists_local = local_tag_exists(tag.name, repo_root=REPO_ROOT)
    if exists_remote or exists_local:
        if not args.force:
            where = []
            if exists_local:
                where.append("local")
            if exists_remote:
                where.append("remote")
            _err(
                f"tag {tag.name!r} already exists ({'+'.join(where)}); "
                "pass --force to delete and recreate"
            )
            return 1
        try:
            delete_tag(tag.name, remote=exists_remote, repo_root=REPO_ROOT)
        except (OSError, subprocess.CalledProcessError) as e:
            _err(f"failed to delete existing tag: {e}")
            return 1

    try:
        create_annotated_tag(tag, sha=sha, repo_root=REPO_ROOT)
        if args.push:
            push_tag(tag.name, repo_root=REPO_ROOT)
    except (OSError, subprocess.CalledProcessError) as e:
        _err(f"git tag/push failed: {e}")
        return 1

    print_success(tag, sha=sha, repo_slug=repo_slug, pushed=bool(args.push))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    def add_tag_flags(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--app-id", required=True, help="deploy.enabled registry id")
        sp.add_argument(
            "--environment",
            required=True,
            choices=sorted(ALLOWED_ENVIRONMENTS),
            help="production | staging",
        )
        sp.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate + print tag only; do not create or push",
        )
        sp.add_argument(
            "--push",
            action="store_true",
            help="git push origin refs/tags/<tag> after create",
        )
        sp.add_argument(
            "--force",
            action="store_true",
            help="Delete existing local/remote tag before recreate",
        )

    sync = sub.add_parser("sync", help="Create sync/<app>/<env> annotated tag")
    add_tag_flags(sync)
    sync.set_defaults(kind="sync")

    boot = sub.add_parser(
        "bootstrap", help="Create bootstrap/<app>/<env> annotated tag"
    )
    add_tag_flags(boot)
    boot.set_defaults(kind="bootstrap")

    ship = sub.add_parser(
        "ship",
        help="Create ship/<app>/<env> annotated tag (verify→ship→deploy→smoke)",
    )
    add_tag_flags(ship)
    ship.set_defaults(kind="ship")

    parse = sub.add_parser(
        "parse",
        help="Parse/validate a tag ref (used by ops-runtime.yml / ship-one.yml)",
    )
    parse.add_argument(
        "--ref-name",
        required=True,
        help="github.ref_name e.g. sync/smart-writer-v2/production",
    )
    parse.add_argument(
        "--github-output",
        action="store_true",
        help="Append kind/app_id/environment/tag to $GITHUB_OUTPUT",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "parse":
        return cmd_parse(args)
    if args.command in ("sync", "bootstrap", "ship"):
        return cmd_tag(args)
    parser.error(f"unknown command {args.command!r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
