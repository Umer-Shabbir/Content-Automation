import pytest
import asyncio
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.api_profile import APIProfile, RequestConfig
from app.ai.retry import RetryPolicy, retry_with_backoff

class DummyException(Exception):
    pass

@pytest.mark.asyncio
async def test_retry_with_backoff_success():
    @retry_with_backoff(max_retries=3, base_backoff=0.01)
    async def always_succeeds():
        response = httpx.Response(200, json={"message": "success"})
        return response

    result = await always_succeeds()
    assert result.status_code == 200
    assert result.json()["message"] == "success"

@pytest.mark.asyncio
async def test_retry_with_backoff_eventual_success():
    attempts = 0

    @retry_with_backoff(max_retries=3, base_backoff=0.01)
    async def succeeds_third_time():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise httpx.ConnectError("Connection failed")
        response = httpx.Response(200, json={"message": "success"})
        return response

    result = await succeeds_third_time()
    assert result.status_code == 200
    assert result.json()["message"] == "success"
    assert attempts == 3

@pytest.mark.asyncio
async def test_retry_with_backoff_max_retries_exceeded():
    attempts = 0

    @retry_with_backoff(max_retries=2, base_backoff=0.01)
    async def always_fails():
        nonlocal attempts
        attempts += 1
        raise httpx.ReadTimeout("Timeout")

    with pytest.raises(httpx.ReadTimeout):
        await always_fails()

    # Initial attempt + 2 retries = 3 attempts total
    assert attempts == 3

@pytest.mark.asyncio
async def test_retry_with_backoff_non_retryable_error():
    attempts = 0

    @retry_with_backoff(max_retries=3, base_backoff=0.01)
    async def fails_badly():
        nonlocal attempts
        attempts += 1
        raise DummyException("Should not retry this")

    with pytest.raises(DummyException):
        await fails_badly()

    assert attempts == 1
