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


def test_rate_limiter_multithreaded_concurrency():
    """Verify that RateLimiter limits concurrency across separate OS threads running independent event loops."""
    import threading

    limiter = RateLimiter(max_concurrent_requests=2, delay_between_requests=0.0)

    active_count = 0
    max_active_count = 0
    count_lock = threading.Lock()
    exceptions = []

    def thread_worker():
        nonlocal active_count, max_active_count
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def worker_task():
            nonlocal active_count, max_active_count
            async with limiter:
                with count_lock:
                    active_count += 1
                    max_active_count = max(max_active_count, active_count)
                await asyncio.sleep(0.08)
                with count_lock:
                    active_count -= 1

        try:
            loop.run_until_complete(worker_task())
        except Exception as e:
            exceptions.append(e)
        finally:
            loop.close()

    # Launch 6 concurrent OS threads
    threads = [threading.Thread(target=thread_worker) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not exceptions, f"Exceptions occurred in worker threads: {exceptions}"
    assert max_active_count == 2, f"Expected max concurrency of 2 across threads, got {max_active_count}"


@pytest.mark.asyncio
async def test_global_rate_limiter_shared():
    """Verify that get_global_rate_limiter returns a shared singleton and updates limits correctly."""
    from app.ai.rate_limiter import get_global_rate_limiter, reset_global_rate_limiter
    from app.ai.client import AnthropicClient
    from app.models.api_profile import APIProfile, RequestConfig

    reset_global_rate_limiter()

    limiter1 = get_global_rate_limiter(max_concurrent_requests=3)
    limiter2 = get_global_rate_limiter()
    assert limiter1 is limiter2
    assert limiter1.max_concurrent == 3

    # Updating limits via get_global_rate_limiter
    limiter3 = get_global_rate_limiter(max_concurrent_requests=5)
    assert limiter3 is limiter1
    assert limiter1.max_concurrent == 5

    # AnthropicClients default to this global rate limiter
    profile = APIProfile(
        name="test",
        base_url="https://api.anthropic.com",
        api_key="test-key",
        model="claude-3-haiku-20240307",
        config=RequestConfig(max_concurrent_requests=4)
    )
    client1 = AnthropicClient(profile=profile)
    client2 = AnthropicClient(profile=profile)

    assert client1.rate_limiter is limiter1
    assert client2.rate_limiter is limiter1
    assert limiter1.max_concurrent == 4

    reset_global_rate_limiter()
