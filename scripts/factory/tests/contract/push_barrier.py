"""A receive-pack barrier that holds each clone's push at origin until the test releases it.

`remote.origin.receivepack` points at a wrapper script. git runs it only when the command
connects to push, which is after the command has fetched and built its event. The wrapper:

1. writes `arrived-<n>`;
2. blocks until `go-<n>` exists;
3. records the refs origin holds at that instant in `advertised-<n>`;
4. execs `git-receive-pack`.

The client gets no ref advertisement until step 4. The test writes origin only while every
push is held, so `advertised-<n>` is exactly what receive-pack advertises. git decides
`[up to date]` (advertised sha == pushed sha) and `[rejected] (fetch first)` (advertised sha
unknown to the client) from that advertisement alone.

Held commands run in forked children (`HeldCommands.spawn`; `PushBarrier` extends it), so they
keep the test's in-process state (monkeypatched clock, fake GitHub) yet can be killed. Tests
that race without a barrier use `HeldCommands` directly. Each child leads its own process
group, which its git and receive-pack processes inherit. Every wait is bounded: on an arrival
or result timeout, and on leaving the `with` block, every child's group is SIGKILLed and
reaped, and any survivor fails the test. No wait depends on a command choosing to exit.
"""

from __future__ import annotations

import contextlib
import os
import pickle
import shlex
import signal
import subprocess
import sys
import time
import traceback
from collections.abc import Callable, Iterable
from pathlib import Path
from types import TracebackType
from typing import Any, NoReturn, Self

WAIT_SECONDS = 30.0
KILL_SECONDS = 10.0
POLL_SECONDS = 0.05

_WRAPPER = """#!/bin/sh
dir={dir}
n={n}
: > "$dir/arrived-$n"
i=0
while [ ! -e "$dir/go-$n" ]; do
  i=$((i + 1))
  if [ "$i" -gt {polls} ]; then
    echo "push barrier $n: never released" >&2
    exit 1
  fi
  sleep {poll}
done
git --git-dir="$1" for-each-ref --format='%(refname) %(objectname)' refs/heads \\
  > "$dir/advertised-$n"
exec git-receive-pack "$@"
"""


def group_members(pgid: int) -> list[int]:
    """Live (not zombie) processes in process group `pgid`, read from /proc."""
    members = []
    for stat in Path("/proc").glob("[0-9]*/stat"):
        try:
            text = stat.read_text()
        except OSError:
            continue
        state, _ppid, pgrp = text[text.rindex(")") + 2 :].split()[:3]
        if state not in ("Z", "X") and int(pgrp) == pgid:
            members.append(int(stat.parent.name))
    return members


class HeldCommand[T]:
    """One command running in a forked child that leads process group `pid`."""

    def __init__(self, pid: int, result_path: Path, label: str) -> None:
        self.pid = pid
        self.label = label
        self._result_path = result_path
        self._status: int | None = None

    def done(self) -> bool:
        if self._status is None:
            pid, status = os.waitpid(self.pid, os.WNOHANG)
            if pid:
                self._status = status
        return self._status is not None

    def outcome(self) -> T:
        """The command's return value; its exception or death fails the test."""
        assert self.done(), f"{self.label} is still running"
        if not self._result_path.exists():
            raise AssertionError(f"{self.label} died without a result (wait status {self._status})")
        ok, value = pickle.loads(self._result_path.read_bytes())
        if not ok:
            raise AssertionError(f"{self.label} raised:\n{value}")
        return value

    def describe(self) -> str:
        try:
            return f"{self.label} -> {self.outcome()!r}"
        except AssertionError as error:
            return str(error)

    def kill(self) -> None:
        """SIGKILL the whole group, reap the child; fail if anything survives `KILL_SECONDS`."""
        deadline = time.monotonic() + KILL_SECONDS
        while True:
            if not self.done() or group_members(self.pid):
                with contextlib.suppress(ProcessLookupError, PermissionError):
                    os.killpg(self.pid, signal.SIGKILL)
            if self.done() and not group_members(self.pid):
                return
            if time.monotonic() >= deadline:
                raise AssertionError(
                    f"{self.label}: processes {group_members(self.pid)} in group {self.pid}"
                    f" survived SIGKILL for {KILL_SECONDS:.0f}s"
                )
            time.sleep(POLL_SECONDS)


