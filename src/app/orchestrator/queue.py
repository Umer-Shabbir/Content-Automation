import asyncio
from typing import Any, Coroutine, Dict
import uuid

class JobQueue:
    """An asynchronous job queue wrapper that tracks active background jobs."""
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._active_jobs: Dict[str, asyncio.Task] = {}
        self._worker_task = None

    async def enqueue(self, coro_func, *args, **kwargs) -> str:
        """Enqueue an async function with arguments, returns a job_id."""
        job_id = str(uuid.uuid4())
        await self._queue.put({"id": job_id, "func": coro_func, "args": args, "kwargs": kwargs})
        return job_id

    async def process_queue(self):
        """Worker loop that processes the queue continuously."""
        while True:
            job = await self._queue.get()
            job_id = job["id"]

            async def run_job(j):
                try:
                    await j["func"](*j["args"], **j["kwargs"])
                finally:
                    # Clean up active jobs when done or failed
                    self._active_jobs.pop(j["id"], None)
                    self._queue.task_done()

            task = asyncio.create_task(run_job(job))
            self._active_jobs[job_id] = task

    def start_worker(self):
        """Start a background worker to consume the queue."""
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self.process_queue())

    async def stop_worker(self):
        """Stop the background worker."""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

    async def join(self):
        """Block until all enqueued items have been processed."""
        await self._queue.join()

    @property
    def active_job_count(self) -> int:
        """Returns the number of current active jobs being processed."""
        return len(self._active_jobs)

    @property
    def pending_count(self) -> int:
        """Returns the number of jobs deep in the queue."""
        return self._queue.qsize()

    @property
    def is_empty(self) -> bool:
        """True if there are no pending and no locally active jobs."""
        return self.active_job_count == 0 and self.pending_count == 0
