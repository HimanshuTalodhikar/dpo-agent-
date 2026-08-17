"""
Event-Driven S3 Ingestion Service.
=================================
Automates fetching PDFs from Amazon S3 upon S3 ObjectCreated events or direct upload,
extracting document text and metadata, and ingesting document chunks into Zep Cloud Agent Memory.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pypdf
import structlog

from ..config import get_settings
from ..storage.s3_client import S3DocumentStore
from .zep_graphrag import (
    DocumentClassification,
    DocumentType,
    GovtDocument,
    GovtGraphRAG,
    IngestionResult,
    get_graphrag_service,
)

logger = structlog.get_logger(__name__)


# ── Metadata Inference ────────────────────────────────────────────────────────

DOC_TYPE_MAP = {
    "cert": DocumentType.REGULATION,
    "dpdp": DocumentType.RULE,
    "it_act": DocumentType.ACT,
    "sdpi": DocumentType.REPORT,
    "rules": DocumentType.RULE,
}
CLASSIFICATION_MAP = {
    "cert": DocumentClassification.SENSITIVE,
    "dpdp": DocumentClassification.UNCLASSIFIED,
    "it_act": DocumentClassification.UNCLASSIFIED,
    "sdpi": DocumentClassification.UNCLASSIFIED,
    "rules": DocumentClassification.UNCLASSIFIED,
}
AUTHORITY_MAP = {
    "cert": "Indian Computer Emergency Response Team (CERT-In)",
    "dpdp": "Ministry of Electronics & Information Technology",
    "it_act": "Parliament of India",
    "sdpi": "National Institute of Public Finance and Policy",
    "rules": "Ministry of Electronics & Information Technology",
}


def infer_doc_metadata(filename: str) -> tuple[DocumentType, DocumentClassification, str, str]:
    """Infer document metadata from filename."""
    fname_lower = filename.lower()
    for key, dtype in DOC_TYPE_MAP.items():
        if key in fname_lower:
            return (
                dtype,
                CLASSIFICATION_MAP[key],
                AUTHORITY_MAP[key],
                "central",
            )
    return (
        DocumentType.REPORT,
        DocumentClassification.UNCLASSIFIED,
        "Unknown Authority",
        "central",
    )


def extract_pdf_pages(file_path: Path) -> list[tuple[int, str]]:
    """Extract page text from PDF."""
    pages = []
    reader = pypdf.PdfReader(file_path)
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if len(text.strip()) >= 30:
            pages.append((i, text))
    return pages


class S3EventIngestor:
    """Event-driven ingestor that downloads PDFs from S3 and loads them into Zep Cloud."""

    def __init__(
        self,
        s3_store: S3DocumentStore | None = None,
        graph_rag: GovtGraphRAG | None = None,
    ) -> None:
        self._s3_store = s3_store
        self._graph_rag = graph_rag

    def _get_s3_store(self) -> S3DocumentStore:
        if self._s3_store is None:
            settings = get_settings()
            self._s3_store = S3DocumentStore(
                bucket=settings.s3.bucket,
                region=settings.s3.region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                endpoint_url=settings.s3.endpoint_url,
            )
        return self._s3_store

    def _get_graph_rag(self) -> GovtGraphRAG:
        if self._graph_rag is None:
            self._graph_rag = get_graphrag_service()
        return self._graph_rag

    async def process_s3_object(
        self,
        bucket: str,
        key: str,
        *,
        document_id: str | None = None,
    ) -> IngestionResult:
        """Download document from S3 by bucket + key and ingest into Zep Cloud Agent Memory."""
        filename = Path(key).name
        doc_id = document_id or f"doc-{Path(key).stem.replace(' ', '-').replace('_', '-')}"

        logger.info("s3_ingestor.start", bucket=bucket, key=key, doc_id=doc_id)

        # 1. Download file from S3
        s3 = self._get_s3_store()
        file_bytes = await s3.download_document(key)

        # 2. Extract text in temporary file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = Path(tmp.name)

        try:
            pages = extract_pdf_pages(tmp_path)
            if not pages:
                raise ValueError(f"No extractable text found in S3 document {key}")

            full_text = "\n\n".join(f"[Page {pn}] {t}" for pn, t in pages)
            dtype, classification, authority, jurisdiction = infer_doc_metadata(filename)

            # 3. Construct GovtDocument
            govt_doc = GovtDocument(
                title=filename.replace(".pdf", ""),
                content=full_text,
                doc_type=dtype,
                classification=classification,
                doc_id=doc_id,
                issuing_authority=authority,
                effective_date=datetime.now(timezone.utc),
                jurisdiction=jurisdiction,
                subject_tags=[dtype.value.lower(), jurisdiction, "s3-automated-ingestion"],
            )

            # 4. Ingest into Zep Cloud Agent Memory
            rag = self._get_graph_rag()
            result = await rag.ingest_document(govt_doc)

            logger.info(
                "s3_ingestor.complete",
                doc_id=doc_id,
                chunks_created=result.chunks_created,
                ingestion_time_ms=result.ingestion_time_ms,
            )
            return result

        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    async def handle_s3_event(self, s3_event_payload: dict[str, Any]) -> list[IngestionResult]:
        """Handle standard AWS S3 ObjectCreated event payload containing 'Records' array."""
        records = s3_event_payload.get("Records", [])
        results = []

        for record in records:
            s3_info = record.get("s3", {})
            bucket = s3_info.get("bucket", {}).get("name")
            key = s3_info.get("object", {}).get("key")

            if not bucket or not key:
                logger.warning("s3_ingestor.skip_record", record=record, reason="Missing bucket or key")
                continue

            if not key.lower().endswith(".pdf"):
                logger.info("s3_ingestor.skip_non_pdf", key=key)
                continue

            res = await self.process_s3_object(bucket, key)
            results.append(res)

        return results
