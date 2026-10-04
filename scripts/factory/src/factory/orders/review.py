"""`handoff`, `pr open`, `verdict`, `bus pr`.

Handoff runs every registered P1 gate that can run without a PR (scope `changed_lines`
or `repo`) on merge-base(main, HEAD)..HEAD. A gate whose entrypoint is not importable
yet is reported as not enforced and skipped; CI (`factory-gates`) remains the authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from pydantic import ValidationError

from factory.api import GateContext, GateEntrypointError, GitHubPort, PullRequest, run_gate
from factory.bus.models import (
    Claim,
    Handoff,
    Verdict,
    WorkOrder,
    order_id_of,
    parse_message,
)
from factory.bus.store import BusError, load_all, load_file, read_bus_text
from factory.config.settings import Settings
from factory.gates.registry import load_registry
from factory.github.rest import GitHubError
from factory.lifecycle.view import OrderRecord, load_order
from factory.orders import git
from factory.orders.errors import External, Refused, Usage
from factory.orders.lease import fetch_or_fail, push_or_fail
from factory.orders.messages import build, path_of, to_yaml, utc_stamp

LOCAL_GATE_SCOPES = frozenset({"changed_lines", "repo"})
BUS_PR_TREES = ("decisions", "corrections", "postmortems")


@dataclass
class HandoffResult:
    order_id: str
    sha: str
    run_complete: str
    run_complete_written: bool
    gates_passed: list[str] = field(default_factory=list)
    gates_not_enforced: list[str] = field(default_factory=list)


def _order_dir(settings: Settings, order_id: str) -> str:
    return f"{settings.bus_dir}/orders/{order_id}"


def _branch_ref(repo: Path, order_id: str) -> str:
    """Local `wo/<id>` when present (it may hold unpushed work), else origin's."""
    branch = git.order_branch(order_id)
    for ref in (f"refs/heads/{branch}", git.remote_ref(branch)):
        if git.rev_parse(repo, ref):
            return ref
    raise Refused(f"{order_id} is not issued (no wo/{order_id} branch)")


def _record(repo: Path, settings: Settings, ref: str, order_id: str) -> OrderRecord:
    try:
        record = load_order(repo, ref, order_id, settings, main_ref=git.main_ref(repo))
    except BusError as exc:
        raise Refused(f"the order branch has an invalid bus file: {exc}") from exc
    if record is None:
        raise Refused(f"no order file for {order_id} on {ref}")
    return record


def read_handoff(repo: Path, settings: Settings, ref: str, order_id: str) -> Handoff:
    relative = f"{_order_dir(settings, order_id)}/handoff.yaml"
    if not git.object_exists(repo, f"{ref}:{relative}"):
        raise Refused(f"no handoff on wo/{order_id}; commit {relative} first")
    raw = yaml.safe_load(read_bus_text(repo, ref, relative))
    if isinstance(raw, dict) and "deviations" not in raw:
        raise Refused(
            "the handoff must list deviations (write `deviations: []` when there were none)"
        )
    try:
        handoff = load_file(repo, ref, relative, settings).message
    except BusError as exc:
        raise Refused(f"the handoff is invalid: {exc}") from exc
    if not isinstance(handoff, Handoff):
        raise Refused(f"{relative} is not a handoff")
    return handoff


def run_local_gates(
    repo: Path, settings: Settings, order_id: str, base: str, head: str
) -> tuple[list[str], list[str], list[str]]:
    """(passed, not enforced yet, failure messages) for the PR-independent P1 gates."""
    try:
        snapshot = load_all(repo, head, settings=settings)
    except BusError as exc:
        raise Refused(f"the branch has an invalid bus file: {exc}") from exc
    ctx = GateContext(
        repo_path=repo,
        base_sha=base,
        head_sha=head,
        order_id=order_id,
        config=settings,
        bus_snapshot=snapshot,
    )
    passed: list[str] = []
    skipped: list[str] = []
    failures: list[str] = []
    for gate in load_registry().gates:
        if gate.priority != "P1" or gate.scope not in LOCAL_GATE_SCOPES:
            continue
        try:
            result = run_gate(gate.id, ctx)
        except GateEntrypointError:
            skipped.append(gate.id)
            continue
        if result.passed:
            passed.append(gate.id)
        else:
            failures.extend(result.messages or [f"{gate.id} failed"])
    return passed, skipped, failures


def _wall_minutes(record: OrderRecord, now: datetime) -> float:
    claim = record.one(Claim)
    if claim is None:
        return 0.0
    return round(max((now - claim.claimed_at).total_seconds(), 0.0) / 60, 1)


