"""The push barrier's held-command harness fails within its bounds and leaves no processes.

Green today: these cases check the test helper, not factory code. A claimer that never
reaches origin, or reaches it and never exits, must make the barrier raise within its bound
(plus `KILL_SECONDS` for cleanup) and leave nothing alive in the claimer's process group,
including the git and receive-pack processes under it.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pytest

from tests.contract.push_barrier import KILL_SECONDS, HeldCommands, PushBarrier, group_members
from tests.fixtures.repo_builder import RepoBuilder

pytestmark = pytest.mark.skipif(
    not Path("/proc/self/stat").exists(), reason="process-group checks read /proc"
)

BOUND = 1.0
CEILING = BOUND + KILL_SECONDS


def _alive(pid: int) -> bool:
    stat = Path(f"/proc/{pid}/stat")
    try:
        text = stat.read_text()
    except OSError:
        return False
    return text[text.rindex(")") + 2] not in ("Z", "X")


def _wait_for(path: Path) -> None:
    deadline = time.monotonic() + KILL_SECONDS
    while not path.exists():
        assert time.monotonic() < deadline, f"{path.name} never appeared"
        time.sleep(0.05)


def test_a_claimer_that_never_arrives_fails_within_the_bound(tmp_path: Path) -> None:
    pid_file = tmp_path / "grandchild.pid"

    def never_pushes() -> None:
        sleeper = subprocess.Popen(["sleep", "600"])
        pid_file.write_text(str(sleeper.pid))
        sleeper.wait()

    started = time.monotonic()
    with pytest.raises(AssertionError, match="never reached origin"):
        with PushBarrier(tmp_path / "barrier") as barrier:
            command = barrier.spawn(never_pushes)
            _wait_for(pid_file)
            barrier.wait_arrived(1, commands=[command], timeout=BOUND)
    assert time.monotonic() - started < CEILING
    assert command.done(), "the claimer was reaped"
    assert not _alive(int(pid_file.read_text())), "the claimer's child was killed"
    assert group_members(command.pid) == []


def test_a_claimer_held_at_origin_that_never_exits_fails_within_the_bound(
    repo: RepoBuilder,
) -> None:
    barrier = PushBarrier(repo.root / "push-barrier")
    barrier.install(repo.path, 1)

    def push() -> int:
        return subprocess.run(
            ["git", "-C", str(repo.path), "push", "-q", "origin", "HEAD:refs/heads/held"],
            check=False,
            capture_output=True,
        ).returncode

    with pytest.raises(AssertionError, match="did not exit within"):
        with barrier:
            command = barrier.spawn(push)
            barrier.wait_arrived(1, commands=[command])
            held = group_members(command.pid)
            assert len(held) > 1, f"git and the receive-pack wrapper run in the group: {held}"
            started = time.monotonic()
            barrier.result(command, timeout=BOUND)
    assert time.monotonic() - started < CEILING
    assert command.done(), "the claimer was reaped"
    assert not any(_alive(pid) for pid in held), f"git children survived: {held}"
    assert group_members(command.pid) == []


def test_leaving_the_block_kills_a_command_that_is_still_running(tmp_path: Path) -> None:
    started = time.monotonic()
    with HeldCommands(tmp_path / "commands") as commands:
        command = commands.spawn(time.sleep, 600)
    assert time.monotonic() - started < KILL_SECONDS
    assert command.done()
    assert group_members(command.pid) == []


def test_a_command_returns_its_value_or_reports_its_exception(tmp_path: Path) -> None:
    def boom() -> None:
        raise RuntimeError("claimer blew up")

    with PushBarrier(tmp_path / "barrier") as barrier:
        value = barrier.spawn(lambda: ("ok", 0))
        failure = barrier.spawn(boom)
        assert barrier.result(value, timeout=KILL_SECONDS) == ("ok", 0)
        with pytest.raises(AssertionError, match="claimer blew up"):
            barrier.result(failure, timeout=KILL_SECONDS)
