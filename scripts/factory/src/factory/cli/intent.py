"""Slice B: `factory check intent [--coverage [--require-target]]` (FR-023; SC-005)."""

from __future__ import annotations

from typing import Annotated

import typer

from factory.cli import exit_codes
from factory.cli.common import DEPS, CommandError, JsonOpt, RepoOpt, emit, resolve_repo
from factory.config.settings import load_env, load_settings
from factory.gates.drift._git import GitError, git
from factory.intent.coverage import IntentError, WorkTree, coverage, presence


def check_intent(
    coverage_opt: Annotated[
        bool,
        typer.Option("--coverage", help="Also report effective coverage (report-only)."),
    ] = False,
    require_target: Annotated[
        bool,
        typer.Option(
            "--require-target",
            help="With --coverage: exit 1 when effective coverage is below 90% (sprint close).",
        ),
    ] = False,
    json_out: JsonOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Every intent maps to at least one check (presence); optionally effective coverage."""
    if require_target and not coverage_opt:
        raise CommandError(exit_codes.USAGE, "--require-target needs --coverage")
    root = resolve_repo(repo)
    settings = load_settings(root)
    tree = WorkTree(root)
    try:
        found = presence(tree, settings.spec_roots)
    except IntentError as exc:
        raise CommandError(exit_codes.GATE_FAILURE, str(exc)) from exc
    data: dict[str, object] = {"intents": found.intents, "unmapped": found.unmapped}
    if found.unmapped:
        message = f"intent(s) without any check mapping: {', '.join(found.unmapped)}"
        if not json_out:
            typer.echo(message)
        raise CommandError(exit_codes.GATE_FAILURE, message, {"unmapped": found.unmapped})
    lines = [f"intent presence ok: {len(found.intents)} intent(s), all mapped"]
    if coverage_opt:
        try:
            head = git(root, "rev-parse", "HEAD").strip()
        except GitError as exc:
            raise CommandError(exit_codes.EXTERNAL, f"cannot resolve HEAD: {exc}") from exc
        github = DEPS.github(settings, load_env())
        statuses = {s.context: s.state for s in github.list_commit_statuses(head)}
        result = coverage(tree, settings.spec_roots, statuses)
        data["coverage"] = result.as_data()
        lines.append(f"effective coverage: {result.summary()}")
        lines += [f"  uncovered: {intent_id}" for intent_id in result.uncovered]
        if require_target and not result.meets_target:
            message = f"effective coverage {result.summary()} is below the 90% sprint target"
            if not json_out:
                typer.echo("\n".join(lines))
            raise CommandError(exit_codes.GATE_FAILURE, message, {"coverage": result.as_data()})
    emit("check intent", as_json=json_out, text="\n".join(lines), data=data)
