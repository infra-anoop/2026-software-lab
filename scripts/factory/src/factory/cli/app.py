"""`factory` CLI root: registers every command in contracts/cli.md. Frozen at CP0.

Command bodies live in per-slice modules; this file only wires them and maps errors
to the exit codes in `factory.cli.exit_codes`.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

import typer

from factory.bus.store import BusError
from factory.cli import board, checks, exit_codes, gates, intent, mining, orders
from factory.config.settings import ConfigError
from factory.gates.registry import RegistryError


def _group(help_text: str) -> typer.Typer:
    return typer.Typer(help=help_text, no_args_is_help=True, add_completion=False)


app = typer.Typer(
    name="factory",
    help="Factory v2: typed bus, derived board, intent-fidelity gates.",
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)

# Slice A — board
app.command("status")(board.status)
app.command("decisions")(board.decisions)
app.command("scorecard")(board.scorecard)

# Slice A — orders
order_app = _group("Work orders.")
order_app.command("new")(orders.order_new)
order_app.command("issue")(orders.order_issue)
app.add_typer(order_app, name="order")
app.command("claim")(orders.claim)
app.command("release")(orders.release)
app.command("handoff")(orders.handoff)
pr_app = _group("Work PRs.")
pr_app.command("open")(orders.pr_open)
app.add_typer(pr_app, name="pr")
app.command("verdict")(orders.verdict)
bus_app = _group("Bus PRs (decisions, corrections, post-mortems).")
bus_app.command("pr")(orders.bus_pr)
app.add_typer(bus_app, name="bus")

# Slice C — gates and hooks
app.command("override")(gates.override)
gate_app = _group("Gates.")
gate_app.command("run")(gates.gate_run)
app.add_typer(gate_app, name="gate")
app.command("hook")(gates.hook)
app.command("retro")(gates.retro)

# Repo-level checks — schema (P0), intent (slice B), hooks/registry/immutability (slice C)
check_app = _group("Repo-level validations.")
check_app.command("schema")(checks.check_schema)
check_app.command("intent")(intent.check_intent)
check_app.command("hooks")(checks.check_hooks)
check_app.command("registry")(checks.check_registry)
check_app.command("immutability")(checks.check_immutability)
app.add_typer(check_app, name="check")

# US7 (Wave 2) — mining loop
correction_app = _group("Governor corrections.")
correction_app.command("new")(mining.correction_new)
app.add_typer(correction_app, name="correction")
sprint_app = _group("Sprint lifecycle.")
sprint_app.command("close")(mining.sprint_close)
app.add_typer(sprint_app, name="sprint")


def run(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return its exit code (usage errors map to 3, not click's 2)."""
    command = typer.main.get_command(app)
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        result = command.main(args=args, prog_name="factory", standalone_mode=False)
    except typer.Exit as exc:
        return exc.exit_code
    except typer.TyperException as exc:
        if exc.format_message():
            typer.echo(f"usage error: {exc.format_message()}", err=True)
        return exit_codes.USAGE
    except typer.Abort:
        typer.echo("aborted", err=True)
        return exit_codes.USAGE
    except ConfigError as exc:
        typer.echo(f"config error: {exc}", err=True)
        return exit_codes.USAGE
    except (BusError, RegistryError) as exc:
        typer.echo(str(exc), err=True)
        return exit_codes.GATE_FAILURE
    return result if isinstance(result, int) else exit_codes.OK


def main() -> None:
    """Console-script entrypoint (`factory = "factory.cli.app:main"`)."""
    sys.exit(run())
