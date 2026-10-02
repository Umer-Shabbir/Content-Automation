import asyncio
import time
import pytest
from app.ai.rate_limiter import RateLimiter

@pytest.mark.asyncio
async def test_rate_limiter_concurrency():
    limiter = RateLimiter(max_concurrent_requests=2, delay_between_requests=0.0)

    # Tracker for active requests
    active_requests = 0
    max_active_requests = 0

    async def simulated_task():
        nonlocal active_requests, max_active_requests
        async with limiter:
            active_requests += 1
            max_active_requests = max(max_active_requests, active_requests)
            await asyncio.sleep(0.1)  # Simulate some async work
            active_requests -= 1

    # Run 5 concurrent tasks
    tasks = [asyncio.create_task(simulated_task()) for _ in range(5)]
    await asyncio.gather(*tasks)

    # Ensure we never exceeded max concurrency
    assert max_active_requests == 2


@pytest.mark.asyncio
async def test_rate_limiter_delay():
    # Only 1 concurrency allowed, mandatory 0.2s delay
    limiter = RateLimiter(max_concurrent_requests=1, delay_between_requests=0.2)

    async def lightweight_task():
        async with limiter:
            pass  # instantly complete

    start_time = time.monotonic()

    # Fire off 3 rapid tasks
    # 1st task: executes immediately (0 delay)
    # 2nd task: waits ~0.2s because of delay spacing
    # 3rd task: waits ~0.4s
    await asyncio.gather(
        lightweight_task(),
        lightweight_task(),
        lightweight_task()
    )

    elapsed = time.monotonic() - start_time

    # We expect roughly 0.4 seconds total wait, definitely at least 0.35 on fast Windows machines
    assert elapsed >= 0.35, f"Elapsed time {elapsed} was shorter than expected minimum 0.35s"
