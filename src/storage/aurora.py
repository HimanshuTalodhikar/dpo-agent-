"""Aurora PostgreSQL + pgvector storage layer."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import asyncpg
import numpy as np
import numpy.typing as npt
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..config import DatabaseSettings

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Engine & session factory
# ──────────────────��──────────────────────────────────────────────────────────

_engine: create_async_engine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine(settings: DatabaseSettings) -> create_async_engine:
    """Get or create the async SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.url,
            pool_size=settings.pool_size,
            max_overflow=settings.max_overflow,
            echo=settings.echo,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory(settings: DatabaseSettings) -> async_sessionmaker[AsyncSession]:
    """Get or create the session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(settings),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


async def get_session() -> AsyncSession | None:
    """Dependency-injectable session accessor."""
    factory = _session_factory
    if factory is None:
        return None
    try:
        return factory()
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Schema initialization
# ─────────────────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Government legal documents metadata
CREATE TABLE IF NOT EXISTS legal_documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     VARCHAR(255) UNIQUE NOT NULL,
    title           TEXT NOT NULL,
    jurisdiction    VARCHAR(100) NOT NULL,   -- e.g. 'EU', 'US-CA', 'US-FEDERAL'
    domain          VARCHAR(100) NOT NULL,   -- e.g. 'regulatory', 'employment', 'contracts'
    law_type        VARCHAR(100) NOT NULL,   -- e.g. 'GDPR', 'CCPA', 'HIPAA'
    effective_date  DATE,
    source_url      TEXT,
    version         VARCHAR(50) DEFAULT '1.0',
    s3_key          TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Legal text chunks with embeddings
CREATE TABLE IF NOT EXISTS legal_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES legal_documents(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    content         TEXT NOT NULL,
    section         VARCHAR(255),
    section_ref     VARCHAR(100),           -- e.g. 'Art. 5', '§ 1798.100'
    embedding       VECTOR({{DIM}}),         -- filled in programmatically
    token_count     INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(document_id, chunk_index)
);

-- Index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_legal_chunks_embedding
    ON legal_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Index for metadata filtering
CREATE INDEX IF NOT EXISTS idx_legal_chunks_doc ON legal_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_legal_documents_jurisdiction ON legal_documents(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_legal_documents_domain ON legal_documents(domain);

-- Audit records
CREATE TABLE IF NOT EXISTS audit_records (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id          VARCHAR(255) UNIQUE NOT NULL,
    decision_id         VARCHAR(255),
    agent_version       VARCHAR(50),
    tool_name           VARCHAR(100) NOT NULL,
    input_hash          VARCHAR(64) NOT NULL,     -- SHA-256 of input
    prompt_hash         VARCHAR(64),              -- SHA-256 of LLM prompt
    retrieved_sources   JSONB DEFAULT '[]',
    output_summary       TEXT,
    exposure_level       VARCHAR(20),
    confidence          FLOAT,
    latency_ms          INTEGER,
    user_id             VARCHAR(255),
    metadata_           JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_request ON audit_records(request_id);
CREATE INDEX IF NOT EXISTS idx_audit_decision ON audit_records(decision_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_records(created_at DESC);
"""


async def init_schema(settings: DatabaseSettings, dimensions: int = 1024) -> None:
    """Create all tables and indexes. Idempotent (IF NOT EXISTS)."""
    engine = get_engine(settings)
    sql = SCHEMA_SQL.replace("{{DIM}}", str(dimensions))

    async with engine.begin() as conn:
        for statement in sql.split(";"):
            stmt = statement.strip()
            if stmt:
                await conn.execute(text(stmt))

    logger.info("aurora.schema_initialized", dimensions=dimensions)


# ─────────────────────────────────────────────────────────────────────────────
# Legal document operations
# ─────────────────────────────────────────────────────────────────────────────

async def upsert_document(
    session: AsyncSession,
    *,
    document_id: str,
    title: str,
    jurisdiction: str,
    domain: str,
    law_type: str,
    effective_date: datetime | None = None,
    source_url: str | None = None,
    version: str = "1.0",
    s3_key: str | None = None,
) -> str:
    """Insert or update a legal document, return its UUID."""
    stmt = text("""
        INSERT INTO legal_documents
            (document_id, title, jurisdiction, domain, law_type, effective_date, source_url, version, s3_key)
        VALUES
            (:document_id, :title, :jurisdiction, :domain, :law_type, :effective_date, :source_url, :version, :s3_key)
        ON CONFLICT (document_id) DO UPDATE SET
            title = EXCLUDED.title,
            jurisdiction = EXCLUDED.jurisdiction,
            domain = EXCLUDED.domain,
            law_type = EXCLUDED.law_type,
            effective_date = EXCLUDED.effective_date,
            source_url = EXCLUDED.source_url,
            version = EXCLUDED.version,
            s3_key = EXCLUDED.s3_key,
            updated_at = NOW()
        RETURNING id
    """)
    row = await session.execute(stmt, {
        "document_id": document_id,
        "title": title,
        "jurisdiction": jurisdiction,
        "domain": domain,
        "law_type": law_type,
        "effective_date": effective_date,
        "source_url": source_url,
        "version": version,
        "s3_key": s3_key,
    })
    return str(row.scalar())


