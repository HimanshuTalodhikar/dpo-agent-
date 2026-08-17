"""Legal retrieval — vector + metadata search over the knowledge base."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog

from ..embedding.base import EmbeddingProvider
from ..storage import aurora as storage

logger = structlog.get_logger(__name__)


@dataclass
class RetrievalQuery:
    """A retrieval query with optional filters."""

    text: str
    top_k: int = 10
    jurisdiction: str | None = None
    domain: str | None = None
    law_type: str | None = None
    min_relevance: float = 0.3
    effective_after: datetime | None = None  # only docs effective after this date
    effective_before: datetime | None = None   # only docs effective before this date


@dataclass
class RetrievedChunk:
    """A retrieved legal chunk with full metadata."""

    chunk_id: str
    document_id: str
    legal_doc_id: str
    chunk_index: int
    content: str
    section: str | None
    section_ref: str | None
    title: str
    jurisdiction: str
    domain: str
    law_type: str
    effective_date: datetime | None
    source_url: str | None
    similarity: float
    token_count: int | None

    def to_source_dict(self) -> dict[str, Any]:
        """Format as a source reference for decision output."""
        return {
            "document_id": self.legal_doc_id,
            "chunk_id": self.chunk_id,
            "section": f"{self.title} — {self.section_ref or self.section or 'General'}",
            "excerpt": self.content[:300] + ("..." if len(self.content) > 300 else ""),
            "jurisdiction": self.jurisdiction,
            "effective_date": (
                self.effective_date.isoformat() if self.effective_date else None
            ),
            "similarity": round(self.similarity, 4),
        }


@dataclass
class RetrievalResult:
    """Result of a retrieval operation."""

    query: RetrievalQuery
    chunks: list[RetrievedChunk] = field(default_factory=list)
    insufficient_context: bool = False
    insufficient_context_reason: str | None = None

    @property
    def has_results(self) -> bool:
        return len(self.chunks) > 0


class LegalRetriever:
    """Retrieves relevant legal context from the Aurora/pgvector knowledge base."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        top_k: int = 10,
        min_relevance: float = 0.3,
    ) -> None:
        self._embedding = embedding_provider
        self._top_k = top_k
        self._min_relevance = min_relevance

    async def retrieve(
        self,
        query: RetrievalQuery,
        session: Any,  # AsyncSession
    ) -> RetrievalResult:
        """Perform vector similarity search + metadata filtering."""
        # Embed the query
        embedded = await self._embedding.embed(query.text)

        # Search Aurora/pgvector
        raw_chunks = await storage.search_chunks(
            session=session,
            query_embedding=embedded.vector,
            top_k=query.top_k or self._top_k,
            jurisdiction=query.jurisdiction,
            domain=query.domain,
            law_type=query.law_type,
            min_relevance=query.min_relevance or self._min_relevance,
        )

        if not raw_chunks:
            logger.warning(
                "retrieval.no_chunks",
                text=query.text[:100],
                jurisdiction=query.jurisdiction,
                domain=query.domain,
            )
            return RetrievalResult(
                query=query,
                insufficient_context=True,
                insufficient_context_reason=(
                    "No relevant legal documents found in the knowledge base "
                    "matching the query. The legal context may not yet be ingested, "
                    "or the query may fall outside the scope of government legal documents."
                ),
            )

        chunks = [
            RetrievedChunk(
                chunk_id=c["chunk_id"],
                document_id=c["document_id"],
                legal_doc_id=c["legal_doc_id"],
                chunk_index=c["chunk_index"],
                content=c["content"],
                section=c["section"],
                section_ref=c["section_ref"],
                title=c["title"],
                jurisdiction=c["jurisdiction"],
                domain=c["domain"],
                law_type=c["law_type"],
                effective_date=c["effective_date"],
                source_url=c["source_url"],
                similarity=c["similarity"],
                token_count=c["token_count"],
            )
            for c in raw_chunks
        ]

        logger.info(
            "retrieval.done",
            top_k=len(chunks),
            top_similarity=max((c.similarity for c in chunks), default=0),
        )
        return RetrievalResult(query=query, chunks=chunks)

    async def retrieve_for_risk_analysis(
        self,
        situation_description: str,
        session: Any,
        *,
        jurisdiction: str | None = None,
        domain: str | None = None,
    ) -> RetrievalResult:
        """Convenience wrapper for risk analysis queries."""
        query = RetrievalQuery(
            text=situation_description,
            top_k=self._top_k,
            jurisdiction=jurisdiction,
            domain=domain,
            min_relevance=0.35,
        )
        return await self.retrieve(query, session)
