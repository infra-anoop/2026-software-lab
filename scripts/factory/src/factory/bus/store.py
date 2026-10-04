"""Read-only bus loader + layout resolver (contracts/messages.md § Layout).

Reads `bus/` either from the working tree (`ref=None`) or from a git ref, never
writes. Frozen at CP0.
"""

from __future__ import annotations

import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from factory.bus.models import ORDER_SCOPED_KINDS, Message, order_id_of, parse_message
from factory.config.settings import Settings, load_settings

# Post-mortems have no message kind yet (US7, Wave 2); the loader skips them.
SKIPPED_SUBDIRS = frozenset({"postmortems"})
YAML_SUFFIXES = (".yaml", ".yml")


class BusError(Exception):
    """A bus file is unreadable, invalid, or not where its kind and id say it lives."""

    def __init__(self, path: str, problem: str) -> None:
        super().__init__(f"{path}: {problem}")
        self.path = path
        self.problem = problem


class BusFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    message: Message


def expected_path(message: Message, bus_dir: str = "bus") -> PurePosixPath:
    """Where `message` must live, relative to the repo root."""
    root = PurePosixPath(bus_dir)
    if message.kind in ORDER_SCOPED_KINDS:
        order_dir = root / "orders" / order_id_of(message.id)
        if message.kind == "order":
            return order_dir / "order.yaml"
        suffix = message.id.split(".", 1)[1]
        name = suffix.replace("amend-", "amendment-", 1) if message.kind == "amendment" else suffix
        return order_dir / f"{name}.yaml"
    if message.kind == "decision_request":
        return root / "decisions" / message.id / "request.yaml"
    if message.kind == "decision_lock":
        return root / "decisions" / message.id.removesuffix(".lock") / "lock.yaml"
    return root / "corrections" / f"{message.id}.yaml"


def _git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(repo), *args], check=False, capture_output=True)
    if result.returncode != 0:
        raise BusError(" ".join(args), result.stderr.decode(errors="replace").strip())
    return result.stdout


def _is_bus_yaml(path: PurePosixPath, bus_dir: str) -> bool:
    relative = path.relative_to(bus_dir)
    if relative.parts and relative.parts[0] in SKIPPED_SUBDIRS:
        return False
    return path.suffix in YAML_SUFFIXES


def list_bus_paths(repo: Path, ref: str | None, bus_dir: str) -> list[str]:
    """Repo-relative POSIX paths of bus YAML files at `ref` (working tree when None)."""
    if ref is None:
        base = Path(repo) / bus_dir
        if not base.is_dir():
            return []
        paths = [
            PurePosixPath(p.relative_to(repo).as_posix()) for p in base.rglob("*") if p.is_file()
        ]
    else:
        out = _git(repo, "ls-tree", "-r", "--name-only", "-z", ref, "--", bus_dir)
        paths = [PurePosixPath(p) for p in out.decode().split("\0") if p]
    return sorted(str(p) for p in paths if _is_bus_yaml(p, bus_dir))


def read_bus_text(repo: Path, ref: str | None, path: str) -> str:
    if ref is None:
        return (Path(repo) / path).read_text(encoding="utf-8")
    return _git(repo, "show", f"{ref}:{path}").decode("utf-8")


def parse_bus_text(text: str, path: str, *, autonomy_horizon_minutes: int | None) -> Message:
    try:
        data: Any = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise BusError(path, f"invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise BusError(path, "a bus message must be a YAML mapping")
    try:
        return parse_message(data, autonomy_horizon_minutes=autonomy_horizon_minutes)
    except ValidationError as exc:
        raise BusError(path, str(exc)) from exc


def load_file(repo: Path, ref: str | None, path: str, settings: Settings) -> BusFile:
    """Load one bus file, validating its schema and that it sits at its layout path."""
    message = parse_bus_text(
        read_bus_text(repo, ref, path),
        path,
        autonomy_horizon_minutes=settings.autonomy_horizon_minutes,
    )
    expected = str(expected_path(message, settings.bus_dir))
    if expected != path:
        raise BusError(path, f"{message.kind} {message.id!r} belongs at {expected}")
    return BusFile(path=path, message=message)


def load_files(
    repo: Path, ref: str | None = None, *, settings: Settings | None = None
) -> list[BusFile]:
    """Load and validate every bus file at `ref`; raises on the first `BusError`."""
    config = settings or load_settings(repo)
    return [
        load_file(repo, ref, path, config) for path in list_bus_paths(repo, ref, config.bus_dir)
    ]


def load_all(
    repo: Path, ref: str | None = None, *, settings: Settings | None = None
) -> list[Message]:
    """Every bus message at `ref` (working tree when None). Read-only; raises `BusError`."""
    return [bus_file.message for bus_file in load_files(repo, ref, settings=settings)]
