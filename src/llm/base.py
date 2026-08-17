"""LLM provider abstraction — defines the interface for LLM backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from pydantic import BaseModel


T = TypeVar("T", bound="BaseModel | None")


@dataclass
class LLMResponse:
    """Raw LLM response."""

    content: str
    model: str
    usage: LLMUsage | None = None
    finish_reason: str | None = None


@dataclass
class LLMUsage:
    """Token usage information."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMConfig:
    """Configuration for a single LLM call."""

    temperature: float = 0.3
    top_p: float = 0.9
    max_tokens: int = 4096
    stop_sequences: list[str] | None = None
    system_prompt: str | None = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    Implementations must be thread-safe and async-capable.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name (e.g. 'bedrock', 'mock')."""
        ...

    @abstractmethod
    async def complete(self, prompt: str, config: LLMConfig | None = None) -> LLMResponse:
        """Send a plain text prompt and return the raw response."""
        ...

    @abstractmethod
    async def structured_complete(
        self,
        prompt: str,
        output_schema: type[T],
        config: LLMConfig | None = None,
    ) -> T:
        """Send a prompt and parse the response into a Pydantic model.

        Implementations should use the model's JSON schema to constrain
        the LLM output format and parse the result.
        """
        ...
