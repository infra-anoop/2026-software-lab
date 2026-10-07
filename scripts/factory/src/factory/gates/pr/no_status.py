"""`bus.no-handwritten-status` (I-M2, FR-003): no bus message this PR adds or edits
carries `status`, `state`, `done`, or `progress` at any depth."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

import yaml

from factory.api import GateContext, GateResult
from factory.bus.models import find_forbidden_key
from factory.bus.store import SKIPPED_SUBDIRS, YAML_SUFFIXES
from factory.gates.repo._git import changed, outcome, read_blobs

GATE_ID = "bus.no-handwritten-status"


def _is_message_path(path: str, bus_dir: str) -> bool:
    relative = PurePosixPath(path).relative_to(bus_dir)
    return relative.suffix in YAML_SUFFIXES and relative.parts[0] not in SKIPPED_SUBDIRS


def run(ctx: GateContext) -> GateResult:
    bus_dir = ctx.config.bus_dir
    paths = [
        path
        for status, path in changed(ctx.repo_path, ctx.base_sha, ctx.head_sha, f"{bus_dir}/")
        if status in {"A", "M", "T"} and _is_message_path(path, bus_dir)
    ]
    problems = []
    for path, text in read_blobs(ctx.repo_path, ctx.head_sha, paths).items():
        try:
            data: Any = yaml.safe_load(text or "")
        except yaml.YAMLError:
            continue  # bus.schema reports unreadable files
        where = find_forbidden_key(data)
        if where:
            problems.append(f"{path}: forbidden key {where!r}; bus messages carry no status")
    return outcome(GATE_ID, problems, "no status keys in changed bus messages")
