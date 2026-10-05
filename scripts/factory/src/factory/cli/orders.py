"""Slice A: order, claim, release, handoff, PR, verdict, bus PR commands.

Thin wrappers: logic lives in `factory.orders` (I-A1); this module maps its outcomes to
exit codes and output.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import typer

from factory.cli import exit_codes
from factory.cli.common import DEPS, CommandError, JsonOpt, RepoOpt, emit, resolve_repo
from factory.config.settings import Settings, load_env, load_settings
from factory.orders.errors import External, OrderError, Refused, Usage
from factory.orders.lease import claim_order, issue_order, release_order
from factory.orders.review import handoff_order, open_bus_pr, open_pr, record_verdict
from factory.orders.scaffold import scaffold_order

OrderIdArg = Annotated[str, typer.Argument(help="Order id (wo-YYYYMMDD-<slug>).")]
ActorModelOpt = Annotated[
    str | None, typer.Option("--actor-model", help="Model of the agent running the command.")
]
UNRECORDED_MODEL = "unrecorded"

_CODES: dict[type[OrderError], int] = {
    Refused: exit_codes.REFUSED,
    Usage: exit_codes.USAGE,
    External: exit_codes.EXTERNAL,
}


def _context(repo: Path | None) -> tuple[Path, Settings]:
    root = resolve_repo(repo)
    return root, load_settings(root)


def _run[T](as_json: bool, action: Callable[[], T]) -> T:
    """Run `action`; a refusal's plain-language lines also go to stdout outside --json."""
    try:
        return action()
    except OrderError as exc:
        if exc.stdout and not as_json:
            typer.echo("\n".join(exc.stdout))
        raise CommandError(_CODES[type(exc)], exc.message, exc.details) from exc


def _notes(notes: list[str]) -> list[str]:
    """Print why a local branch was left where it was (stderr, so --json stays one object)."""
    for note in notes:
        typer.echo(note, err=True)
    return notes