class HeldCommands:
    """Commands in forked children; leaving the `with` block kills and reaps every one."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._commands: list[HeldCommand[Any]] = []

    def spawn[T](self, fn: Callable[..., T], *args: Any) -> HeldCommand[T]:
        """Run `fn(*args)` in a forked child that leads a new process group."""
        label = f"command {len(self._commands) + 1}"
        result_path = self.root / f"result-{len(self._commands) + 1}.pickle"
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            status = 1
            try:
                os.setpgid(0, 0)
                try:
                    outcome: tuple[bool, Any] = (True, fn(*args))
                except BaseException:
                    outcome = (False, traceback.format_exc())
                partial = result_path.with_suffix(".partial")
                partial.write_bytes(pickle.dumps(outcome))
                partial.replace(result_path)
                status = 0
            finally:
                with contextlib.suppress(BaseException):
                    sys.stdout.flush()
                    sys.stderr.flush()
                os._exit(status)
        with contextlib.suppress(OSError):
            os.setpgid(pid, pid)
        command: HeldCommand[T] = HeldCommand(pid, result_path, label)
        self._commands.append(command)
        return command

    def kill_all(self) -> None:
        for command in self._commands:
            command.kill()

    def _fail(self, reason: str) -> NoReturn:
        self.kill_all()
        raise AssertionError(f"{reason}; killed every held command")

    def result[T](self, command: HeldCommand[T], timeout: float) -> T:
        """`command`'s return value once it exits; fail if it is still running at `timeout`."""
        deadline = time.monotonic() + timeout
        while not command.done():
            if time.monotonic() >= deadline:
                self._fail(f"{command.label} did not exit within {timeout:.0f}s")
            time.sleep(POLL_SECONDS)
        return command.outcome()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.kill_all()


class PushBarrier(HeldCommands):
    """Hold pushes from up to N clones at origin; release them one at a time."""

    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self._installed: list[int] = []

    def install(self, work: Path, n: int) -> None:
        script = self.root / f"receive-pack-{n}"
        script.write_text(
            _WRAPPER.format(
                dir=shlex.quote(str(self.root)),
                n=n,
                polls=int(WAIT_SECONDS / POLL_SECONDS),
                poll=POLL_SECONDS,
            ),
            encoding="utf-8",
        )
        script.chmod(0o755)
        subprocess.run(
            ["git", "-C", str(work), "config", "remote.origin.receivepack", str(script)],
            check=True,
            capture_output=True,
        )
        self._installed.append(n)

    def arrived(self, n: int) -> bool:
        return (self.root / f"arrived-{n}").exists()

    def wait_arrived(
        self, *ns: int, commands: Iterable[HeldCommand[Any]], timeout: float = WAIT_SECONDS
    ) -> None:
        """Block until every push `ns` is held at origin; fail if a command ends first."""
        pending = list(commands)
        deadline = time.monotonic() + timeout
        while not all(self.arrived(n) for n in ns):
            ended = [command.describe() for command in pending if command.done()]
            if ended:
                self._fail(f"{ended} exited before its push reached origin")
            if time.monotonic() >= deadline:
                self._fail(
                    f"pushes {[n for n in ns if not self.arrived(n)]} never reached origin"
                    f" within {timeout:.0f}s"
                )
            time.sleep(POLL_SECONDS)

    def release(self, n: int) -> None:
        (self.root / f"go-{n}").touch()

    def advertised(self, n: int) -> dict[str, str]:
        """Origin's `refs/heads/*` as receive-pack advertised them to push `n`."""
        path = self.root / f"advertised-{n}"
        assert path.exists(), f"push {n} was never released to receive-pack"
        lines = path.read_text().splitlines()
        return dict(line.split(" ", 1) for line in lines if line)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            super().__exit__(exc_type, exc, traceback)
        finally:
            for n in self._installed:
                self.release(n)


def has_object(work: Path, sha: str) -> bool:
    return (
        subprocess.run(
            ["git", "-C", str(work), "cat-file", "-e", f"{sha}^{{commit}}"],
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )


def origin_sha(origin: Path, branch: str) -> str:
    return subprocess.run(
        ["git", "--git-dir", str(origin), "rev-parse", f"refs/heads/{branch}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