def handoff_order(repo: Path, settings: Settings, order_id: str, *, now: datetime) -> HandoffResult:
    branch = git.order_branch(order_id)
    if git.current_branch(repo) != branch:
        raise Refused(f"check out {branch} first (handoff validates the branch you worked on)")
    head = git.git_text(repo, "rev-parse", "HEAD")
    handoff = read_handoff(repo, settings, head, order_id)
    record = _record(repo, settings, head, order_id)
    if record.one(Claim) is None:
        raise Refused(f"{order_id} has no claim on this branch; claim it before handing off")
    main = git.main_ref(repo)
    base = git.merge_base(repo, main, head) if main else head
    passed, skipped, failures = run_local_gates(repo, settings, order_id, base, head)
    if failures:
        raise Refused(
            "a gate fails on this branch:\n" + "\n".join(f"- {m}" for m in failures),
            details={"failures": failures, "not_enforced": skipped},
        )
    questions = [
        q.question for q in handoff.open_questions if q.question_class == "blocker_governor"
    ]
    if questions:
        push_or_fail(repo, head, branch, lost=f"origin {branch} moved; pull and retry")
        raise Refused(
            "Waiting on the governor:\n" + "\n".join(f"- {q}" for q in questions),
            details={"questions": questions},
            stdout=questions,
        )
    relative = f"{_order_dir(settings, order_id)}/run-complete.yaml"
    written = False
    sha = head
    if not git.object_exists(repo, f"{head}:{relative}"):
        event = build(
            {
                "schema_version": 1,
                "kind": "run_complete",
                "id": f"{order_id}.run-complete",
                "created": utc_stamp(now),
                "actor": "worker",
                "actor_model": handoff.actor_model or handoff.author_model,
                "wall_minutes": _wall_minutes(record, now),
                "governor_interrupts": 0,
                "cost_usd": None,
                "cost_usd_estimated": True,
                "deviations_count": len(handoff.deviations),
                "refs": [order_id],
            },
            settings,
        )
        sha = git.commit_files(
            repo,
            head,
            {relative: to_yaml(event, keep_none=("cost_usd",))},
            f"run-complete: {order_id}",
        )
        git.advance_local_branch(repo, branch, sha)
        written = True
    push_or_fail(repo, sha, branch, lost=f"origin {branch} moved; pull and retry")
    return HandoffResult(
        order_id=order_id,
        sha=sha,
        run_complete=relative,
        run_complete_written=written,
        gates_passed=passed,
        gates_not_enforced=skipped,
    )


def pr_body(order: WorkOrder, handoff: Handoff) -> str:
    intents = ", ".join(order.intents) or "(none listed)"
    lines = [
        f"Order: {order.id}",
        f"Intents: {intents}",
        f"Feature: {order.feature}",
        "",
        f"Goal: {order.goal}",
        "",
        "Owned paths:",
        *[f"- `{p}`" for p in order.owned_paths],
        "",
        "Required checks: " + (", ".join(f"factory/{c}" for c in order.checks) or "(none)"),
        "",
        "Handoff summary:",
        handoff.summary.strip(),
        "",
        f"Deviations: {len(handoff.deviations)}",
    ]
    return "\n".join(lines) + "\n"


def open_pr(repo: Path, settings: Settings, github: GitHubPort, order_id: str) -> PullRequest:
    ref = _branch_ref(repo, order_id)
    handoff = read_handoff(repo, settings, ref, order_id)
    record = _record(repo, settings, ref, order_id)
    branch = git.order_branch(order_id)
    sha = git.git_text(repo, "rev-parse", ref)
    push_or_fail(repo, sha, branch, lost=f"origin {branch} moved; pull and retry")
    try:
        existing = [pr for pr in github.list_prs_by_head(branch) if pr.open]
        if existing:
            raise Refused(f"PR #{existing[0].number} is already open for {branch}")
        title = f"{order_id}: {record.order.goal}"[:120]
        return github.create_pr(branch, git.MAIN, title, pr_body(record.order, handoff))
    except GitHubError as exc:
        raise External(str(exc)) from exc


def _load_verdict(path: Path, settings: Settings) -> tuple[Verdict, bytes]:
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise Usage(f"cannot read {path}: {exc}") from exc
    data: Any = yaml.safe_load(content)
    if not isinstance(data, dict):
        raise Refused(f"{path} is not a YAML mapping")
    try:
        message = parse_message(data, autonomy_horizon_minutes=settings.autonomy_horizon_minutes)
    except ValidationError as exc:
        raise Refused(f"the verdict is invalid: {exc}") from exc
    if not isinstance(message, Verdict):
        raise Refused(f"{path} is a {message.kind}, not a verdict")
    return message, content


