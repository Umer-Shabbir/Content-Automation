from typing import Optional
from pydantic import BaseModel, Field, SecretStr, field_validator

class RequestConfig(BaseModel):
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(default=8192, gt=0, le=64000)
    request_timeout: float = Field(default=180.0, gt=0.0)
    max_concurrent_requests: int = Field(default=3, ge=1, le=20)
    delay_between_requests: float = Field(default=0.5, ge=0.0)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_backoff: float = Field(default=2.0, ge=1.0)

class APIProfile(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100)
    base_url: str = Field(..., min_length=1)
    api_key: SecretStr = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    config: RequestConfig = Field(default_factory=RequestConfig)

    @field_validator("base_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("Base URL must start with http:// or https://")
        return v

    def get_api_key(self) -> str:
        return self.api_key.get_secret_value()

    def __repr__(self) -> str:
        return f"<APIProfile name={self.name!r} base_url={self.base_url!r} model={self.model!r}>"
