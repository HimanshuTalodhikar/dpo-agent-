"""
Zep Cloud Agent Memory Service for Government Knowledge Base
=====================================================================
Ingests government documents -> builds temporal knowledge graph -> retrieves relevant context.

Backend: Zep Cloud SDK (zep-cloud 3.28.0)
API: Zep Cloud Context & Graph Memory (graph_id: govt-knowledge-base)

Architecture:
    Document -> parse -> chunk -> azep.graph.add() -> Zep Cloud Graph (nodes/edges/episodes)
    Query -> azep.graph.search() -> Zep Cloud -> SearchResult -> RetrievedChunks -> CLO Agent
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

log = logging.getLogger(__name__)

# -- Configuration (read from env, defaults match .env) ------------------------

ZEP_API_KEY = os.getenv(
    "ZEP_API_KEY",
    "your_zep_api_key_here",
)
ZEP_GRAPH_ID = os.getenv("ZEP_GRAPH_ID", "govt-knowledge-base")

DEFAULT_CHUNK_SIZE = int(os.getenv("ZEP_CHUNK_SIZE", "1000"))
DEFAULT_CHUNK_OVERLAP = int(os.getenv("ZEP_CHUNK_OVERLAP", "200"))


# -- Domain Enums ---------------------------------------------------------------

class DocumentClassification(str, Enum):
    UNCLASSIFIED = "UNCLASSIFIED"
    SENSITIVE = "SENSITIVE"
    CONFIDENTIAL = "CONFIDENTIAL"
    SECRET = "SECRET"


class DocumentType(str, Enum):
    ACT = "ACT"
    RULE = "RULE"
    NOTIFICATION = "NOTIFICATION"
    ORDER = "ORDER"
    GUIDELINE = "GUIDELINE"
    REPORT = "REPORT"
    CIRCULAR = "CIRCULAR"
    REGULATION = "REGULATION"


# -- Domain Models --------------------------------------------------------------

@dataclass
class GovtDocument:
    title: str
    content: str
    doc_type: DocumentType
    classification: DocumentClassification
    doc_id: str
    issuing_authority: str
    effective_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    jurisdiction: str = "central"
    subject_tags: list[str] = field(default_factory=list)
    reference_numbers: list[str] = field(default_factory=list)
    source_uri: str = ""
    content_hash: str = ""
    version: str = "1.0"


@dataclass
class SearchResult:
    content: str
    score: float
    metadata: dict[str, Any]
    source: str  # "episode" | "edge" | "node"


@dataclass
class IngestionResult:
    doc_id: str
    title: str
    chunks_created: int
    episode_ids: list[str]
    ingestion_time_ms: float
    errors: list[str] = field(default_factory=list)


# -- Zep Agent Memory Service ---------------------------------------------------

class GovtGraphRAG:
    """Government knowledge base powered by Zep Cloud Agent Memory."""

    def __init__(
        self,
        api_key: str = ZEP_API_KEY,
        graph_id: str = ZEP_GRAPH_ID,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        **kwargs: Any,
    ):
        self.api_key = api_key
        self.graph_id = graph_id
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._async_client: Any | None = None

    async def _get_client(self):
        """Lazily initialize and return AsyncZep client."""
        if self._async_client is not None:
            return self._async_client

        if not self.api_key:
            raise ValueError("ZEP_API_KEY is required to connect to Zep Cloud.")

        from zep_cloud.client import AsyncZep

        log.info("Initializing AsyncZep client for graph_id=%s", self.graph_id)
        self._async_client = AsyncZep(api_key=self.api_key)

        # Verify or create graph
        try:
            await self._async_client.graph.get(self.graph_id)
            log.info("Zep Cloud Graph '%s' verified", self.graph_id)
        except Exception:
            try:
                await self._async_client.graph.create(
                    graph_id=self.graph_id,
                    name="Government Knowledge Base",
                    description="Government Knowledge Base - Temporal Context Graph",
                )
                log.info("Created Zep Cloud Graph '%s'", self.graph_id)
            except Exception as e:
                log.debug("Zep Cloud Graph create info: %s", e)

        return self._async_client

    async def close(self) -> None:
        """Cleanup client reference."""
        self._async_client = None
        log.info("Zep client connection closed")

    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> list[dict[str, Any]]:
        """Split text into overlapping character-based chunks."""
        chunks = []
        start = 0
        index = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({"content": chunk_text, "chunk_index": index})
            start += chunk_size - overlap
            index += 1
        return chunks

    async def ingest_document(
        self,
        doc: GovtDocument,
        chunk_size: int | None = None,
        *,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> IngestionResult:
        """Ingest a government document into Zep Cloud Agent Memory."""
        cs = chunk_size or self.chunk_size
        start_ts = time.monotonic()
        errors: list[str] = []
        episode_ids: list[str] = []

        log.info("ingestion.start doc_id=%s title=%r", doc.doc_id, doc.title[:80])

        try:
            azep = await self._get_client()

            header = (
                f"Document: {doc.title}\n"
                f"Type: {doc.doc_type.value} | Classification: {doc.classification.value}\n"
                f"Authority: {doc.issuing_authority}\n"
                f"Effective: {doc.effective_date.strftime('%Y-%m-%d')}\n"
                f"Jurisdiction: {doc.jurisdiction}\n"
            )
            if doc.source_uri:
                header += f"Source: {doc.source_uri}\n"
            header += "-" * 60 + "\n"

            source_description = (
                f"{doc.doc_type.value}: {doc.title} "
                f"(issued by {doc.issuing_authority}, "
                f"{doc.effective_date.strftime('%Y-%m-%d')})"
            )

            chunks = self._chunk_text(doc.content, cs, self.chunk_overlap)
            log.info("ingestion.chunked doc_id=%s chunks=%d", doc.doc_id, len(chunks))

            for chunk in chunks:
                chunk_name = f"{doc.doc_id}-chunk-{chunk['chunk_index']}"
                chunk_body = f"{header}{chunk['content']}"

                for attempt in range(max_retries):
                    try:
                        log.debug(
                            "ingestion.episode_start name=%s attempt=%d",
                            chunk_name, attempt + 1,
                        )
                        episode = await azep.graph.add(
                            graph_id=self.graph_id,
                            type="text",
                            data=chunk_body,
                            source_description=source_description,
                            metadata={
                                "doc_id": doc.doc_id,
                                "chunk_index": chunk["chunk_index"],
                                "title": doc.title,
                                "doc_type": doc.doc_type.value,
                                "issuing_authority": doc.issuing_authority,
                            },
                        )
                        episode_uuid = str(getattr(episode, "uuid_", getattr(episode, "id", chunk_name)))
                        episode_ids.append(episode_uuid)
                        log.debug(
                            "ingestion.episode_done name=%s uuid=%s",
                            chunk_name, episode_uuid,
                        )
                        break

                    except Exception as e:
                        if attempt < max_retries - 1:
                            wait = retry_delay * (2 ** attempt)
                            log.warning(
                                "ingestion.retry chunk=%s attempt=%d error=%s wait=%.1fs",
                                chunk_name, attempt + 1, e, wait,
                            )
                            await asyncio.sleep(wait)
                        else:
                            err = f"Chunk {chunk['chunk_index']} failed after {max_retries} retries: {e}"
                            log.error("ingestion.chunk_failed %s", err)
                            errors.append(err)

        except Exception as e:
            err = f"Document ingestion failed for '{doc.title}': {e}"
            log.exception("ingestion.document_error doc_id=%s", doc.doc_id)
            errors.append(err)

        elapsed_ms = (time.monotonic() - start_ts) * 1000
        log.info(
            "ingestion.complete doc_id=%s chunks_ok=%d errors=%d elapsed_ms=%.0f",
            doc.doc_id, len(episode_ids), len(errors), elapsed_ms,
        )
        return IngestionResult(
            doc_id=doc.doc_id,
            title=doc.title,
            chunks_created=len(episode_ids),
            episode_ids=episode_ids,
            ingestion_time_ms=elapsed_ms,
            errors=errors,
        )

    async def search(
        self,
        query: str,
        scope: str = "auto",
        limit: int = 10,
        filters: dict[str, Any] | None = None,
        group_ids: list[str] | None = None,
    ) -> list[SearchResult]:
        """Search Zep Cloud Agent Memory graph."""
        azep = await self._get_client()
        log.info("retrieval.start query=%r limit=%d", query[:100], limit)

        # Truncate query to comply with Zep Cloud's max 400 character limit
        search_query = query.strip()[:350]

        try:
            res = await azep.graph.search(
                graph_id=self.graph_id,
                query=search_query,
                limit=limit,
            )

            results: list[SearchResult] = []

            # 1. Process Edges (facts / relationships)
            if hasattr(res, "edges") and res.edges:
                for e in res.edges:
                    fact = getattr(e, "fact", "") or getattr(e, "name", "")
                    score = float(getattr(e, "score", 0.0) or 0.0)
                    uuid_str = str(getattr(e, "uuid_", getattr(e, "id", "")))
                    name_str = getattr(e, "name", "")
                    results.append(
                        SearchResult(
                            content=fact,
                            score=score,
                            metadata={"uuid": uuid_str, "name": name_str, "type": "edge"},
                            source="edge",
                        )
                    )

            # 2. Process Episodes
            if hasattr(res, "episodes") and res.episodes:
                for ep in res.episodes:
                    content = getattr(ep, "content", "") or getattr(ep, "data", "")
                    score = float(getattr(ep, "score", 0.0) or 0.0)
                    uuid_str = str(getattr(ep, "uuid_", getattr(ep, "id", "")))
                    source_desc = getattr(ep, "source_description", "")
                    results.append(
                        SearchResult(
                            content=content,
                            score=score,
                            metadata={"uuid": uuid_str, "source_description": source_desc, "type": "episode"},
                            source="episode",
                        )
                    )

            # 3. Process Nodes
            if hasattr(res, "nodes") and res.nodes:
                for n in res.nodes:
                    name = getattr(n, "name", "")
                    summary = getattr(n, "summary", "")
                    content = f"{name}: {summary}" if summary else name
                    score = float(getattr(n, "score", 0.0) or 0.0)
                    uuid_str = str(getattr(n, "uuid_", getattr(n, "id", "")))
                    results.append(
                        SearchResult(
                            content=content,
                            score=score,
                            metadata={"uuid": uuid_str, "name": name, "type": "node"},
                            source="node",
                        )
                    )

            # Sort by score descending
            results.sort(key=lambda r: r.score, reverse=True)
            log.info("retrieval.done results=%d", len(results))
            return results[:limit]

        except Exception as e:
            log.error("retrieval.error query=%r error=%s", query[:100], e)
            return []

    async def get_graph_stats(self) -> dict[str, Any]:
        """Return high-level stats about the Zep Cloud Agent Memory graph."""
        try:
            azep = await self._get_client()
            g = await azep.graph.get(self.graph_id)
            return {
                "graph_id": getattr(g, "graph_id", self.graph_id),
                "name": getattr(g, "name", "Government Knowledge Base"),
                "description": getattr(g, "description", ""),
                "status": "connected",
                "provider": "Zep Cloud Agent Memory",
            }
        except Exception as e:
            return {"error": str(e), "status": "disconnected"}


# -- Synchronous wrapper --------------------------------------------------------

class SyncGovtGraphRAG:
    """Synchronous wrapper around async GovtGraphRAG."""

    def __init__(self, **kwargs):
        self._async = GovtGraphRAG(**kwargs)

    @property
    def graph_id(self) -> str:
        return self._async.graph_id

    def ingest_document(self, doc: GovtDocument, chunk_size: int | None = None) -> IngestionResult:
        return asyncio.run(self._async.ingest_document(doc, chunk_size))

    def search(
        self,
        query: str,
        scope: str = "auto",
        limit: int = 10,
        filters: dict | None = None,
        group_ids: list[str] | None = None,
    ) -> list[SearchResult]:
        return asyncio.run(self._async.search(query, scope, limit, filters, group_ids))

    def get_graph_stats(self) -> dict[str, Any]:
        return asyncio.run(self._async.get_graph_stats())

    def close(self) -> None:
        asyncio.run(self._async.close())


# -- Factory functions ----------------------------------------------------------

def get_graphrag_service(
    api_key: str = ZEP_API_KEY,
    graph_id: str = ZEP_GRAPH_ID,
    sync: bool = False,
    **kwargs,
) -> GovtGraphRAG | SyncGovtGraphRAG:
    """Factory function for the Zep graph service."""
    if sync:
        return SyncGovtGraphRAG(
            api_key=api_key,
            graph_id=graph_id,
            **kwargs,
        )
    return GovtGraphRAG(
        api_key=api_key,
        graph_id=graph_id,
        **kwargs,
    )


def get_sync_graphrag_service(**kwargs) -> SyncGovtGraphRAG:
    """Return a synchronous GovtGraphRAG wrapper."""
    return get_graphrag_service(sync=True, **kwargs)  # type: ignore[return-value]


# -- Retriever Adapter ----------------------------------------------------------

from ..retrieval.vector_store import (
    LegalRetriever,
    RetrievalQuery,
    RetrievalResult,
    RetrievedChunk,
)


class ZepRetrieverAdapter(LegalRetriever):
    """Adapts Zep Cloud Agent Memory (GovtGraphRAG) to the LegalRetriever interface."""

    def __init__(
        self,
        graph_service: GovtGraphRAG,
        *,
        top_k: int = 10,
        min_relevance: float = 0.0,
    ) -> None:
        self._graph = graph_service
        self._top_k = top_k
        self._min_relevance = min_relevance

    async def retrieve(
        self,
        query: RetrievalQuery,
        session: Any = None,
    ) -> RetrievalResult:
        """Perform search using Zep Cloud Agent Memory."""
        limit = max(query.top_k, self._top_k)
        log.info("zep_retriever.retrieve query=%r limit=%d", query.text[:80], limit)

        results = await self._graph.search(
            query=query.text,
            scope="auto",
            limit=limit,
        )

        chunks: list[RetrievedChunk] = []
        for r in results:
            if r.score < self._min_relevance:
                continue
            doc_id = r.metadata.get("doc_id", "")
            chunks.append(
                RetrievedChunk(
                    chunk_id=r.metadata.get("uuid", str(uuid4())),
                    document_id=doc_id,
                    legal_doc_id=doc_id,
                    chunk_index=0,
                    content=r.content,
                    section=r.metadata.get("name", ""),
                    section_ref=None,
                    title=r.metadata.get("name", ""),
                    jurisdiction="",
                    domain="",
                    law_type="",
                    effective_date=None,
                    source_url=r.metadata.get("source_description", ""),
                    similarity=r.score,
                    token_count=None,
                )
            )

        if not chunks:
            return RetrievalResult(
                query=query,
                chunks=[],
                insufficient_context=True,
                insufficient_context_reason=(
                    "No relevant results found in Zep Agent Memory. "
                    "Documents may not be ingested yet, or the query may fall outside "
                    "the scope of ingested government documents."
                ),
            )

        log.info("zep_retriever.done chunks=%d", len(chunks))
        return RetrievalResult(query=query, chunks=chunks)

    async def retrieve_for_risk_analysis(
        self,
        situation_description: str,
        session: Any = None,
        *,
        jurisdiction: str | None = None,
        domain: str | None = None,
    ) -> RetrievalResult:
        """Convenience wrapper for risk analysis queries."""
        q = RetrievalQuery(
            text=situation_description,
            top_k=self._top_k,
            jurisdiction=jurisdiction,
            domain=domain,
            min_relevance=self._min_relevance,
        )
        return await self.retrieve(q, session)

    async def close(self) -> None:
        """Close the underlying Zep connection."""
        await self._graph.close()


# Backward compatibility alias
GraphitiRetrieverAdapter = ZepRetrieverAdapter
