from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future
from typing import Any
from uuid import uuid4

from .execution import ExecutionEngine
from .storage import RunStore


class JobSupervisor:
    def __init__(self, store: RunStore, engine: ExecutionEngine) -> None:
        self.store = store
        self.engine = engine
        self._tasks: dict[str, Future[None]] = {}
        self._lock = threading.RLock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    def enqueue_run(self, run_id: str) -> dict[str, Any]:
        job = self.store.enqueue_job(run_id, f"job-{uuid4().hex}")
        self.start_job(str(job["id"]))
        return job

    def recover_jobs(self) -> None:
        for job in self.store.list_recoverable_jobs():
            self.start_job(str(job["id"]))

    def start_job(self, job_id: str) -> None:
        with self._lock:
            task = self._tasks.get(job_id)
            if task and not task.done():
                return
        loop = self._ensure_loop()
        with self._lock:
            task = self._tasks.get(job_id)
            if task and not task.done():
                return
            self._tasks[job_id] = asyncio.run_coroutine_threadsafe(self._run(job_id), loop)

    def active_job_ids(self) -> list[str]:
        with self._lock:
            return [job_id for job_id, task in self._tasks.items() if not task.done()]

    async def shutdown(self) -> None:
        with self._lock:
            tasks = [task for task in self._tasks.values() if not task.done()]
            loop = self._loop
            thread = self._thread
            self._tasks.clear()
        for task in tasks:
            task.cancel()
        if loop and loop.is_running():
            loop.call_soon_threadsafe(loop.stop)
        if thread and thread.is_alive():
            await asyncio.to_thread(thread.join, 1)

    async def _run(self, job_id: str) -> None:
        try:
            await self.engine.execute_job(job_id)
        finally:
            with self._lock:
                self._tasks.pop(job_id, None)

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop and self._loop.is_running():
            return self._loop

        ready = threading.Event()

        def run_loop() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            with self._lock:
                self._loop = loop
            ready.set()
            loop.run_forever()
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()

        self._thread = threading.Thread(target=run_loop, name="nanus-job-supervisor", daemon=True)
        self._thread.start()
        ready.wait(timeout=2)
        if not self._loop:
            raise RuntimeError("Nanus job supervisor failed to start")
        return self._loop