async def get_document_by_doc_id(
    session: AsyncSession,
    document_id: str,
) -> dict[str, Any] | None:
    """Get a document by its logical document_id."""
    stmt = text("""
        SELECT id, document_id, title, jurisdiction, domain, law_type,
               effective_date, source_url, version, s3_key, created_at
        FROM legal_documents
        WHERE document_id = :document_id
    """)
    row = await session.execute(stmt, {"document_id": document_id})
    result = row.fetchone()
    if result is None:
        return None
    return {
        "id": str(result[0]),
        "document_id": result[1],
        "title": result[2],
        "jurisdiction": result[3],
        "domain": result[4],
        "law_type": result[5],
        "effective_date": result[6],
        "source_url": result[7],
        "version": result[8],
        "s3_key": result[9],
        "created_at": result[10],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Chunk operations
# ──────────────────��──────────────────────────────────────────────────────────

async def insert_chunks(
    session: AsyncSession,
    document_uuid: str,
    chunks: list[dict[str, Any]],
    embeddings: list[npt.NDArray[np.float32]],
) -> int:
    """Bulk-insert chunks with their embeddings."""
    assert len(chunks) == len(embeddings), "Chunks and embeddings count mismatch"

    inserted = 0
    for chunk, embedding in zip(chunks, embeddings):
        stmt = text("""
            INSERT INTO legal_chunks
                (document_id, chunk_index, content, section, section_ref, embedding, token_count)
            VALUES
                (:document_id, :chunk_index, :content, :section, :section_ref, :embedding, :token_count)
            ON CONFLICT (document_id, chunk_index) DO UPDATE SET
                content = EXCLUDED.content,
                section = EXCLUDED.section,
                section_ref = EXCLUDED.section_ref,
                embedding = EXCLUDED.embedding,
                token_count = EXCLUDED.token_count
        """)
        await session.execute(stmt, {
            "document_id": document_uuid,
            "chunk_index": chunk["chunk_index"],
            "content": chunk["content"],
            "section": chunk.get("section"),
            "section_ref": chunk.get("section_ref"),
            "embedding": embedding.tolist(),
            "token_count": chunk.get("token_count"),
        })
        inserted += 1

    await session.commit()
    logger.info("aurora.chunks_inserted", document_uuid=document_uuid, count=inserted)
    return inserted


async def search_chunks(
    session: AsyncSession,
    query_embedding: npt.NDArray[np.float32],
    *,
    top_k: int = 10,
    jurisdiction: str | None = None,
    domain: str | None = None,
    law_type: str | None = None,
    min_relevance: float = 0.0,
) -> list[dict[str, Any]]:
    """Vector similarity search over legal chunks with optional metadata filters."""

    # Cosine distance = 1 - cosine_similarity; lower is better
    # We use <= (1 - min_relevance) so higher relevance score passes
    max_distance = 1.0 - min_relevance

    # Build filter subquery
    filter_conditions = []
    params: dict[str, Any] = {
        "embedding": query_embedding.tolist(),
        "top_k": top_k,
        "max_distance": max_distance,
    }

    if jurisdiction:
        filter_conditions.append("d.jurisdiction = :jurisdiction")
        params["jurisdiction"] = jurisdiction
    if domain:
        filter_conditions.append("d.domain = :domain")
        params["domain"] = domain
    if law_type:
        filter_conditions.append("d.law_type = :law_type")
        params["law_type"] = law_type

    filter_sql = ""
    if filter_conditions:
        filter_sql = "WHERE " + " AND ".join(filter_conditions)

    stmt = text(f"""
        WITH filtered_docs AS (
            SELECT id FROM legal_documents d {filter_sql}
        )
        SELECT
            c.id,
            c.document_id,
            c.chunk_index,
            c.content,
            c.section,
            c.section_ref,
            c.token_count,
            d.document_id   AS doc_id,
            d.title,
            d.jurisdiction,
            d.domain,
            d.law_type,
            d.effective_date,
            d.source_url,
            1 - (c.embedding <=> :embedding::vector) AS similarity
        FROM legal_chunks c
        JOIN legal_documents d ON c.document_id = d.id
        WHERE c.document_id IN (SELECT id FROM filtered_docs)
          AND (c.embedding <=> :embedding::vector) <= :max_distance
        ORDER BY c.embedding <=> :embedding::vector
        LIMIT :top_k
    """)

    rows = await session.execute(stmt, params)
    results = []
    for row in rows.fetchall():
        results.append({
            "chunk_id": str(row[0]),
            "document_id": str(row[1]),
            "chunk_index": row[2],
            "content": row[3],
            "section": row[4],
            "section_ref": row[5],
            "token_count": row[6],
            "legal_doc_id": row[7],
            "title": row[8],
            "jurisdiction": row[9],
            "domain": row[10],
            "law_type": row[11],
            "effective_date": row[12],
            "source_url": row[13],
            "similarity": float(row[14]),
        })

    return results
