import asyncio
import time
import threading
from typing import Optional
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Controls concurrency and request spacing for API calls across threads and event loops."""

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
        self.last_request_time = 0.0
        self._active_requests = 0
        self._thread_lock = threading.Lock()

    def update_limits(
        self,
        max_concurrent_requests: Optional[int] = None,
        delay_between_requests: Optional[float] = None,
        max_concurrent: Optional[int] = None,
    ):
        """Dynamically update concurrency limit and request spacing."""
        limit = max_concurrent_requests if max_concurrent_requests is not None else max_concurrent
        with self._thread_lock:
            if limit is not None:
                self.max_concurrent = max(1, int(limit))
                self.max_concurrent_requests = self.max_concurrent
            if delay_between_requests is not None:
                self.delay_between_requests = max(0.0, float(delay_between_requests))

    @property
    def active_requests(self) -> int:
        with self._thread_lock:
            return self._active_requests

    async def acquire(self):
        """
        Acquires a slot, waiting if necessary to respect concurrency and spacing limits.
        Thread-safe and cross-event-loop safe: uses threading.Lock for atomic state updates
        and non-blocking asyncio.sleep for yielding back to the current event loop.
        """
        while True:
            sleep_needed = 0.0
            with self._thread_lock:
                now = time.monotonic()
                if self._active_requests < self.max_concurrent:
                    elapsed = now - self.last_request_time
                    if elapsed < self.delay_between_requests:
                        sleep_needed = self.delay_between_requests - elapsed
                    else:
                        self._active_requests += 1
                        self.last_request_time = time.monotonic()
                        return
                else:
                    # Slot is full, wait for an in-flight request to finish
                    sleep_needed = 0.02

            # Sleep asynchronously outside the lock on the caller's event loop
            await asyncio.sleep(max(sleep_needed, 0.005))

    def release(self):
        """Releases a concurrency slot."""
        with self._thread_lock:
            if self._active_requests > 0:
                self._active_requests -= 1

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.release()


_global_rate_limiter: Optional[RateLimiter] = None
_global_limiter_lock = threading.Lock()


def get_global_rate_limiter(
    max_concurrent_requests: Optional[int] = None,
    delay_between_requests: Optional[float] = None,
) -> RateLimiter:
    """Returns the shared application-wide RateLimiter, updating limits if specified."""
    global _global_rate_limiter
    with _global_limiter_lock:
        if _global_rate_limiter is None:
            _global_rate_limiter = RateLimiter(
                max_concurrent_requests=max_concurrent_requests or 3,
                delay_between_requests=delay_between_requests if delay_between_requests is not None else 0.5,
            )
        else:
            if max_concurrent_requests is not None or delay_between_requests is not None:
                _global_rate_limiter.update_limits(
                    max_concurrent_requests=max_concurrent_requests,
                    delay_between_requests=delay_between_requests,
                )
        return _global_rate_limiter


def reset_global_rate_limiter():
    """Reset the global rate limiter (useful for unit tests)."""
    global _global_rate_limiter
    with _global_limiter_lock:
        _global_rate_limiter = None
