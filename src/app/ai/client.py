import httpx
from typing import List, Dict, Any, Optional
from app.models.api_profile import APIProfile, RequestConfig
from app.ai.retry import RetryPolicy, retry_with_backoff
from app.ai.rate_limiter import RateLimiter, get_global_rate_limiter
from app.ai.usage import TokenUsage, global_usage_tracker, UsageTracker
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AnthropicClient:
    """Client for Anthropic-compatible Messages API."""

    def __init__(
        self,
        profile: Optional[APIProfile] = None,
        usage_tracker: Optional[UsageTracker] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        if profile is None:
            # Default fallback profile
            profile = APIProfile(
                name="default",
                base_url="https://api.anthropic.com",
                api_key="default",
                model="claude-sonnet-4-6",
                config=RequestConfig()
            )
        self.profile = profile
        self.base_url = profile.base_url
        self._api_key = profile.get_api_key()
        self.model = profile.model
        self.max_tokens = profile.config.max_tokens
        self.temperature = profile.config.temperature
        self.timeout = profile.config.request_timeout
        self.usage_tracker = usage_tracker or global_usage_tracker
        self._client: Optional[httpx.AsyncClient] = None

        self.retry_policy = RetryPolicy(
            max_retries=profile.config.max_retries,
            base_backoff=profile.config.retry_backoff
        )

        if rate_limiter is not None:
            self.rate_limiter = rate_limiter
        else:
            self.rate_limiter = get_global_rate_limiter(
                max_concurrent_requests=profile.config.max_concurrent_requests,
                delay_between_requests=profile.config.delay_between_requests
            )

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "x-api-key": self._api_key,
            "Authorization": f"Bearer {self._api_key}",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "x-omniroute-no-memory": "true"
        }
        return headers

    def _get_api_url(self) -> str:
        base = self.base_url.rstrip("/")
        if not base.endswith("v1/messages"):
            if base.endswith("v1"):
                return f"{base}/messages"
            return f"{base}/v1/messages"
        return base

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def create_message(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates a message following the Anthropic /v1/messages API structure."""

        url = self._get_api_url()
        payload = {
            "model": model or self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature
        }
        if system:
            payload["system"] = system

        logger.info(f"Sending message to Anthropic-compatible API at {url} using model {payload['model']}")

        async def _make_request() -> httpx.Response:
            await self.rate_limiter.acquire()
            try:
                client = await self._get_client()
                headers = self._get_headers()
                response = await client.post(url, json=payload, headers=headers)
                return response
            finally:
                self.rate_limiter.release()

        response = await self.retry_policy.execute(_make_request)
        data = response.json()

        # Extract usage and record it
        usage_data = data.get("usage", {})
        if usage_data:
            input_tokens = usage_data.get("input_tokens", 0)
            output_tokens = usage_data.get("output_tokens", 0)
            token_usage = TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens)
            self.usage_tracker.record_usage(token_usage)

        return data

    async def generate_message(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convenience wrapper returning extracted text and usage info.
        Format: {"text": str, "usage": dict, "raw": dict}
        """
        raw_response = await self.create_message(
            messages=messages,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        )

        content_blocks = raw_response.get("content", [])
        text_content = ""
        for block in content_blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                text_content += block.get("text", "")
            elif isinstance(block, dict) and "text" in block:
                text_content += block.get("text", "")

        usage_info = raw_response.get("usage", {})

        return {
            "text": text_content,
            "usage": usage_info,
            "raw": raw_response,
        }

    def __repr__(self) -> str:
        return f"<AnthropicClient base_url={self.base_url!r} model={self.model!r}>"


def get_ai_client(
    profile: Optional[APIProfile] = None,
    rate_limiter: Optional[RateLimiter] = None
) -> AnthropicClient:
    return AnthropicClient(profile=profile, rate_limiter=rate_limiter)
