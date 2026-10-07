"""Slice C: `factory override`, `gate run`, `hook` (`retro` is Phase 9, T069)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Annotated, Any

import typer
import yaml
from pydantic import ValidationError

from factory.api import GitHubPort, IdentityPort, PullRequest
from factory.bus.models import ORDER_ID_RE, Override, parse_message
from factory.bus.store import expected_path
from factory.cli import exit_codes
from factory.cli.common import (
    DEPS,
    CommandError,
    JsonOpt,
    RepoOpt,
    emit,
    not_implemented,
    resolve_repo,
)
from factory.config.settings import Settings, load_env, load_settings
from factory.gates.evidence import BUNDLE_FILE, produce, write_bundle
from factory.gates.evidence import GATE_ID as RED_FIRST_GATE
from factory.gates.evidence import judge as judge_evidence
from factory.gates.registry import Gate, RegistryError, load_registry
from factory.gates.repo._git import git, object_type, rev_parse
from factory.gates.runner import (
    build_context,
    ci_gates,
    commit_status,
    failures,
    order_id_from_ref,
    render_text,
    run_gates,
)
from factory.hooks.entry import run_hook

OVERRIDERS = ("governor", "orchestrator")
OVERRIDE_FILE = re.compile(r"^override-(\d{2})\.ya?ml$")
DEFAULT_BASES = ("origin/main", "main")


class _Adapters:
    """GitHub and identity adapters, built only when a command needs them."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._github: GitHubPort | None = None
        self._identity: IdentityPort | None = None

    @property
    def github(self) -> GitHubPort:
        if self._github is None:
            self._github = DEPS.github(self.settings, load_env())
        return self._github

    @property
    def identity(self) -> IdentityPort:
        if self._identity is None:
            self._identity = DEPS.identity(self.settings, self.github)
        return self._identity


def _registered(gate_id: str) -> Gate:
    try:
        return load_registry().get(gate_id)
    except RegistryError as exc:
        raise CommandError(exit_codes.USAGE, str(exc)) from exc


def _next_override_number(order_dir: Path) -> int:
    numbers = [
        int(match[1])
        for path in (order_dir.iterdir() if order_dir.is_dir() else [])
        if (match := OVERRIDE_FILE.match(path.name))
    ]
    return max(numbers, default=0) + 1


def _open_pr_number(adapters: _Adapters, order_id: str) -> int:
    open_prs = [pr for pr in adapters.github.list_prs_by_head(f"wo/{order_id}") if pr.open]
    if len(open_prs) != 1:
        raise CommandError(
            exit_codes.USAGE, f"--pr is required: wo/{order_id} has {len(open_prs)} open PRs"
        )
    return open_prs[0].number