def order_new(
    feature: Annotated[str, typer.Option("--feature", help="Feature folder under specs/.")],
    from_task: Annotated[list[str], typer.Option("--from-task", help="Task id (repeatable).")],
    slug: Annotated[str | None, typer.Option("--slug", help="Order id slug.")] = None,
    size_minutes: Annotated[
        int | None, typer.Option("--size-minutes", help="Size estimate in minutes.")
    ] = None,
    lock: Annotated[
        list[str] | None,
        typer.Option("--lock", help="Fidelity for a touched named lock: ID=letter|intent|waived."),
    ] = None,
    check: Annotated[
        list[str] | None,
        typer.Option("--check", help="Required gate id (repeatable; default: every P1 gate)."),
    ] = None,
    owned_path: Annotated[
        list[str] | None,
        typer.Option("--owned-path", help="Owned path glob (repeatable; default: task paths)."),
    ] = None,
    intent: Annotated[
        list[str] | None, typer.Option("--intent", help="Intent id served (repeatable).")
    ] = None,
    actor_model: ActorModelOpt = None,
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Scaffold an order file from tasks locally and validate it."""
    root, settings = _context(repo)
    path, order = _run(
        json_out,
        lambda: scaffold_order(
            root,
            settings,
            feature=feature,
            task_ids=from_task,
            slug=slug,
            size_minutes=size_minutes,
            lock_args=lock or [],
            checks=check or [],
            owned_paths=owned_path or [],
            intents=intent or [],
            actor_model=actor_model or UNRECORDED_MODEL,
            now=DEPS.clock(),
        ),
    )
    emit(
        "order new",
        as_json=json_out,
        text=f"wrote {path}; review it, then `factory order issue {order.id}`",
        data={"order_id": order.id, "path": path, "checks": order.checks},
    )


def order_issue(order_id: OrderIdArg, json_out: JsonOpt = False, repo: RepoOpt = None) -> None:
    """Create wo/<order-id> from main with the order as its first commit; push."""
    root, settings = _context(repo)
    pushed = _run(json_out, lambda: issue_order(root, settings, order_id))
    emit(
        "order issue",
        as_json=json_out,
        text=f"issued {order_id} on origin/{pushed.branch} ({pushed.sha[:7]})",
        data={
            "order_id": order_id,
            "branch": pushed.branch,
            "sha": pushed.sha,
            "notes": _notes(pushed.notes),
        },
    )


def claim(
    order_id: OrderIdArg,
    actor_model: Annotated[
        str | None, typer.Option("--actor-model", help="Claiming worker's model.")
    ] = None,
    worker_runtime: Annotated[
        str, typer.Option("--worker-runtime", help="local_subagent | cloud_agent.")
    ] = "local_subagent",
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Fast-forward push of the claim event to wo/<order-id>."""
    root, settings = _context(repo)
    github = DEPS.github(settings, load_env())
    pushed = _run(
        json_out,
        lambda: claim_order(
            root,
            settings,
            order_id,
            github=github,
            actor_model=actor_model,
            worker_runtime=worker_runtime,
            now=DEPS.clock(),
        ),
    )
    emit(
        "claim",
        as_json=json_out,
        text=f"claimed {order_id} ({pushed.sha[:7]})",
        data={
            "order_id": order_id,
            "branch": pushed.branch,
            "sha": pushed.sha,
            "notes": _notes(pushed.notes),
        },
    )


def release(
    order_id: OrderIdArg,
    reason: Annotated[str, typer.Option("--reason", help="abandoned | superseded | blocked.")],
    actor_model: ActorModelOpt = None,
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Append a release event; frees capacity."""
    root, settings = _context(repo)
    pushed = _run(
        json_out,
        lambda: release_order(
            root,
            settings,
            order_id,
            reason=reason,
            actor_model=actor_model or UNRECORDED_MODEL,
            now=DEPS.clock(),
        ),
    )
    emit(
        "release",
        as_json=json_out,
        text=f"released {order_id} ({reason})",
        data={
            "order_id": order_id,
            "branch": pushed.branch,
            "sha": pushed.sha,
            "reason": reason,
            "notes": _notes(pushed.notes),
        },
    )


def handoff(order_id: OrderIdArg, json_out: JsonOpt = False, repo: RepoOpt = None) -> None:
    """Validate the handoff and run-complete event on the order branch."""
    root, settings = _context(repo)
    result = _run(json_out, lambda: handoff_order(root, settings, order_id, now=DEPS.clock()))
    lines = [f"handoff for {order_id} is valid; pushed {result.sha[:7]}"]
    if result.gates_not_enforced:
        lines.append(f"not enforced locally yet: {', '.join(result.gates_not_enforced)}")
    emit(
        "handoff",
        as_json=json_out,
        text="\n".join(lines),
        data={
            "order_id": order_id,
            "sha": result.sha,
            "run_complete": result.run_complete,
            "run_complete_written": result.run_complete_written,
            "gates_passed": result.gates_passed,
            "gates_not_enforced": result.gates_not_enforced,
            "notes": _notes(result.notes),
        },
    )


def pr_open(order_id: OrderIdArg, json_out: JsonOpt = False, repo: RepoOpt = None) -> None:
    """Open PR wo/<order-id> -> main; body links order and intents."""
    root, settings = _context(repo)
    github = DEPS.github(settings, load_env())
    pr = _run(json_out, lambda: open_pr(root, settings, github, order_id))
    emit(
        "pr open",
        as_json=json_out,
        text=f"opened PR #{pr.number} {pr.html_url}".rstrip(),
        data={"order_id": order_id, "number": pr.number, "url": pr.html_url},
    )


def verdict(
    order_id: OrderIdArg,
    file: Annotated[Path, typer.Option("--file", help="Verdict YAML file.")],
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Validate a verdict (family, isolation inputs) and commit it to the branch."""
    root, settings = _context(repo)
    path, sha, notes = _run(json_out, lambda: record_verdict(root, settings, order_id, file))
    emit(
        "verdict",
        as_json=json_out,
        text=f"recorded {path} ({sha[:7]})",
        data={"order_id": order_id, "path": path, "sha": sha, "notes": _notes(notes)},
    )


def bus_pr(
    message: Annotated[list[Path], typer.Option("--message", help="Message file (repeatable).")],
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Open a bus PR for decision, correction, or post-mortem messages."""
    root, settings = _context(repo)
    github = DEPS.github(settings, load_env())
    pr = _run(json_out, lambda: open_bus_pr(root, settings, github, message, now=DEPS.clock()))
    emit(
        "bus pr",
        as_json=json_out,
        text=f"opened bus PR #{pr.number} from {pr.head_ref}",
        data={"number": pr.number, "head": pr.head_ref, "url": pr.html_url},
    )
