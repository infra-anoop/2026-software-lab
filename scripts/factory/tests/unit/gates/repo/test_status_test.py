"""T102 — gate `factory-status-test` (PR-C3; I-M4; contracts/gates.md § CI topology).

Oracle (proposed here for T* review; the contract row says only "repo (unit)"): the gate
reads every bus file at `head_sha` from git and runs `main`'s installed lifecycle
derivation over that data alone (no GitHub data). It passes when every file parses, every
order directory on the head bus yields one board entry, and every governor wait the board
reports points at a recorded decision request. Anything else blocks, naming the gate.

The board is `main`'s lifecycle derivation (`factory.lifecycle.derive.derive_order` per
record, directly or through `derive_from_view`) over a `BusView` built from the head; the
gate compares it with the head's order folders, so a scanner cannot pass (T-ST1, T-ST6).

Trust boundary (D5): the head is only data. The gate never imports, runs or checks out
head code, and never trusts `ctx.bus_snapshot` to be complete (the runner loads it
tolerantly and skips files that do not parse).
"""

from __future__ import annotations

import importlib
from types import ModuleType
from typing import Any

import pytest

from factory.api import GateContext, GateResult, OrderLifecycle
from factory.bus.models import Message
from factory.bus.store import BusError, list_bus_paths, load_file
from tests.fixtures.repo_builder import BaseHeadPair, RepoBuilder, message, order, yaml_text

GATE = "factory-status-test"
MODULE = "factory.gates.repo.status_test"
DAY = "20261006"
DECISION = "board-web-view"


def oid(slug: str) -> str:
    return f"wo-{DAY}-{slug}"


READY, WORKING, DONE, WAITING = oid("ready"), oid("working"), oid("done"), oid("waiting")


def load_gate() -> ModuleType:
    try:
        module: ModuleType | None = importlib.import_module(MODULE)
    except ImportError as exc:
        module, reason = None, str(exc)
    assert module is not None, f"{MODULE}:run is not implemented: {reason}"
    return module


def judge(ctx: GateContext) -> GateResult:
    """Run the entrypoint; a gate that raises has not failed closed."""
    run = getattr(load_gate(), "run", None)
    assert callable(run), f"{MODULE} must export run(ctx)"
    try:
        result = run(ctx)
    except Exception as exc:  # noqa: BLE001 - the assertion is that nothing escapes
        raise AssertionError(f"{GATE} raised instead of failing closed: {exc!r}") from exc
    assert isinstance(result, GateResult), type(result)
    assert result.gate_id == GATE, result
    return result


def assert_passes(ctx: GateContext) -> None:
    result = judge(ctx)
    assert result.passed is True, f"{GATE} blocked a valid head bus: {result.messages}"


def assert_blocks(ctx: GateContext, *needles: str) -> None:
    result = judge(ctx)
    assert result.passed is False, f"{GATE} let a bad head bus through: {result.messages}"
    assert any(GATE in line for line in result.messages), result.messages
    text = "\n".join(result.messages)
    for needle in needles:
        assert needle in text, f"{GATE} message does not mention {needle!r}: {result.messages}"


def order_yaml(order_id: str, **fields: Any) -> tuple[str, str]:
    data = order(order_id, owned_paths=[f"apps/demo/{order_id}/**"], **fields)
    return f"bus/orders/{order_id}/order.yaml", yaml_text(data)


def event_yaml(order_id: str, kind: str) -> tuple[str, str]:
    return f"bus/orders/{order_id}/{kind}.yaml", yaml_text(message(kind, order_id=order_id))


def valid_bus() -> dict[str, str]:
    """Orders that are ready, in flight, released, and waiting on a recorded decision."""
    return dict(
        [
            order_yaml(READY),
            order_yaml(WORKING),
            event_yaml(WORKING, "claim"),
            order_yaml(DONE),
            event_yaml(DONE, "claim"),
            event_yaml(DONE, "release"),
            order_yaml(WAITING, depends_on_decisions=[DECISION]),
            (
                f"bus/decisions/{DECISION}/request.yaml",
                yaml_text(message("decision_request", decision_id=DECISION)),
            ),
        ]
    )


def tolerant_snapshot(repo: RepoBuilder, sha: str) -> list[Message]:
    """What the runner hands a gate: the head bus with unparseable files skipped."""
    settings = repo.settings
    out: list[Message] = []
    for path in list_bus_paths(repo.path, sha, settings.bus_dir):
        try:
            out.append(load_file(repo.path, sha, path, settings).message)
        except BusError:
            continue
    return out


def head_ctx(repo: RepoBuilder, head_files: dict[str, str]) -> tuple[GateContext, BaseHeadPair]:
    pair = repo.base_head_pair({}, head_files, head_branch=f"wo/{oid('status-under-test')}")
    ctx = GateContext(
        repo_path=repo.path,
        base_sha=pair.base_sha,
        head_sha=pair.head_sha,
        pr_number=1,
        config=repo.settings,
        bus_snapshot=tolerant_snapshot(repo, pair.head_sha),
    )
    return ctx, pair


def test_passes_on_a_valid_head_bus(repo: RepoBuilder) -> None:
    ctx, _ = head_ctx(repo, valid_bus())
    assert_passes(ctx)


