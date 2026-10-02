import asyncio
import random
from functools import wraps
from typing import Optional, List, Dict, Any, TypeVar, Callable, Awaitable
import httpx
from app.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')

RETRYABLE_STATUS_CODES = (429, 500, 502, 503, 504)


class RetryPolicy:
    """Exponential backoff with jitter and respect for retry-after."""

    def __init__(self, max_retries: int = 5, base_backoff: float = 2.0, max_backoff: float = 60.0):
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.max_backoff = max_backoff

    async def execute(
        self,
        func: Callable[[], Awaitable[httpx.Response]],
    ) -> httpx.Response:
        retries = 0
        while True:
            try:
                response = await func()

                # Success
                if response.status_code < 400:
                    return response

                # Non-retryable HTTP status
                if response.status_code not in RETRYABLE_STATUS_CODES:
                    response.raise_for_status()

                # Retryable status code (429, 500, etc.)
                if retries >= self.max_retries:
                    logger.error(f'Max retries ({self.max_retries}) reached for status {response.status_code}')
                    response.raise_for_status()

                # Calculate delay
                retry_after_str = response.headers.get('retry-after')
                delay = 0.0
                if retry_after_str:
                    try:
                        delay = float(retry_after_str)
                        logger.debug(f'Server requested retry after {delay} seconds')
                    except ValueError:
                        pass

                if delay <= 0:
                    base_delay = min(self.base_backoff ** retries, self.max_backoff)
                    delay = base_delay * (0.5 + random.random())

                logger.info(f'Sleeping for {delay:.2f} seconds before retry {retries + 1}/{self.max_retries}')
                await asyncio.sleep(delay)
                retries += 1

            except httpx.HTTPStatusError as e:
                # Catch HTTPStatusError if raised by func() or response
                status_code = e.response.status_code if e.response is not None else None
                if status_code not in RETRYABLE_STATUS_CODES:
                    raise

                if retries >= self.max_retries:
                    logger.error(f'Max retries ({self.max_retries}) reached with HTTPStatusError: {e}')
                    raise

                retry_after_str = e.response.headers.get('retry-after') if e.response is not None else None
                delay = 0.0
                if retry_after_str:
                    try:
                        delay = float(retry_after_str)
                    except ValueError:
                        pass

                if delay <= 0:
                    base_delay = min(self.base_backoff ** retries, self.max_backoff)
                    delay = base_delay * (0.5 + random.random())

                logger.warning(f'HTTPStatusError {status_code}, retrying in {delay:.2f}s...')
                await asyncio.sleep(delay)
                retries += 1

            except httpx.RequestError as e:
                if retries >= self.max_retries:
                    logger.error(f'Max retries ({self.max_retries}) reached with request error: {e}')
                    raise

                base_delay = min(self.base_backoff ** retries, self.max_backoff)
                delay = base_delay * (0.5 + random.random())
                logger.warning(f'Request error: {e}, retrying in {delay:.2f}s...')
                await asyncio.sleep(delay)
                retries += 1


def retry_with_backoff(max_retries: int = 5, base_backoff: float = 2.0, max_backoff: float = 60.0):
    """Decorator version of RetryPolicy."""
    policy = RetryPolicy(max_retries=max_retries, base_backoff=base_backoff, max_backoff=max_backoff)

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            async def _call():
                return await func(*args, **kwargs)
            return await policy.execute(_call)
        return wrapper
    return decorator
