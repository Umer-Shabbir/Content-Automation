import asyncio
import pytest
import pytest_asyncio
from app.orchestrator.event_bus import EventBus
from app.orchestrator.queue import JobQueue
from app.orchestrator.engine import Orchestrator, JobState

@pytest.fixture
def event_bus():
    return EventBus()

@pytest_asyncio.fixture
async def queue():
    q = JobQueue()
    q.start_worker()
    yield q
    await q.stop_worker()

@pytest_asyncio.fixture
async def orchestrator(queue, event_bus):
    engine = Orchestrator(queue=queue, event_bus=event_bus)
    return engine

@pytest.mark.asyncio
async def test_event_bus():
    bus = EventBus()

    events_received = []

    async def async_handler(*args, **kwargs):
        events_received.append(("async", args, kwargs))

    def sync_handler(*args, **kwargs):
        events_received.append(("sync", args, kwargs))

    bus.subscribe("test_event", async_handler)
    bus.subscribe("test_event", sync_handler)

    # 1. Async publish
    await bus.publish("test_event", "arg1", kwarg1="val1")

    assert len(events_received) == 2
    assert ("async", ("arg1",), {"kwarg1": "val1"}) in events_received
    assert ("sync", ("arg1",), {"kwarg1": "val1"}) in events_received

    events_received.clear()

    # 2. Sync publish
    bus.publish_sync("test_event", "arg2")
    # Wait for the event loop to run the async task spawned by publish_sync
    await asyncio.sleep(0.01)

    assert len(events_received) == 2
    # Sync handler executes immediately, async is queued
    assert ("sync", ("arg2",), {}) in events_received
    assert ("async", ("arg2",), {}) in events_received

    # 3. Unsubscribe
    bus.unsubscribe("test_event", async_handler)
    events_received.clear()

    await bus.publish("test_event", "arg3")
    assert len(events_received) == 1
    assert ("sync", ("arg3",), {}) in events_received


@pytest.mark.asyncio
async def test_queue():
    queue = JobQueue()
    queue.start_worker()

    assert queue.is_empty is True

    execution_order = []

    async def demo_task(name: str):
        execution_order.append(f"{name}_start")
        await asyncio.sleep(0.1)
        execution_order.append(f"{name}_end")

    await queue.enqueue(demo_task, "task1")
    await queue.enqueue(demo_task, "task2")

    # Wait for jobs to finish
    await queue.join()

    assert queue.is_empty is True
    assert "task1_start" in execution_order
    assert "task2_start" in execution_order

    await queue.stop_worker()


@pytest.mark.asyncio
async def test_orchestrator_engine(orchestrator):
    events_published = []

    orchestrator.event_bus.subscribe("job_submitted", lambda **k: events_published.append("job_submitted"))
    orchestrator.event_bus.subscribe("job_started", lambda **k: events_published.append("job_started"))
    orchestrator.event_bus.subscribe("job_completed", lambda **k: events_published.append("job_completed"))
    orchestrator.event_bus.subscribe("job_failed", lambda **k: events_published.append("job_failed"))

    # Pipeline task
    async def mock_pipeline(data: dict):
        if data.get("should_fail"):
            raise ValueError("Pipeline failed as requested")
        return {"status": "success", "processed": data["val"]}

    # Success scenario
    job_id = await orchestrator.submit_job(mock_pipeline, {"val": 42})
    job = orchestrator.get_job(job_id)
    assert job is not None

    # Wait for completion
    await orchestrator.queue.join()

    assert job.state == JobState.COMPLETED
    assert job.result == {"status": "success", "processed": 42}

    assert "job_submitted" in events_published
    assert "job_started" in events_published
    assert "job_completed" in events_published

    events_published.clear()

    # Failure scenario
    job_id2 = await orchestrator.submit_job(mock_pipeline, {"should_fail": True})
    job2 = orchestrator.get_job(job_id2)

    # Wait for completion
    await orchestrator.queue.join()

    assert job2.state == JobState.FAILED
    assert job2.error == "Pipeline failed as requested"

    assert "job_submitted" in events_published
    assert "job_started" in events_published
    assert "job_failed" in events_published
