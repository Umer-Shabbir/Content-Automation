import asyncio
import time
from typing import Optional
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Controls concurrency and request spacing for API calls."""

    def __init__(
        self,
        max_concurrent_requests: Optional[int] = None,
        delay_between_requests: float = 0.5,
        max_concurrent: Optional[int] = None,
    ):
        # Support both max_concurrent_requests and max_concurrent
        if max_concurrent_requests is not None:
            self.max_concurrent = max_concurrent_requests
        elif max_concurrent is not None:
            self.max_concurrent = max_concurrent
        else:
            self.max_concurrent = 3

        self.max_concurrent_requests = self.max_concurrent
        self.delay_between_requests = delay_between_requests
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        self.last_request_time = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Acquires a slot, waiting if necessary to respect concurrency and spacing limits."""
        await self.semaphore.acquire()

        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_request_time
            if elapsed < self.delay_between_requests:
                sleep_time = self.delay_between_requests - elapsed
                await asyncio.sleep(sleep_time)

            self.last_request_time = time.monotonic()

    def release(self):
        """Releases a concurrency slot."""
        self.semaphore.release()

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.release()
