"""
Integration tests for Zep Cloud Agent Memory layer.
=====================================================================
These tests verify Zep Cloud Agent Memory integration.
"""

from __future__ import annotations

import os
import pytest
import asyncio
import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

log = logging.getLogger(__name__)

from src.services.zep_graphrag import (
    GovtDocument,
    DocumentType,
    DocumentClassification,
    GovtGraphRAG,
    SyncGovtGraphRAG,
    SearchResult,
    IngestionResult,
    ZepRetrieverAdapter,
    GraphitiRetrieverAdapter,
    get_graphrag_service,
    get_sync_graphrag_service,
)


class TestGovtDocument:
    """Test GovtDocument dataclass."""

    def test_defaults(self):
        doc = GovtDocument(
            title="Test Act",
            content="Some content",
            doc_type=DocumentType.ACT,
            classification=DocumentClassification.UNCLASSIFIED,
            doc_id="test-001",
            issuing_authority="Test Authority",
        )
        assert doc.jurisdiction == "central"
        assert doc.subject_tags == []
        assert doc.reference_numbers == []
        assert doc.source_uri == ""
        assert doc.version == "1.0"

    def test_all_document_types_valid(self):
        for doc_type in DocumentType:
            doc = GovtDocument(
                title="Test",
                content="Content",
                doc_type=doc_type,
                classification=DocumentClassification.UNCLASSIFIED,
                doc_id="id",
                issuing_authority="Auth",
            )
            assert doc.doc_type == doc_type

    def test_all_classifications_valid(self):
        for cls in DocumentClassification:
            doc = GovtDocument(
                title="Test",
                content="Content",
                doc_type=DocumentType.ACT,
                classification=cls,
                doc_id="id",
                issuing_authority="Auth",
            )
            assert doc.classification == cls


class TestIngestionResult:
    """Test IngestionResult dataclass."""

    def test_defaults(self):
        r = IngestionResult(
            doc_id="doc-001",
            title="Test",
            chunks_created=5,
            episode_ids=["ep1", "ep2"],
            ingestion_time_ms=1234.5,
        )
        assert r.errors == []

    def test_with_errors(self):
        r = IngestionResult(
            doc_id="doc-001",
            title="Test",
            chunks_created=3,
            episode_ids=["ep1"],
            ingestion_time_ms=500.0,
            errors=["Chunk 2 failed: timeout"],
        )
        assert len(r.errors) == 1


class TestGovtGraphRAGConfig:
    """Test GovtGraphRAG configuration validation."""

    @pytest.mark.asyncio
    async def test_missing_api_key_raises(self):
        service = GovtGraphRAG(api_key="")
        with pytest.raises(ValueError, match="ZEP_API_KEY"):
            await service._get_client()


class TestChunking:
    """Test text chunking logic."""

    def test_chunks_long_text(self):
        service = GovtGraphRAG(api_key="sk-test", chunk_size=100, chunk_overlap=20)
        text = "A" * 250
        chunks = service._chunk_text(text, chunk_size=100, overlap=20)
        assert len(chunks) >= 3
        for c in chunks:
            assert "content" in c
            assert "chunk_index" in c

    def test_chunk_indices_sequential(self):
        service = GovtGraphRAG(api_key="sk-test")
        text = "Hello world " * 100
        chunks = service._chunk_text(text, chunk_size=200, overlap=50)
        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_empty_text_no_chunks(self):
        service = GovtGraphRAG(api_key="sk-test")
        chunks = service._chunk_text("", chunk_size=100, overlap=20)
        assert chunks == []


class TestZepRetrieverAdapter:
    """Test the retriever adapter with mocked graph service."""

    @pytest.mark.asyncio
    async def test_retrieve_returns_chunks(self):
        mock_graph = AsyncMock()
        mock_graph.search.return_value = [
            SearchResult(
                content="The DPDP Act requires data fiduciaries to...",
                score=0.92,
                metadata={"uuid": "ep-001", "doc_id": "DPDP-2023", "name": "Data Protection"},
                source="edge",
            ),
            SearchResult(
                content="Penalty up to Rs. 250 crore for breach.",
                score=0.78,
                metadata={"uuid": "ep-002", "doc_id": "DPDP-2023"},
                source="episode",
            ),
        ]

        from src.retrieval.vector_store import RetrievalQuery
        adapter = ZepRetrieverAdapter(mock_graph, top_k=5)
        query = RetrievalQuery(text="data protection penalties", top_k=5)
        result = await adapter.retrieve(query, session=None)

        assert not result.insufficient_context
        assert len(result.chunks) == 2
        assert result.chunks[0].similarity == 0.92
        assert result.chunks[0].content == "The DPDP Act requires data fiduciaries to..."
        assert result.chunks[0].document_id == "DPDP-2023"

    @pytest.mark.asyncio
    async def test_retrieve_empty_returns_insufficient_context(self):
        mock_graph = AsyncMock()
        mock_graph.search.return_value = []

        from src.retrieval.vector_store import RetrievalQuery
        adapter = ZepRetrieverAdapter(mock_graph, top_k=5)
        query = RetrievalQuery(text="some obscure query", top_k=5)
        result = await adapter.retrieve(query, session=None)

        assert result.insufficient_context
        assert result.chunks == []
        assert result.insufficient_context_reason is not None


class TestLiveZepIntegration:
    """Live integration tests against Zep Cloud."""

    @pytest.mark.asyncio
    async def test_graph_stats_connected(self):
        service = get_graphrag_service()
        stats = await service.get_graph_stats()
        assert stats.get("status") == "connected", f"Expected connected, got: {stats}"
        await service.close()

    @pytest.mark.asyncio
    async def test_search_zep_agent_memory(self):
        service = get_graphrag_service()
        results = await service.search("data breach penalties CERT-In", limit=5)
        assert isinstance(results, list)
        assert len(results) > 0, "Should return results from Zep memory"
        await service.close()