def record_verdict(repo: Path, settings: Settings, order_id: str, file: Path) -> tuple[str, str]:
    """Validate family + isolation inputs and commit the verdict; returns (path, sha)."""
    verdict, content = _load_verdict(file, settings)
    if order_id_of(verdict.id) != order_id:
        raise Refused(f"the verdict is for {order_id_of(verdict.id)}, not {order_id}")
    ref = _branch_ref(repo, order_id)
    handoff = read_handoff(repo, settings, ref, order_id)
    author_family = settings.family_of(handoff.author_model)
    reviewer_family = settings.family_of(verdict.reviewer_model)
    if reviewer_family is None:
        raise Refused(f"unknown model family for reviewer {verdict.reviewer_model}")
    if verdict.reviewer_family != reviewer_family:
        raise Refused(
            f"reviewer_family says {verdict.reviewer_family} but {verdict.reviewer_model}"
            f" is in family {reviewer_family}"
        )
    if author_family is None or author_family == reviewer_family:
        raise Refused(
            f"the reviewer must be from a different model family than the author"
            f" ({handoff.author_model}, family {author_family or 'unknown'})"
        )
    for item in verdict.inputs:
        if not git.object_exists(repo, f"{item.sha}^{{commit}}"):
            raise Refused(f"verdict input {item.path} cites commit {item.sha}, which is not in git")
        if not git.object_exists(repo, f"{item.sha}:{item.path}"):
            raise Refused(
                f"verdict input {item.path} is not in git at {item.sha[:7]}; reviewers may"
                " only read committed files"
            )
    relative = path_of(verdict, settings)
    base = git.git_text(repo, "rev-parse", ref)
    if git.object_exists(repo, f"{base}:{relative}"):
        raise Refused(f"{relative} is already recorded; number the next verdict")
    sha = git.commit_files(repo, base, {relative: content}, f"verdict: {verdict.id}")
    branch = git.order_branch(order_id)
    push_or_fail(repo, sha, branch, lost=f"origin {branch} moved; pull and retry")
    git.advance_local_branch(repo, branch, sha)
    return relative, sha


def _bus_relative(repo: Path, settings: Settings, given: Path) -> str:
    path = given if given.is_absolute() else repo / given
    try:
        relative = path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return given.as_posix()
    return relative


def open_bus_pr(
    repo: Path, settings: Settings, github: GitHubPort, files: list[Path], *, now: datetime
) -> PullRequest:
    if not files:
        raise Usage("name at least one --message file")
    allowed = tuple(f"{settings.bus_dir}/{tree}/" for tree in BUS_PR_TREES)
    relatives = [_bus_relative(repo, settings, f) for f in files]
    outside = [r for r in relatives if not r.startswith(allowed)]
    if outside:
        raise Refused(
            f"bus pr only carries {', '.join(allowed)}; not: {', '.join(outside)}",
            details={"outside": outside},
        )
    contents: dict[str, bytes] = {}
    slug_source = ""
    for relative in relatives:
        if not (repo / relative).is_file():
            raise Refused(f"{relative} does not exist")
        if not relative.startswith(f"{settings.bus_dir}/postmortems/"):
            try:
                message = load_file(repo, None, relative, settings).message
            except BusError as exc:
                raise Refused(f"invalid bus message: {exc}") from exc
            slug_source = slug_source or message.id.removesuffix(".lock")
        contents[relative] = (repo / relative).read_bytes()
        slug_source = slug_source or PurePosixPath(relative).stem
    fetch_or_fail(repo)
    main = git.main_ref(repo)
    if main is None:
        raise External("origin has no main branch")
    slug = "".join(c if c.isalnum() else "-" for c in slug_source.lower()).strip("-")
    branch = f"bus/{now:%Y-%m-%d}-{slug}"
    if git.rev_parse(repo, git.remote_ref(branch)):
        raise Refused(f"{branch} already exists on origin")
    base = git.git_text(repo, "rev-parse", main)
    sha = git.commit_files(repo, base, contents, f"bus: {slug}")
    push_or_fail(repo, sha, branch, lost=f"{branch} was created by someone else first")
    body = "Bus messages:\n" + "\n".join(f"- `{r}`" for r in sorted(contents)) + "\n"
    try:
        return github.create_pr(branch, git.MAIN, f"bus: {slug}", body)
    except GitHubError as exc:
        raise External(str(exc)) from exc