def test_judges_the_head_commit_not_the_checkout(repo: RepoBuilder) -> None:
    """Broken bus files in the working tree (untracked, never committed) are not head data."""
    ctx, _ = head_ctx(repo, valid_bus())
    lost = oid("only-in-checkout")
    repo.write(f"bus/orders/{lost}/claim.yaml", yaml_text(message("claim", order_id=lost)))
    repo.write(f"bus/orders/{READY}/handoff.yaml", "kind: [handoff\n")
    assert_passes(ctx)


def test_blocks_order_events_the_board_would_drop(repo: RepoBuilder) -> None:
    """A claim and handoff with no order: work in flight that the derivation cannot place."""
    lost = oid("no-order")
    ctx, _ = head_ctx(
        repo, {**valid_bus(), **dict([event_yaml(lost, "claim"), event_yaml(lost, "handoff")])}
    )
    assert_blocks(ctx, lost)


def test_blocks_when_main_derivation_omits_a_head_order(
    repo: RepoBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The verdict comes from `main`'s derivation: if it loses a valid order, the gate blocks.

    `derive_order` is the per-record step that `derive_from_view` also calls, so the gate
    may derive either way. A scanner that never derives passes the valid bus here.
    """
    derive = importlib.import_module("factory.lifecycle.derive")
    original = derive.derive_order
    calls: list[str] = []

    def losing_working(*args: Any, **kwargs: Any) -> OrderLifecycle:
        item: OrderLifecycle = original(*args, **kwargs)
        calls.append(item.order_id)
        if item.order_id != WORKING:
            return item
        return item.model_copy(update={"order_id": oid("not-on-the-bus")})

    ctx, _ = head_ctx(repo, valid_bus())
    gate = load_gate()
    monkeypatch.setattr(derive, "derive_order", losing_working)
    for name, value in vars(gate).items():
        if value is original:
            monkeypatch.setattr(gate, name, losing_working)
    assert_blocks(ctx, WORKING)
    assert calls, "the gate never called main's factory.lifecycle.derive.derive_order"


def test_blocks_a_governor_wait_with_no_recorded_decision(repo: RepoBuilder) -> None:
    """The board would show a placeholder instead of the question the governor must answer."""
    bus = valid_bus()
    del bus[f"bus/decisions/{DECISION}/request.yaml"]
    ctx, _ = head_ctx(repo, bus)
    assert_blocks(ctx, WAITING, DECISION)


HEAD_PACKAGE_MODULES = (
    "__init__.py",
    "api.py",
    "bus/__init__.py",
    "bus/models.py",
    "bus/store.py",
    "bus/schema.py",
    "config/__init__.py",
    "config/settings.py",
    "orders/__init__.py",
    "orders/git.py",
    "lifecycle/__init__.py",
    "lifecycle/view.py",
    "lifecycle/derive.py",
    "board/__init__.py",
    "board/render.py",
    "gates/__init__.py",
    "gates/drift/_common.py",
    "gates/drift/_git.py",
)


def test_executes_no_head_code(repo: RepoBuilder) -> None:
    """Head ships a pass-always gate and a hostile `factory` package; `main`'s code judges.

    Every module the gate could plausibly import (package root, bus loader and models,
    config, lifecycle, board, shared gate helpers) writes the marker when imported.
    """
    marker = repo.root / "head-code-ran"
    hostile = f"import pathlib\npathlib.Path({str(marker)!r}).write_text(__name__)\n"
    lost = oid("no-order")
    package = {f"scripts/factory/src/factory/{name}": hostile for name in HEAD_PACKAGE_MODULES}
    head = {
        **valid_bus(),
        **dict([event_yaml(lost, "claim")]),
        **package,
        "scripts/factory/src/factory/gates/repo/status_test.py": hostile
        + "\n\ndef run(ctx):\n    return None\n",
        "scripts/factory/tests/conftest.py": hostile,
        "conftest.py": hostile,
        "sitecustomize.py": hostile,
    }
    ctx, _ = head_ctx(repo, head)
    before = repo.git("status", "--porcelain")
    assert_blocks(ctx, lost)
    assert not marker.exists(), f"head code ran: {marker.read_text()}"
    assert repo.current_branch() == "main", "the gate checked out the head"
    assert repo.git("worktree", "list", "--porcelain").count("worktree ") == 1
    assert repo.git("status", "--porcelain") == before, "the gate wrote to the checkout"


@pytest.mark.parametrize(
    ("path", "text"),
    [
        (f"bus/orders/{READY}/claim.yaml", "kind: [claim\n"),
        (f"bus/orders/{READY}/order.yaml", yaml_text({**order(READY), "status": "in_flight"})),
    ],
    ids=["invalid-yaml", "schema-invalid"],
)
def test_fails_closed_on_a_malformed_bus_file(repo: RepoBuilder, path: str, text: str) -> None:
    ctx, _ = head_ctx(repo, {**valid_bus(), path: text})
    assert_blocks(ctx, path)


def test_fails_closed_when_the_head_commit_is_unreadable(repo: RepoBuilder) -> None:
    _, pair = head_ctx(repo, valid_bus())
    missing = "f" * 40
    ctx = GateContext(
        repo_path=repo.path,
        base_sha=pair.base_sha,
        head_sha=missing,
        pr_number=1,
        config=repo.settings,
    )
    assert_blocks(ctx, missing[:7])
