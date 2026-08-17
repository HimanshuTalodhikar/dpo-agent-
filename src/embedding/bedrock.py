"""Amazon Bedrock Titan embedding implementation."""

from __future__ import annotations

import json

import boto3
import numpy as np
import structlog

from .base import EmbeddingProvider, EmbeddingResult

logger = structlog.get_logger(__name__)


class BedrockEmbeddingProvider(EmbeddingProvider):
    """Amazon Bedrock Titan Text Embeddings provider via boto3."""

    def __init__(
        self,
        model_id: str = "amazon.titan-embed-text-v2",
        region: str = "us-east-1",
        *,
        dimensions: int = 1024,
        endpoint_url: str | None = None,
    ) -> None:
        self._model_id = model_id
        self._region = region
        self._dimensions = dimensions
        self._endpoint_url = endpoint_url
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            endpoint_url=endpoint_url,
        )

    @property
    def provider_name(self) -> str:
        return "bedrock-titan"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, text: str) -> EmbeddingResult:
        """Embed a single text string."""
        body = json.dumps({"inputText": text})
        response = self._client.invoke_model(
            modelId=self._model_id,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        result = json.loads(response["body"].read().decode("utf-8"))
        vector = np.array(result["embedding"], dtype=np.float32)
        return EmbeddingResult(
            vector=vector,
            model=self._model_id,
            dimensions=self._dimensions,
            token_count=result.get("inputTokenCount"),
        )

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        """Embed multiple texts in a batch."""
        # Titan v2 supports batch input
        body = json.dumps({"inputTexts": texts})
        response = self._client.invoke_model(
            modelId=self._model_id,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        result = json.loads(response["body"].read().decode("utf-8"))
        return [
            EmbeddingResult(
                vector=np.array(emb, dtype=np.float32),
                model=self._model_id,
                dimensions=self._dimensions,
                token_count=None,
            )
            for emb in result["embedding"]
        ]
