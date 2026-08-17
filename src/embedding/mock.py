"""Mock embedding provider for local development and testing."""

from __future__ import annotations

import hashlib
import numpy as np
import numpy.typing as npt
import structlog

from .base import EmbeddingProvider, EmbeddingResult

logger = structlog.get_logger(__name__)


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic mock embedding provider.

    Generates reproducible vectors based on text hash — same text always
    produces the same vector, enabling deterministic retrieval tests.
    """

    def __init__(self, dimensions: int = 1024) -> None:
        self._dimensions = dimensions

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _text_to_seed(self, text: str) -> int:
        """Convert text to a deterministic integer seed."""
        h = hashlib.sha256(text.encode("utf-8")).digest()
        return int.from_bytes(h[:4], byteorder="big", signed=False)

    def _seed_to_vector(self, seed: int) -> npt.NDArray[np.float32]:
        """Generate a unit-norm vector from a seed."""
        rng = np.random.Generator(np.random.PCG64(seed))
        vec = rng.normal(size=self._dimensions).astype(np.float32)
        # L2 normalize to unit sphere (required for cosine similarity)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    async def embed(self, text: str) -> EmbeddingResult:
        """Embed a single text string."""
        seed = self._text_to_seed(text)
        vector = self._seed_to_vector(seed)
        logger.debug("mock.embed", text_len=len(text), seed=seed)
        return EmbeddingResult(
            vector=vector,
            model="mock/titan-embed",
            dimensions=self._dimensions,
            token_count=len(text.split()),
        )

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        """Embed multiple texts."""
        return [await self.embed(t) for t in texts]
