"""
Unit tests for Event-Driven S3 Ingestion Service & Webhook endpoints.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.services.s3_ingestor import S3EventIngestor, infer_doc_metadata
from src.services.zep_graphrag import DocumentClassification, DocumentType, IngestionResult


def test_infer_doc_metadata():
    """Verify metadata inference from various PDF filenames."""
    dtype, classification, authority, jurisdiction = infer_doc_metadata("CERT-In_Directions_2022.pdf")
    assert dtype == DocumentType.REGULATION
    assert classification == DocumentClassification.SENSITIVE
    assert "CERT-In" in authority
    assert jurisdiction == "central"

    dtype2, classification2, authority2, jurisdiction2 = infer_doc_metadata("DPDP_Rules_2025.pdf")
    assert dtype2 == DocumentType.RULE
    assert classification2 == DocumentClassification.UNCLASSIFIED

    dtype3, _, authority3, _ = infer_doc_metadata("it_act_2000_updated.pdf")
    assert dtype3 == DocumentType.ACT
    assert "Parliament" in authority3


@pytest.mark.asyncio
async def test_s3_event_handler_payload():
    """Test parsing standard AWS S3 ObjectCreated event notification."""
    mock_s3_store = MagicMock()
    mock_s3_store.download_document = AsyncMock(return_value=b"%PDF-1.4 Mock PDF binary content")

    mock_graph_rag = MagicMock()
    mock_graph_rag.ingest_document = AsyncMock(
        return_value=IngestionResult(
            doc_id="doc-DPDP-Rules-2025",
            title="DPDP-Rules-2025",
            chunks_created=12,
            episode_ids=["ep1", "ep2"],
            ingestion_time_ms=120.0,
            errors=[],
        )
    )

    ingestor = S3EventIngestor(s3_store=mock_s3_store, graph_rag=mock_graph_rag)

    # Standard AWS S3 notification payload
    s3_event_payload = {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "awsRegion": "ap-south-1",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {"name": "clo-legal-docs-bucket"},
                    "object": {"key": "incoming/DPDP_Rules_2025.pdf"},
                },
            }
        ]
    }

    with patch("src.services.s3_ingestor.extract_pdf_pages", return_value=[(1, "Rule text for testing DPDP Rules 2025 breach notification. " * 5)]):
        results = await ingestor.handle_s3_event(s3_event_payload)

    assert len(results) == 1
    assert results[0].doc_id == "doc-DPDP-Rules-2025"
    assert results[0].chunks_created == 12
    assert mock_s3_store.download_document.called
    assert mock_graph_rag.ingest_document.called


def test_s3_webhook_api_endpoint():
    """Test FastAPI /api/v1/ingest/s3-file endpoint."""
    client = TestClient(app)

    with patch("src.services.s3_ingestor.S3EventIngestor.process_s3_object", new_callable=AsyncMock) as mock_process:
        mock_process.return_value = IngestionResult(
            doc_id="doc-cert-in-faq",
            title="CERT-In FAQ",
            chunks_created=8,
            episode_ids=["ep10"],
            ingestion_time_ms=85.5,
            errors=[],
        )

        response = client.post(
            "/api/v1/ingest/s3-file",
            json={"bucket": "clo-legal-docs", "key": "cert_faq.pdf", "document_id": "doc-cert-in-faq"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"]["doc_id"] == "doc-cert-in-faq"
        assert data["result"]["chunks_created"] == 8