def override(
    order_id: Annotated[str, typer.Argument(help="Order id.")],
    gate: Annotated[str, typer.Option("--gate", help="Gate id to override.")],
    reason: Annotated[str, typer.Option("--reason", help="Why the override is justified.")],
    actor: Annotated[
        str, typer.Option("--actor", help="governor | orchestrator.")
    ] = "orchestrator",
    actor_model: Annotated[
        str | None, typer.Option("--actor-model", help="Model of a non-governor actor.")
    ] = None,
    pr: Annotated[int | None, typer.Option("--pr", help="PR number.")] = None,
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Write an override message for a failing gate."""
    root = resolve_repo(repo)
    settings = load_settings(root)
    if not ORDER_ID_RE.match(order_id):
        raise CommandError(exit_codes.USAGE, f"{order_id!r} is not an order id")
    if actor not in OVERRIDERS:
        raise CommandError(exit_codes.USAGE, f"--actor must be one of {', '.join(OVERRIDERS)}")
    if actor != "governor" and not actor_model:
        raise CommandError(exit_codes.USAGE, f"--actor-model is required for actor {actor}")
    registered = _registered(gate)
    number = pr if pr is not None else _open_pr_number(_Adapters(settings), order_id)
    order_dir = root / settings.bus_dir / "orders" / order_id
    message_id = f"{order_id}.override-{_next_override_number(order_dir):02d}"
    data: dict[str, Any] = {
        "schema_version": 1,
        "kind": "override",
        "id": message_id,
        "created": DEPS.clock().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "actor": actor,
        **({"actor_model": actor_model} if actor_model else {}),
        "gate": registered.id,
        "pr": number,
        "reason": reason,
        "gate_class": registered.gate_class,
        "refs": [order_id],
    }
    try:
        message = parse_message(data, autonomy_horizon_minutes=settings.autonomy_horizon_minutes)
    except ValidationError as exc:
        problem = "; ".join(str(error["msg"]) for error in exc.errors())
        raise CommandError(exit_codes.REFUSED, f"override refused: {problem}") from exc
    relative = expected_path(message, settings.bus_dir)
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    emit(
        "override",
        as_json=json_out,
        text=f"wrote {relative} ({registered.gate_class} gate {registered.id}, PR {number})",
        data={"id": message.id, "path": str(relative), "gate_class": registered.gate_class},
    )


def _find_pr(github: GitHubPort, number: int) -> PullRequest:
    pull = github.get_pr(number)
    if pull is None:
        raise CommandError(exit_codes.USAGE, f"PR {number} does not exist in this repository")
    return pull


def _resolve(root: Path, ref: str, what: str) -> str:
    sha = rev_parse(root, ref)
    if sha is None:
        raise CommandError(exit_codes.USAGE, f"{what} {ref!r} is not a commit in {root}")
    return sha


def _default_base(root: Path) -> str:
    return next((ref for ref in DEFAULT_BASES if rev_parse(root, ref)), DEFAULT_BASES[0])


def _default_base_for(root: Path, base_ref: str) -> str:
    remote = f"origin/{base_ref}"
    return remote if rev_parse(root, remote) else base_ref


def gate_run(
    gate: Annotated[list[str] | None, typer.Option("--gate", help="Gate id (repeatable).")] = None,
    pr: Annotated[int | None, typer.Option("--pr", help="PR number.")] = None,
    base: Annotated[str | None, typer.Option("--base", help="Base ref.")] = None,
    head: Annotated[str | None, typer.Option("--head", help="Head ref.")] = None,
    expect_head: Annotated[
        str | None,
        typer.Option("--expect-head", help="Head sha the run is for; post nothing if it moved."),
    ] = None,
    evidence: Annotated[
        Path | None,
        typer.Option("--evidence", help=f"Directory holding {BUNDLE_FILE} (red-first)."),
    ] = None,
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Run registered gates; print per-intent results."""
    root = resolve_repo(repo)
    settings = load_settings(root)
    selected = [_registered(gate_id) for gate_id in gate] if gate else ci_gates(load_registry())
    adapters = _Adapters(settings)
    pull: PullRequest | None = None
    if expect_head is not None and pr is None:
        raise CommandError(exit_codes.USAGE, "--expect-head needs --pr")
    if pr is not None:
        if base or head:
            raise CommandError(exit_codes.USAGE, "--pr cannot be combined with --base/--head")
        pull = _find_pr(adapters.github, pr)
        if expect_head is not None and pull.head_sha != expect_head:
            emit(
                "gate run",
                as_json=json_out,
                text=(
                    f"PR {pr} head moved to {pull.head_sha[:12]} (this run is for "
                    f"{expect_head[:12]}): no statuses posted"
                ),
                data={"pr": pr, "head": pull.head_sha, "expected_head": expect_head, "posted": 0},
            )
            return
        if object_type(root, f"{pull.head_sha}^{{commit}}") != "commit":
            raise CommandError(exit_codes.EXTERNAL, f"PR {pr} head {pull.head_sha} is not fetched")
        head_sha = pull.head_sha
        base_sha = _resolve(root, _default_base_for(root, pull.base_ref), "base")
        order_id = order_id_from_ref(pull.head_ref)
    else:
        head_ref = head or "HEAD"
        head_sha = _resolve(root, head_ref, "head")
        base_sha = _resolve(root, base or _default_base(root), "base")
        if head_ref == "HEAD":
            head_ref = git(root, "rev-parse", "--abbrev-ref", "HEAD").strip()
        order_id = order_id_from_ref(head_ref)
    ctx = build_context(
        root, settings, base_sha=base_sha, head_sha=head_sha, order_id=order_id, pr_number=pr
    )

    def verify(message: Override) -> bool:
        return adapters.identity.is_governor_verified(message, pull)

    judges = {}
    if pull is not None or evidence is not None:
        judges[RED_FIRST_GATE] = lambda context: judge_evidence(context, evidence)
    report = run_gates(selected, ctx, verify=verify, judges=judges)
    if pull is not None:
        for entry in report["gates"]:
            state, description = commit_status(entry)
            adapters.github.set_commit_status(
                head_sha, f"factory/{entry['id']}", state, description
            )
    text = render_text(report)
    failing = failures(report)
    if failing:
        if not json_out:
            typer.echo(text)
        raise CommandError(
            exit_codes.GATE_FAILURE, f"{len(failing)} gate(s) failed: {', '.join(failing)}", report
        )
    emit("gate run", as_json=json_out, text=text, data=report)


def gate_evidence(
    base: Annotated[str, typer.Option("--base", help="Base ref or sha.")],
    head: Annotated[str, typer.Option("--head", help="Head ref or sha.")],
    out: Annotated[Path, typer.Option("--out", help=f"Directory to write {BUNDLE_FILE} into.")],
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Record red-first raw facts for the trusted judge (untrusted side; posts nothing)."""
    root = resolve_repo(repo)
    settings = load_settings(root)
    head_sha = _resolve(root, head, "head")
    ctx = build_context(
        root,
        settings,
        base_sha=_resolve(root, base, "base"),
        head_sha=head_sha,
        order_id=order_id_from_ref(head),
        pr_number=None,
    )
    bundle = produce(ctx)
    target = write_bundle(bundle, out)
    red_first = bundle.red_first
    summary = (
        f"{len(red_first.tests)} test fact(s)"
        if red_first.status == "ran"
        else f"producer crashed: {red_first.error}"
    )
    emit(
        "gate evidence",
        as_json=json_out,
        text=f"wrote {target} ({summary})",
        data={"path": str(target), "status": red_first.status, "tests": len(red_first.tests)},
    )


def hook(
    name: Annotated[str, typer.Argument(help="Hook name (contracts/hooks.md).")],
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Cursor hook entrypoint: stdin JSON -> stdout JSON."""
    code, response = run_hook(name, sys.stdin.read(), fallback_root=repo or Path.cwd())
    typer.echo(json.dumps(response))
    raise typer.Exit(code)


def retro(
    since: Annotated[str, typer.Option("--since", help="Git ref where Wave 1 started.")],
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Run P1 gates retroactively on merged Wave 1 PRs; write a report."""
    not_implemented("retro")
