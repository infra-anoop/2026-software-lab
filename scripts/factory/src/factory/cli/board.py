"""Slice A: `factory status`, `factory decisions`, `factory scorecard`."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from factory.board.render import build_board, render_markdown
from factory.cli import exit_codes
from factory.cli.common import DEPS, CommandError, JsonOpt, RepoOpt, emit, resolve_repo
from factory.config.settings import Settings, load_env, load_settings
from factory.gates.registry import load_registry
from factory.github.rest import GitHubError
from factory.lifecycle.derive import derive_from_view
from factory.lifecycle.view import load_view
from factory.metrics.scorecard import compute_scorecard
from factory.orders import git


def _refresh(root: Path) -> None:
    """Best-effort fetch: the board still renders from the last known refs when offline."""
    try:
        git.fetch(root)
    except git.GitError as exc:
        typer.echo(f"warning: could not fetch origin; showing last known refs ({exc})", err=True)


def _open(repo: Path | None) -> tuple[Path, Settings]:
    root = resolve_repo(repo)
    settings = load_settings(root)
    _refresh(root)
    return root, settings


def status(json_out: JsonOpt = False, repo: RepoOpt = None) -> None:
    """Print the board derived from git, PR, and check reality."""
    root, settings = _open(repo)
    github = DEPS.github(settings, load_env())
    identity = DEPS.identity(settings, github)
    try:
        view = load_view(root, settings)
        snapshot = derive_from_view(view, github, settings, DEPS.clock(), repo=root)
        board = build_board(snapshot, view, github, identity, load_registry().ids())
    except GitHubError as exc:
        raise CommandError(exit_codes.EXTERNAL, str(exc)) from exc
    text = render_markdown(board, settings.concurrency_cap)
    emit("status", as_json=json_out, text=text, data=board)


def _decision_rows(root: Path, settings: Settings) -> list[dict[str, Any]]:
    view = load_view(root, settings)
    rows = []
    for decision_id, request in sorted(view.open_requests().items()):
        rows.append(
            {
                "decision_id": decision_id,
                "question": request.prompt,
                "options": [option.label for option in request.options],
                "recommended": request.recommended,
                "blocking": request.blocking,
                "feature": request.feature,
            }
        )
    return rows


def decisions(json_out: JsonOpt = False, repo: RepoOpt = None) -> None:
    """Print open decision requests (the governor's batch)."""
    root, settings = _open(repo)
    rows = _decision_rows(root, settings)
    lines = ["# Decisions waiting on you", ""]
    for n, row in enumerate(rows, start=1):
        blocking = " (blocking work)" if row["blocking"] else ""
        lines.append(f"{n}. {row['question']}{blocking}")
        for label in row["options"]:
            marker = " — recommended" if label == row["recommended"] else ""
            lines.append(f"   - {label}{marker}")
    if not rows:
        lines.append("Nothing is waiting on you.")
    emit("decisions", as_json=json_out, text="\n".join(lines), data={"open": rows})


def scorecard(
    sprint: Annotated[str | None, typer.Option("--sprint", help="Sprint id.")] = None,
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Compute the scorecard from run events, verdicts, corrections, overrides."""
    root, settings = _open(repo)
    github = DEPS.github(settings, load_env())
    try:
        card = compute_scorecard(root, settings=settings, github=github, sprint=sprint)
    except GitHubError as exc:
        raise CommandError(exit_codes.EXTERNAL, str(exc)) from exc
    card["sprint"] = sprint
    lines = ["# Scorecard", ""]
    lines.extend(f"- {key}: {value}" for key, value in card.items() if not isinstance(value, dict))
    for key, value in card.items():
        if isinstance(value, dict):
            lines.append(f"- {key}:")
            lines.extend(f"  - {name}: {n}" for name, n in value.items())
    emit("scorecard", as_json=json_out, text="\n".join(lines), data=card)
