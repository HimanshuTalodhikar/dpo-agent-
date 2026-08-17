"""Full document ingestion pipeline: parse → chunk → embed → store."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from ..config import AppSettings
from ..embedding.base import EmbeddingProvider
from ..storage import aurora as storage
from .chunker import LegalChunker
from .parser import extract_metadata_from_filename, parse_document

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)


class IngestionPipeline:
    """End-to-end document ingestion pipeline.

    Run: parse → chunk → embed → store to Aurora + S3
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        chunker: LegalChunker | None = None,
    ) -> None:
        self._embedding = embedding_provider
        self._chunker = chunker or LegalChunker()

    async def ingest_file(
        self,
        file_path: str | Path,
        session: Any,  # AsyncSession
        *,
        document_id: str | None = None,
        s3_client: Any | None = None,
        title: str | None = None,
        jurisdiction: str | None = None,
        domain: str | None = None,
        law_type: str | None = None,
        effective_date: str | None = None,
        source_url: str | None = None,
    ) -> dict[str, Any]:
        """Ingest a single file end-to-end."""
        path = Path(file_path)
        document_id = document_id or path.stem

        logger.info("ingestion.start", document_id=document_id, path=str(path))

        # 1. Parse
        text = await parse_document(path)
        if not text.strip():
            raise ValueError(f"Document {path} produced no text content")

        # 2. Chunk
        chunks = self._chunker.chunk_text(text)
        logger.debug("ingestion.chunked", document_id=document_id, chunks=len(chunks))

        # 3. Embed
        chunk_texts = [c.content for c in chunks]
        embedded = await self._embedding.embed_batch(chunk_texts)

        # 4. Metadata
        inferred = extract_metadata_from_filename(path.name)
        doc_metadata = {
            "document_id": document_id,
            "title": title or inferred.get("title") or path.stem,
            "jurisdiction": jurisdiction or inferred.get("jurisdiction", "UNKNOWN"),
            "domain": domain or inferred.get("domain", "general"),
            "law_type": law_type or inferred.get("law_type", "UNKNOWN"),
            "effective_date": effective_date or inferred.get("effective_date"),
            "source_url": source_url,
            "version": "1.0",
        }

        # 5. Store document metadata
        doc_uuid = await storage.upsert_document(session, **doc_metadata)

        # 6. Store chunks
        chunk_dicts = [
            {
                "chunk_index": c.chunk_index,
                "content": c.content,
                "section": c.section,
                "section_ref": c.section_ref,
                "token_count": c.token_count,
            }
            for c in chunks
        ]
        embeddings = [e.vector for e in embedded]
        inserted = await storage.insert_chunks(session, doc_uuid, chunk_dicts, embeddings)

        # 7. Upload raw file to S3 (if client provided)
        s3_key = None
        if s3_client is not None:
            raw_content = path.read_bytes()
            s3_key = await s3_client.upload_document(
                document_id=document_id,
                filename=path.name,
                content=raw_content,
                content_type="text/plain",
                metadata={"document_id": document_id, "version": "1.0"},
            )

        logger.info(
            "ingestion.complete",
            document_id=document_id,
            doc_uuid=doc_uuid,
            chunks=inserted,
            s3_key=s3_key,
        )

        return {
            "document_id": document_id,
            "doc_uuid": doc_uuid,
            "chunks_ingested": inserted,
            "s3_key": s3_key,
        }


async def ingest_sample_documents() -> dict[str, Any]:
    """Ingest all sample government documents.

    Called automatically on docker-compose startup if INGEST_SAMPLE_DOCS=true.
    """
    from ..config import get_settings
    from ..llm.mock import MockEmbeddingProvider
    from ..storage.aurora import get_session

    settings = get_settings()
    session = await get_session()

    # Use mock embedding for ingestion (works without real Bedrock)
    embed_provider = MockEmbeddingProvider(dimensions=settings.embedding.dimensions)
    pipeline = IngestionPipeline(embedding_provider=embed_provider)

    sample_dir = Path(__file__).parent.parent.parent / "sample_docs"
    results = []

    for root, dirs, files in os.walk(sample_dir):
        for filename in sorted(files):
            if not filename.endswith(".txt"):
                continue
            file_path = Path(root) / filename
            try:
                result = await pipeline.ingest_file(
                    file_path=file_path,
                    session=session,
                )
                results.append(result)
            except Exception as exc:
                logger.warning("ingestion.skip", path=str(file_path), reason=str(exc))

    await session.commit()
    return {"ingested": results}
