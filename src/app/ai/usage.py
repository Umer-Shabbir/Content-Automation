from contextlib import contextmanager
from typing import Generator
from pydantic import BaseModel, Field

from app.utils.logging import get_logger

logger = get_logger(__name__)

class TokenUsage(BaseModel):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def add(self, other: "TokenUsage") -> None:
        """Add another TokenUsage object's stats to this one."""
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens


class UsageTracker:
    """
    Global or scoped usage tracker to maintain a running tally of API token usage.
    """

    def __init__(self):
        self._total_usage = TokenUsage()

    @property
    def current_usage(self) -> TokenUsage:
        """Returns a snapshot of current total usage."""
        # Return a copy to prevent accidental mutation
        return TokenUsage(
            input_tokens=self._total_usage.input_tokens,
            output_tokens=self._total_usage.output_tokens
        )

    def record_usage(self, usage: TokenUsage) -> None:
        """Record usage from a single API call."""
        self._total_usage.add(usage)
        logger.debug(f"Usage recorded: {usage.input_tokens} input, {usage.output_tokens} output")

    def reset(self) -> None:
        """Reset total tracked usage."""
        self._total_usage = TokenUsage()


# Global tracker for simple use cases
# (In a larger DI framework, you might inject this instead of using a global variable)
global_usage_tracker = UsageTracker()


@contextmanager
def scoped_usage() -> Generator[UsageTracker, None, None]:
    """
    Context manager for tracking token usage within a specific scope.
    Useful for job-level or pipeline-level tracking.
    """
    tracker = UsageTracker()
    try:
        yield tracker
    finally:
        logger.info(
            f"Scoped usage complete: "
            f"{tracker.current_usage.input_tokens} in / "
            f"{tracker.current_usage.output_tokens} out "
            f"({tracker.current_usage.total_tokens} total tokens)"
        )
