"""Unit tests for the retrieval layer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.retrieval.vector_store import LegalRetriever, RetrievalQuery, RetrievedChunk
from src.embedding.mock import MockEmbeddingProvider


class TestRetrievalQuery:
    def test_retrieval_query_defaults(self):
        q = RetrievalQuery(text="Is GDPR applicable to our data processing?")
        assert q.top_k == 10
        assert q.min_relevance == 0.3
        assert q.jurisdiction is None

    def test_retrieval_query_with_filters(self):
        q = RetrievalQuery(
            text="Breach notification",
            jurisdiction="EU",
            domain="regulatory",
            law_type="GDPR",
            top_k=5,
        )
        assert q.jurisdiction == "EU"
        assert q.law_type == "GDPR"
        assert q.top_k == 5


class TestRetrievedChunk:
    def test_to_source_dict(self):
        chunk = RetrievedChunk(
            chunk_id="chunk-001",
            document_id="doc-uuid-001",
            legal_doc_id="gdpr-art5",
            chunk_index=0,
            content="Article 5: Personal data shall be processed lawfully...",
            section="Principles",
            section_ref="Art. 5",
            title="GDPR Article 5",
            jurisdiction="EU",
            domain="regulatory",
            law_type="GDPR",
            effective_date=None,
            source_url=None,
            similarity=0.95,
            token_count=30,
        )
        source = chunk.to_source_dict()
        assert source["document_id"] == "gdpr-art5"
        assert source["chunk_id"] == "chunk-001"
        assert source["section"] == "GDPR Article 5 — Art. 5"
        assert "Personal data shall be" in source["excerpt"]
        assert source["similarity"] == 0.95


class TestLegalRetriever:
    @pytest.mark.asyncio
    async def test_retrieve_no_chunks_returns_insufficient_context(self):
        mock_embed = MockEmbeddingProvider()
        retriever = LegalRetriever(embedding_provider=mock_embed, top_k=5)
        mock_session = AsyncMock()

        # Mock the storage search to return empty
        with patch(
            "src.storage.aurora.search_chunks",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await retriever.retrieve(
                RetrievalQuery(text="completely obscure query xyz123"),
                session=mock_session,
            )

        assert result.insufficient_context is True
        assert result.insufficient_context_reason is not None
        assert len(result.chunks) == 0

    @pytest.mark.asyncio
    async def test_retrieve_with_chunks(self):
        mock_embed = MockEmbeddingProvider()
        retriever = LegalRetriever(embedding_provider=mock_embed, top_k=5)
        mock_session = AsyncMock()

        raw_chunks = [
            {
                "chunk_id": "c1",
                "document_id": "doc1",
                "chunk_index": 0,
                "content": "GDPR text",
                "section": "Art. 5",
                "section_ref": "Art. 5",
                "token_count": 50,
                "legal_doc_id": "gdpr-2016",
                "title": "GDPR",
                "jurisdiction": "EU",
                "domain": "regulatory",
                "law_type": "GDPR",
                "effective_date": None,
                "source_url": None,
                "similarity": 0.95,
            }
        ]

        with patch(
            "src.storage.aurora.search_chunks",
            new_callable=AsyncMock,
            return_value=raw_chunks,
        ):
            result = await retriever.retrieve(
                RetrievalQuery(text="data minimization"),
                session=mock_session,
            )

        assert result.insufficient_context is False
        assert len(result.chunks) == 1
        assert result.chunks[0].content == "GDPR text"
        assert result.chunks[0].similarity == 0.95

    @pytest.mark.asyncio
    async def test_retrieve_for_risk_analysis_convenience_method(self):
        mock_embed = MockEmbeddingProvider()
        retriever = LegalRetriever(embedding_provider=mock_embed)
        mock_session = AsyncMock()

        with patch(
            "src.storage.aurora.search_chunks",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await retriever.retrieve_for_risk_analysis(
                situation_description="We share user data with third-party advertisers",
                session=mock_session,
                jurisdiction="EU",
            )

        assert result.query.jurisdiction == "EU"
        assert result.query.min_relevance == 0.35
