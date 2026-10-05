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

Every wait is bounded (`WAIT_SECONDS`), so a broken implementation fails instead of hanging.
"""

from __future__ import annotations

import shlex
import subprocess
import time
from collections.abc import Iterable
from concurrent.futures import Future
from pathlib import Path
from types import TracebackType
from typing import Any

WAIT_SECONDS = 30.0
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


class PushBarrier:
    """Hold pushes from up to N clones at origin; release them one at a time."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
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

    def wait_arrived(self, *ns: int, commands: Iterable[Future[Any]]) -> None:
        """Block until every push `ns` is held at origin; fail if a command ends first."""
        pending = list(commands)
        deadline = time.monotonic() + WAIT_SECONDS
        while not all(self.arrived(n) for n in ns):
            ended = [future.result() for future in pending if future.done()]
            assert not ended, f"a command exited {ended} before its push reached origin"
            assert time.monotonic() < deadline, (
                f"pushes {[n for n in ns if not self.arrived(n)]} never reached origin"
                f" within {WAIT_SECONDS:.0f}s"
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

    def __enter__(self) -> PushBarrier:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
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
