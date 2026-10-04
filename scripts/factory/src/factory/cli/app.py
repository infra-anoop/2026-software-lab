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
from factory.cli.common import CliError, CommandError, JsonEnvelope
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


GROUPS = frozenset(group.name for group in app.registered_groups if group.name)


def command_path(args: Sequence[str]) -> str:
    """The command path named by `args` (`check schema`, `claim`), as in the envelope."""
    words = [args[0]] if args and not args[0].startswith("-") else []
    if words and words[0] in GROUPS and len(args) > 1 and not args[1].startswith("-"):
        words.append(args[1])
    return " ".join(words) or "factory"


def _report(args: Sequence[str], error: CliError) -> int:
    typer.echo(error.message, err=True)
    if "--json" in args:
        typer.echo(JsonEnvelope(ok=False, command=command_path(args), error=error).render())
    return error.code


def run(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return its exit code (usage errors map to 3, not click's 2)."""
    command = typer.main.get_command(app)
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        result = command.main(args=args, prog_name="factory", standalone_mode=False)
    except typer.Exit as exc:
        return exc.exit_code
    except CommandError as exc:
        return _report(args, exc.error)
    except typer.TyperException as exc:
        message = f"usage error: {exc.format_message() or 'invalid arguments'}"
        return _report(args, CliError(code=exit_codes.USAGE, message=message))
    except typer.Abort:
        return _report(args, CliError(code=exit_codes.USAGE, message="aborted"))
    except ConfigError as exc:
        return _report(args, CliError(code=exit_codes.USAGE, message=f"config error: {exc}"))
    except (BusError, RegistryError) as exc:
        return _report(args, CliError(code=exit_codes.GATE_FAILURE, message=str(exc)))
    return result if isinstance(result, int) else exit_codes.OK


def main() -> None:
    """Console-script entrypoint (`factory = "factory.cli.app:main"`)."""
    sys.exit(run())
