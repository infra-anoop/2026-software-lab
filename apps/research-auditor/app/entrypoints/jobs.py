"""In-memory audit job runner (HTTP only).

Not durable: a process restart drops all jobs. Multiple Railway instances do not
share this store. Acceptable P3 residual — do not treat job_id as a database key.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

logger = logging.getLogger(__name__)

JobStatus = Literal["queued", "running", "succeeded", "failed", "timed_out"]

ExecuteFn = Callable[[dict[str, Any]], Awaitable[Any]]
TimeoutFn = Callable[[], float | None]


def utc_now_iso() -> str:
    """UTC timestamp for job records (ISO-8601)."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Job:
    """One audit job in the in-memory store."""

    job_id: str
    status: JobStatus
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    result: Any = None
    payload: dict[str, Any] = field(default_factory=dict)


class QueueFullError(Exception):
    """Too many jobs already waiting (not counting the in-flight graph)."""


class SlidingWindowRateLimiter:
    """Process-local sliding window. Not shared across instances."""

    def __init__(self) -> None:
        self._hits: deque[float] = deque()

    def allow(self, limit: int, window_sec: float = 60.0) -> bool:
        """Return True and record a hit if under the limit."""
        now = time.monotonic()
        while self._hits and now - self._hits[0] >= window_sec:
            self._hits.popleft()
        if limit <= 0:
            return True
        if len(self._hits) >= limit:
            return False
        self._hits.append(now)
        return True


class JobRunner:
    """Asyncio queue + N worker tasks calling ``execute`` with a wall-clock cap."""

    def __init__(
        self,
        *,
        execute: ExecuteFn,
        timeout_sec: TimeoutFn,
        concurrency: int = 1,
        queue_max: int = 4,
    ) -> None:
        self._execute = execute
        self._timeout_sec = timeout_sec
        self._concurrency = max(1, concurrency)
        self._queue_max = max(1, queue_max)
        self._jobs: dict[str, Job] = {}
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._workers: list[asyncio.Task[None]] = []
        self._started = False

    async def start(self) -> None:
        """Start worker tasks. Idempotent."""
        if self._started:
            return
        self._started = True
        for i in range(self._concurrency):
            task = asyncio.create_task(self._worker_loop(), name=f"audit-job-worker-{i}")
            self._workers.append(task)

    async def stop(self) -> None:
        """Cancel workers (in-flight graphs may still complete an LLM call)."""
        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        self._started = False

    def enqueue(self, payload: dict[str, Any]) -> Job:
        """Create a queued job. Raises QueueFullError if the wait line is full."""
        queued = sum(1 for job in self._jobs.values() if job.status == "queued")
        if queued >= self._queue_max:
            raise QueueFullError()
        job = Job(
            job_id=str(uuid4()),
            status="queued",
            created_at=utc_now_iso(),
            payload=payload,
        )
        self._jobs[job.job_id] = job
        self._queue.put_nowait(job.job_id)
        return job

    def get(self, job_id: str) -> Job | None:
        """Return a job snapshot, or None if unknown."""
        return self._jobs.get(job_id)

    async def _worker_loop(self) -> None:
        while True:
            job_id = await self._queue.get()
            try:
                await self._run_job(job_id)
            finally:
                self._queue.task_done()

    async def _run_job(self, job_id: str) -> None:
        job = self._jobs[job_id]
        job.status = "running"
        job.started_at = utc_now_iso()
        timeout = self._timeout_sec()
        try:
            coro = self._execute(job.payload)
            if timeout is not None:
                result = await asyncio.wait_for(coro, timeout=timeout)
            else:
                result = await coro
            job.result = result
            job.status = "succeeded"
        except asyncio.TimeoutError:
            job.status = "timed_out"
            job.error = f"Workflow exceeded wall-clock timeout ({timeout}s)"
            logger.warning("audit job %s timed out after %ss", job_id, timeout)
        except asyncio.CancelledError:
            job.status = "failed"
            job.error = "Job cancelled"
            job.finished_at = utc_now_iso()
            raise
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            logger.exception("audit job %s failed", job_id)
        finally:
            if job.finished_at is None:
                job.finished_at = utc_now_iso()
