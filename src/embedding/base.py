"""Embedding provider abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt


@dataclass
class EmbeddingResult:
    """Result of an embedding call."""

    vector: npt.NDArray[np.float32]
    model: str
    dimensions: int
    token_count: int | None = None


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Embedding vector dimension for this provider."""
        ...

    @abstractmethod
    async def embed(self, text: str) -> EmbeddingResult:
        """Embed a single text string."""
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        """Embed multiple texts in a batch."""
        ...
