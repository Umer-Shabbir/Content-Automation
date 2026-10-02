import pytest
import asyncio
import httpx
import time
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.api_profile import APIProfile, RequestConfig
from app.ai.client import AnthropicClient
from app.ai.retry import RetryPolicy, retry_with_backoff
from app.ai.usage import global_usage_tracker


@pytest.fixture
def api_profile():
    return APIProfile(
        name="test-profile",
        base_url="https://api.anthropic.com",
        api_key="sk-test-key",
        model="claude-3-haiku-20240307",
        config=RequestConfig(
            temperature=0.7,
            max_tokens=1000,
            request_timeout=30.0,
            max_concurrent_requests=2,
            delay_between_requests=0.1,
            max_retries=2,
            retry_backoff=1.5
        )
    )

@pytest.mark.asyncio
async def test_anthropic_client_create_message(api_profile):
    client = AnthropicClient(profile=api_profile)

    expected_payload = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 1000,
        "temperature": 0.7,
        "messages": [{"role": "user", "content": "Hello"}],
        "system": "You are a helpful assistant"
    }

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None

    mock_content = {
        "id": "msg_123",
        "content": [{"type": "text", "text": "Hi there"}],
        "usage": {"input_tokens": 10, "output_tokens": 20}
    }
    mock_response.json.return_value = mock_content

    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        # Test both create_message and generate_message
        raw_response = await client.create_message(
            messages=[{"role": "user", "content": "Hello"}],
            system="You are a helpful assistant"
        )
        assert raw_response == mock_content

        response = await client.generate_message(
            messages=[{"role": "user", "content": "Hello"}],
            system="You are a helpful assistant"
        )

        assert response["text"] == "Hi there"
        assert response["usage"]["input_tokens"] == 10
        assert response["usage"]["output_tokens"] == 20

        assert mock_post.call_count == 2
        args, kwargs = mock_post.call_args
        assert args[0] == "https://api.anthropic.com/v1/messages"
        assert kwargs['json'] == expected_payload
        assert kwargs['headers']['x-api-key'] == "sk-test-key"
        assert kwargs['headers']['anthropic-version'] == "2023-06-01"

    # Verify key is redacted from repr
    repr_str = repr(client)
    assert "sk-test-key" not in repr_str
    assert "https://api.anthropic.com" in repr_str
    assert "claude-3-haiku-20240307" in repr_str

    await client.close()

@pytest.mark.asyncio
async def test_anthropic_client_handles_429_with_retry_after(api_profile):
    client = AnthropicClient(profile=api_profile)

    error_response = MagicMock(spec=httpx.Response)
    error_response.status_code = 429
    error_response.headers = {"retry-after": "0.05"}

    error_to_raise = httpx.HTTPStatusError("429 Too Many Requests", request=MagicMock(), response=error_response)

    success_response = MagicMock(spec=httpx.Response)
    success_response.status_code = 200
    success_response.raise_for_status.return_value = None
    success_response.json.return_value = {
        "id": "msg_124",
        "content": [{"type": "text", "text": "Recovered!"}],
        "usage": {"input_tokens": 5, "output_tokens": 5}
    }

    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [error_to_raise, success_response]

        response = await client.generate_message(
            messages=[{"role": "user", "content": "Hello again"}]
        )

        assert mock_post.call_count == 2
        assert response["text"] == "Recovered!"

    await client.close()

@pytest.mark.asyncio
async def test_anthropic_client_handles_500_server_error(api_profile):
    client = AnthropicClient(profile=api_profile)

    error_response = MagicMock(spec=httpx.Response)
    error_response.status_code = 500
    error_response.headers = {}

    error_to_raise = httpx.HTTPStatusError("500 Internal Server Error", request=MagicMock(), response=error_response)

    success_response = MagicMock(spec=httpx.Response)
    success_response.status_code = 200
    success_response.raise_for_status.return_value = None
    success_response.json.return_value = {
        "id": "msg_125",
        "content": [{"type": "text", "text": "Server ok!"}],
        "usage": {"input_tokens": 8, "output_tokens": 12}
    }

    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [error_to_raise, success_response]

        response = await client.generate_message(
            messages=[{"role": "user", "content": "Hello server"}]
        )

        assert mock_post.call_count == 2
        assert response["text"] == "Server ok!"

    await client.close()

@pytest.mark.asyncio
async def test_anthropic_client_non_retryable_error(api_profile):
    client = AnthropicClient(profile=api_profile)

    error_response = MagicMock(spec=httpx.Response)
    error_response.status_code = 400
    error_response.headers = {}

    error_to_raise = httpx.HTTPStatusError("400 Bad Request", request=MagicMock(), response=error_response)

    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = error_to_raise

        with pytest.raises(httpx.HTTPStatusError):
            await client.generate_message(
                messages=[{"role": "user", "content": "Invalid request"}]
            )

        # 400 is not retryable, should fail immediately
        assert mock_post.call_count == 1

    await client.close()
