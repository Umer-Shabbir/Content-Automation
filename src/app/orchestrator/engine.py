import asyncio
from typing import Any, Callable, Dict, Optional, Awaitable
from datetime import datetime
import uuid

from .event_bus import default_bus
from .queue import JobQueue

class JobState:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Job:
    def __init__(self, id: str, pipeline: Callable[[Any], Awaitable[Any]], input_data: Any):
        self.id = id
        self.pipeline = pipeline
        self.input_data = input_data
        self.state = JobState.PENDING
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def update_state(self, new_state: str, result: Any = None, error: str = None):
        self.state = new_state
        self.updated_at = datetime.utcnow()
        if result is not None:
            self.result = result
        if error is not None:
            self.error = error

class Orchestrator:
    def __init__(self, queue: JobQueue, event_bus=default_bus):
        self._jobs: Dict[str, Job] = {}
        self.queue = queue
        self.event_bus = event_bus

    def start(self):
        """Start the orchestrator's background queue processing."""
        self.queue.start_worker()

    async def stop(self):
        """Stop processing and wait."""
        await self.queue.stop_worker()

    async def submit_job(self, pipeline: Callable[[Any], Awaitable[Any]], input_data: Any) -> str:
        """Submit a job to the orchestrator to be executed via a pipeline state machine."""
        job_id = str(uuid.uuid4())
        job = Job(id=job_id, pipeline=pipeline, input_data=input_data)
        self._jobs[job_id] = job

        # We start the job execution in background
        await self.queue.enqueue(self._execute_job, job_id)

        # Publish event synchronously
        self.event_bus.publish_sync("job_submitted", job_id=job_id)

        return job_id

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    async def _execute_job(self, job_id: str):
        job = self._jobs.get(job_id)
        if not job:
            return

        job.update_state(JobState.RUNNING)
        await self.event_bus.publish("job_started", job_id=job_id)

        try:
            # Here pipeline is an async function that runs the steps
            result = await job.pipeline(job.input_data)
            # Simulated DB save logic or similar state storage
            self._save_state(job_id, JobState.COMPLETED, result=result)
            await self.event_bus.publish("job_completed", job_id=job_id, result=result)
        except Exception as e:
            # State transitions to FAILED
            error_msg = str(e)
            self._save_state(job_id, JobState.FAILED, error=error_msg)
            await self.event_bus.publish("job_failed", job_id=job_id, error=error_msg)

    def _save_state(self, job_id: str, new_state: str, result: Any = None, error: str = None):
        """Simulate saving the state transitions persistently to DB"""
        job = self._jobs.get(job_id)
        if job:
            job.update_state(new_state, result=result, error=error)
            # A real implementation would persist to a database here
